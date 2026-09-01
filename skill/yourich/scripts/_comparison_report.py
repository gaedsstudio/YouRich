from __future__ import annotations

from typing import Any

from _report_format import basis_label, korean_basis_label, multiple_or_percent, pct


def render_comparison_markdown(rows: list[dict[str, Any]], language: str = "en") -> str:
    labels = comparison_labels(language)
    tickers = [str(row.get("ticker", "")) for row in rows]
    title = " vs ".join(tickers)
    lines = [
        f"# {title}",
        "",
        f"## {labels['overall']}",
        "",
        comparison_table(rows, language),
        "",
        f"## {labels['differences']}",
        "",
        labels["differences_body"],
        "",
        f"## {labels['business']}",
        "",
        entity_table(rows, labels["business_gap"]),
        "",
        f"## {labels['financial']}",
        "",
        metric_comparison_table(rows, ("net_margin", "fcf_margin"), language),
        "",
        f"## {labels['valuation']}",
        "",
        valuation_comparison_table(rows, language),
        "",
        f"## {labels['risks']}",
        "",
        risk_comparison_table(rows, language),
    ]
    for ticker in tickers:
        lines.extend(["", f"## {ticker} {labels['scenario']}", "", labels["scenario_body"]])
    lines.extend(
        [
            "",
            f"## {labels['conclusion']}",
            "",
            labels["conclusion_body"],
            "",
            f"## {labels['methodology']}",
            "",
            methodology_table(rows, language),
        ]
    )
    return "\n".join(lines).strip() + "\n"


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
    return "근거가 부족합니다." if language == "ko" else "Insufficient evidence"


def entity_table(rows: list[dict[str, Any]], fallback: str) -> str:
    return markdown_table([{str(row.get("ticker", "")): fallback for row in rows}])


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
    label = "비교 기준" if language == "ko" else "Comparison basis"
    return markdown_table(
        [
            {"항목" if language == "ko" else "Item": label}
            | {
                str(row.get("ticker", "")): str(
                    comparison_basis_label(
                        row.get("comparison_basis", {}).get("pe", "unknown"), language
                    )
                )
                for row in rows
            }
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


def risk_label(value: str, language: str) -> str:
    labels = {
        "debt_risk": "부채 위험",
        "liquidity_risk": "유동성 위험",
        "negative_equity": "자본잠식 위험",
        "earnings_deterioration": "이익 악화 위험",
        "fcf_deterioration": "잉여현금흐름 악화 위험",
        "margin_deterioration": "마진 악화 위험",
        "valuation_risk": "가치평가 위험",
        "share_dilution": "주식 희석 위험",
    }
    if language == "ko":
        return labels.get(value, value.replace("_", " "))
    return value.replace("_", " ")


def comparison_basis_label(value: Any, language: str) -> str:
    raw = str(value)
    if raw == "unknown":
        return "알 수 없음" if language == "ko" else raw
    parts = [part for part in raw.split("|") if part]
    if language != "ko":
        return " + ".join(basis_label(part) for part in parts)
    return " + ".join(korean_basis_label(basis_label(part)) for part in parts)


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
