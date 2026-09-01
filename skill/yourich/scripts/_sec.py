from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from _core import FUNDAMENTALS_TTL_SECONDS, ToolError, clean_ticker, fetch_json, ratio
from _market import get_market_quote
from _sec_debug import debug_trace
from _sec_facts import annual_series, derived_eps, select_field
from _sec_quality import (
    currency_warnings,
    data_quality,
    freshness_warnings,
    mapping_warnings,
    missing_fields,
    provider_metadata,
)

if TYPE_CHECKING:
    from _sec_types import Concept

CONCEPTS: dict[str, tuple[Concept, ...]] = {
    "revenue": (
        ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", ("USD",)),
        ("us-gaap", "SalesRevenueNet", ("USD",)),
        ("us-gaap", "Revenues", ("USD",)),
    ),
    "net_income": (("us-gaap", "NetIncomeLoss", ("USD",)), ("us-gaap", "ProfitLoss", ("USD",))),
    "operating_income": (
        ("us-gaap", "OperatingIncomeLoss", ("USD",)),
        (
            "us-gaap",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            ("USD",),
        ),
    ),
    "gross_profit": (("us-gaap", "GrossProfit", ("USD",)),),
    "current_assets": (("us-gaap", "AssetsCurrent", ("USD",)),),
    "current_liabilities": (("us-gaap", "LiabilitiesCurrent", ("USD",)),),
    "total_assets": (("us-gaap", "Assets", ("USD",)),),
    "total_liabilities": (("us-gaap", "Liabilities", ("USD",)),),
    "total_debt": (
        ("us-gaap", "DebtAndFinanceLeaseObligations", ("USD",)),
        ("us-gaap", "LongTermDebtAndFinanceLeaseObligations", ("USD",)),
        ("us-gaap", "ShortTermBorrowings", ("USD",)),
        ("us-gaap", "LongTermDebtCurrent", ("USD",)),
        ("us-gaap", "LongTermDebtAndFinanceLeaseObligationsCurrent", ("USD",)),
        ("us-gaap", "LongTermDebtNoncurrent", ("USD",)),
        ("us-gaap", "LongTermDebtAndFinanceLeaseObligationsNoncurrent", ("USD",)),
    ),
    "shareholder_equity": (
        ("us-gaap", "StockholdersEquity", ("USD",)),
        (
            "us-gaap",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            ("USD",),
        ),
    ),
    "cash": (
        ("us-gaap", "CashAndCashEquivalentsAtCarryingValue", ("USD",)),
        ("us-gaap", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", ("USD",)),
    ),
    "inventory": (("us-gaap", "InventoryNet", ("USD",)),),
    "shares_outstanding": (("dei", "EntityCommonStockSharesOutstanding", ("shares",)),),
    "weighted_average_basic_shares": (
        ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic", ("shares",)),
    ),
    "weighted_average_diluted_shares": (
        ("us-gaap", "WeightedAverageNumberOfDilutedSharesOutstanding", ("shares",)),
    ),
    "eps": (
        ("us-gaap", "EarningsPerShareDiluted", ("USD/shares",)),
        ("us-gaap", "EarningsPerShareBasic", ("USD/shares",)),
    ),
    "operating_cash_flow": (
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivities", ("USD",)),
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations", ("USD",)),
    ),
    "capital_expenditures": (
        ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment", ("USD",)),
        ("us-gaap", "PaymentsToAcquireProductiveAssets", ("USD",)),
    ),
}


def fetch_financials(ticker: str, debug: bool = False) -> dict[str, Any]:
    symbol = clean_ticker(ticker)
    ticker_map = fetch_json(
        "https://www.sec.gov/files/company_tickers.json",
        FUNDAMENTALS_TTL_SECONDS,
        "sec_company_tickers",
    )
    cik, name = lookup_cik(symbol, ticker_map)
    source = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    payload = fetch_json(source, FUNDAMENTALS_TTL_SECONDS, f"sec_companyfacts_{cik}")
    company = company_from_sec(symbol, name, payload, debug)
    market_quote, market_warnings = get_market_quote(symbol)
    warnings = market_warnings
    if market_quote is not None:
        merge_market_quote(company, market_quote)
    warnings.extend(freshness_warnings(company))
    warnings.extend(mapping_warnings(company))
    warnings.extend(currency_warnings(company))
    company["provider"] = provider_metadata(source, company, warnings)
    company["data_quality"] = data_quality(company)
    company["missing_fields"] = missing_fields(company)
    return company


def lookup_cik(ticker: str, ticker_map: dict[str, Any]) -> tuple[int, str]:
    for entry in ticker_map.values():
        if isinstance(entry, dict) and entry.get("ticker") == ticker:
            return int(entry["cik_str"]), str(entry["title"])
    raise ToolError(f"ticker not found in SEC company list: {ticker}")


def company_from_sec(
    ticker: str, name: str, payload: dict[str, Any], debug: bool = False
) -> dict[str, Any]:
    facts = payload.get("facts", {})
    fields = base_company(ticker, name, facts)
    selections = {
        field: select_field(facts, field, concepts) for field, concepts in CONCEPTS.items()
    }
    for field, selection in selections.items():
        fields[field] = selection.value
        metadata = selection.metadata()
        if metadata is not None:
            fields["field_sources"][field] = selection.source()
            fields["fact_metadata"][field] = metadata
            remember_financial_period(fields, metadata)
    apply_derived_values(fields, selections)
    if debug:
        fields["selection_debug"] = {
            field: debug_trace(facts, field, concepts) for field, concepts in CONCEPTS.items()
        }
    return fields


def base_company(ticker: str, name: str, facts: Any) -> dict[str, Any]:
    return {
        "company": name,
        "ticker": ticker,
        "currency": None,
        "financial_currency": "USD",
        "market_currency": None,
        "current_price": None,
        "market_cap": None,
        "market_quote": None,
        "field_sources": {},
        "fact_metadata": {},
        "data_freshness": {},
        "data_quality": {},
        "annuals": annual_series(facts, CONCEPTS["revenue"]),
    }


def apply_derived_values(fields: dict[str, Any], selections: dict[str, Any]) -> None:
    fields["free_cash_flow"] = free_cash_flow(fields)
    if fields["free_cash_flow"] is not None:
        fields["field_sources"]["free_cash_flow"] = (
            "computed: ttm_operating_cash_flow - abs(ttm_capex)"
        )
        fields["fact_metadata"]["free_cash_flow"] = derived_metadata(
            "ttm", ("operating_cash_flow", "capital_expenditures")
        )
    fields["book_value_per_share"] = ratio(
        fields["shareholder_equity"], fields["shares_outstanding"]
    )
    if fields["book_value_per_share"] is not None:
        fields["field_sources"]["book_value_per_share"] = (
            "computed: latest_shareholder_equity / latest_shares_outstanding"
        )
    if fields.get("eps") is None:
        eps, method = derived_eps(
            fields.get("net_income"),
            fields.get("weighted_average_diluted_shares"),
            fields.get("weighted_average_basic_shares"),
        )
        fields["eps"] = eps
        if eps is not None:
            fields["field_sources"]["eps"] = "computed: net_income / weighted_average_shares"
            fields["fact_metadata"]["eps"] = derived_metadata(
                method or "derived_eps", ("net_income",)
            )
    fields["eps_method"] = eps_method(fields, selections)


def merge_market_quote(company: dict[str, Any], quote: dict[str, object]) -> None:
    price = quote["price"]
    company["current_price"] = price
    company["currency"] = quote["currency"]
    company["market_currency"] = quote["currency"]
    company["market_quote"] = quote
    company["field_sources"]["current_price"] = str(quote["source"])
    company["fact_metadata"]["current_price"] = {
        "basis": "market_quote",
        "provider": quote["provider"],
        "price_date": quote["timestamp"],
        "delayed": quote["is_delayed"],
    }
    shares = company.get("shares_outstanding")
    if isinstance(price, Decimal) and isinstance(shares, Decimal):
        company["market_cap"] = price * shares
        company["field_sources"]["market_cap"] = (
            "computed: current_price * latest_shares_outstanding"
        )
        company["fact_metadata"]["market_cap"] = derived_metadata(
            "market_snapshot", ("current_price", "shares_outstanding")
        )
    company["data_freshness"]["market_price_date"] = quote["timestamp"]


def free_cash_flow(fields: dict[str, Any]) -> Decimal | None:
    operating = fields.get("operating_cash_flow")
    capex = fields.get("capital_expenditures")
    if not isinstance(operating, Decimal) or not isinstance(capex, Decimal):
        return None
    return operating - abs(capex)


def remember_financial_period(company: dict[str, Any], metadata: dict[str, Any]) -> None:
    filed = metadata.get("filed")
    period = metadata.get("fp")
    period_end = metadata.get("period_end")
    current_filed = company["data_freshness"].get("latest_financial_filed")
    if isinstance(filed, str) and (not isinstance(current_filed, str) or filed > current_filed):
        company["data_freshness"]["latest_financial_filed"] = filed
        company["data_freshness"]["latest_financial_period"] = period
        company["data_freshness"]["latest_financial_period_end"] = period_end


def derived_metadata(basis: str, fields: tuple[str, ...]) -> dict[str, Any]:
    return {
        "basis": basis,
        "type": "derived_metric",
        "derived_from": list(fields),
        "confidence": "HIGH",
    }


def eps_method(fields: dict[str, Any], selections: dict[str, Any]) -> str | None:
    if fields.get("eps") is None:
        return None
    metadata = fields.get("fact_metadata", {}).get("eps")
    if isinstance(metadata, dict):
        return str(metadata.get("basis"))
    selection = selections.get("eps")
    if selection is not None:
        return str(selection.basis)
    return None
