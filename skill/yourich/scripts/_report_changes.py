from __future__ import annotations

from typing import Any

from _report_format import localized
from _report_types import ReportSection


def changed_section(
    research_context: dict[str, Any] | None, title: str, language: str
) -> ReportSection:
    change = (
        research_context.get("risk_analysis", {}).get("risk_factor_change")
        if research_context
        else None
    )
    if isinstance(change, dict) and change.get("status") not in {None, "INSUFFICIENT_EVIDENCE"}:
        return ReportSection("changed", title, f"Risk factor change: {change['status']}", [])
    return ReportSection("changed", title, localized("Insufficient evidence", language), [])
