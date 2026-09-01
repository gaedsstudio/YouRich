from __future__ import annotations

from typing import Any

from _report_types import ReportSection


def tracking_section(context: dict[str, Any], language: str) -> ReportSection:
    title = "지난 분석 이후 변화" if language == "ko" else "Since Previous Analysis"
    body = body_text(context, language)
    rows = tracking_rows(context, language)
    return ReportSection("tracking", title, body, rows)


def body_text(context: dict[str, Any], language: str) -> str:
    status = str(context.get("status") or "INSUFFICIENT_EVIDENCE")
    if language == "ko":
        return f"저장된 YouRich 연구 스냅샷 기준 변화 상태는 {status}입니다."
    return f"Stored YouRich research snapshot comparison status is {status}."


def tracking_rows(context: dict[str, Any], language: str) -> list[dict[str, str]]:
    changes = context.get("changes", [])
    rows = (
        [
            row(str(item.get("field")), str(item.get("direction")), language)
            for item in changes[:5]
            if isinstance(item, dict)
        ]
        if isinstance(changes, list)
        else []
    )
    if rows:
        return rows
    return [row("material_change", str(context.get("status") or "NO_MATERIAL_CHANGE"), language)]


def row(item: str, value: str, language: str) -> dict[str, str]:
    if language == "ko":
        return {"항목": item, "평가": value}
    return {"Item": item, "Assessment": value}
