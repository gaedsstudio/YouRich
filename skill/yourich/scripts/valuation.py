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
from _valuation_basis import (
    LATEST_SNAPSHOT_BASIS,
    MARKET_SNAPSHOT_BASIS,
    annual_fallback_warnings,
    earnings_yield_spec,
    fcf_yield_spec,
    has_currency_mismatch,
    metric_periods,
    normalized_eps,
    pe_spec,
    provider_warnings,
    ps_spec,
    sources,
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
    warnings = provider_warnings(company) + annual_fallback_warnings(fact_metadata)
    if has_currency_mismatch(company):
        price = None
        market_cap = None
        warnings.append("CURRENCY_MISMATCH")
    eps_context = normalized_eps(company, fact_metadata)
    normalized_eps_value = eps_context.value
    graham = sqrt_decimal(
        None
        if normalized_eps_value is None or book is None
        else Decimal("22.5") * normalized_eps_value * book
    )
    ncav = None if assets_current is None or liabilities is None else assets_current - liabilities
    ncav_per_share = ratio(ncav, shares)
    intrinsic = (
        None
        if normalized_eps_value is None or normalized_eps_value <= 0
        else normalized_eps_value * Decimal("12")
    )
    reference = intrinsic if intrinsic is not None else graham
    margin = None if reference is None or price is None else percent(reference - price, reference)
    pe = pe_spec(fact_metadata)
    ps = ps_spec(fact_metadata)
    fcf_yield = fcf_yield_spec(fact_metadata)
    earnings_yield = earnings_yield_spec(fact_metadata)
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
                basis=MARKET_SNAPSHOT_BASIS,
            ),
            "pe": metric(
                ratio(price, eps),
                pe.formula,
                {"price": price, pe.input_name: eps},
                sources(field_sources, price="current_price", eps="eps"),
                metric_periods(fact_metadata, price="current_price", eps="eps"),
                basis=pe.basis,
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
                basis=LATEST_SNAPSHOT_BASIS,
            ),
            "ps": metric(
                ratio(market_cap, revenue),
                ps.formula,
                {"market_cap": market_cap, ps.input_name: revenue},
                sources(field_sources, market_cap="market_cap", revenue="revenue"),
                metric_periods(fact_metadata, price="current_price", revenue="revenue"),
                basis=ps.basis,
            ),
            "fcf_yield": metric(
                percent(fcf, market_cap),
                fcf_yield.formula,
                {fcf_yield.input_name: fcf, "market_cap": market_cap},
                sources(field_sources, free_cash_flow="free_cash_flow", market_cap="market_cap"),
                metric_periods(
                    fact_metadata,
                    price="current_price",
                    fcf="free_cash_flow",
                ),
                basis=fcf_yield.basis,
            ),
            "earnings_yield": metric(
                percent(decimal_or_none(company.get("net_income")), market_cap),
                earnings_yield.formula,
                {
                    earnings_yield.input_name: decimal_or_none(company.get("net_income")),
                    "market_cap": market_cap,
                },
                sources(field_sources, net_income="net_income", market_cap="market_cap"),
                metric_periods(fact_metadata, price="current_price", net_income="net_income"),
                basis=earnings_yield.basis,
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
                basis=LATEST_SNAPSHOT_BASIS,
            ),
            "graham_number": metric(
                graham,
                "sqrt(22.5 * normalized eps * book value per share)",
                {"normalized_eps": normalized_eps_value, "book_value_per_share": book},
                sources(
                    field_sources, normalized_eps="eps", book_value_per_share="book_value_per_share"
                ),
                metric_periods(fact_metadata, eps="eps", equity="shareholder_equity"),
                basis=eps_context.basis,
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
                basis=eps_context.basis,
            ),
            "normalized_eps": metric(
                normalized_eps_value,
                eps_context.formula,
                {"eps": normalized_eps_value},
                periods=metric_periods(fact_metadata, eps="eps"),
                basis=eps_context.basis,
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
