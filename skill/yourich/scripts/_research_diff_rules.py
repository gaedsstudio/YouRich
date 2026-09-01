from __future__ import annotations

from decimal import Decimal
from typing import Any, Final

from _core import decimal_or_none

MATERIALITY: Final = {
    "revenue": Decimal("10"),
    "revenue_growth": Decimal("1"),
    "net_income": Decimal("10"),
    "eps": Decimal("5"),
    "operating_margin": Decimal("0.5"),
    "net_margin": Decimal("0.5"),
    "free_cash_flow": Decimal("10"),
    "fcf_margin": Decimal("0.5"),
    "total_debt": Decimal("10"),
    "cash": Decimal("10"),
    "shares_outstanding": Decimal("2"),
    "pe": Decimal("5"),
    "fcf_yield": Decimal("0.5"),
    "required_fcf_cagr": Decimal("2"),
}
HIGHER_IS_GOOD: Final = {
    "revenue",
    "revenue_growth",
    "net_income",
    "eps",
    "operating_margin",
    "net_margin",
    "free_cash_flow",
    "fcf_margin",
    "cash",
    "fcf_yield",
}
HIGHER_IS_BAD: Final = {"total_debt", "shares_outstanding", "pe", "required_fcf_cagr"}


def numeric_change(
    category: str, field: str, previous: dict[str, Any], current: dict[str, Any]
) -> list[dict[str, Any]]:
    previous_value = decimal_or_none(previous.get("value"))
    current_value = decimal_or_none(current.get("value"))
    if previous_value is None or current_value is None:
        return []
    delta = current_value - previous_value
    materiality = materiality_for(field, delta)
    if materiality == "IMMATERIAL":
        return []
    return [change(category, field, previous, current, direction_for(field, delta), materiality)]


def status_change(
    category: str, field: str, previous: str | None, current: str | None
) -> list[dict[str, Any]]:
    if previous == current:
        return []
    order = {"LOWERED": -1, "REITERATED": 0, "RAISED": 1}
    if previous in order and current in order:
        direction = "IMPROVED" if order[current] > order[previous] else "WORSENED"
    else:
        direction = "NOT_COMPARABLE"
    return [change(category, field, previous, current, direction, "MATERIAL")]


def direction_for(field: str, delta: Decimal) -> str:
    if delta == 0:
        return "UNCHANGED"
    if field in HIGHER_IS_GOOD:
        return "IMPROVED" if delta > 0 else "WORSENED"
    if field in HIGHER_IS_BAD:
        return "WORSENED" if delta > 0 else "IMPROVED"
    return "NOT_COMPARABLE"


def materiality_for(field: str, delta: Decimal) -> str:
    threshold = MATERIALITY.get(field, Decimal("1"))
    absolute = abs(delta)
    if absolute < threshold:
        return "IMMATERIAL"
    if absolute < threshold * Decimal("2"):
        return "NOTABLE"
    return "MATERIAL"


def metric_row(snapshot: dict[str, Any], section: str, field: str) -> dict[str, Any]:
    rows = snapshot.get(section, {})
    if not isinstance(rows, dict):
        return {}
    row = rows.get(field)
    return row if isinstance(row, dict) else {}


def valuation_metric(snapshot: dict[str, Any], field: str) -> dict[str, Any]:
    valuation = snapshot.get("valuation", {})
    metrics = valuation.get("metrics", {}) if isinstance(valuation, dict) else {}
    row = metrics.get(field) if isinstance(metrics, dict) else None
    return row if isinstance(row, dict) else {}


def reverse_dcf_metric(snapshot: dict[str, Any], field: str) -> dict[str, Any]:
    intelligence = snapshot.get("valuation_intelligence", {})
    reverse = intelligence.get("reverse_dcf", {}) if isinstance(intelligence, dict) else {}
    if isinstance(reverse, dict):
        return {"value": reverse.get(field), "basis": "market_snapshot"}
    return {}


def latest_earnings_period(snapshot: dict[str, Any]) -> str | None:
    earnings = snapshot.get("earnings", {})
    latest = earnings.get("latest_earnings", {}) if isinstance(earnings, dict) else {}
    if isinstance(latest, dict) and latest.get("period") is not None:
        return str(latest["period"])
    return None


def guidance_status(snapshot: dict[str, Any]) -> str | None:
    earnings = snapshot.get("earnings", {})
    changes = earnings.get("guidance_changes", []) if isinstance(earnings, dict) else []
    if isinstance(changes, list) and changes:
        first = changes[0]
        if isinstance(first, dict) and first.get("status") is not None:
            return str(first["status"])
    return None


def margin_position(snapshot: dict[str, Any]) -> str | None:
    intelligence = snapshot.get("valuation_intelligence", {})
    margin = intelligence.get("margin_of_safety", {}) if isinstance(intelligence, dict) else {}
    if isinstance(margin, dict) and margin.get("position") is not None:
        return str(margin["position"])
    return None


def risk_statuses(snapshot: dict[str, Any]) -> dict[str, str]:
    risks = snapshot.get("risk", {})
    checks = risks.get("risk_checks", []) if isinstance(risks, dict) else []
    return {
        str(item["id"]): str(item["status"])
        for item in checks
        if isinstance(item, dict) and item.get("id") is not None
    }


def peer_tickers(snapshot: dict[str, Any]) -> list[str]:
    context = snapshot.get("peer_context", {})
    peer_set = context.get("peer_set", {}) if isinstance(context, dict) else {}
    candidates = peer_set.get("candidates", []) if isinstance(peer_set, dict) else []
    return sorted(
        str(item.get("ticker"))
        for item in candidates
        if isinstance(item, dict) and item.get("ticker") is not None
    )


def snapshot_ref(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": snapshot.get("id") or snapshot.get("created_at"),
        "created_at": snapshot.get("created_at"),
        "fingerprint": snapshot.get("fingerprint"),
    }


def change(
    category: str,
    field: str,
    previous: Any,
    current: Any,
    direction: str,
    materiality: str,
) -> dict[str, Any]:
    return {
        "category": category,
        "field": field,
        "previous": previous,
        "current": current,
        "direction": direction,
        "materiality": materiality,
    }
