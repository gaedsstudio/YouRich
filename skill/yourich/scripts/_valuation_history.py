from __future__ import annotations

from decimal import Decimal
from typing import Any, Final

from _core import decimal_or_none

SUPPORTED_METRICS: Final = ("pe", "ps", "pb", "fcf_yield", "earnings_yield")
MIN_OBSERVATIONS: Final = 5


def historical_valuation(company: dict[str, Any]) -> dict[str, Any]:
    supplied = company.get("historical_valuation")
    metrics = []
    if isinstance(supplied, dict):
        for metric in SUPPORTED_METRICS:
            summary = metric_summary(metric, supplied.get(metric), current_value(company, metric))
            if summary is not None:
                metrics.append(summary)
    warnings = [] if metrics else ["HISTORICAL_VALUATION_UNAVAILABLE"]
    return {
        "metrics": metrics,
        "warnings": warnings,
        "data_source": "company_payload" if metrics else "unavailable",
    }


def metric_summary(
    metric: str, observations: object, current: Decimal | None
) -> dict[str, Any] | None:
    values = observed_values(observations)
    if current is None or len(values) < MIN_OBSERVATIONS:
        return None
    sorted_values = sorted(values)
    return {
        "metric": metric,
        "current": current,
        "median": median(sorted_values),
        "min": sorted_values[0],
        "max": sorted_values[-1],
        "percentile": percentile_rank(sorted_values, current),
        "period_years": len(values),
        "basis": "historical_observations",
    }


def observed_values(observations: object) -> list[Decimal]:
    if not isinstance(observations, list):
        return []
    values = []
    for observation in observations:
        if isinstance(observation, dict):
            value = decimal_or_none(observation.get("value"))
            if value is not None:
                values.append(value)
    return values


def median(values: list[Decimal]) -> Decimal:
    midpoint = len(values) // 2
    if len(values) % 2:
        return values[midpoint]
    return (values[midpoint - 1] + values[midpoint]) / Decimal("2")


def percentile_rank(values: list[Decimal], current: Decimal) -> int:
    below_or_equal = sum(1 for value in values if value <= current)
    return int(
        (Decimal(below_or_equal) / Decimal(len(values)) * Decimal("100")).to_integral_value()
    )


def current_value(company: dict[str, Any], metric: str) -> Decimal | None:
    price = decimal_or_none(company.get("current_price"))
    market_cap = decimal_or_none(company.get("market_cap"))
    revenue = decimal_or_none(company.get("revenue"))
    eps = decimal_or_none(company.get("eps"))
    book = decimal_or_none(company.get("book_value_per_share"))
    fcf = decimal_or_none(company.get("free_cash_flow"))
    net_income = decimal_or_none(company.get("net_income"))
    if metric == "pe":
        return ratio(price, eps)
    if metric == "ps":
        return ratio(market_cap, revenue)
    if metric == "pb":
        return ratio(price, book)
    if metric == "fcf_yield":
        return percent(fcf, market_cap)
    if metric == "earnings_yield":
        return percent(net_income, market_cap)
    return None


def ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def percent(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    result = ratio(numerator, denominator)
    return None if result is None else result * Decimal("100")
