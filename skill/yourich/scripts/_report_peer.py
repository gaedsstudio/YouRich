from __future__ import annotations

from typing import Any

from _report_types import ReportSection


def peer_section(peer_context: dict[str, Any], language: str) -> ReportSection:
    title = "동종기업 비교" if language == "ko" else "Peer Comparison"
    body = interpretation(peer_context, language)
    return ReportSection("peer_comparison", title, body, rows(peer_context, language))


def rows(peer_context: dict[str, Any], language: str) -> list[dict[str, str]]:
    aggregate = first_relative_valuation(peer_context)
    status = str(
        peer_context.get("premium_justification", {}).get("status", "INSUFFICIENT_EVIDENCE")
    )
    if language == "ko":
        return [
            {"항목": "동종기업 중앙값", "값": str(aggregate.get("peer_median", "Unavailable"))},
            {"항목": "프리미엄", "값": str(aggregate.get("premium_percent", "Unavailable"))},
            {"항목": "현재 프리미엄은 정당한가", "값": status},
        ]
    return [
        {"Item": "Peer median", "Value": str(aggregate.get("peer_median", "Unavailable"))},
        {"Item": "Premium", "Value": str(aggregate.get("premium_percent", "Unavailable"))},
        {"Item": "Is the premium justified", "Value": status},
    ]


def first_relative_valuation(peer_context: dict[str, Any]) -> dict[str, Any]:
    relative = peer_context.get("relative_valuation")
    if not isinstance(relative, list):
        return {}
    for item in relative:
        if isinstance(item, dict) and item.get("metric") == "pe":
            return item
    return {}


def interpretation(peer_context: dict[str, Any], language: str) -> str:
    status = str(
        peer_context.get("premium_justification", {}).get("status", "INSUFFICIENT_EVIDENCE")
    )
    if language == "ko":
        return f"동종기업 대비 프리미엄 판단은 {status}입니다. 투자 행동 지시는 제공하지 않습니다."
    return f"Peer-relative premium assessment is {status}. This is not an action instruction."
