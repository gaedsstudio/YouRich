import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from _comparison_model import build_comparison_report  # noqa: E402
from _comparison_report import render_comparison_markdown  # noqa: E402
from _report_format import render_markdown  # noqa: E402
from _report_model import build_report  # noqa: E402
from _reverse_dcf import solve_reverse_dcf  # noqa: E402
from _valuation_history import historical_valuation  # noqa: E402
from _valuation_intelligence import build_valuation_intelligence  # noqa: E402
from _valuation_scenarios import classify_position, value_range  # noqa: E402


def test_reverse_dcf_solved_case() -> None:
    result = solve_reverse_dcf(company(), forecast_years=5, discount_rate=10, terminal_growth=3)

    assert result["status"] == "SOLVED"
    assert result["required_fcf_cagr"] is not None
    assert result["forecast_years"] == 5
    assert result["discount_rate"] == Decimal("10")
    assert result["terminal_growth"] == Decimal("3")


def test_reverse_dcf_rejects_zero_or_negative_fcf() -> None:
    payload = company()
    payload["free_cash_flow"] = "0"

    assert solve_reverse_dcf(payload)["status"] == "NO_VALID_FCF"
    payload["free_cash_flow"] = "-1"
    assert solve_reverse_dcf(payload)["status"] == "NO_VALID_FCF"


def test_reverse_dcf_requires_market_cap() -> None:
    payload = company()
    payload["market_cap"] = None

    assert solve_reverse_dcf(payload)["status"] == "NO_MARKET_CAP"


def test_reverse_dcf_reports_impossible_root() -> None:
    payload = company()
    payload["market_cap"] = "1000000"

    assert solve_reverse_dcf(payload)["status"] == "NO_NUMERICAL_SOLUTION"


def test_reverse_dcf_rejects_discount_rate_below_terminal_growth() -> None:
    result = solve_reverse_dcf(company(), discount_rate=3, terminal_growth=3)

    assert result["status"] == "INVALID_ASSUMPTIONS"


def test_historical_valuation_percentile_uses_observed_history() -> None:
    result = historical_valuation(company_with_history())

    pe = next(item for item in result["metrics"] if item["metric"] == "pe")
    assert pe["current"] == Decimal("20")
    assert pe["median"] == Decimal("14")
    assert pe["percentile"] == 100
    assert pe["period_years"] == 5


def test_historical_valuation_warns_when_history_is_insufficient() -> None:
    result = historical_valuation(company())

    assert result["metrics"] == []
    assert "HISTORICAL_VALUATION_UNAVAILABLE" in result["warnings"]


def test_scenario_assumption_sources_and_ordering() -> None:
    result = build_valuation_intelligence(company())

    scenarios = result["scenarios"]
    assert [item["scenario"] for item in scenarios] == ["bear", "base", "bull"]
    assert scenarios[0]["value_midpoint"] < scenarios[1]["value_midpoint"]
    assert scenarios[1]["value_midpoint"] < scenarios[2]["value_midpoint"]
    assert scenarios[1]["assumption_sources"]["fcf_margin"] == "latest_ttm"


def test_value_range_avoids_fake_precision() -> None:
    assert value_range(Decimal("187.42")) == "$170-205"


def test_margin_of_safety_classification() -> None:
    assert classify_position(Decimal("100"), Decimal("130")) == "MATERIAL_UPSIDE"
    assert classify_position(Decimal("100"), Decimal("101")) == "NEAR_SCENARIO_VALUE"
    assert classify_position(Decimal("100"), Decimal("70")) == "MATERIAL_DOWNSIDE"


def test_sensitivity_analysis_returns_material_drivers() -> None:
    result = build_valuation_intelligence(company())

    assert result["sensitivity"]["table"]
    drivers = [item["driver"] for item in result["valuation_drivers"]]
    assert "discount_rate" in drivers
    assert "fcf_growth" in drivers


def test_guidance_integration_marks_near_term_source() -> None:
    result = build_valuation_intelligence(
        company(),
        earnings_context={
            "guidance": [
                {
                    "metric": "revenue",
                    "period": "next_quarter",
                    "midpoint": "1100",
                    "status": "reported",
                }
            ]
        },
    )

    base = next(item for item in result["scenarios"] if item["scenario"] == "base")
    assert base["assumption_sources"]["near_term_revenue_growth"] == "official_guidance"


def test_annual_and_ttm_basis_are_preserved() -> None:
    result = build_valuation_intelligence(company())

    assert result["current_valuation"]["metrics"]["pe"]["basis"] == "latest_annual"
    assert result["current_valuation"]["metrics"]["fcf_yield"]["basis"] == "ttm"


def test_korean_report_renders_valuation_intelligence() -> None:
    markdown = render_markdown(build_report(company(), language="ko"))

    assert "현재 가격이 요구하는 성장" in markdown
    assert "시나리오 위치" in markdown
    assert "BUY" not in markdown
    assert "SELL" not in markdown


def test_english_report_renders_valuation_intelligence() -> None:
    markdown = render_markdown(build_report(company(), language="en"))

    assert "Required FCF growth" in markdown
    assert "Scenario position" in markdown
    assert "TARGET PRICE" not in markdown


def test_comparison_valuation_intelligence() -> None:
    rows = [comparison_row("AMD", "45"), comparison_row("NVDA", "15")]

    markdown = render_comparison_markdown(build_comparison_report(rows), "en")

    assert "Required FCF Growth" in markdown
    assert "Base Scenario Position" in markdown
    assert "BUY" not in markdown
    assert "SELL" not in markdown


def test_no_third_party_analyst_estimates_are_added() -> None:
    result = build_valuation_intelligence(company())

    assert "analyst_estimates" not in result
    assert "third_party_price_targets" not in result


def test_valuation_intelligence_cli_emits_json_and_markdown(tmp_path: Path) -> None:
    payload = tmp_path / "company.json"
    payload.write_text(json.dumps(company()), encoding="utf-8")

    json_run = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "valuation_intelligence.py"), "--input", str(payload)],
        capture_output=True,
        text=True,
        check=True,
    )
    markdown_run = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "valuation_intelligence.py"),
            "--input",
            str(payload),
            "--format",
            "markdown",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(json_run.stdout)["version"] == "0.7.0"
    assert "Required FCF growth" in markdown_run.stdout


def company() -> dict[str, Any]:
    return {
        "company": "Test Co",
        "ticker": "TEST",
        "current_price": "20",
        "market_cap": "2000",
        "shares_outstanding": "100",
        "revenue": "1000",
        "net_income": "200",
        "eps": "2",
        "free_cash_flow": "150",
        "cash": "100",
        "total_debt": "200",
        "book_value_per_share": "10",
        "field_sources": {
            "current_price": "market-source",
            "market_cap": "computed: current_price * shares_outstanding",
            "free_cash_flow": "computed: operating_cash_flow - capex",
        },
        "fact_metadata": {
            "current_price": {"basis": "market_quote", "price_date": "2026-08-28"},
            "revenue": {"basis": "ttm", "period_end": "2026-06-30"},
            "net_income": {"basis": "ttm", "period_end": "2026-06-30"},
            "eps": {"basis": "latest_annual", "period_end": "2025-12-31"},
            "free_cash_flow": {"basis": "ttm"},
            "shareholder_equity": {"basis": "latest_snapshot"},
            "shares_outstanding": {"basis": "latest_snapshot"},
        },
        "data_quality": {"currency_match": True, "ttm_coverage": "complete"},
        "provider": {"warnings": []},
        "annuals": [],
    }


def company_with_history() -> dict[str, Any]:
    payload = company()
    payload["eps"] = "1"
    payload["historical_valuation"] = {
        "pe": [
            {"period_end": "2021-12-31", "value": "10"},
            {"period_end": "2022-12-31", "value": "12"},
            {"period_end": "2023-12-31", "value": "14"},
            {"period_end": "2024-12-31", "value": "16"},
            {"period_end": "2025-12-31", "value": "18"},
        ]
    }
    return payload


def comparison_row(ticker: str, market_cap: str) -> dict[str, Any]:
    payload = company()
    payload["ticker"] = ticker
    payload["company"] = ticker
    payload["market_cap"] = market_cap
    return {
        "company": ticker,
        "ticker": ticker,
        "valuation": {"conclusion": "FAIRLY VALUED", "metrics": {}},
        "financial_quality": {"metrics": {}},
        "risk": {"risk_checks": []},
        "comparison_basis": {},
        "valuation_intelligence": build_valuation_intelligence(payload),
    }
