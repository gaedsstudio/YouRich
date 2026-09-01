from __future__ import annotations

from typing import Any, Final

from _research_diff_rules import (
    change,
    guidance_status,
    latest_earnings_period,
    margin_position,
    metric_row,
    numeric_change,
    peer_tickers,
    reverse_dcf_metric,
    risk_statuses,
    snapshot_ref,
    status_change,
    valuation_metric,
)

FINANCIAL_FIELDS: Final = (
    "revenue",
    "revenue_growth",
    "net_income",
    "eps",
    "operating_margin",
    "net_margin",
    "free_cash_flow",
    "fcf_margin",
    "total_debt",
    "cash",
    "shares_outstanding",
)
FULL_CHANGE_COUNT: Final = 2


def compare_snapshots(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    warnings: list[str] = []
    changes.extend(financial_changes(previous, current, warnings))
    changes.extend(earnings_changes(previous, current))
    changes.extend(valuation_changes(previous, current))
    changes.extend(risk_changes(previous, current))
    changes.extend(peer_changes(previous, current, warnings))
    thesis = thesis_change(previous.get("thesis", {}), current.get("thesis", {}), changes)
    valuation = valuation_change(changes)
    if not changes:
        warnings.append("NO_MATERIAL_CHANGE")
    return {
        "ticker": current.get("ticker") or previous.get("ticker"),
        "status": "NO_MATERIAL_CHANGE" if not changes else "CHANGED",
        "previous_snapshot": snapshot_ref(previous),
        "current_snapshot": snapshot_ref(current),
        "changes": changes,
        "thesis_change": thesis,
        "valuation_change": valuation,
        "risk_change": risk_change(changes),
        "watch_variables": current.get("thesis", {}).get("watch_variables", []),
        "thesis_risk_conditions": current.get("thesis", {}).get("thesis_risk_conditions", []),
        "warnings": sorted(set(warnings)),
        "data_quality": current.get("data_quality", {}),
    }


def financial_changes(
    previous: dict[str, Any], current: dict[str, Any], warnings: list[str]
) -> list[dict[str, Any]]:
    rows = []
    for field in FINANCIAL_FIELDS:
        previous_row = metric_row(previous, "financials", field)
        current_row = metric_row(current, "financials", field)
        if previous_row.get("basis") != current_row.get("basis") and previous_row and current_row:
            warnings.append("SNAPSHOT_BASIS_CHANGED")
            rows.append(
                change("FINANCIAL", field, previous_row, current_row, "NOT_COMPARABLE", "MATERIAL")
            )
            continue
        rows.extend(numeric_change("FINANCIAL", field, previous_row, current_row))
    return rows


def earnings_changes(previous: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    previous_period = latest_earnings_period(previous)
    current_period = latest_earnings_period(current)
    if previous_period != current_period:
        rows.append(
            change(
                "EARNINGS",
                "latest_earnings_period",
                previous_period,
                current_period,
                "NEW",
                "NOTABLE",
            )
        )
    rows.extend(
        status_change(
            "GUIDANCE",
            "guidance_direction",
            guidance_status(previous),
            guidance_status(current),
        )
    )
    return rows


def valuation_changes(previous: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for field in ("pe", "ps", "fcf_yield"):
        rows.extend(
            numeric_change(
                "VALUATION",
                field,
                valuation_metric(previous, field),
                valuation_metric(current, field),
            )
        )
    rows.extend(
        numeric_change(
            "VALUATION",
            "required_fcf_cagr",
            reverse_dcf_metric(previous, "required_fcf_cagr"),
            reverse_dcf_metric(current, "required_fcf_cagr"),
        )
    )
    previous_position = margin_position(previous)
    current_position = margin_position(current)
    if previous_position != current_position:
        rows.append(
            change(
                "VALUATION",
                "base_scenario_position",
                previous_position,
                current_position,
                "NOT_COMPARABLE",
                "NOTABLE",
            )
        )
    return rows


def risk_changes(previous: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    previous_risks = risk_statuses(previous)
    current_risks = risk_statuses(current)
    for risk_id in sorted(set(previous_risks) | set(current_risks)):
        previous_status = previous_risks.get(risk_id)
        current_status = current_risks.get(risk_id)
        if previous_status == current_status:
            continue
        direction = "NEW" if current_status == "triggered" else "REMOVED"
        rows.append(change("RISK", risk_id, previous_status, current_status, direction, "MATERIAL"))
    return rows


def peer_changes(
    previous: dict[str, Any], current: dict[str, Any], warnings: list[str]
) -> list[dict[str, Any]]:
    previous_set = peer_tickers(previous)
    current_set = peer_tickers(current)
    if previous_set != current_set:
        warnings.append("PEER_SET_CHANGED")
        return [
            change("PEERS", "peer_set", previous_set, current_set, "NOT_COMPARABLE", "MATERIAL")
        ]
    return []


def thesis_change(previous: Any, current: Any, changes: list[dict[str, Any]]) -> dict[str, Any]:
    dimensions = {
        key: thesis_dimension(previous, current, key)
        for key in (
            "business_quality",
            "financial_quality",
            "growth_outlook",
            "valuation_attractiveness",
            "risk_level",
        )
    }
    positives = sum(1 for value in dimensions.values() if value == "IMPROVED")
    negatives = sum(1 for value in dimensions.values() if value == "WORSENED")
    financial_positive = sum(
        1 for item in changes if item["category"] == "FINANCIAL" and item["direction"] == "IMPROVED"
    )
    financial_negative = sum(
        1 for item in changes if item["category"] == "FINANCIAL" and item["direction"] == "WORSENED"
    )
    positives += financial_positive
    negatives += financial_negative
    return {"dimensions": dimensions, "overall_change": overall_change(positives, negatives)}


def thesis_dimension(previous: Any, current: Any, key: str) -> str:
    if not isinstance(previous, dict) or not isinstance(current, dict):
        return "INSUFFICIENT_EVIDENCE"
    if previous.get(key) == current.get(key):
        return "UNCHANGED"
    if label_score(current.get(key)) > label_score(previous.get(key)):
        return "IMPROVED"
    if label_score(current.get(key)) < label_score(previous.get(key)):
        return "WORSENED"
    return "NOT_COMPARABLE"


def overall_change(positives: int, negatives: int) -> str:
    if positives and negatives:
        return "MIXED"
    if positives >= FULL_CHANGE_COUNT:
        return "STRENGTHENED"
    if positives == 1:
        return "SLIGHTLY_STRENGTHENED"
    if negatives >= FULL_CHANGE_COUNT:
        return "WEAKENED"
    if negatives == 1:
        return "SLIGHTLY_WEAKENED"
    return "UNCHANGED"


def label_score(value: Any) -> int:
    scores = {"WEAK": 0, "HIGH": 0, "MODERATE": 1, "LOW": 2, "STRONG": 2}
    return scores.get(str(value), 1)


def valuation_change(changes: list[dict[str, Any]]) -> dict[str, str]:
    directions = [item["direction"] for item in changes if item["category"] == "VALUATION"]
    if "WORSENED" in directions:
        return {"direction": "WORSENED"}
    if "IMPROVED" in directions:
        return {"direction": "IMPROVED"}
    return {"direction": "UNCHANGED"}


def risk_change(changes: list[dict[str, Any]]) -> dict[str, str]:
    directions = [item["direction"] for item in changes if item["category"] == "RISK"]
    if "NEW" in directions:
        return {"direction": "WORSENED"}
    if "REMOVED" in directions:
        return {"direction": "IMPROVED"}
    return {"direction": "UNCHANGED"}
