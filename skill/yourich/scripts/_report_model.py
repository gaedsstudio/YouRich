from __future__ import annotations

from typing import Any

from _report_format import (
    meaning_for_basis,
    metadata_for,
    money,
    multiple_or_percent,
    text_or_none,
)
from _report_sections import assessment_rows, build_sections
from _report_text import overall_label, overall_summary
from _report_tracking import tracking_section
from _report_types import InvestmentReport, ReportMetric
from _valuation_intelligence import build_valuation_intelligence
from financial_health import financial_health
from risk import risk_checks
from valuation import valuation


def build_report(
    company: dict[str, Any],
    research_context: dict[str, Any] | None = None,
    peer_context: dict[str, Any] | None = None,
    tracking_context: dict[str, Any] | None = None,
    language: str = "en",
) -> InvestmentReport:
    lang = "ko" if language.lower().startswith("ko") else "en"
    value = valuation(company)
    health = financial_health(company)
    risks = risk_checks(company)
    intelligence = build_valuation_intelligence(
        company, earnings_context=earnings_context(research_context)
    )
    key_metrics = important_metrics(company, value)
    assessments = assessment_rows(company, value, health, risks, research_context)
    overall = overall_label(assessments)
    sections = build_sections(
        company,
        value,
        health,
        risks,
        research_context,
        key_metrics,
        lang,
        intelligence,
        peer_context,
    )
    if tracking_context is not None:
        insert_tracking_section(sections, tracking_context, lang)
    return InvestmentReport(
        company=str(company.get("company") or company.get("ticker") or "Unknown company"),
        ticker=str(company.get("ticker") or ""),
        language=lang,
        overall_label=overall,
        overall_summary=overall_summary(overall, lang),
        sections=sections,
        key_metrics=key_metrics,
        raw={
            "financials": company,
            "valuation": value,
            "valuation_intelligence": intelligence,
            "peer_context": peer_context,
            "tracking_context": tracking_context,
            "financial_health": health,
            "risk": risks,
        },
    )


def insert_tracking_section(
    sections: list[Any], tracking_context: dict[str, Any], language: str
) -> None:
    section = tracking_section(tracking_context, language)
    for index, item in enumerate(sections):
        if getattr(item, "key", "") == "conclusion":
            sections.insert(index, section)
            return
    sections.append(section)


def earnings_context(research_context: dict[str, Any] | None) -> dict[str, Any] | None:
    if research_context is None:
        return None
    context = research_context.get("earnings_context")
    return context if isinstance(context, dict) else None


def important_metrics(company: dict[str, Any], value: dict[str, Any]) -> list[ReportMetric]:
    metrics = value.get("metrics", {})
    return [
        financial_metric("Revenue", company, "revenue", "Revenue scale on the selected basis."),
        financial_metric(
            "Net Income", company, "net_income", "Profit after expenses on the selected basis."
        ),
        valuation_metric("P/E", metrics, "pe", "Price paid for each dollar of selected earnings."),
        valuation_metric(
            "FCF Yield",
            metrics,
            "fcf_yield",
            "Cash return generated for each $100 of market value.",
        ),
    ]


def financial_metric(name: str, company: dict[str, Any], key: str, meaning: str) -> ReportMetric:
    metadata = metadata_for(company, key)
    source = company.get("field_sources", {}).get(key)
    return ReportMetric(
        name,
        money(company.get(key)),
        meaning_for_basis(meaning, metadata.get("basis")),
        financial_provenance_type(metadata, text_or_none(source)),
        text_or_none(metadata.get("basis")),
        text_or_none(source),
    )


def financial_provenance_type(metadata: dict[str, Any], source: str | None) -> str:
    if metadata.get("provenance_type") == "derived_metric":
        return "derived_metric"
    if metadata.get("type") == "derived_metric":
        return "derived_metric"
    if source is not None and source.startswith("computed:"):
        return "derived_metric"
    if metadata.get("basis") == "ttm" and reconstructed_from_components(metadata):
        return "derived_metric"
    return "reported_fact"


def reconstructed_from_components(metadata: dict[str, Any]) -> bool:
    source_facts = metadata.get("source_facts")
    return bool(
        metadata.get("derived_from")
        or metadata.get("component_periods")
        or (isinstance(source_facts, list) and len(source_facts) > 1)
    )


def valuation_metric(name: str, metrics: dict[str, Any], key: str, meaning: str) -> ReportMetric:
    metric = metrics.get(key, {})
    return ReportMetric(
        name,
        multiple_or_percent(metric.get("value"), key),
        meaning,
        "derived_metric",
        text_or_none(metric.get("basis")),
        text_or_none(metric.get("formula")),
    )
