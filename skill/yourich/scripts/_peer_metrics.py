from __future__ import annotations

from decimal import Decimal
from typing import Any, Final

from _core import decimal_or_none, percent
from _valuation_intelligence import build_valuation_intelligence
from financial_health import financial_health
from valuation import valuation

METRICS: Final = (
    "revenue",
    "revenue_growth",
    "net_margin",
    "operating_margin",
    "fcf_margin",
    "roe",
    "roa",
    "debt_to_equity",
    "current_ratio",
    "pe",
    "ps",
    "pb",
    "fcf_yield",
    "required_fcf_growth",
)
VALUATION_METRICS: Final = {"pe", "ps", "pb", "fcf_yield"}
HEALTH_METRICS: Final = {
    "revenue_growth",
    "net_margin",
    "operating_margin",
    "fcf_margin",
    "roe",
    "roa",
    "debt_to_equity",
    "current_ratio",
}
MIN_PERCENTILE_PEERS: Final = 2


def normalized_metrics(company: dict[str, Any]) -> dict[str, dict[str, Any]]:
    value = valuation(company)
    health = financial_health(company)
    intelligence = build_valuation_intelligence(company)
    metrics = {
        "revenue": metric_payload(company.get("revenue"), basis_for(company, "revenue")),
        "base_scenario_position": {
            "value": intelligence["margin_of_safety"]["position"],
            "basis": "base_scenario",
        },
    }
    for name in VALUATION_METRICS:
        metrics[name] = metric_from(value.get("metrics", {}), name)
    for name in HEALTH_METRICS:
        metrics[name] = metric_from(health.get("metrics", {}), name)
    metrics["required_fcf_growth"] = {
        "value": intelligence["reverse_dcf"].get("required_fcf_cagr"),
        "required_fcf_cagr": intelligence["reverse_dcf"].get("required_fcf_cagr"),
        "basis": "reverse_dcf",
    }
    return metrics


def peer_aggregates(
    company_metrics: dict[str, dict[str, Any]], peer_metrics: list[dict[str, dict[str, Any]]]
) -> dict[str, Any]:
    aggregates = []
    warnings = []
    for metric in METRICS:
        compatible = compatible_peer_values(company_metrics, peer_metrics, metric)
        if compatible["basis_mismatch"]:
            warnings.append("PEER_METRIC_BASIS_MISMATCH")
        values = compatible["values"]
        company_value = decimal_or_none(company_metrics.get(metric, {}).get("value"))
        if company_value is None or not values:
            continue
        median_value = median(sorted(values))
        aggregates.append(
            {
                "metric": metric,
                "company": str(company_value),
                "peer_median": str(median_value),
                "peer_min": str(min(values)),
                "peer_max": str(max(values)),
                "premium_percent": pct_string(percent(company_value - median_value, median_value)),
                "percentile": (
                    percentile_rank(values, company_value)
                    if len(values) >= MIN_PERCENTILE_PEERS
                    else None
                ),
                "peer_count": len(values),
                "basis": company_metrics.get(metric, {}).get("basis"),
            }
        )
    return {"aggregates": aggregates, "warnings": sorted(set(warnings))}


def compatible_peer_values(
    company_metrics: dict[str, dict[str, Any]],
    peers: list[dict[str, dict[str, Any]]],
    metric: str,
) -> dict[str, Any]:
    company_basis = company_metrics.get(metric, {}).get("basis")
    values = []
    basis_mismatch = False
    for peer in peers:
        peer_metric = peer.get(metric, {})
        if peer_metric.get("basis") != company_basis:
            basis_mismatch = True
            continue
        value = decimal_or_none(peer_metric.get("value"))
        if value is not None:
            values.append(value)
    return {"values": values, "basis_mismatch": basis_mismatch}


def metric_from(metrics: Any, key: str) -> dict[str, Any]:
    metric = metrics.get(key, {}) if isinstance(metrics, dict) else {}
    return {
        "value": metric.get("value") if isinstance(metric, dict) else None,
        "basis": metric.get("basis") if isinstance(metric, dict) else None,
        "type": metric.get("type") if isinstance(metric, dict) else None,
    }


def metric_payload(value: Any, basis: str | None) -> dict[str, Any]:
    return {"value": value, "basis": basis}


def basis_for(company: dict[str, Any], field: str) -> str | None:
    metadata = company.get("fact_metadata")
    if not isinstance(metadata, dict):
        return None
    item = metadata.get(field)
    return str(item.get("basis")) if isinstance(item, dict) and item.get("basis") else None


def median(values: list[Decimal]) -> Decimal:
    midpoint = len(values) // 2
    if len(values) % 2:
        return values[midpoint]
    return (values[midpoint - 1] + values[midpoint]) / Decimal("2")


def percentile_rank(values: list[Decimal], company_value: Decimal) -> int:
    ranked = sorted([*values, company_value])
    below_or_equal = sum(1 for value in ranked if value <= company_value)
    return int(
        (Decimal(below_or_equal) / Decimal(len(ranked)) * Decimal("100")).to_integral_value()
    )


def pct_string(value: Decimal | None) -> str | None:
    return None if value is None else str(value.quantize(Decimal("0.1")))
