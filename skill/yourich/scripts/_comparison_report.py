from __future__ import annotations

from typing import Any

from _comparison_model import build_comparison_report
from _comparison_text import (
    bullet_list,
    change_text,
    comparison_basis_label,
    risk_label,
    scenario_text,
)
from _report_format import multiple_or_percent, pct


def render_comparison_markdown(
    report: dict[str, Any] | list[dict[str, Any]], language: str = "en"
) -> str:
    model = report if isinstance(report, dict) else build_comparison_report(report)
    labels = comparison_labels(language)
    entries = model_entries(model)
    lines = [
        f"# {model.get('title', '')}",
        "",
        f"## {labels['overall']}",
        "",
        comparison_table(entries, language),
        "",
        f"## {labels['differences']}",
        "",
        bullet_list(model.get("key_differences", []), language, labels["differences_body"]),
        "",
        f"## {labels['business']}",
        "",
        business_table(entries, labels["business_gap"], language),
        "",
        f"## {labels['financial']}",
        "",
        metric_comparison_table(entries, ("net_margin", "fcf_margin"), language),
        "",
        f"## {labels['valuation']}",
        "",
        valuation_comparison_table(entries, language),
        "",
        f"## {labels['risks']}",
        "",
        risk_comparison_table(entries, language),
    ]
    for entry in entries:
        lines.extend(
            [
                "",
                f"## {entry['ticker']} {labels['scenario']}",
                "",
                scenario_text(entry, labels, language),
            ]
        )
    lines.extend(
        [
            "",
            f"## {labels['conclusion']}",
            "",
            bullet_list(model.get("conclusion", []), language, labels["conclusion_body"]),
            "",
            f"## {labels['methodology']}",
            "",
            methodology_text(model, entries, language),
        ]
    )
    return "\n".join(lines).strip() + "\n"


def model_entries(report: dict[str, Any]) -> list[dict[str, Any]]:
    entries = report.get("entries", [])
    return (
        [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []
    )


def comparison_table(rows: list[dict[str, Any]], language: str) -> str:
    row_labels = comparison_row_labels(language)
    table_rows = []
    for label, key in row_labels:
        table_rows.append(
            {"항목" if language == "ko" else "Area": label}
            | {str(row.get("ticker", "")): comparison_value(row, key, language) for row in rows}
        )
    return markdown_table(table_rows)


def comparison_value(row: dict[str, Any], key: str, language: str) -> str:
    if key == "conclusion":
        return str(row.get("valuation", {}).get("conclusion", "Unavailable"))
    if key == "pe":
        metric = row.get("valuation", {}).get("metrics", {}).get("pe", {})
        return multiple_or_percent(metric.get("value"), "pe")
    if key == "fcf_yield":
        metric = row.get("valuation", {}).get("metrics", {}).get("fcf_yield", {})
        return multiple_or_percent(metric.get("value"), "fcf_yield")
    if key == "business":
        value = row.get("business_quality")
        if value:
            return str(value)
    return "근거가 부족합니다." if language == "ko" else "Insufficient evidence"


def business_table(rows: list[dict[str, Any]], fallback: str, language: str) -> str:
    company = "기업" if language == "ko" else "Company"
    judgment = "핵심 판단" if language == "ko" else "Key judgment"
    return markdown_table(
        [
            {
                company: str(row.get("ticker", "")),
                judgment: str(row.get("business_quality") or fallback),
            }
            for row in rows
        ]
    )


def metric_comparison_table(
    rows: list[dict[str, Any]], keys: tuple[str, ...], language: str
) -> str:
    labels = {
        "net_margin": "순이익률" if language == "ko" else "Net margin",
        "fcf_margin": "잉여현금흐름 마진" if language == "ko" else "FCF margin",
    }
    table_rows = [
        (
            {"항목" if language == "ko" else "Metric": labels[key]}
            | {str(row.get("ticker", "")): health_metric(row, key) for row in rows}
        )
        for key in keys
    ]
    return markdown_table(table_rows)


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
    return markdown_table(table_rows)


def risk_comparison_table(rows: list[dict[str, Any]], language: str) -> str:
    label = "주요 위험" if language == "ko" else "Triggered risks"
    return markdown_table(
        [
            {"항목" if language == "ko" else "Area": label}
            | {str(row.get("ticker", "")): risk_summary(row, language) for row in rows}
        ]
    )


def methodology_table(rows: list[dict[str, Any]], language: str) -> str:
    basis = "비교 기준" if language == "ko" else "Comparison basis"
    evidence = "근거 품질" if language == "ko" else "Evidence Quality"
    return markdown_table(
        [
            {"항목" if language == "ko" else "Item": basis}
            | {
                str(row.get("ticker", "")): str(
                    comparison_basis_label(
                        row.get("comparison_basis", {}).get("pe", "unknown"), language
                    )
                )
                for row in rows
            },
            {"항목" if language == "ko" else "Item": evidence}
            | {str(row.get("ticker", "")): str(row.get("evidence_quality", "LOW")) for row in rows},
        ]
    )


def health_metric(row: dict[str, Any], key: str) -> str:
    metric = row.get("financial_quality", {}).get("metrics", {}).get(key, {})
    return pct(metric.get("value"))


def valuation_metric(row: dict[str, Any], key: str) -> str:
    metric = row.get("valuation", {}).get("metrics", {}).get(key, {})
    return multiple_or_percent(metric.get("value"), key)


def risk_summary(row: dict[str, Any], language: str) -> str:
    checks = row.get("risk", {}).get("risk_checks", [])
    triggered = [
        item for item in checks if isinstance(item, dict) and item.get("status") == "triggered"
    ]
    if not triggered:
        return "확인된 정량 위험 없음" if language == "ko" else "No triggered quantitative checks"
    return ", ".join(risk_label(str(item.get("id", "risk")), language) for item in triggered[:3])


def methodology_text(report: dict[str, Any], entries: list[dict[str, Any]], language: str) -> str:
    changes = report.get("what_changed", [])
    if not isinstance(changes, list) or not changes:
        return methodology_table(entries, language)
    label = "최근 변화" if language == "ko" else "What Changed"
    lines = [methodology_table(entries, language), "", label]
    lines.extend(
        f"- {change_text(change, language)}" for change in changes if isinstance(change, dict)
    )
    return "\n".join(lines)


def markdown_table(rows: list[dict[str, str]]) -> str:
    columns = list(rows[0])
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(row.get(column, "") for column in columns) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def comparison_labels(language: str) -> dict[str, str]:
    if language == "ko":
        return {
            "overall": "종합 비교",
            "differences": "핵심 차이",
            "differences_body": "수익성, 현금창출력, 가치평가 부담을 같은 기준에서 비교합니다.",
            "business": "사업 경쟁력",
            "business_gap": "근거가 부족합니다.",
            "financial": "재무 상태",
            "valuation": "가치평가",
            "risks": "주요 위험",
            "scenario": "상승 / 하락 시나리오",
            "bull_case": "상승 시나리오",
            "bear_case": "하락 시나리오",
            "scenario_body": "상승 가능성과 하락 위험은 별도로 검토해야 합니다.",
            "conclusion": "결론",
            "conclusion_body": (
                "현재 YouRich 기준에서는 비교 우위를 설명하되 투자 행동 지시는 "
                "제공하지 않습니다."
            ),
            "methodology": "데이터 및 산출 기준",
        }
    return {
        "overall": "Overall Comparison",
        "differences": "Key Differences",
        "differences_body": (
            "Profitability, cash generation, and valuation burden are compared on "
            "the selected bases."
        ),
        "business": "Business Quality",
        "business_gap": "Insufficient evidence",
        "financial": "Financial Quality",
        "valuation": "Valuation",
        "risks": "Key Risks",
        "scenario": "Bull / Bear Case",
        "bull_case": "Bull case",
        "bear_case": "Bear case",
        "scenario_body": "Upside and downside scenarios should be evaluated separately.",
        "conclusion": "Conclusion",
        "conclusion_body": (
            "YouRich compares evidence without giving investment action instructions."
        ),
        "methodology": "Data Quality & Methodology",
    }


def comparison_row_labels(language: str) -> list[tuple[str, str]]:
    if language == "ko":
        return [
            ("결론", "conclusion"),
            ("P/E(주가수익비율)", "pe"),
            ("잉여현금흐름 수익률", "fcf_yield"),
            ("사업 근거", "business"),
        ]
    return [
        ("Conclusion", "conclusion"),
        ("P/E", "pe"),
        ("FCF Yield", "fcf_yield"),
        ("Business evidence", "business"),
    ]
