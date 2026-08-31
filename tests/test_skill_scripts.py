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
        "annuals": [],
    }
