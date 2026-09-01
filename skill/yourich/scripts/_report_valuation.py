from __future__ import annotations

from typing import Any

from _report_format import localized_valuation_row, pct


def valuation_rows(
    metrics: dict[str, Any], intelligence: dict[str, Any] | None, language: str
) -> list[dict[str, str]]:
    rows = [
        localized_valuation_row(metrics, "P/E", "pe", language),
        localized_valuation_row(metrics, "P/S", "ps", language),
        localized_valuation_row(metrics, "FCF Yield", "fcf_yield", language),
        localized_valuation_row(metrics, "Earnings Yield", "earnings_yield", language),
    ]
    if intelligence is not None:
        rows.extend(valuation_intelligence_rows(intelligence, language))
    return rows


def valuation_intelligence_rows(
    intelligence: dict[str, Any], language: str
) -> list[dict[str, str]]:
    reverse = intelligence.get("reverse_dcf", {})
    margin = intelligence.get("margin_of_safety", {})
    base = base_scenario(intelligence.get("scenarios"))
    required = pct(reverse.get("required_fcf_cagr"))
    position = str(margin.get("position") or "INSUFFICIENT_DATA")
    base_range = "Unavailable" if base is None else str(base.get("value_range"))
    if language != "ko":
        return [
            {"Metric": "Required FCF growth", "Value": required, "Basis": "Reverse DCF"},
            {"Metric": "Base scenario", "Value": base_range, "Basis": "Scenario range"},
            {"Metric": "Scenario position", "Value": position, "Basis": "Current price"},
        ]
    return [
        {"지표": "현재 가격이 요구하는 성장", "값": required, "기준": "역산 DCF"},
        {"지표": "기준 시나리오", "값": base_range, "기준": "시나리오 범위"},
        {"지표": "시나리오 위치", "값": position, "기준": "현재 가격"},
    ]


def base_scenario(scenarios: Any) -> dict[str, Any] | None:
    if not isinstance(scenarios, list):
        return None
    for scenario in scenarios:
        if isinstance(scenario, dict) and scenario.get("scenario") == "base":
            return scenario
    return None
