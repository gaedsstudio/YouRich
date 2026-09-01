from __future__ import annotations

from decimal import Decimal
from typing import Any, Final

from _core import decimal_or_none, percent
from _reverse_dcf import (
    DEFAULT_DISCOUNT_RATE,
    DEFAULT_FORECAST_YEARS,
    DEFAULT_TERMINAL_GROWTH,
    dcf_value,
    solve_reverse_dcf,
)
from _valuation_history import historical_valuation
from _valuation_scenarios import classify_position, scenario_valuation
from valuation import valuation

VERSION: Final = "0.7.0"
WARNING_BY_REVERSE_STATUS: Final = {
    "NO_VALID_FCF": "REVERSE_DCF_NO_VALID_FCF",
    "NO_NUMERICAL_SOLUTION": "REVERSE_DCF_NO_SOLUTION",
}


def build_valuation_intelligence(
    company: dict[str, Any],
    *,
    forecast_years: int = DEFAULT_FORECAST_YEARS,
    discount_rate: Decimal | int | str = DEFAULT_DISCOUNT_RATE,
    terminal_growth: Decimal | int | str = DEFAULT_TERMINAL_GROWTH,
    growth_overrides: dict[str, Decimal] | None = None,
    earnings_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    discount = decimal_or_none(discount_rate) or DEFAULT_DISCOUNT_RATE
    terminal = decimal_or_none(terminal_growth) or DEFAULT_TERMINAL_GROWTH
    current_valuation = valuation(company)
    reverse = solve_reverse_dcf(
        company,
        forecast_years=forecast_years,
        discount_rate=discount,
        terminal_growth=terminal,
    )
    scenarios = scenario_valuation(
        company,
        forecast_years=forecast_years,
        discount_rate=discount,
        terminal_growth=terminal,
        growth_overrides=growth_overrides,
        earnings_context=earnings_context,
    )
    history = historical_valuation(company)
    warnings = valuation_warnings(history, reverse, scenarios)
    base = scenario_by_name(scenarios, "base")
    return {
        "version": VERSION,
        "ticker": company.get("ticker"),
        "market_snapshot": market_snapshot(company),
        "current_valuation": current_valuation,
        "historical_valuation": history,
        "reverse_dcf": reverse,
        "scenarios": scenarios,
        "forward_bridge": forward_bridge(company, reverse, base),
        "sensitivity": sensitivity(company, forecast_years, discount, terminal),
        "valuation_drivers": valuation_drivers(company, forecast_years, discount, terminal),
        "margin_of_safety": margin_of_safety(company, base),
        "warnings": warnings,
        "data_quality": data_quality(company, history, reverse, scenarios),
    }


def market_snapshot(company: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_price": decimal_or_none(company.get("current_price")),
        "market_cap": decimal_or_none(company.get("market_cap")),
        "shares_outstanding": decimal_or_none(company.get("shares_outstanding")),
        "quote": company.get("market_quote"),
    }


def valuation_warnings(
    history: dict[str, Any], reverse: dict[str, Any], scenarios: list[dict[str, Any]]
) -> list[str]:
    warnings = [str(item) for item in history.get("warnings", [])]
    status = str(reverse.get("status"))
    if status in WARNING_BY_REVERSE_STATUS:
        warnings.append(WARNING_BY_REVERSE_STATUS[status])
    if any(item.get("position") == "INSUFFICIENT_DATA" for item in scenarios):
        warnings.append("SCENARIO_ASSUMPTION_WEAK")
    return sorted(set(warnings))


def sensitivity(
    company: dict[str, Any],
    forecast_years: int,
    discount_rate: Decimal,
    terminal_growth: Decimal,
) -> dict[str, Any]:
    fcf = decimal_or_none(company.get("free_cash_flow"))
    shares = decimal_or_none(company.get("shares_outstanding"))
    if fcf is None or fcf <= 0 or shares is None or shares <= 0:
        return {"table": [], "status": "INSUFFICIENT_DATA"}
    discounts = [discount_rate - Decimal("2"), discount_rate, discount_rate + Decimal("2")]
    terminals = [terminal_growth - Decimal("1"), terminal_growth, terminal_growth + Decimal("1")]
    rows = []
    for discount in discounts:
        row = {"discount_rate": discount}
        for terminal in terminals:
            if discount <= terminal:
                row[str(terminal)] = None
            else:
                assumptions = {
                    "forecast_years": forecast_years,
                    "discount_rate": discount,
                    "terminal_growth": terminal,
                }
                row[str(terminal)] = (dcf_value(fcf, Decimal("5"), assumptions) / shares).quantize(
                    Decimal("0.01")
                )
        rows.append(row)
    return {"status": "SOLVED", "table": rows, "terminal_growth_columns": terminals}


def valuation_drivers(
    company: dict[str, Any],
    forecast_years: int,
    discount_rate: Decimal,
    terminal_growth: Decimal,
) -> list[dict[str, Any]]:
    fcf = decimal_or_none(company.get("free_cash_flow"))
    shares = decimal_or_none(company.get("shares_outstanding"))
    if fcf is None or fcf <= 0 or shares is None or shares <= 0:
        return []
    base = driver_value(fcf, shares, forecast_years, Decimal("5"), discount_rate, terminal_growth)
    checks = [
        (
            "discount_rate",
            driver_value(
                fcf, shares, forecast_years, Decimal("5"), discount_rate + 2, terminal_growth
            ),
        ),
        (
            "terminal_growth",
            driver_value(
                fcf, shares, forecast_years, Decimal("5"), discount_rate, terminal_growth + 1
            ),
        ),
        (
            "fcf_growth",
            driver_value(
                fcf, shares, forecast_years, Decimal("10"), discount_rate, terminal_growth
            ),
        ),
    ]
    drivers = [
        {"driver": name, "impact_percent": percent(value - base, base)}
        for name, value in checks
        if base != 0
    ]
    return sorted(
        drivers, key=lambda item: abs(item["impact_percent"] or Decimal("0")), reverse=True
    )[:3]


def driver_value(
    fcf: Decimal,
    shares: Decimal,
    forecast_years: int,
    growth: Decimal,
    discount_rate: Decimal,
    terminal_growth: Decimal,
) -> Decimal:
    assumptions = {
        "forecast_years": forecast_years,
        "discount_rate": discount_rate,
        "terminal_growth": terminal_growth,
    }
    return dcf_value(fcf, growth, assumptions) / shares


def margin_of_safety(company: dict[str, Any], base: dict[str, Any] | None) -> dict[str, Any]:
    current_price = decimal_or_none(company.get("current_price"))
    midpoint = decimal_or_none(None if base is None else base.get("value_midpoint"))
    difference = (
        None
        if current_price is None or midpoint is None
        else percent(midpoint - current_price, current_price)
    )
    return {
        "current_price": current_price,
        "base_value_midpoint": midpoint,
        "difference_percent": difference,
        "position": classify_position(current_price, midpoint),
        "basis": "base_scenario",
    }


def forward_bridge(
    company: dict[str, Any], reverse: dict[str, Any], base: dict[str, Any] | None
) -> list[dict[str, Any]]:
    return [
        {"step": "current_ttm_fcf", "value": decimal_or_none(company.get("free_cash_flow"))},
        {"step": "required_fcf_growth", "value": reverse.get("required_fcf_cagr")},
        {"step": "base_scenario_growth", "value": None if base is None else base.get("fcf_growth")},
        {"step": "terminal_growth", "value": reverse.get("terminal_growth")},
    ]


def data_quality(
    company: dict[str, Any],
    history: dict[str, Any],
    reverse: dict[str, Any],
    scenarios: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "metric_bases": metric_bases(company),
        "historical_valuation_status": "AVAILABLE" if history.get("metrics") else "UNAVAILABLE",
        "reverse_dcf_status": reverse.get("status"),
        "scenario_status": (
            "INSUFFICIENT_DATA"
            if any(item.get("position") == "INSUFFICIENT_DATA" for item in scenarios)
            else "AVAILABLE"
        ),
    }


def metric_bases(company: dict[str, Any]) -> dict[str, str]:
    metadata = company.get("fact_metadata")
    if not isinstance(metadata, dict):
        return {}
    bases = {}
    for key in ("revenue", "net_income", "free_cash_flow", "eps"):
        item = metadata.get(key)
        if isinstance(item, dict) and item.get("basis"):
            bases[key] = str(item["basis"])
    return bases


def scenario_by_name(scenarios: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for scenario in scenarios:
        if scenario.get("scenario") == name:
            return scenario
    return None
