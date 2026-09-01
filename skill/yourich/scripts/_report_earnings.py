from __future__ import annotations

from typing import Any

from _report_format import localized
from _report_types import ReportSection


def earnings_section(
    research_context: dict[str, Any] | None, title: str, language: str
) -> ReportSection:
    earnings = earnings_context(research_context)
    if earnings is None:
        return ReportSection("earnings", title, localized("Insufficient evidence", language), [])
    return ReportSection(
        "earnings",
        title,
        localized(
            "Latest official earnings evidence is summarized separately from SEC facts.", language
        ),
        earnings_rows(earnings, language),
    )


def earnings_context(research_context: dict[str, Any] | None) -> dict[str, Any] | None:
    if research_context is None:
        return None
    context = research_context.get("earnings_context")
    return context if isinstance(context, dict) else None


def earnings_rows(earnings: dict[str, Any], language: str) -> list[dict[str, str]]:
    thesis = earnings.get("thesis_change")
    thesis_status = (
        str(thesis.get("status")) if isinstance(thesis, dict) else "INSUFFICIENT_EVIDENCE"
    )
    rows = [
        earnings_row("Revenue growth", earnings_change_label(earnings, "revenue"), language),
        earnings_row("Margin", earnings_change_label(earnings, "margin"), language),
        earnings_row("Cash flow", earnings_change_label(earnings, "fcf"), language),
        earnings_row("Guidance", first_guidance_change(earnings), language),
        earnings_row("Thesis Change", thesis_status, language),
    ]
    commentary = earnings.get("management_commentary")
    if isinstance(commentary, list) and commentary:
        first = commentary[0]
        if isinstance(first, dict):
            rows.append(earnings_row("Management Focus", str(first.get("category")), language))
    return rows


def first_guidance_change(earnings: dict[str, Any]) -> str:
    changes = earnings.get("guidance_changes")
    if not isinstance(changes, list) or not changes:
        return "INSUFFICIENT_EVIDENCE"
    first = changes[0]
    return str(first.get("status")) if isinstance(first, dict) else "INSUFFICIENT_EVIDENCE"


def earnings_change_label(earnings: dict[str, Any], metric_fragment: str) -> str:
    changes = earnings.get("changes")
    if not isinstance(changes, list):
        return "INSUFFICIENT_EVIDENCE"
    for item in changes:
        if isinstance(item, dict) and metric_fragment in str(item.get("change_type", "")):
            return str(item.get("status"))
    return "INSUFFICIENT_EVIDENCE"


def earnings_row(label: str, value: str, language: str) -> dict[str, str]:
    if language != "ko":
        return {"Item": label, "Assessment": value}
    labels = {
        "Revenue growth": "매출 성장",
        "Margin": "마진",
        "Cash flow": "현금흐름",
        "Guidance": "가이던스",
        "Thesis Change": "투자 논리 변화",
        "Management Focus": "경영진 강조점",
    }
    return {"항목": labels.get(label, label), "평가": value}
