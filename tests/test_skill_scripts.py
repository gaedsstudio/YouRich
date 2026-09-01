import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import financial_health as financial_health_module  # noqa: E402
import risk as risk_module  # noqa: E402
import valuation as valuation_module  # noqa: E402


def test_valuation_calculates_core_price_metrics() -> None:
    payload = sample_payload()

    result = valuation_module.valuation(payload)

    metrics = result["metrics"]
    assert Decimal(metrics["market_cap"]["value"]) == Decimal("2000")
    assert Decimal(metrics["pe"]["value"]) == Decimal("10")
    assert Decimal(metrics["pb"]["value"]) == Decimal("1")
    assert Decimal(metrics["ps"]["value"]) == Decimal("2")
    assert Decimal(metrics["fcf_yield"]["value"]) == Decimal("7.500")
    assert Decimal(metrics["earnings_yield"]["value"]) == Decimal("10.0")
    assert Decimal(metrics["price_to_ncav"]["value"]) == Decimal("5")
    assert metrics["pe"]["sources"]["price"] == "market-source"
    assert metrics["pe"]["basis"] == "ttm"
    assert metrics["pe"]["formula"] == "price / ttm diluted eps"
    assert "ttm_diluted_eps" in metrics["pe"]["inputs"]
    assert metrics["ps"]["formula"] == "market cap / ttm revenue"
    assert "ttm_revenue" in metrics["ps"]["inputs"]
    assert metrics["fcf_yield"]["formula"] == "ttm free cash flow / market cap * 100"
    assert "ttm_free_cash_flow" in metrics["fcf_yield"]["inputs"]
    assert metrics["earnings_yield"]["formula"] == "ttm net income / market cap * 100"
    assert "ttm_net_income" in metrics["earnings_yield"]["inputs"]


def test_valuation_calculates_graham_ncav_and_margin_of_safety() -> None:
    payload = sample_payload()

    result = valuation_module.valuation(payload)

    metrics = result["metrics"]
    assert Decimal(metrics["graham_number"]["value"]) == Decimal("30")
    assert Decimal(metrics["ncav"]["value"]) == Decimal("400")
    assert Decimal(metrics["ncav_per_share"]["value"]) == Decimal("4")
    assert Decimal(metrics["margin_of_safety"]["value"]) == Decimal(
        "16.66666666666666666666666667",
    )
    assert metrics["normalized_eps"]["formula"] == "current selected EPS"
    assert metrics["normalized_eps"]["basis"] == "ttm"


def test_financial_health_calculates_liquidity_and_leverage() -> None:
    payload = sample_payload()

    result = financial_health_module.financial_health(payload)

    metrics = result["metrics"]
    assert Decimal(metrics["current_ratio"]["value"]) == Decimal("2")
    assert Decimal(metrics["debt_to_equity"]["value"]) == Decimal("0.25")


def test_risk_marks_negative_equity_as_triggered() -> None:
    payload = sample_payload()
    payload["shareholder_equity"] = "-10"

    result = risk_module.risk_checks(payload)

    risk_checks = cast(list[dict[str, object]], result["risk_checks"])
    checks = {item["id"]: item for item in risk_checks}
    assert checks["negative_equity"]["status"] == "triggered"


def test_valuation_is_reproducible_for_same_input() -> None:
    payload = sample_payload()

    first = valuation_module.valuation(payload)
    second = valuation_module.valuation(payload)

    assert first == second


def test_missing_price_does_not_fabricate_price_sensitive_metrics() -> None:
    payload = sample_payload()
    payload["current_price"] = None

    result = valuation_module.valuation(payload)

    metrics = result["metrics"]
    assert metrics["pe"]["value"] is None
    assert metrics["margin_of_safety"]["value"] is None


def test_missing_eps_and_book_do_not_fabricate_valuation_metrics() -> None:
    payload = sample_payload()
    payload["eps"] = None
    payload["book_value_per_share"] = None

    result = valuation_module.valuation(payload)

    metrics = result["metrics"]
    assert metrics["pe"]["value"] is None
    assert metrics["pb"]["value"] is None
    assert metrics["graham_number"]["value"] is None


def test_annual_eps_fallback_does_not_label_pe_as_ttm() -> None:
    payload = annual_fallback_payload()

    result = valuation_module.valuation(payload)

    pe = result["metrics"]["pe"]
    assert pe["basis"] == "latest_annual"
    assert pe["formula"] == "price / latest annual diluted eps"
    assert "latest_annual_diluted_eps" in pe["inputs"]
    assert "ttm_diluted_eps" not in pe["inputs"]
    assert "TTM_INCOMPLETE_USING_ANNUAL_FALLBACK" in cast(list[str], result["warnings"])


def test_annual_revenue_fallback_does_not_label_ps_as_ttm() -> None:
    payload = annual_fallback_payload()

    result = valuation_module.valuation(payload)

    ps = result["metrics"]["ps"]
    assert ps["basis"] == "latest_annual"
    assert ps["formula"] == "market cap / latest annual revenue"
    assert "latest_annual_revenue" in ps["inputs"]
    assert "ttm_revenue" not in ps["inputs"]


def test_annual_fcf_and_net_income_fallbacks_do_not_label_yields_as_ttm() -> None:
    payload = annual_fallback_payload()

    result = valuation_module.valuation(payload)

    fcf_yield = result["metrics"]["fcf_yield"]
    earnings_yield = result["metrics"]["earnings_yield"]
    assert fcf_yield["basis"] == "latest_annual"
    assert fcf_yield["formula"] == "latest annual free cash flow / market cap * 100"
    assert "latest_annual_free_cash_flow" in fcf_yield["inputs"]
    assert "ttm_free_cash_flow" not in fcf_yield["inputs"]
    assert earnings_yield["basis"] == "latest_annual"
    assert earnings_yield["formula"] == "latest annual net income / market cap * 100"
    assert "latest_annual_net_income" in earnings_yield["inputs"]
    assert "ttm_net_income" not in earnings_yield["inputs"]


def test_pb_and_market_cap_keep_snapshot_basis() -> None:
    result = valuation_module.valuation(sample_payload())

    metrics = result["metrics"]
    assert metrics["pb"]["basis"] == "latest_snapshot"
    assert metrics["market_cap"]["basis"] == "market_snapshot"


def test_skill_trigger_examples_match_expected_boundary() -> None:
    skill = (ROOT / "skill" / "yourich" / "SKILL.md").read_text(encoding="utf-8")

    positive = (
        "Analyze AAPL.",
        "Compare AAPL and MSFT.",
        "Is NVDA overvalued?",
        "What financial risks does INTC have?",
    )
    negative = ("Explain this Python function.", "Fix my CSS.")

    for prompt in positive:
        assert should_trigger(skill, prompt)
    for prompt in negative:
        assert not should_trigger(skill, prompt)


def should_trigger(skill: str, prompt: str) -> bool:
    stock_terms = ("stock", "company", "investment", "valuation", "financial", "risk")
    blocked_terms = ("python function", "css", "debug")
    prompt_lower = prompt.lower()
    skill_lower = skill.lower()
    has_ticker = re.search(r"\b[A-Z]{2,5}\b", prompt) is not None
    has_stock_intent = any(term in prompt_lower for term in stock_terms) or has_ticker
    return (
        has_stock_intent
        and not any(term in prompt_lower for term in blocked_terms)
        and "do not use yourich for ordinary programming" in skill_lower
    )


def sample_payload() -> dict[str, object]:
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
        "cash": "100",
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
            "shares_outstanding": "SEC:dei:EntityCommonStockSharesOutstanding:shares",
            "revenue": "SEC:us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax:USD",
            "eps": "SEC:us-gaap:EarningsPerShareDiluted:USD/shares",
            "free_cash_flow": "computed: operating_cash_flow - capex",
            "book_value_per_share": "computed: shareholder_equity / shares_outstanding",
            "current_assets": "SEC:us-gaap:AssetsCurrent:USD",
            "total_liabilities": "SEC:us-gaap:Liabilities:USD",
        },
        "market_quote": {"timestamp": "2026-08-28", "provider": "test"},
        "data_quality": {"currency_match": True},
        "fact_metadata": {
            "current_price": {"basis": "market_quote", "price_date": "2026-08-28"},
            "market_cap": {"basis": "market_snapshot"},
            "revenue": {"basis": "ttm", "period_end": "2026-06-30"},
            "net_income": {"basis": "ttm", "period_end": "2026-06-30"},
            "eps": {"basis": "ttm", "period_end": "2026-06-30"},
            "free_cash_flow": {"basis": "ttm"},
            "shareholder_equity": {"basis": "latest_snapshot", "period_end": "2026-06-30"},
            "shares_outstanding": {"basis": "latest_snapshot", "period_end": "2026-06-30"},
        },
        "annuals": [],
    }


def annual_fallback_payload() -> dict[str, object]:
    payload = sample_payload()
    payload["fact_metadata"]["revenue"]["basis"] = "latest_annual"
    payload["fact_metadata"]["net_income"]["basis"] = "latest_annual"
    payload["fact_metadata"]["eps"]["basis"] = "latest_annual"
    payload["fact_metadata"]["free_cash_flow"]["basis"] = "latest_annual"
    payload["data_quality"] = {"currency_match": True, "ttm_coverage": "partial"}
    return payload
