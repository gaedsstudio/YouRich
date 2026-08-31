import argparse
from decimal import Decimal

from _core import (
    ToolError,
    add_input_arg,
    decimal_or_none,
    load_financials,
    metric,
    percent,
    ratio,
    sqrt_decimal,
    write_json,
)


def valuation(company: dict[str, object]) -> dict[str, object]:
    price = decimal_or_none(company.get("current_price"))
    market_cap = decimal_or_none(company.get("market_cap"))
    shares = decimal_or_none(company.get("shares_outstanding"))
    revenue = decimal_or_none(company.get("revenue"))
    eps = decimal_or_none(company.get("eps"))
    fcf = decimal_or_none(company.get("free_cash_flow"))
    assets_current = decimal_or_none(company.get("current_assets"))
    liabilities = decimal_or_none(company.get("total_liabilities"))
    book = decimal_or_none(company.get("book_value_per_share"))
    field_sources = company.get("field_sources", {})
    fact_metadata = company.get("fact_metadata", {})
    warnings = provider_warnings(company)
    if has_currency_mismatch(company):
        price = None
        market_cap = None
        warnings.append("CURRENCY_MISMATCH")
    normalized_eps = normalized_eps_value(company)
    graham = sqrt_decimal(
        None if normalized_eps is None or book is None else Decimal("22.5") * normalized_eps * book
    )
    ncav = None if assets_current is None or liabilities is None else assets_current - liabilities
    ncav_per_share = ratio(ncav, shares)
    intrinsic = (
        None if normalized_eps is None or normalized_eps <= 0 else normalized_eps * Decimal("12")
    )
    reference = intrinsic if intrinsic is not None else graham
    margin = None if reference is None or price is None else percent(reference - price, reference)
    return {
        "ticker": company.get("ticker"),
        "metrics": {
            "market_cap": metric(
                market_cap,
                "current price * latest shares outstanding",
                {"price": price, "shares_outstanding": shares},
                sources(
                    field_sources,
                    price="current_price",
                    shares_outstanding="shares_outstanding",
                ),
                metric_periods(fact_metadata, price="current_price", shares="shares_outstanding"),
            ),
            "pe": metric(
                ratio(price, eps),
                "price / ttm diluted eps",
                {"price": price, "ttm_diluted_eps": eps},
                sources(field_sources, price="current_price", eps="eps"),
                metric_periods(fact_metadata, price="current_price", eps="eps"),
            ),
            "pb": metric(
                ratio(price, book),
                "price / latest book value per share",
                {"price": price, "book_value_per_share": book},
                sources(
                    field_sources,
                    price="current_price",
                    book_value_per_share="book_value_per_share",
                ),
                metric_periods(
                    fact_metadata,
                    price="current_price",
                    equity="shareholder_equity",
                    shares="shares_outstanding",
                ),
            ),
            "ps": metric(
                ratio(market_cap, revenue),
                "market cap / ttm revenue",
                {"market_cap": market_cap, "ttm_revenue": revenue},
                sources(field_sources, market_cap="market_cap", revenue="revenue"),
                metric_periods(fact_metadata, price="current_price", revenue="revenue"),
            ),
            "fcf_yield": metric(
                percent(fcf, market_cap),
                "ttm free cash flow / market cap * 100",
                {"ttm_free_cash_flow": fcf, "market_cap": market_cap},
                sources(field_sources, free_cash_flow="free_cash_flow", market_cap="market_cap"),
                metric_periods(
                    fact_metadata,
                    price="current_price",
                    fcf="free_cash_flow",
                ),
            ),
            "earnings_yield": metric(
                percent(decimal_or_none(company.get("net_income")), market_cap),
                "ttm net income / market cap * 100",
                {
                    "ttm_net_income": decimal_or_none(company.get("net_income")),
                    "market_cap": market_cap,
                },
                sources(field_sources, net_income="net_income", market_cap="market_cap"),
                metric_periods(fact_metadata, price="current_price", net_income="net_income"),
            ),
            "ncav": metric(
                ncav,
                "current assets - total liabilities",
                {"current_assets": assets_current, "total_liabilities": liabilities},
                sources(
                    field_sources,
                    current_assets="current_assets",
                    total_liabilities="total_liabilities",
                ),
                metric_periods(
                    fact_metadata,
                    current_assets="current_assets",
                    liabilities="total_liabilities",
                ),
            ),
            "ncav_per_share": metric(
                ncav_per_share,
                "ncav / shares outstanding",
                {"ncav": ncav, "shares_outstanding": shares},
                sources(
                    field_sources, ncav="computed:ncav", shares_outstanding="shares_outstanding"
                ),
                metric_periods(fact_metadata, shares="shares_outstanding"),
            ),
            "price_to_ncav": metric(
                ratio(price, ncav_per_share),
                "price / ncav per share",
                {"price": price, "ncav_per_share": ncav_per_share},
                sources(
                    field_sources, price="current_price", ncav_per_share="computed:ncav_per_share"
                ),
                metric_periods(fact_metadata, price="current_price", shares="shares_outstanding"),
            ),
            "graham_number": metric(
                graham,
                "sqrt(22.5 * normalized eps * book value per share)",
                {"normalized_eps": normalized_eps, "book_value_per_share": book},
                sources(
                    field_sources, normalized_eps="eps", book_value_per_share="book_value_per_share"
                ),
                metric_periods(fact_metadata, eps="eps", equity="shareholder_equity"),
            ),
            "margin_of_safety": metric(
                margin,
                "(reference value - price) / reference value * 100",
                {"reference_value": reference, "price": price},
                sources(
                    field_sources,
                    reference_value="computed:intrinsic_or_graham",
                    price="current_price",
                ),
                metric_periods(fact_metadata, price="current_price", eps="eps"),
            ),
            "normalized_eps": metric(
                normalized_eps, "average available EPS, else latest EPS", {"eps": eps}
            ),
            "simple_dcf": metric(
                None, "not calculated without sufficient FCF growth assumptions", {}
            ),
        },
        "conclusion": valuation_conclusion(margin, ratio(price, eps), percent(fcf, market_cap)),
        "warnings": warnings,
        "market_quote": company.get("market_quote"),
        "data_freshness": company.get("data_freshness"),
        "data_quality": company.get("data_quality"),
    }


def normalized_eps_value(company: dict[str, object]) -> Decimal | None:
    annuals = company.get("annuals")
    values: list[Decimal] = []
    if isinstance(annuals, list):
        for item in annuals:
            if isinstance(item, dict):
                value = decimal_or_none(item.get("eps"))
                if value is not None:
                    values.append(value)
    if values:
        return sum(values, Decimal("0")) / Decimal(len(values))
    return decimal_or_none(company.get("eps"))


def sources(field_sources: object, **fields: str) -> dict[str, str | None]:
    if not isinstance(field_sources, dict):
        return {}
    resolved = {}
    for output_name, field_name in fields.items():
        if field_name.startswith("computed:"):
            resolved[output_name] = field_name
        else:
            value = field_sources.get(field_name)
            resolved[output_name] = str(value) if value is not None else None
    return resolved


def metric_periods(fact_metadata: object, **fields: str) -> dict[str, str | None]:
    if not isinstance(fact_metadata, dict):
        return {}
    periods = {}
    for output_name, field_name in fields.items():
        item = fact_metadata.get(field_name)
        if not isinstance(item, dict):
            continue
        periods[f"{output_name}_basis"] = str(item.get("basis")) if item.get("basis") else None
        periods[f"{output_name}_end"] = (
            str(item.get("period_end")) if item.get("period_end") else None
        )
        periods[f"{output_name}_filed"] = str(item.get("filed")) if item.get("filed") else None
        periods[f"{output_name}_date"] = (
            str(item.get("price_date")) if item.get("price_date") else None
        )
    return periods


def provider_warnings(company: dict[str, object]) -> list[str]:
    provider = company.get("provider")
    if not isinstance(provider, dict):
        return []
    warnings = provider.get("warnings")
    if not isinstance(warnings, list):
        return []
    return [str(item) for item in warnings]


def has_currency_mismatch(company: dict[str, object]) -> bool:
    financial = company.get("financial_currency")
    market = company.get("market_currency")
    return isinstance(financial, str) and isinstance(market, str) and financial != market


def valuation_conclusion(
    margin: Decimal | None,
    pe: Decimal | None,
    fcf_yield: Decimal | None,
) -> str:
    if margin is None and pe is None and fcf_yield is None:
        return "INSUFFICIENT DATA"
    if margin is not None and margin >= Decimal("25"):
        return "ATTRACTIVE VALUATION"
    if pe is not None and pe > Decimal("45"):
        return "EXPENSIVE"
    if fcf_yield is not None and fcf_yield >= Decimal("6"):
        return "ATTRACTIVE VALUATION"
    return "FAIRLY VALUED"


def main() -> int:
    parser = argparse.ArgumentParser()
    add_input_arg(parser)
    args = parser.parse_args()
    try:
        write_json(valuation(load_financials(args)))
    except ToolError as exc:
        write_json({"status": "error", "error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
