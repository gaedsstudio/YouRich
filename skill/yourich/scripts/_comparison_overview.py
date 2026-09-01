from __future__ import annotations

from typing import Any

from _report_format import multiple_or_percent


def comparison_value(row: dict[str, Any], key: str, language: str) -> str:
    value = comparison_value_for_key(row, key)
    if value is not None:
        return value
    return "근거가 부족합니다." if language == "ko" else "Insufficient evidence"


def comparison_value_for_key(row: dict[str, Any], key: str) -> str | None:
    if key == "conclusion":
        return str(row.get("valuation", {}).get("conclusion", "Unavailable"))
    if key in {"pe", "fcf_yield"}:
        metric = row.get("valuation", {}).get("metrics", {}).get(key, {})
        return multiple_or_percent(metric.get("value"), key)
    if key == "business" and row.get("business_quality"):
        return str(row["business_quality"])
    if key == "guidance_change":
        return earnings_guidance_change(row)
    if key == "thesis_change":
        return earnings_thesis_change(row)
    return None


def has_earnings(rows: list[dict[str, Any]]) -> bool:
    return any(isinstance(row.get("earnings"), dict) for row in rows)


def earnings_guidance_change(row: dict[str, Any]) -> str:
    earnings = row.get("earnings")
    if not isinstance(earnings, dict):
        return "INSUFFICIENT_EVIDENCE"
    changes = earnings.get("guidance_changes")
    if not isinstance(changes, list) or not changes:
        return "INSUFFICIENT_EVIDENCE"
    first = changes[0]
    return str(first.get("status")) if isinstance(first, dict) else "INSUFFICIENT_EVIDENCE"


def earnings_thesis_change(row: dict[str, Any]) -> str:
    earnings = row.get("earnings")
    if not isinstance(earnings, dict):
        return "INSUFFICIENT_EVIDENCE"
    thesis = earnings.get("thesis_change")
    return str(thesis.get("status")) if isinstance(thesis, dict) else "INSUFFICIENT_EVIDENCE"


def comparison_row_labels(language: str, include_earnings: bool = False) -> list[tuple[str, str]]:
    base = [
        ("Conclusion", "conclusion"),
        ("P/E", "pe"),
        ("FCF Yield", "fcf_yield"),
        ("Business evidence", "business"),
    ]
    if language == "ko":
        rows = [
            ("결론", "conclusion"),
            ("P/E(주가수익비율)", "pe"),
            ("잉여현금흐름 수익률", "fcf_yield"),
            ("사업 근거", "business"),
        ]
        if include_earnings:
            rows.extend([("가이던스 변화", "guidance_change"), ("투자 논리 변화", "thesis_change")])
        return rows
    if include_earnings:
        return [*base, ("Guidance Change", "guidance_change"), ("Thesis Change", "thesis_change")]
    return base
