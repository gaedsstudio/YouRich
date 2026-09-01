from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from _core import decimal_or_none

if TYPE_CHECKING:
    from _earnings_types import EarningsMetric, EarningsRelease, GuidanceItem

GUIDANCE_EPSILON = Decimal("1")
STRONG_THESIS_SCORE = 3


def compare_guidance(current: GuidanceItem, previous: GuidanceItem | None) -> str:
    status = guidance_comparison_status(current, previous)
    return "REITERATED" if status is None else status


def guidance_comparison_status(current: GuidanceItem, previous: GuidanceItem | None) -> str | None:
    if current.status == "withdrawn":
        return "WITHDRAWN"
    if previous is None:
        return "NEW"
    if current.metric != previous.metric or current.period != previous.period:
        return "NOT_COMPARABLE"
    current_midpoint = guidance_midpoint(current)
    previous_midpoint = guidance_midpoint(previous)
    if current_midpoint is None or previous_midpoint is None:
        return "INSUFFICIENT_EVIDENCE"
    return guidance_delta_status(current_midpoint - previous_midpoint)


def guidance_delta_status(delta: Decimal) -> str | None:
    if delta > GUIDANCE_EPSILON:
        return "RAISED"
    if delta < -GUIDANCE_EPSILON:
        return "LOWERED"
    return None


def guidance_vs_actual(previous: GuidanceItem, actual: EarningsMetric) -> str:
    if previous.metric != actual.metric:
        return "NOT_COMPARABLE"
    actual_value = decimal_or_none(actual.value)
    low = decimal_or_none(previous.low)
    high = decimal_or_none(previous.high)
    if actual_value is None or low is None or high is None:
        return "NOT_COMPARABLE"
    if actual_value < low:
        return "BELOW_GUIDANCE"
    if actual_value > high:
        return "ABOVE_GUIDANCE"
    return "WITHIN_GUIDANCE"


def guidance_changes(
    latest: EarningsRelease | None, previous: EarningsRelease | None
) -> list[dict[str, Any]]:
    if latest is None:
        return []
    return [
        {
            "metric": item.metric,
            "period": item.period,
            "status": compare_guidance(item, matching_guidance(item, previous)),
            "current": item.to_dict(),
            "previous": (
                matched.to_dict()
                if (matched := matching_guidance(item, previous)) is not None
                else None
            ),
        }
        for item in latest.guidance
    ]


def actual_comparisons(
    latest: EarningsRelease | None, previous: EarningsRelease | None
) -> list[dict[str, Any]]:
    if latest is None or previous is None:
        return []
    comparisons = []
    for item in previous.guidance:
        actual = latest.reported_metrics.get(item.metric)
        if actual is None:
            continue
        comparisons.append(
            {
                "metric": item.metric,
                "status": guidance_vs_actual(item, actual),
                "previous_guidance": item.to_dict(),
                "actual": actual.to_dict(),
            }
        )
    return comparisons


def management_tone_changes(
    latest: EarningsRelease | None, previous: EarningsRelease | None
) -> list[dict[str, Any]]:
    if latest is None or previous is None:
        return []
    changes = []
    for current in latest.management_commentary:
        prior = next(
            (item for item in previous.management_commentary if item.category == current.category),
            None,
        )
        if prior is None:
            prior = previous.management_commentary[0] if previous.management_commentary else None
        if prior is None:
            changes.append({"category": current.category, "status": "INSUFFICIENT_EVIDENCE"})
            continue
        changes.append(
            {
                "category": current.category,
                "status": statement_change_status(current.statement, prior.statement),
                "current": current.to_dict(),
                "previous": prior.to_dict(),
            }
        )
    return changes


def earnings_changes(
    latest: EarningsRelease | None,
    previous: EarningsRelease | None,
    guidance_delta: list[dict[str, Any]],
) -> list[dict[str, str]]:
    if latest is None:
        return []
    changes = metric_changes(latest, previous)
    changes.extend(guidance_change_summary(guidance_delta))
    return changes


def thesis_change(changes: list[dict[str, str]], latest: EarningsRelease | None) -> dict[str, Any]:
    if latest is None or not changes:
        return {"status": "INSUFFICIENT_EVIDENCE", "drivers": []}
    score = sum(change_score(item["status"]) for item in changes)
    if score >= STRONG_THESIS_SCORE:
        status = "STRENGTHENED"
    elif score > 0:
        status = "SLIGHTLY_STRENGTHENED"
    elif score <= -STRONG_THESIS_SCORE:
        status = "WEAKENED"
    elif score < 0:
        status = "SLIGHTLY_WEAKENED"
    else:
        status = "UNCHANGED"
    return {"status": status, "drivers": changes}


def metric_mismatches(
    latest: EarningsRelease | None, deterministic_financials: dict[str, Any] | None
) -> list[dict[str, str]]:
    if latest is None or deterministic_financials is None:
        return []
    mismatches = []
    for metric in ("revenue", "net_income", "free_cash_flow"):
        earnings = latest.reported_metrics.get(metric)
        deterministic = decimal_or_none(deterministic_financials.get(metric))
        earnings_value = decimal_or_none(earnings.value) if earnings is not None else None
        if deterministic is None or earnings_value is None:
            continue
        comparable = (
            deterministic / Decimal("1000000000")
            if deterministic > Decimal("1000000")
            else deterministic
        )
        if abs(comparable - earnings_value) > Decimal("0.5"):
            mismatches.append(
                {
                    "metric": metric,
                    "reported_earnings_metric": str(earnings_value),
                    "deterministic_financial_metric": str(deterministic),
                }
            )
    return mismatches


def matching_guidance(
    current: GuidanceItem, previous: EarningsRelease | None
) -> GuidanceItem | None:
    if previous is None:
        return None
    return next(
        (
            item
            for item in previous.guidance
            if item.metric == current.metric and item.period == current.period
        ),
        None,
    )


def guidance_midpoint(item: GuidanceItem) -> Decimal | None:
    explicit = decimal_or_none(item.midpoint)
    if explicit is not None:
        return explicit
    low = decimal_or_none(item.low)
    high = decimal_or_none(item.high)
    if low is None or high is None:
        return None
    return (low + high) / Decimal("2")


def metric_changes(
    latest: EarningsRelease, previous: EarningsRelease | None
) -> list[dict[str, str]]:
    if previous is None:
        return []
    return [
        change
        for metric, positive, negative in (
            ("revenue_growth", "revenue_acceleration", "revenue_deceleration"),
            ("gross_margin", "margin_expansion", "margin_contraction"),
            ("free_cash_flow", "fcf_improvement", "fcf_deterioration"),
        )
        if (change := metric_change(latest, previous, metric, positive, negative)) is not None
    ]


def metric_change(
    latest: EarningsRelease,
    previous: EarningsRelease,
    metric: str,
    positive: str,
    negative: str,
) -> dict[str, str] | None:
    current = metric_value(latest, metric)
    prior = metric_value(previous, metric)
    if current is None or prior is None or abs(current - prior) < Decimal("2"):
        return None
    return {
        "change_type": positive if current > prior else negative,
        "metric": metric,
        "status": "IMPROVED" if current > prior else "WEAKENED",
    }


def metric_value(release: EarningsRelease, metric: str) -> Decimal | None:
    item = release.reported_metrics.get(metric)
    return decimal_or_none(item.value) if item is not None else None


def guidance_change_summary(guidance_delta: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "change_type": f"guidance_{str(item['status']).lower()}",
            "metric": str(item["metric"]),
            "status": str(item["status"]),
        }
        for item in guidance_delta
        if item.get("status") in {"RAISED", "LOWERED", "REITERATED", "WITHDRAWN"}
    ]


def statement_change_status(current: str, previous: str) -> str:
    current_lower = current.lower()
    previous_lower = previous.lower()
    if positive_terms(current_lower) and negative_terms(previous_lower):
        return "IMPROVED"
    if negative_terms(current_lower) and positive_terms(previous_lower):
        return "WEAKENED"
    if negative_terms(current_lower):
        return "NEW_RISK"
    return "UNCHANGED"


def positive_terms(text: str) -> bool:
    return any(term in text for term in ("improved", "strong", "accelerated", "expanded"))


def negative_terms(text: str) -> bool:
    return any(term in text for term in ("weak", "constrained", "declined", "pressure"))


def change_score(status: str) -> int:
    scores = {
        "IMPROVED": 1,
        "RAISED": 1,
        "REITERATED": 0,
        "WEAKENED": -1,
        "LOWERED": -1,
        "WITHDRAWN": -1,
    }
    return scores.get(status, 0)
