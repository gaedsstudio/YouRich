from __future__ import annotations

from decimal import ROUND_FLOOR, Decimal
from typing import Any, Final

from _core import decimal_or_none, percent, ratio
from _reverse_dcf import (
    DEFAULT_DISCOUNT_RATE,
    DEFAULT_FORECAST_YEARS,
    DEFAULT_TERMINAL_GROWTH,
    dcf_value,
)

SCENARIO_GROWTH_DEFAULTS: Final = {
    "bear": Decimal("0"),
    "base": Decimal("5"),
    "bull": Decimal("10"),
}
CLASSIFICATION_THRESHOLDS: Final = {
    "material_downside": Decimal("-25"),
    "modest_downside": Decimal("-10"),
    "near": Decimal("10"),
    "modest_upside": Decimal("25"),
}
MIN_HISTORY_POINTS: Final = 3
CLASSIFICATIONS: Final = (
    ("MATERIAL_DOWNSIDE", CLASSIFICATION_THRESHOLDS["material_downside"]),
    ("MODEST_DOWNSIDE", CLASSIFICATION_THRESHOLDS["modest_downside"]),
    ("NEAR_SCENARIO_VALUE", CLASSIFICATION_THRESHOLDS["near"]),
    ("MODEST_UPSIDE", CLASSIFICATION_THRESHOLDS["modest_upside"]),
)


def scenario_valuation(
    company: dict[str, Any],
    *,
    discount_rate: Decimal = DEFAULT_DISCOUNT_RATE,
    terminal_growth: Decimal = DEFAULT_TERMINAL_GROWTH,
    forecast_years: int = DEFAULT_FORECAST_YEARS,
    growth_overrides: dict[str, Decimal] | None = None,
    earnings_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    current_fcf = decimal_or_none(company.get("free_cash_flow"))
    price = decimal_or_none(company.get("current_price"))
    shares = share_count(company)
    if current_fcf is None or current_fcf <= 0 or shares is None or shares <= 0:
        return unavailable_scenarios()
    assumptions = {
        "forecast_years": forecast_years,
        "discount_rate": discount_rate,
        "terminal_growth": terminal_growth,
    }
    guidance_growth = near_term_guidance_growth(company, earnings_context)
    scenarios = []
    for name in ("bear", "base", "bull"):
        growth, source = scenario_growth(company, name, growth_overrides)
        enterprise_value = dcf_value(current_fcf, growth, assumptions)
        equity_value = enterprise_value - net_debt(company)
        midpoint = equity_value / shares
        sources = {
            "fcf_growth": source,
            "fcf_margin": fcf_margin_source(company),
            "discount_rate": "default" if discount_rate == DEFAULT_DISCOUNT_RATE else "explicit",
            "terminal_growth": "default"
            if terminal_growth == DEFAULT_TERMINAL_GROWTH
            else "explicit",
        }
        if guidance_growth is not None and name == "base":
            sources["near_term_revenue_growth"] = "official_guidance"
        scenarios.append(
            {
                "scenario": name,
                "fcf_growth": growth,
                "forecast_years": forecast_years,
                "discount_rate": discount_rate,
                "terminal_growth": terminal_growth,
                "value_midpoint": midpoint.quantize(Decimal("0.01")),
                "value_range": value_range(midpoint),
                "position": classify_position(price, midpoint),
                "assumption_sources": sources,
            }
        )
    return scenarios


def scenario_growth(
    company: dict[str, Any], scenario: str, overrides: dict[str, Decimal] | None
) -> tuple[Decimal, str]:
    if overrides is not None and scenario in overrides:
        return overrides[scenario], "explicit"
    history = historical_fcf_cagr(company)
    if history is not None:
        adjustment = {"bear": Decimal("-5"), "base": Decimal("0"), "bull": Decimal("5")}[scenario]
        return max(Decimal("-10"), history + adjustment), "historical"
    return SCENARIO_GROWTH_DEFAULTS[scenario], "default"


def historical_fcf_cagr(company: dict[str, Any]) -> Decimal | None:
    annuals = company.get("annuals")
    if not isinstance(annuals, list) or len(annuals) < MIN_HISTORY_POINTS:
        return None
    values = []
    for item in annuals[-5:]:
        if isinstance(item, dict):
            value = decimal_or_none(item.get("free_cash_flow"))
            if value is not None and value > 0:
                values.append(value)
    if len(values) < MIN_HISTORY_POINTS:
        return None
    start = values[0]
    end = values[-1]
    years = Decimal(len(values) - 1)
    return (((end / start) ** (Decimal("1") / years)) - Decimal("1")) * Decimal("100")


def value_range(midpoint: Decimal) -> str:
    if midpoint <= 0:
        return "Unavailable"
    low = midpoint * Decimal("0.925")
    high = midpoint * Decimal("1.075")
    increment = range_increment(midpoint)
    rounded_low = floor_to_increment(low, increment)
    rounded_high = ceil_to_increment(high, increment)
    if rounded_low == rounded_high:
        rounded_high += increment
    return f"${format_range_value(rounded_low)}-{format_range_value(rounded_high)}"


def classify_position(price: Decimal | None, base_midpoint: Decimal | None) -> str:
    if price is None or price <= 0 or base_midpoint is None or base_midpoint <= 0:
        return "INSUFFICIENT_DATA"
    difference = percent(base_midpoint - price, price)
    if difference is None:
        return "INSUFFICIENT_DATA"
    for label, threshold in CLASSIFICATIONS:
        if difference < threshold:
            return label
    return "MATERIAL_UPSIDE"


def share_count(company: dict[str, Any]) -> Decimal | None:
    shares = decimal_or_none(company.get("shares_outstanding"))
    if shares is not None:
        return shares
    return ratio(
        decimal_or_none(company.get("market_cap")), decimal_or_none(company.get("current_price"))
    )


def net_debt(company: dict[str, Any]) -> Decimal:
    cash = decimal_or_none(company.get("cash")) or Decimal("0")
    debt = decimal_or_none(company.get("total_debt")) or Decimal("0")
    return debt - cash


def fcf_margin_source(company: dict[str, Any]) -> str:
    basis = company.get("fact_metadata", {}).get("free_cash_flow", {}).get("basis")
    return "latest_ttm" if basis == "ttm" else str(basis or "default")


def near_term_guidance_growth(
    company: dict[str, Any], earnings_context: dict[str, Any] | None
) -> Decimal | None:
    if earnings_context is None:
        return None
    current_revenue = decimal_or_none(company.get("revenue"))
    if current_revenue is None or current_revenue <= 0:
        return None
    guidance = earnings_context.get("guidance")
    if not isinstance(guidance, list):
        return None
    for item in guidance:
        if isinstance(item, dict) and item.get("metric") == "revenue":
            midpoint = decimal_or_none(item.get("midpoint"))
            if midpoint is not None:
                return percent(midpoint * Decimal("4") - current_revenue, current_revenue)
    return None


def unavailable_scenarios() -> list[dict[str, Any]]:
    return [
        {
            "scenario": name,
            "status": "INSUFFICIENT_DATA",
            "value_midpoint": None,
            "value_range": "Unavailable",
            "position": "INSUFFICIENT_DATA",
            "assumption_sources": {},
        }
        for name in ("bear", "base", "bull")
    ]


def range_increment(midpoint: Decimal) -> Decimal:
    if midpoint >= Decimal("50"):
        return Decimal("5")
    if midpoint >= Decimal("10"):
        return Decimal("1")
    return Decimal("0.1")


def floor_to_increment(value: Decimal, increment: Decimal) -> Decimal:
    return (value / increment).to_integral_value(rounding=ROUND_FLOOR) * increment


def ceil_to_increment(value: Decimal, increment: Decimal) -> Decimal:
    floor = floor_to_increment(value, increment)
    return floor if floor == value else floor + increment


def format_range_value(value: Decimal) -> str:
    return f"{value:.1f}" if value % 1 else f"{value:.0f}"
