from __future__ import annotations

from typing import Any

from _report_format import multiple_or_percent, pct


def valuation_comparison_table(rows: list[dict[str, Any]], language: str) -> str:
    labels = [
        ("P/E(주가수익비율)" if language == "ko" else "P/E", "pe"),
        ("잉여현금흐름 수익률" if language == "ko" else "FCF Yield", "fcf_yield"),
    ]
    table_rows = []
    for label, key in labels:
        table_rows.append(
            {"항목" if language == "ko" else "Metric": label}
            | {str(row.get("ticker", "")): valuation_metric(row, key) for row in rows}
        )
    extra_labels = {
        "required_growth": "요구 FCF 성장률" if language == "ko" else "Required FCF Growth",
        "base_position": "기준 시나리오 위치" if language == "ko" else "Base Scenario Position",
        "sensitivity": "민감도 핵심 변수" if language == "ko" else "Valuation Sensitivity",
    }
    table_rows.extend(
        [
            ({"항목" if language == "ko" else "Metric": extra_labels["required_growth"]})
            | {str(row.get("ticker", "")): required_growth(row) for row in rows},
            ({"항목" if language == "ko" else "Metric": extra_labels["base_position"]})
            | {str(row.get("ticker", "")): base_position(row) for row in rows},
            ({"항목" if language == "ko" else "Metric": extra_labels["sensitivity"]})
            | {str(row.get("ticker", "")): sensitivity_summary(row) for row in rows},
        ]
    )
    return markdown_table(table_rows)


def valuation_metric(row: dict[str, Any], key: str) -> str:
    metric = row.get("valuation", {}).get("metrics", {}).get(key, {})
    return multiple_or_percent(metric.get("value"), key)


def required_growth(row: dict[str, Any]) -> str:
    reverse = row.get("valuation_intelligence", {}).get("reverse_dcf", {})
    return pct(reverse.get("required_fcf_cagr"))


def base_position(row: dict[str, Any]) -> str:
    margin = row.get("valuation_intelligence", {}).get("margin_of_safety", {})
    return str(margin.get("position") or "INSUFFICIENT_DATA")


def sensitivity_summary(row: dict[str, Any]) -> str:
    drivers = row.get("valuation_intelligence", {}).get("valuation_drivers", [])
    if not isinstance(drivers, list) or not drivers:
        return "Unavailable"
    names = [
        str(item.get("driver", "")).replace("_", " ")
        for item in drivers[:2]
        if isinstance(item, dict)
    ]
    return ", ".join(names) if names else "Unavailable"


def markdown_table(rows: list[dict[str, str]]) -> str:
    columns = list(rows[0])
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(row.get(column, "") for column in columns) + " |" for row in rows]
    return "\n".join([header, separator, *body])
