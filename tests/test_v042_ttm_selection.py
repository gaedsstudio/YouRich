import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _sec  # noqa: E402
import _sec_facts  # noqa: E402
import valuation as valuation_module  # noqa: E402
from _sec_periods import select_ttm  # noqa: E402
from v042_fixtures import (  # noqa: E402
    REVENUE_CONCEPT,
    FactSpec,
    additive_bridge_payload,
    apple_bridge_facts,
    fact,
    row,
)


def test_annual_plus_ytd_bridge_reconstructs_apple_like_revenue_ttm() -> None:
    facts = apple_bridge_facts(Decimal("416.161"), Decimal("364.357"), Decimal("313.695"))

    selection = select_ttm(facts)

    assert selection.value == Decimal("466.823")
    assert selection.basis == "ttm"
    assert selection.coverage == "complete"
    metadata = selection.metadata()
    assert metadata is not None
    assert metadata["period_start"] == "2025-06-29"
    assert metadata["period_end"] == "2026-06-27"
    assert metadata["basis"] == "ttm"
    assert metadata["period_class"] == "DERIVED_TTM"
    assert metadata["source_kind"] == "derived_ttm"
    assert metadata["coverage"] == "complete"
    assert metadata["derived_from"] == [
        "2024-09-29:2025-06-28",
        "2024-09-29:2025-09-27",
        "2025-09-28:2026-06-27",
    ]
    assert {
        (item["fy"], item["fp"], item["period_start"], item["period_end"], item["value"])
        for item in metadata["source_facts"]
    } == {
        (2025, "FY", "2024-09-29", "2025-09-27", Decimal("416.161")),
        (2025, "Q3", "2024-09-29", "2025-06-28", Decimal("313.695")),
        (2026, "Q3", "2025-09-28", "2026-06-27", Decimal("364.357")),
    }


def test_missing_comparable_prior_ytd_does_not_create_ttm() -> None:
    facts = apple_bridge_facts(Decimal("416.161"), Decimal("364.357"), Decimal("313.695"))[:2]

    selection = select_ttm(facts)

    assert selection.value is None
    assert selection.coverage == "partial"


def test_mismatched_concept_does_not_create_ttm() -> None:
    facts = [
        fact(FactSpec(Decimal("416.161"), concept=REVENUE_CONCEPT, fp="FY", form="10-K", fy=2025)),
        fact(FactSpec(Decimal("364.357"), concept=REVENUE_CONCEPT)),
        fact(
            FactSpec(
                Decimal("313.695"),
                concept="SalesRevenueNet",
                start="2024-09-29",
                end="2025-06-28",
                fy=2025,
                accn="accn-prior",
            )
        ),
    ]

    selection = select_ttm(facts)

    assert selection.value is None
    assert selection.coverage == "partial"


def test_mismatched_unit_does_not_create_ttm() -> None:
    facts = apple_bridge_facts(Decimal("416.161"), Decimal("364.357"), Decimal("313.695"))
    facts[2] = fact(
        FactSpec(
            Decimal("313.695"),
            unit="shares",
            start="2024-09-29",
            end="2025-06-28",
            fy=2025,
            accn="accn-prior",
        )
    )

    selection = select_ttm(facts)

    assert selection.value is None
    assert selection.coverage == "partial"


def test_mismatched_fiscal_calendar_does_not_create_ttm() -> None:
    facts = apple_bridge_facts(Decimal("416.161"), Decimal("364.357"), Decimal("313.695"))
    facts[1] = fact(FactSpec(Decimal("364.357"), start="2025-09-29"))

    selection = select_ttm(facts)

    assert selection.value is None
    assert selection.coverage == "partial"


def test_restated_comparable_ytd_does_not_create_ttm() -> None:
    facts = apple_bridge_facts(Decimal("416.161"), Decimal("364.357"), Decimal("313.695"))
    facts.append(
        fact(
            FactSpec(
                Decimal("313.111"),
                start="2024-09-29",
                end="2025-06-28",
                fy=2025,
                filed="2025-07-30",
                accn="accn-prior-original",
            )
        )
    )

    selection = select_ttm(facts)

    assert selection.value is None
    assert selection.coverage == "partial"


def test_annual_fallback_selection_remains_latest_annual() -> None:
    facts = {
        "us-gaap": {
            REVENUE_CONCEPT: {
                "units": {
                    "USD": [
                        {
                            "val": "416.161",
                            "fy": 2025,
                            "fp": "FY",
                            "form": "10-K",
                            "filed": "2025-10-31",
                            "start": "2024-09-29",
                            "end": "2025-09-27",
                        }
                    ]
                }
            }
        }
    }

    selection = _sec_facts.select_field(facts, "revenue", _sec.CONCEPTS["revenue"])

    assert selection.value == Decimal("416.161")
    assert selection.basis == "latest_annual"
    assert selection.coverage == "partial"


def test_company_from_sec_reconstructs_additive_ttm_fields_and_fcf() -> None:
    company = _sec.company_from_sec("AAPL", "Apple Inc.", additive_bridge_payload(), debug=False)

    assert company["revenue"] == Decimal("466.823")
    assert company["gross_profit"] == Decimal("220")
    assert company["operating_income"] == Decimal("160")
    assert company["net_income"] == Decimal("124")
    assert company["operating_cash_flow"] == Decimal("136")
    assert company["capital_expenditures"] == Decimal("14")
    assert company["free_cash_flow"] == Decimal("122")
    assert company["fact_metadata"]["revenue"]["basis"] == "ttm"
    assert company["fact_metadata"]["free_cash_flow"]["basis"] == "ttm"
    assert company["fact_metadata"]["free_cash_flow"]["period_start"] == "2025-06-29"
    assert company["fact_metadata"]["free_cash_flow"]["period_end"] == "2026-06-27"
    assert company["fact_metadata"]["free_cash_flow"]["source_facts"]
    assert company["data_quality"]["ttm_coverage_by_field"]["revenue"] == "complete"
    assert company["data_quality"]["ttm_coverage"] == "partial"


def test_eps_annual_plus_ytd_bridge_remains_latest_annual() -> None:
    facts = {
        "us-gaap": {
            "EarningsPerShareDiluted": {
                "units": {
                    "USD/shares": [
                        row("7.46", "FY", "10-K", "2024-09-29", "2025-09-27", 2025, "2025-10-31"),
                        row("6.42", "Q3", "10-Q", "2025-09-28", "2026-06-27", 2026, "2026-07-31"),
                        row("5.16", "Q3", "10-Q", "2024-09-29", "2025-06-28", 2025, "2025-08-01"),
                    ]
                }
            }
        }
    }

    selection = _sec_facts.select_field(facts, "eps", _sec.CONCEPTS["eps"])

    assert selection.value == Decimal("7.46")
    assert selection.basis == "latest_annual"
    assert selection.coverage == "partial"


def test_valuation_cannot_label_annual_fallback_ttm() -> None:
    company = {
        "ticker": "AAPL",
        "current_price": "200",
        "market_cap": "3000",
        "revenue": "416.161",
        "net_income": "112.010",
        "eps": "7.46",
        "free_cash_flow": "98.767",
        "book_value_per_share": "4",
        "field_sources": {},
        "provider": {"warnings": []},
        "fact_metadata": {
            "revenue": {"basis": "latest_annual"},
            "net_income": {"basis": "latest_annual"},
            "eps": {"basis": "latest_annual"},
            "free_cash_flow": {"basis": "latest_annual"},
        },
    }

    result = valuation_module.valuation(company)

    metrics = result["metrics"]
    assert metrics["pe"]["basis"] == "latest_annual"
    assert metrics["pe"]["formula"] == "price / latest annual diluted eps"
    assert metrics["ps"]["basis"] == "latest_annual"
    assert metrics["earnings_yield"]["basis"] == "latest_annual"
    assert metrics["fcf_yield"]["basis"] == "latest_annual"
