import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from _report_format import render_markdown  # noqa: E402
from _report_model import build_report, financial_metric  # noqa: E402
from _report_types import SECTION_ORDER  # noqa: E402


def test_report_sections_follow_default_order() -> None:
    report = build_report(sample_company())

    assert [section.key for section in report.sections] == list(SECTION_ORDER)


def test_report_preserves_metric_basis_without_ttm_label_for_annual_eps() -> None:
    report = build_report(sample_company())
    markdown = render_markdown(report)
    quality = report.sections[-1]

    assert "| P/E | 10.0x | Latest annual |" in markdown
    assert {"Item": "EPS basis", "Value": "Latest annual"} in quality.rows
    assert "| P/E | 10.0x | TTM |" not in markdown


def test_report_renders_annual_fallback_warning_for_humans() -> None:
    markdown = render_markdown(build_report(sample_company()))

    assert "Annual fallback used: EPS" in markdown
    assert "TTM_INCOMPLETE_USING_ANNUAL_FALLBACK" not in markdown


def test_report_renders_missing_metrics_as_unavailable() -> None:
    company = sample_company()
    company["free_cash_flow"] = None

    markdown = render_markdown(build_report(company))

    assert (
        "| FCF Yield | Unavailable | Cash return generated for each $100 of market value. |"
        in markdown
    )
    assert "| Free Cash Flow | Unavailable |" in markdown


def test_report_renders_insufficient_business_evidence() -> None:
    markdown = render_markdown(build_report(sample_company()))

    assert "## Business Quality" in markdown
    assert "Insufficient evidence" in markdown


def test_report_json_generation_keeps_stable_keys() -> None:
    payload = build_report(sample_company()).to_dict()

    assert payload["overall_assessment"]["label"] == "HIGH QUALITY / ATTRACTIVE VALUATION"
    assert payload["key_metrics"][2]["basis"] == "latest_annual"
    assert payload["sections"][0]["key"] == "overall"
    assert payload["raw"]["valuation"]["metrics"]["pe"]["basis"] == "latest_annual"


def test_report_marks_latest_annual_revenue_as_reported_fact() -> None:
    company = sample_company()
    company["fact_metadata"]["revenue"] = {"basis": "latest_annual"}

    payload = build_report(company).to_dict()

    assert metric_types(payload)["Revenue"] == "reported_fact"


def test_report_marks_direct_ytd_revenue_as_reported_fact() -> None:
    company = sample_company()
    company["fact_metadata"]["revenue"] = {"basis": "ytd_9m"}

    payload = build_report(company).to_dict()

    assert metric_types(payload)["Revenue"] == "reported_fact"


def test_report_marks_reconstructed_ttm_revenue_as_derived_metric() -> None:
    company = sample_company()
    company["fact_metadata"]["revenue"] = reconstructed_ttm_metadata()

    payload = build_report(company).to_dict()

    assert metric_types(payload)["Revenue"] == "derived_metric"


def test_report_marks_reconstructed_ttm_net_income_as_derived_metric() -> None:
    company = sample_company()
    company["fact_metadata"]["net_income"] = reconstructed_ttm_metadata()

    payload = build_report(company).to_dict()

    assert metric_types(payload)["Net Income"] == "derived_metric"


def test_report_marks_calculated_fcf_as_derived_metric() -> None:
    metric = financial_metric("Free Cash Flow", sample_company(), "free_cash_flow", "Cash flow.")

    assert metric.to_dict()["type"] == "derived_metric"


def test_report_marks_annual_fallback_eps_as_reported_fact() -> None:
    company = sample_company()
    company["eps"] = "2"
    company["fact_metadata"]["eps"] = {"basis": "latest_annual"}

    metric = financial_metric("EPS", company, "eps", "Earnings per share.")

    assert metric.to_dict()["type"] == "reported_fact"


def test_report_valuation_metrics_remain_derived_metric() -> None:
    payload = build_report(sample_company()).to_dict()

    assert metric_types(payload)["P/E"] == "derived_metric"
    assert metric_types(payload)["FCF Yield"] == "derived_metric"


def test_report_selects_korean_headings() -> None:
    markdown = render_markdown(build_report(sample_company(), language="ko"))

    assert "## 종합 판단" in markdown
    assert "## 핵심 지표" in markdown
    assert "## 데이터 및 산출 기준" in markdown


def test_report_cli_emits_markdown_by_default(tmp_path: Path) -> None:
    payload = tmp_path / "company.json"
    payload.write_text(json.dumps(sample_company()), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "report.py"), "--input", str(payload)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.stdout.startswith("# Test Co · TEST")
    assert "## Overall Assessment" in completed.stdout
    assert not completed.stdout.lstrip().startswith("{")


def test_report_cli_emits_json_when_requested(tmp_path: Path) -> None:
    payload = tmp_path / "company.json"
    payload.write_text(json.dumps(sample_company()), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "report.py"),
            "--input",
            str(payload),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    result = json.loads(completed.stdout)
    assert result["ticker"] == "TEST"
    assert result["sections"][3]["key"] == "metrics"


def metric_types(payload: dict[str, Any]) -> dict[str, str]:
    return {item["name"]: item["type"] for item in payload["key_metrics"]}


def reconstructed_ttm_metadata() -> dict[str, Any]:
    return {
        "basis": "ttm",
        "derived_from": ["annual", "current_ytd", "prior_ytd"],
        "source_facts": [
            {"form": "10-K", "fp": "FY"},
            {"form": "10-Q", "fp": "Q3"},
            {"form": "10-Q", "fp": "Q3"},
        ],
    }


def sample_company() -> dict[str, Any]:
    return {
        "company": "Test Co",
        "ticker": "TEST",
        "current_price": "20",
        "market_cap": "2000",
        "shares_outstanding": "100",
        "revenue": "1000",
        "gross_profit": "500",
        "operating_income": "250",
        "net_income": "200",
        "eps": "2",
        "free_cash_flow": "150",
        "current_assets": "900",
        "current_liabilities": "450",
        "inventory": "100",
        "total_assets": "1600",
        "total_liabilities": "500",
        "total_debt": "200",
        "shareholder_equity": "800",
        "book_value_per_share": "20",
        "field_sources": {
            "current_price": "market-source",
            "market_cap": "computed: current_price * shares_outstanding",
            "revenue": "SEC:revenue",
            "net_income": "SEC:net_income",
            "eps": "SEC:eps",
            "free_cash_flow": "computed: operating_cash_flow - capex",
        },
        "market_quote": {"timestamp": "2026-08-28", "provider": "test"},
        "data_quality": {"currency_match": True, "ttm_coverage": "partial"},
        "fact_metadata": {
            "current_price": {"basis": "market_quote", "price_date": "2026-08-28"},
            "market_cap": {"basis": "market_snapshot"},
            "revenue": {"basis": "ttm", "period_end": "2026-06-30"},
            "net_income": {"basis": "ttm", "period_end": "2026-06-30"},
            "eps": {"basis": "latest_annual", "period_end": "2025-09-30"},
            "free_cash_flow": {"basis": "ttm"},
            "shareholder_equity": {"basis": "latest_snapshot", "period_end": "2026-06-30"},
            "shares_outstanding": {"basis": "latest_snapshot", "period_end": "2026-06-30"},
        },
        "annuals": [],
    }
