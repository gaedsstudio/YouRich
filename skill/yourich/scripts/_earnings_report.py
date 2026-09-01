from __future__ import annotations

from typing import Any

from _report_format import markdown_table


def render_earnings_markdown(context: dict[str, Any], language: str = "en") -> str:
    labels = report_labels(language)
    latest = context.get("latest_earnings")
    company = (
        str(latest.get("company"))
        if isinstance(latest, dict)
        else str(context.get("ticker", "Unknown company"))
    )
    ticker = str(context.get("ticker", ""))
    lines = [
        f"# {company} · {ticker}",
        "",
        f"## {labels['summary']}",
        "",
        thesis_status(context),
        "",
        f"## {labels['numbers']}",
        "",
        metrics_table(context, language),
        "",
        f"## {labels['prior']}",
        "",
        changes_table(context, language),
        "",
        f"## {labels['guidance']}",
        "",
        guidance_table(context, language),
        "",
        f"## {labels['actual']}",
        "",
        actual_table(context, language),
        "",
        f"## {labels['management']}",
        "",
        commentary_table(context, language),
        "",
        f"## {labels['better']}",
        "",
        change_points(context, "IMPROVED", language),
        "",
        f"## {labels['caution']}",
        "",
        warning_points(context, language),
        "",
        f"## {labels['thesis']}",
        "",
        thesis_status(context),
        "",
        f"## {labels['evidence']}",
        "",
        evidence_table(context, language),
    ]
    return "\n".join(lines).strip() + "\n"


def metrics_table(context: dict[str, Any], language: str) -> str:
    metrics = context.get("reported_metrics")
    if not isinstance(metrics, dict) or not metrics:
        return empty_text(language)
    rows = [
        row("Metric", key, "Value", str(item.get("value")), language)
        for key, item in metrics.items()
        if isinstance(item, dict)
    ]
    return markdown_table(rows[:8]) if rows else empty_text(language)


def changes_table(context: dict[str, Any], language: str) -> str:
    changes = context.get("changes")
    if not isinstance(changes, list) or not changes:
        return empty_text(language)
    return markdown_table(
        [
            row("Change", str(item.get("change_type")), "Status", str(item.get("status")), language)
            for item in changes
            if isinstance(item, dict)
        ]
    )


def guidance_table(context: dict[str, Any], language: str) -> str:
    guidance = context.get("guidance_changes")
    if not isinstance(guidance, list) or not guidance:
        return empty_text(language)
    return markdown_table(
        [
            row("Guidance", str(item.get("metric")), "Change", str(item.get("status")), language)
            for item in guidance
            if isinstance(item, dict)
        ]
    )


def actual_table(context: dict[str, Any], language: str) -> str:
    comparisons = context.get("guidance_vs_actual")
    if not isinstance(comparisons, list) or not comparisons:
        return empty_text(language)
    return markdown_table(
        [
            row("Metric", str(item.get("metric")), "Result", str(item.get("status")), language)
            for item in comparisons
            if isinstance(item, dict)
        ]
    )


def commentary_table(context: dict[str, Any], language: str) -> str:
    commentary = context.get("management_commentary")
    if not isinstance(commentary, list) or not commentary:
        return empty_text(language)
    return markdown_table(
        [
            row(
                "Topic",
                str(item.get("category")),
                "Statement",
                str(item.get("statement")),
                language,
            )
            for item in commentary
            if isinstance(item, dict)
        ]
    )


def evidence_table(context: dict[str, Any], language: str) -> str:
    evidence = context.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return empty_text(language)
    return markdown_table(
        [
            row(
                "Source", str(item.get("document")), "Date", str(item.get("published_at")), language
            )
            for item in evidence[:6]
            if isinstance(item, dict)
        ]
    )


def change_points(context: dict[str, Any], status: str, language: str) -> str:
    changes = context.get("changes")
    if not isinstance(changes, list):
        return empty_text(language)
    points = [
        f"- {item.get('change_type')}"
        for item in changes
        if isinstance(item, dict) and item.get("status") == status
    ]
    return "\n".join(points) if points else empty_text(language)


def warning_points(context: dict[str, Any], language: str) -> str:
    warnings = context.get("warnings")
    if not isinstance(warnings, list) or not warnings:
        return (
            "- No material data-quality warnings."
            if language != "ko"
            else "- 중요한 데이터 경고 없음."
        )
    return "\n".join(f"- {str(item).replace('_', ' ').title()}" for item in warnings)


def thesis_status(context: dict[str, Any]) -> str:
    thesis = context.get("thesis_change")
    return str(thesis.get("status")) if isinstance(thesis, dict) else "INSUFFICIENT_EVIDENCE"


def row(left_label: str, left: str, right_label: str, right: str, language: str) -> dict[str, str]:
    if language == "ko":
        return {"항목": left, "평가": right}
    return {left_label: left, right_label: right}


def empty_text(language: str) -> str:
    return "근거가 부족합니다." if language == "ko" else "Insufficient evidence"


def report_labels(language: str) -> dict[str, str]:
    if language == "ko":
        return {
            "summary": "실적 요약",
            "numbers": "핵심 숫자",
            "prior": "이전 분기와 비교",
            "guidance": "가이던스",
            "actual": "가이던스 대비 실제 결과",
            "management": "경영진이 강조한 내용",
            "better": "좋아진 점",
            "caution": "주의할 점",
            "thesis": "투자 논리 변화",
            "evidence": "데이터 및 근거",
        }
    return {
        "summary": "Earnings Summary",
        "numbers": "Key Numbers",
        "prior": "Compared With Prior Quarter",
        "guidance": "Guidance",
        "actual": "Guidance vs Actual Result",
        "management": "Management Emphasis",
        "better": "What Improved",
        "caution": "What To Watch",
        "thesis": "Thesis Change",
        "evidence": "Data & Evidence",
    }
