from __future__ import annotations

from typing import Any

from _report_format import basis_label, human_warning, localized, metadata_for
from _report_types import ReportSection


def quality_section(
    company: dict[str, Any], value: dict[str, Any], title: str, language: str
) -> ReportSection:
    rows = [
        quality_row("Financial data", "SEC Company Facts", language),
        quality_row("Market data", market_data_label(company), language),
        quality_row(
            "Revenue basis", basis_label(metadata_for(company, "revenue").get("basis")), language
        ),
        quality_row(
            "Net income basis",
            basis_label(metadata_for(company, "net_income").get("basis")),
            language,
        ),
        quality_row("EPS basis", basis_label(metadata_for(company, "eps").get("basis")), language),
        quality_row(
            "FCF basis",
            basis_label(metadata_for(company, "free_cash_flow").get("basis")),
            language,
        ),
        quality_row(
            "TTM coverage",
            str(company.get("data_quality", {}).get("ttm_coverage", "unknown")).title(),
            language,
        ),
    ]
    warnings = [human_warning(item, company, language) for item in value.get("warnings", [])]
    return ReportSection("quality", title, warning_body(warnings, language), rows)


def market_data_label(company: dict[str, Any]) -> str:
    quote = company.get("market_quote")
    if isinstance(quote, dict):
        provider = quote.get("provider")
        return str(provider) if provider else "Delayed market quote"
    return "Unavailable"


def quality_row(label: str, value: str, language: str) -> dict[str, str]:
    if language != "ko":
        return {"Item": label, "Value": value}
    labels = {
        "Financial data": "재무 데이터",
        "Market data": "시장 가격",
        "Revenue basis": "매출 기준",
        "Net income basis": "순이익 기준",
        "EPS basis": "EPS 기준",
        "FCF basis": "FCF 기준",
        "TTM coverage": "TTM 커버리지",
    }
    from _report_format import korean_basis_label

    return {"항목": labels.get(label, label), "값": korean_basis_label(value)}


def warning_body(warnings: list[str], language: str) -> str:
    if not warnings:
        return localized("No material warnings.", language)
    if language == "ko":
        return "주의\n" + "\n".join(f"- {warning}" for warning in warnings)
    return "Warnings: " + "; ".join(warnings)
