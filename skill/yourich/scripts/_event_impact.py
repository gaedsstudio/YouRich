from __future__ import annotations

from typing import Any

STRONG_THRESHOLD = 4


def thesis_impacts(events: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    impacts: dict[str, list[dict[str, str]]] = {}
    for event in events:
        for dimension in event.get("thesis_dimensions", []):
            if not isinstance(dimension, str):
                continue
            impacts.setdefault(dimension, []).append(
                {
                    "event_id": str(event.get("event_id") or ""),
                    "event_type": str(event.get("event_type") or ""),
                    "direction": str(event.get("direction") or "INSUFFICIENT_EVIDENCE"),
                    "materiality": str(event.get("materiality") or "MEDIUM"),
                }
            )
    return impacts


def event_impact_summary(events: list[dict[str, Any]]) -> str:
    if not events:
        return "INSUFFICIENT_EVIDENCE"
    positive = weighted_count(events, {"POSITIVE"})
    negative = weighted_count(events, {"NEGATIVE"})
    mixed = weighted_count(events, {"MIXED"})
    if positive > 0 and negative > 0:
        return mixed_summary(positive, negative)
    if mixed > 0 and (positive > 0 or negative > 0):
        return "MIXED_POSITIVE" if positive >= negative else "MIXED_NEGATIVE"
    return directional_summary(positive, negative, mixed)


def mixed_summary(positive: int, negative: int) -> str:
    return "MIXED_POSITIVE" if positive >= negative else "MIXED_NEGATIVE"


def directional_summary(positive: int, negative: int, mixed: int) -> str:
    if positive >= STRONG_THRESHOLD:
        return "STRONGLY_POSITIVE"
    if negative >= STRONG_THRESHOLD:
        return "STRONGLY_NEGATIVE"
    if positive > 0:
        return "POSITIVE"
    if negative > 0:
        return "NEGATIVE"
    return "NEUTRAL" if mixed == 0 else "MIXED_POSITIVE"


def weighted_count(events: list[dict[str, Any]], directions: set[str]) -> int:
    total = 0
    weights = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 4}
    for event in events:
        if event.get("direction") in directions:
            total += weights.get(str(event.get("materiality") or "MEDIUM"), 1)
    return total
