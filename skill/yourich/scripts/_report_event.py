from __future__ import annotations

from typing import Any

from _report_types import ReportSection


def event_section(context: dict[str, Any], language: str) -> ReportSection:
    title = "주요 최근 이벤트" if language == "ko" else "Key Recent Events"
    events = context.get("material_events")
    rows = []
    if isinstance(events, list):
        rows = [event_row(event, language) for event in events[:5] if isinstance(event, dict)]
    body = body_text(context, language)
    return ReportSection("events", title, body, rows)


def event_row(event: dict[str, Any], language: str) -> dict[str, str]:
    if language == "ko":
        return {
            "일자": str(event.get("published_at") or ""),
            "유형": str(event.get("event_type") or ""),
            "방향": str(event.get("direction") or ""),
            "중요도": str(event.get("materiality") or ""),
            "근거": source_label(event),
        }
    return {
        "Date": str(event.get("published_at") or ""),
        "Type": str(event.get("event_type") or ""),
        "Direction": str(event.get("direction") or ""),
        "Materiality": str(event.get("materiality") or ""),
        "Source": source_label(event),
    }


def body_text(context: dict[str, Any], language: str) -> str:
    summary = str(context.get("event_impact_summary") or "INSUFFICIENT_EVIDENCE")
    if language == "ko":
        return f"공식 출처 기반 최근 이벤트의 종합 영향은 {summary}입니다."
    return f"Recent primary-source events have an overall impact of {summary}."


def source_label(event: dict[str, Any]) -> str:
    source_type = str(event.get("source_type") or "")
    if source_type.startswith("SEC"):
        return "SEC reported"
    return "Derived from official company source"
