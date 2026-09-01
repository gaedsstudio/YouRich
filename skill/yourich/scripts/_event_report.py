from __future__ import annotations

from typing import Any


def render_event_markdown(result: dict[str, Any], language: str = "en") -> str:
    return render_ko(result) if language.lower().startswith("ko") else render_en(result)


def render_ko(result: dict[str, Any]) -> str:
    lines = [f"# {result.get('ticker')} 이벤트 인텔리전스", "", "## 핵심 이벤트", ""]
    lines.extend(
        event_lines(result.get("material_events"), empty="- 공식 근거가 있는 주요 이벤트 없음")
    )
    lines.extend(["", "## 앞으로 확인할 촉매", ""])
    lines.extend(event_lines(result.get("upcoming_catalysts"), empty="- 확인된 예정 촉매 없음"))
    lines.extend(
        ["", "## 투자 논리 영향", "", f"- 종합 영향: {result.get('event_impact_summary')}"]
    )
    lines.extend(["", "## 데이터 품질", ""])
    lines.extend(warning_lines(result))
    return "\n".join(lines).strip() + "\n"


def render_en(result: dict[str, Any]) -> str:
    lines = [f"# {result.get('ticker')} Event Intelligence", "", "## Key Events", ""]
    lines.extend(
        event_lines(
            result.get("material_events"), empty="- No material primary-source events found"
        )
    )
    lines.extend(["", "## Upcoming Catalysts", ""])
    lines.extend(
        event_lines(result.get("upcoming_catalysts"), empty="- No confirmed upcoming catalysts")
    )
    lines.extend(
        ["", "## Thesis Impact", "", f"- Overall impact: {result.get('event_impact_summary')}"]
    )
    lines.extend(["", "## Data Quality", ""])
    lines.extend(warning_lines(result))
    return "\n".join(lines).strip() + "\n"


def event_lines(value: Any, empty: str) -> list[str]:
    if not isinstance(value, list) or not value:
        return [empty]
    return [
        (
            f"- {item.get('published_at')}: {item.get('event_type')} "
            f"({item.get('direction')}, {item.get('materiality')})"
        )
        for item in value[:8]
        if isinstance(item, dict)
    ]


def warning_lines(result: dict[str, Any]) -> list[str]:
    warnings = result.get("warnings")
    if not isinstance(warnings, list) or not warnings:
        return ["- OK"]
    return [f"- {warning}" for warning in warnings]
