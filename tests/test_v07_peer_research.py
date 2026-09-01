import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from _industry import classify_industry  # noqa: E402
from _peer_analysis import build_peer_research  # noqa: E402
from _peer_comparability import candidate_for  # noqa: E402
from _peer_metrics import peer_aggregates  # noqa: E402
from _peer_report import render_peer_markdown  # noqa: E402
from _report_format import render_markdown  # noqa: E402
from _report_model import build_report  # noqa: E402


def test_explicit_peer_set_is_preserved() -> None:
    result = build_peer_research(company("NVDA"), [company("AMD"), company("AVGO")])

    assert result["peer_set"]["selection_mode"] == "explicit"
    assert [item["ticker"] for item in result["peer_set"]["candidates"]] == ["AMD", "AVGO"]


def test_automatic_peer_candidates_are_conservative() -> None:
    result = build_peer_research(company("NVDA"), [])

    assert result["peer_set"]["selection_mode"] == "automatic"
    assert [item["ticker"] for item in result["peer_set"]["candidates"]] == ["AMD", "AVGO", "INTC"]
    assert result["peer_set"]["quality"] in {"MEDIUM", "LOW"}


def test_industry_classification_uses_sic_and_description() -> None:
    result = classify_industry(company("NVDA"))

    assert result["industry"] == "Semiconductors"
    assert result["sic"] == "3674"
    assert result["confidence"] == "HIGH"


def test_weak_classification_warning_when_only_sic_is_known() -> None:
    payload = company("TEST")
    payload["business_description"] = ""
    payload["segments"] = []

    result = classify_industry(payload)

    assert result["confidence"] == "MEDIUM"
    assert "INDUSTRY_CLASSIFICATION_WEAK" in result["warnings"]


def test_comparability_scoring_is_explainable() -> None:
    result = candidate_for(company("NVDA"), company("AMD"), "explicit")

    assert result["comparability_score"] >= 70
    assert result["comparability_status"] in {"HIGHLY_COMPARABLE", "COMPARABLE"}
    assert result["classification_match"] == "same_industry"


def test_peer_set_quality_warns_for_small_sets() -> None:
    result = build_peer_research(company("NVDA"), [company("AMD")])

    assert result["peer_set"]["quality"] == "LOW"
    assert "PEER_SET_TOO_SMALL" in result["warnings"]


def test_basis_mismatch_excludes_peer_metric_from_aggregate() -> None:
    peer = company("AMD")
    peer["fact_metadata"]["eps"] = {"basis": "ttm"}
    result = build_peer_research(company("NVDA"), [peer, company("AVGO")])

    pe = next(item for item in result["peer_aggregates"] if item["metric"] == "pe")
    assert pe["peer_count"] == 1
    assert "PEER_METRIC_BASIS_MISMATCH" in result["warnings"]


def test_peer_median_premium_discount_and_percentile() -> None:
    result = peer_aggregates(
        company_metrics(company("NVDA"), pe="45"),
        [company_metrics(company("AMD"), pe="30"), company_metrics(company("AVGO"), pe="35")],
    )

    pe = next(item for item in result["aggregates"] if item["metric"] == "pe")
    assert pe["peer_median"] == "32.5"
    assert pe["premium_percent"] == "38.5"
    assert pe["percentile"] == 100


def test_premium_supported_and_unsupported() -> None:
    supported = build_peer_research(company("NVDA"), [company("AMD"), company("AVGO")])
    weak = company("NVDA")
    weak["net_income"] = "50"
    weak["free_cash_flow"] = "60"
    unsupported = build_peer_research(weak, [company("AMD"), company("AVGO")])

    assert supported["premium_justification"]["status"] in {
        "PREMIUM_SUPPORTED",
        "PREMIUM_PARTIALLY_SUPPORTED",
    }
    assert unsupported["premium_justification"]["status"] == "PREMIUM_NOT_SUPPORTED"


def test_segment_non_comparability_is_reported() -> None:
    result = build_peer_research(company("WMT"), [company("COST")])

    assert "SEGMENT_NOT_COMPARABLE" in result["warnings"]


def test_industry_signal_requires_two_companies() -> None:
    one = build_peer_research(company("NVDA", risk="supply constraints"), [company("AMD")])
    two = build_peer_research(
        company("NVDA", risk="supply constraints"),
        [company("AMD", risk="supply constraints")],
    )

    assert one["industry_changes"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert two["industry_changes"]["status"] in {"EMERGING", "PERSISTENT"}


def test_earnings_and_valuation_intelligence_are_integrated() -> None:
    result = build_peer_research(
        company("NVDA"),
        [company("AMD")],
        earnings_context={"thesis_change": {"status": "STRENGTHENED"}},
    )

    assert result["earnings_context"]["thesis_change"]["status"] == "STRENGTHENED"
    assert "required_fcf_cagr" in result["company_metrics"]["required_fcf_growth"]


def test_korean_and_english_peer_reports_render() -> None:
    result = build_peer_research(company("NVDA"), [company("AMD"), company("AVGO")])

    korean = render_peer_markdown(result, "ko")
    english = render_peer_markdown(result, "en")

    assert "## 산업 분류" in korean
    assert "## Is The Premium Justified" in english
    assert "BUY" not in korean
    assert "SELL" not in english


def test_single_company_report_adds_peer_section_when_context_exists() -> None:
    peer_context = build_peer_research(company("NVDA"), [company("AMD"), company("AVGO")])

    markdown = render_markdown(
        build_report(company("NVDA"), peer_context=peer_context, language="ko")
    )

    assert "## 동종기업 비교" in markdown
    assert "현재 프리미엄은 정당한가" in markdown


def test_no_overall_buy_ranking_or_invented_evidence() -> None:
    result = build_peer_research(company("NVDA"), [company("AMD"), company("AVGO")])
    markdown = render_peer_markdown(result, "en")

    assert "#1" not in markdown
    assert "BUY" not in markdown
    assert "analyst" not in json.dumps(result, default=str).lower()
    assert result["evidence"]


def test_peer_research_cli_json_and_markdown(tmp_path: Path) -> None:
    payload = {"company": company("NVDA"), "peers": [company("AMD"), company("AVGO")]}
    fixture = tmp_path / "peers.json"
    fixture.write_text(json.dumps(payload), encoding="utf-8")

    json_run = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "peer_research.py"), "--input", str(fixture)],
        capture_output=True,
        text=True,
        check=True,
    )
    markdown_run = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "peer_research.py"),
            "--input",
            str(fixture),
            "--format",
            "markdown",
            "--language",
            "ko",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(json_run.stdout)["version"] == "0.7.0"
    assert "## 비교 기업" in markdown_run.stdout


def company_metrics(payload: dict[str, Any], *, pe: str) -> dict[str, Any]:
    result = build_peer_research(payload, [])["company_metrics"]
    result["pe"]["value"] = pe
    return result


def company(ticker: str, *, risk: str = "pricing pressure") -> dict[str, Any]:
    profiles = {
        "NVDA": (
            "NVIDIA Corporation",
            "3674",
            "Semiconductors",
            "AI accelerator data center GPU networking",
            ["Data Center"],
        ),
        "AMD": (
            "Advanced Micro Devices",
            "3674",
            "Semiconductors",
            "CPU GPU data center gaming embedded",
            ["Data Center"],
        ),
        "AVGO": (
            "Broadcom Inc.",
            "3674",
            "Semiconductors",
            "semiconductor infrastructure software networking",
            ["Semiconductor Solutions"],
        ),
        "INTC": (
            "Intel Corporation",
            "3674",
            "Semiconductors",
            "CPU foundry data center client semiconductor",
            ["Client"],
        ),
        "WMT": (
            "Walmart Inc.",
            "5331",
            "Retail",
            "retail grocery ecommerce stores",
            ["Walmart U.S."],
        ),
        "COST": (
            "Costco Wholesale",
            "5331",
            "Retail",
            "warehouse retail membership grocery",
            ["Membership"],
        ),
        "TEST": ("Test Co", "3674", "Semiconductors", "", []),
    }
    name, sic, sic_description, description, segments = profiles[ticker]
    return {
        "company": name,
        "ticker": ticker,
        "sic": sic,
        "sic_description": sic_description,
        "business_description": description,
        "segments": [{"name": segment, "revenue": "100"} for segment in segments],
        "industry_risks": [risk],
        "current_price": "45" if ticker == "NVDA" else "20",
        "market_cap": "4500" if ticker == "NVDA" else "2000",
        "shares_outstanding": "100",
        "revenue": "1000",
        "gross_profit": "600" if ticker == "NVDA" else "450",
        "operating_income": "500" if ticker == "NVDA" else "250",
        "net_income": "400" if ticker == "NVDA" else "160",
        "eps": "1" if ticker == "NVDA" else "2",
        "free_cash_flow": "350" if ticker == "NVDA" else "120",
        "current_assets": "900",
        "current_liabilities": "300",
        "inventory": "100",
        "total_assets": "1600",
        "total_liabilities": "500",
        "total_debt": "100",
        "shareholder_equity": "900",
        "book_value_per_share": "9",
        "field_sources": {"business_description": "SEC:10-K:item-1"},
        "fact_metadata": {
            "current_price": {"basis": "market_quote"},
            "revenue": {"basis": "ttm"},
            "net_income": {"basis": "ttm"},
            "eps": {"basis": "latest_annual"},
            "free_cash_flow": {"basis": "ttm"},
            "shareholder_equity": {"basis": "latest_snapshot"},
            "shares_outstanding": {"basis": "latest_snapshot"},
        },
        "data_quality": {"currency_match": True},
        "provider": {"warnings": []},
        "missing_fields": [],
        "annuals": [
            {"revenue": "700", "net_income": "100", "free_cash_flow": "80"},
            {"revenue": "850", "net_income": "130", "free_cash_flow": "100"},
            {"revenue": "1000", "net_income": "160", "free_cash_flow": "120"},
        ],
    }
