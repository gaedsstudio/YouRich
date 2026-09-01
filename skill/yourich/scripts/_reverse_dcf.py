from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Any, Final

from _core import decimal_or_none

MIN_GROWTH: Final = Decimal("-50")
MAX_GROWTH: Final = Decimal("100")
DEFAULT_FORECAST_YEARS: Final = 5
DEFAULT_DISCOUNT_RATE: Final = Decimal("10")
DEFAULT_TERMINAL_GROWTH: Final = Decimal("3")
SOLVE_STEPS: Final = 80
TOLERANCE: Final = Decimal("0.0001")


def solve_reverse_dcf(
    company: dict[str, Any],
    *,
    forecast_years: int = DEFAULT_FORECAST_YEARS,
    discount_rate: Decimal | int | str = DEFAULT_DISCOUNT_RATE,
    terminal_growth: Decimal | int | str = DEFAULT_TERMINAL_GROWTH,
) -> dict[str, Any]:
    assumptions = reverse_dcf_assumptions(forecast_years, discount_rate, terminal_growth)
    current_fcf = decimal_or_none(company.get("free_cash_flow"))
    market_cap = decimal_or_none(company.get("market_cap"))
    cash = decimal_or_none(company.get("cash")) or Decimal("0")
    debt = decimal_or_none(company.get("total_debt")) or Decimal("0")
    if current_fcf is None or current_fcf <= 0:
        return reverse_dcf_result("NO_VALID_FCF", assumptions, current_fcf, market_cap, cash, debt)
    if market_cap is None or market_cap <= 0:
        return reverse_dcf_result("NO_MARKET_CAP", assumptions, current_fcf, market_cap, cash, debt)
    if not valid_assumptions(assumptions):
        return reverse_dcf_result(
            "INVALID_ASSUMPTIONS", assumptions, current_fcf, market_cap, cash, debt
        )

    target_value = market_cap + debt - cash
    low_value = dcf_value(current_fcf, MIN_GROWTH, assumptions)
    high_value = dcf_value(current_fcf, MAX_GROWTH, assumptions)
    if target_value <= 0 or target_value < low_value or target_value > high_value:
        return reverse_dcf_result(
            "NO_NUMERICAL_SOLUTION", assumptions, current_fcf, market_cap, cash, debt
        )

    low = MIN_GROWTH
    high = MAX_GROWTH
    for _ in range(SOLVE_STEPS):
        mid = (low + high) / Decimal("2")
        value = dcf_value(current_fcf, mid, assumptions)
        if abs(value - target_value) <= TOLERANCE:
            return solved_result(mid, value, assumptions, current_fcf, market_cap, cash, debt)
        if value < target_value:
            low = mid
        else:
            high = mid
    mid = (low + high) / Decimal("2")
    return solved_result(
        mid,
        dcf_value(current_fcf, mid, assumptions),
        assumptions,
        current_fcf,
        market_cap,
        cash,
        debt,
    )


def reverse_dcf_assumptions(
    forecast_years: int, discount_rate: Decimal | int | str, terminal_growth: Decimal | int | str
) -> dict[str, Any]:
    return {
        "forecast_years": forecast_years,
        "discount_rate": decimal_or_none(discount_rate),
        "terminal_growth": decimal_or_none(terminal_growth),
        "discount_rate_source": "default"
        if decimal_or_none(discount_rate) == DEFAULT_DISCOUNT_RATE
        else "explicit",
        "terminal_growth_source": (
            "default" if decimal_or_none(terminal_growth) == DEFAULT_TERMINAL_GROWTH else "explicit"
        ),
    }


def valid_assumptions(assumptions: dict[str, Any]) -> bool:
    years = assumptions["forecast_years"]
    discount = assumptions["discount_rate"]
    terminal = assumptions["terminal_growth"]
    return (
        isinstance(years, int)
        and years > 0
        and isinstance(discount, Decimal)
        and isinstance(terminal, Decimal)
        and discount > terminal
        and discount > 0
    )


def dcf_value(current_fcf: Decimal, growth_rate: Decimal, assumptions: dict[str, Any]) -> Decimal:
    discount = assumptions["discount_rate"] / Decimal("100")
    terminal = assumptions["terminal_growth"] / Decimal("100")
    growth = growth_rate / Decimal("100")
    years = int(assumptions["forecast_years"])
    total = Decimal("0")
    with localcontext() as context:
        context.prec = 34
        for year in range(1, years + 1):
            fcf = current_fcf * ((Decimal("1") + growth) ** year)
            total += fcf / ((Decimal("1") + discount) ** year)
        terminal_fcf = current_fcf * ((Decimal("1") + growth) ** years)
        terminal_value = terminal_fcf * (Decimal("1") + terminal) / (discount - terminal)
        return total + terminal_value / ((Decimal("1") + discount) ** years)


def solved_result(
    growth: Decimal,
    solved_value: Decimal,
    assumptions: dict[str, Any],
    current_fcf: Decimal,
    market_cap: Decimal,
    cash: Decimal,
    debt: Decimal,
) -> dict[str, Any]:
    result = reverse_dcf_result("SOLVED", assumptions, current_fcf, market_cap, cash, debt)
    result["required_fcf_cagr"] = growth.quantize(Decimal("0.1"))
    result["solved_enterprise_value"] = solved_value.quantize(Decimal("0.01"))
    return result


def reverse_dcf_result(
    status: str,
    assumptions: dict[str, Any],
    current_fcf: Decimal | None,
    market_cap: Decimal | None,
    cash: Decimal,
    debt: Decimal,
) -> dict[str, Any]:
    return {
        "status": status,
        "required_fcf_cagr": None,
        "forecast_years": assumptions["forecast_years"],
        "discount_rate": assumptions["discount_rate"],
        "terminal_growth": assumptions["terminal_growth"],
        "current_fcf": current_fcf,
        "current_market_cap": market_cap,
        "cash": cash,
        "debt": debt,
        "net_debt": debt - cash,
        "growth_search_min": MIN_GROWTH,
        "growth_search_max": MAX_GROWTH,
        "assumption_sources": {
            "forecast_years": "default"
            if assumptions["forecast_years"] == DEFAULT_FORECAST_YEARS
            else "explicit",
            "discount_rate": assumptions["discount_rate_source"],
            "terminal_growth": assumptions["terminal_growth_source"],
            "net_debt": "latest_snapshot",
        },
    }
