from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from _core import decimal_or_none

ANNUAL_FALLBACK_WARNING: Final = "TTM_INCOMPLETE_USING_ANNUAL_FALLBACK"
TTM_BASIS: Final = "ttm"
LATEST_ANNUAL_BASIS: Final = "latest_annual"
LATEST_SNAPSHOT_BASIS: Final = "latest_snapshot"
MARKET_SNAPSHOT_BASIS: Final = "market_snapshot"
DERIVED_BASIS: Final = "derived"
UNAVAILABLE_BASIS: Final = "unavailable"


@dataclass(frozen=True, slots=True)
class BasisMetricSpec:
    formula: str
    input_name: str
    basis: str


@dataclass(frozen=True, slots=True)
class NormalizedEps:
    value: Decimal | None
    formula: str
    basis: str


def basis_for(fact_metadata: object, field: str, fallback: str = UNAVAILABLE_BASIS) -> str:
    if not isinstance(fact_metadata, dict):
        return fallback
    item = fact_metadata.get(field)
    if not isinstance(item, dict):
        return fallback
    basis = item.get("basis")
    return str(basis) if basis else fallback


def pe_spec(fact_metadata: object) -> BasisMetricSpec:
    basis = basis_for(fact_metadata, "eps")
    match basis:
        case "ttm":
            return BasisMetricSpec("price / ttm diluted eps", "ttm_diluted_eps", TTM_BASIS)
        case "latest_annual":
            return BasisMetricSpec(
                "price / latest annual diluted eps",
                "latest_annual_diluted_eps",
                LATEST_ANNUAL_BASIS,
            )
        case _:
            return BasisMetricSpec("price / diluted eps", "diluted_eps", basis)


def ps_spec(fact_metadata: object) -> BasisMetricSpec:
    return duration_spec(
        basis_for(fact_metadata, "revenue"),
        TTM_BASIS,
        "market cap / ttm revenue",
        "ttm_revenue",
        "market cap / latest annual revenue",
        "latest_annual_revenue",
        "market cap / revenue",
        "revenue",
    )


def fcf_yield_spec(fact_metadata: object) -> BasisMetricSpec:
    return duration_spec(
        basis_for(fact_metadata, "free_cash_flow", DERIVED_BASIS),
        TTM_BASIS,
        "ttm free cash flow / market cap * 100",
        "ttm_free_cash_flow",
        "latest annual free cash flow / market cap * 100",
        "latest_annual_free_cash_flow",
        "free cash flow / market cap * 100",
        "free_cash_flow",
    )


def earnings_yield_spec(fact_metadata: object) -> BasisMetricSpec:
    return duration_spec(
        basis_for(fact_metadata, "net_income"),
        TTM_BASIS,
        "ttm net income / market cap * 100",
        "ttm_net_income",
        "latest annual net income / market cap * 100",
        "latest_annual_net_income",
        "net income / market cap * 100",
        "net_income",
    )


def duration_spec(
    basis: str,
    ttm_basis: str,
    ttm_formula: str,
    ttm_input: str,
    annual_formula: str,
    annual_input: str,
    fallback_formula: str,
    fallback_input: str,
) -> BasisMetricSpec:
    match basis:
        case "ttm":
            return BasisMetricSpec(ttm_formula, ttm_input, ttm_basis)
        case "latest_annual":
            return BasisMetricSpec(annual_formula, annual_input, LATEST_ANNUAL_BASIS)
        case _:
            return BasisMetricSpec(fallback_formula, fallback_input, basis)


def annual_fallback_warnings(fact_metadata: object) -> list[str]:
    fields = ("eps", "revenue", "free_cash_flow", "net_income")
    if any(basis_for(fact_metadata, field) == LATEST_ANNUAL_BASIS for field in fields):
        return [ANNUAL_FALLBACK_WARNING]
    return []


def normalized_eps(company: dict[str, object], fact_metadata: object) -> NormalizedEps:
    annual_values = annual_eps_values(company.get("annuals"))
    if annual_values:
        return NormalizedEps(
            sum(annual_values, Decimal("0")) / Decimal(len(annual_values)),
            "average available annual EPS",
            LATEST_ANNUAL_BASIS,
        )
    selected = decimal_or_none(company.get("eps"))
    selected_basis = basis_for(fact_metadata, "eps", UNAVAILABLE_BASIS)
    return NormalizedEps(selected, "current selected EPS", selected_basis)


def annual_eps_values(annuals: object) -> list[Decimal]:
    values: list[Decimal] = []
    if isinstance(annuals, list):
        for item in annuals:
            if isinstance(item, dict):
                value = decimal_or_none(item.get("eps"))
                if value is not None:
                    values.append(value)
    return values


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
