import os
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _core  # noqa: E402
import _market  # noqa: E402
import _sec  # noqa: E402
import _sec_facts  # noqa: E402
import _sec_quality  # noqa: E402
import compare as compare_module  # noqa: E402
import valuation as valuation_module  # noqa: E402
from v03_fixtures import (  # noqa: E402
    apple_like_ytd_payload,
    companyfacts_payload,
    duplicate_annual_payload,
    no_direct_eps_payload,
    stale_preferred_annual_facts,
    valuation_payload,
    wrong_unit_facts,
)


def test_ttm_income_statement_fields_use_four_quarters() -> None:
    company = _sec.company_from_sec("TEST", "Test Co", companyfacts_payload(), debug=False)

    assert company["revenue"] == Decimal("460")
    assert company["net_income"] == Decimal("46")
    assert company["operating_income"] == Decimal("92")
    assert company["operating_cash_flow"] == Decimal("68")
    assert company["capital_expenditures"] == Decimal("-18")
    assert company["free_cash_flow"] == Decimal("50")
    assert company["fact_metadata"]["revenue"]["basis"] == "ttm"


def test_latest_balance_sheet_uses_snapshot_not_ttm() -> None:
    company = _sec.company_from_sec("TEST", "Test Co", companyfacts_payload(), debug=False)

    assert company["cash"] == Decimal("90")
    assert company["shareholder_equity"] == Decimal("400")
    assert company["shares_outstanding"] == Decimal("100")
    assert company["fact_metadata"]["shareholder_equity"]["basis"] == "latest_snapshot"


def test_duplicate_and_amended_facts_select_latest_filing_and_detect_restatement() -> None:
    company = _sec.company_from_sec("TEST", "Test Co", companyfacts_payload(), debug=False)

    metadata = company["fact_metadata"]["current_assets"]
    assert company["current_assets"] == Decimal("710")
    assert metadata["form"] == "10-Q/A"
    assert metadata["restated"] is True
    assert metadata["previous_value"] == Decimal("700")


def test_wrong_unit_is_rejected_for_revenue() -> None:
    selection = _sec_facts.select_field(wrong_unit_facts(), "revenue", _sec.CONCEPTS["revenue"])

    assert selection.value is None


def test_fallback_ttm_beats_stale_preferred_annual() -> None:
    selection = _sec_facts.select_field(
        stale_preferred_annual_facts(), "revenue", _sec.CONCEPTS["revenue"]
    )

    assert selection.value == Decimal("460")
    assert selection.basis == "ttm"
    assert selection.facts[0].concept == "SalesRevenueNet"


def test_basic_vs_diluted_eps_prefers_diluted_ttm() -> None:
    company = _sec.company_from_sec("TEST", "Test Co", companyfacts_payload(), debug=False)

    assert company["eps"] == Decimal("4.6")
    assert company["eps_method"] == "diluted_ttm"


def test_derived_eps_uses_weighted_average_shares_when_direct_eps_missing() -> None:
    company = _sec.company_from_sec("TEST", "Test Co", no_direct_eps_payload(), debug=False)

    assert company["eps"] == Decimal("0.46")
    assert company["eps_method"] == "net_income_diluted_weighted_average"


def test_currency_mismatch_blocks_price_sensitive_valuation() -> None:
    payload = valuation_payload()
    payload["financial_currency"] = "EUR"
    payload["market_currency"] = "USD"

    result = valuation_module.valuation(payload)

    assert result["metrics"]["pe"]["value"] is None
    assert "CURRENCY_MISMATCH" in cast(list[str], result["warnings"])


def test_valuation_period_metadata_exposes_ttm_and_snapshot_basis() -> None:
    result = valuation_module.valuation(valuation_payload())

    assert result["metrics"]["pe"]["periods"]["eps_basis"] == "ttm"
    assert result["metrics"]["ps"]["periods"]["revenue_basis"] == "ttm"
    assert result["metrics"]["fcf_yield"]["periods"]["fcf_basis"] == "ttm"
    assert result["metrics"]["pb"]["periods"]["equity_basis"] == "latest_snapshot"


def test_data_quality_output_reports_mapping_and_ttm_coverage() -> None:
    company = _sec.company_from_sec("TEST", "Test Co", companyfacts_payload(), debug=False)
    company["market_quote"] = {"provider": "test"}
    company["provider"] = {"warnings": []}

    result = _sec_quality.data_quality(company)

    assert result["ttm_coverage"] == "complete"
    assert result["mapping_confidence"] == "high"
    assert result["currency_match"] is True


def test_apple_like_ytd_facts_are_reconstructed_before_ttm() -> None:
    company = _sec.company_from_sec("AAPL", "Apple Inc.", apple_like_ytd_payload(), debug=False)

    assert company["revenue"] == Decimal("117")
    assert company["net_income"] == Decimal("24")
    assert company["operating_income"] == Decimal("29")
    assert company["eps"] == Decimal("8")
    assert company["eps_method"] == "diluted_ttm"
    assert company["operating_cash_flow"] == Decimal("46")
    assert company["capital_expenditures"] == Decimal("-13")
    assert company["free_cash_flow"] == Decimal("33")
    assert company["fact_metadata"]["revenue"]["basis"] == "ttm"
    assert company["fact_metadata"]["revenue"]["period_class"] == "DERIVED_TTM"
    assert company["fact_metadata"]["revenue"]["component_periods"] == [
        "2025-06-29:2025-09-27",
        "2025-09-28:2025-12-27",
        "2025-12-28:2026-03-28",
        "2026-03-29:2026-06-27",
    ]


def test_overlapping_ytd_rows_do_not_create_complete_ttm() -> None:
    selection = _sec_facts.select_field(
        apple_like_ytd_payload()["facts"],
        "revenue",
        _sec.CONCEPTS["revenue"],
    )

    assert selection.value == Decimal("117")
    assert [fact.value for fact in selection.facts] == [
        Decimal("27"),
        Decimal("24"),
        Decimal("21"),
        Decimal("45"),
    ]
    assert not any(fact.period_class in {"YTD_6M", "YTD_9M"} for fact in selection.facts)


def test_ttm_rejects_gap_between_discrete_quarters() -> None:
    facts = {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "USD": [
                        quarter_fact(10, "Q1", "2025-01-01", "2025-03-31"),
                        quarter_fact(20, "Q2", "2025-04-01", "2025-06-30"),
                        quarter_fact(30, "Q3", "2025-10-01", "2025-12-31"),
                        quarter_fact(40, "Q4", "2026-01-01", "2026-03-31"),
                    ]
                }
            }
        }
    }

    selection = _sec_facts.select_field(facts, "revenue", _sec.CONCEPTS["revenue"])

    assert selection.value is None
    assert selection.basis == "unavailable"


def test_stale_ttm_does_not_beat_newer_annual_for_same_concept() -> None:
    facts = {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "USD": [
                        quarter_fact(10, "Q1", "2016-07-01", "2016-09-30"),
                        quarter_fact(20, "Q2", "2016-10-01", "2016-12-31"),
                        quarter_fact(30, "Q3", "2017-01-01", "2017-03-31"),
                        quarter_fact(40, "Q4", "2017-04-01", "2017-06-30"),
                        annual_fact(500, 2026, "2025-07-01", "2026-06-30"),
                    ]
                }
            }
        }
    }

    selection = _sec_facts.select_field(facts, "revenue", _sec.CONCEPTS["revenue"])

    assert selection.value == Decimal("500")
    assert selection.basis == "latest_annual"


def test_annual_series_dedupes_restated_fiscal_years() -> None:
    rows = _sec_facts.annual_series(
        duplicate_annual_payload(),
        _sec.CONCEPTS["revenue"],
    )

    assert rows == [
        {"year": 2025, "revenue": Decimal("82")},
        {"year": 2024, "revenue": Decimal("70")},
    ]


def test_single_debt_component_is_not_reported_as_total_debt() -> None:
    facts = {
        "us-gaap": {
            "LongTermDebtCurrent": {
                "units": {
                    "USD": [
                        {
                            "val": 10,
                            "fy": 2026,
                            "fp": "Q3",
                            "form": "10-Q",
                            "filed": "2026-07-31",
                            "end": "2026-06-27",
                        }
                    ]
                }
            }
        }
    }

    selection = _sec_facts.select_field(facts, "total_debt", _sec.CONCEPTS["total_debt"])

    assert selection.value is None
    assert selection.basis == "total_debt_partial"


def quarter_fact(value: int, fp: str, start: str, end: str) -> dict[str, object]:
    return {
        "val": value,
        "fy": 2026,
        "fp": fp,
        "form": "10-Q",
        "filed": "2026-04-30",
        "start": start,
        "end": end,
    }


def annual_fact(value: int, fy: int, start: str, end: str) -> dict[str, object]:
    return {
        "val": value,
        "fy": fy,
        "fp": "FY",
        "form": "10-K",
        "filed": "2026-07-30",
        "start": start,
        "end": end,
    }


def test_stock_split_warning_requires_large_per_share_date_gap() -> None:
    normal = {
        "eps": {"period_end": "2026-06-30"},
        "shares_outstanding": {"period_end": "2026-07-15"},
    }
    risky = {
        "eps": {"period_end": "2024-06-30"},
        "shares_outstanding": {"period_end": "2026-07-15"},
    }

    assert not _sec_quality.potential_split_issue(normal)
    assert _sec_quality.potential_split_issue(risky)


def test_debug_selection_trace_lists_selected_and_rejected_facts() -> None:
    company = _sec.company_from_sec("TEST", "Test Co", companyfacts_payload(), debug=True)

    trace = company["selection_debug"]["revenue"]
    assert trace["selected"]["concept"] == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert trace["rejected"]


def test_market_provider_fallback_and_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class FailingProvider:
        def get_quote(self, ticker: str) -> _market.MarketQuote:
            raise _core.ToolError(f"failed {ticker}")

    class WorkingProvider:
        def get_quote(self, ticker: str) -> _market.MarketQuote:
            return _market.MarketQuote(
                ticker=ticker,
                price=Decimal("10"),
                currency="USD",
                timestamp="2026-08-28",
                source="source",
                is_delayed=True,
                provider="test",
            )

    monkeypatch.setattr(
        _market, "configured_providers", lambda: [FailingProvider(), WorkingProvider()]
    )
    monkeypatch.setenv("YOURICH_CACHE_DIR", str(tmp_path))

    quote, warnings = _market.get_market_quote("AAPL")
    assert quote is not None
    assert quote["price"] == Decimal("10")
    assert warnings == ["failed AAPL"]
    assert cache_round_trip(tmp_path) == ({"calls": 1}, {"calls": 1}, {"calls": 2})


def test_compare_marks_different_basis_as_not_comparable(monkeypatch: pytest.MonkeyPatch) -> None:
    first = valuation_payload()
    second = valuation_payload()
    second["fact_metadata"]["revenue"]["basis"] = "latest_annual"

    def fake_fetch_financials(ticker: str) -> dict[str, object]:
        return first if ticker == "AAA" else second

    monkeypatch.setattr(compare_module, "fetch_financials", fake_fetch_financials)

    rows = compare_module.compare(["AAA", "BBB"])

    assert rows[0]["comparison_warnings"] == ["NOT_COMPARABLE:ps"]


def cache_round_trip(tmp_path: Path) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    calls = 0
    os.environ["YOURICH_CACHE_DIR"] = str(tmp_path)

    def loader() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"calls": calls}

    first = _core.cached_json("unit/cache", 1_000, loader)
    second = _core.cached_json("unit/cache", 1_000, loader)
    path = _core.cache_path("unit/cache")
    stale_time = time.time() - 2_000
    os.utime(path, (stale_time, stale_time))
    third = _core.cached_json("unit/cache", 1_000, loader)
    return first, second, third
