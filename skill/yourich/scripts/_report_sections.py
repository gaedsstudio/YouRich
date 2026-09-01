from __future__ import annotations

from decimal import Decimal
from typing import Any

from _core import decimal_or_none
from _report_format import (
    basis_label,
    human_warning,
    localized,
    market_data_label,
    metadata_for,
    metric_rows,
    money,
    number,
    pct,
    risk_label,
    valuation_row,
)
from _report_types import HEADINGS, ReportMetric, ReportSection


def build_sections(
    company: dict[str, Any],
    value: dict[str, Any],
    health: dict[str, Any],
    risks: dict[str, Any],
    research_context: dict[str, Any] | None,
    key_metrics: list[ReportMetric],
    language: str,
) -> list[ReportSection]:
    from _report_text import investment_summary, overall_label, overall_summary

    heading = HEADINGS[language]
    assessments = assessment_rows(company, value, health, risks, research_context)
    overall = overall_label(assessments)
    return [
        ReportSection("overall", heading["overall"], overall_summary(overall, language), []),
        ReportSection("glance", heading["glance"], "", assessments),
        ReportSection(
            "summary", heading["summary"], investment_summary(overall, value, language), []
        ),
        ReportSection("metrics", heading["metrics"], "", metric_rows(key_metrics)),
        business_section(research_context, heading["business"], language),
        financial_section(company, health, heading["financial"], language),
        valuation_section(value, heading["valuation"], language),
        risk_section(risks, heading["risks"], language),
        scenario_section("bull", heading["bull"], value, risks, language),
        scenario_section("bear", heading["bear"], value, risks, language),
        changed_section(research_context, heading["changed"], language),
        ReportSection(
            "conclusion", heading["conclusion"], investment_summary(overall, value, language), []
        ),
        quality_section(company, value, heading["quality"], language),
    ]


def assessment_rows(
    company: dict[str, Any],
    value: dict[str, Any],
    health: dict[str, Any],
    risks: dict[str, Any],
    research_context: dict[str, Any] | None,
) -> list[dict[str, str]]:
    return [
        {"Area": "Business Quality", "Assessment": business_assessment(research_context)},
        {"Area": "Profitability", "Assessment": profitability_assessment(health)},
        {"Area": "Financial Health", "Assessment": financial_assessment(health, risks)},
        {
            "Area": "Valuation",
            "Assessment": str(value.get("conclusion") or "Insufficient data").title(),
        },
        {"Area": "Risk", "Assessment": risk_assessment(risks)},
        {"Area": "Evidence Quality", "Assessment": evidence_assessment(company, research_context)},
    ]


def business_section(
    research_context: dict[str, Any] | None, title: str, language: str
) -> ReportSection:
    if business_assessment(research_context) == "Insufficient evidence":
        return ReportSection("business", title, localized("Insufficient evidence", language), [])
    evidence_message = "Filing evidence is available; review linked evidence before relying on"
    return ReportSection(
        "business",
        title,
        localized(f"{evidence_message} qualitative claims.", language),
        [],
    )


def financial_section(
    company: dict[str, Any], health: dict[str, Any], title: str, language: str
) -> ReportSection:
    metrics = health.get("metrics", {})
    rows = [
        {"Metric": "Gross Margin", "Value": pct(metrics.get("gross_margin", {}).get("value"))},
        {
            "Metric": "Operating Margin",
            "Value": pct(metrics.get("operating_margin", {}).get("value")),
        },
        {"Metric": "Net Margin", "Value": pct(metrics.get("net_margin", {}).get("value"))},
        {"Metric": "Current Ratio", "Value": number(metrics.get("current_ratio", {}).get("value"))},
        {
            "Metric": "Debt / Assets",
            "Value": number(metrics.get("debt_to_assets", {}).get("value")),
        },
        {"Metric": "Free Cash Flow", "Value": money(company.get("free_cash_flow"))},
    ]
    body = localized(
        "Profitability, liquidity, leverage, and cash generation are shown before interpretation.",
        language,
    )
    return ReportSection("financial", title, body, rows)


def valuation_section(value: dict[str, Any], title: str, language: str) -> ReportSection:
    metrics = value.get("metrics", {})
    rows = [
        valuation_row(metrics, "P/E", "pe"),
        valuation_row(metrics, "P/S", "ps"),
        valuation_row(metrics, "FCF Yield", "fcf_yield"),
        valuation_row(metrics, "Earnings Yield", "earnings_yield"),
    ]
    body = localized(
        "Valuation is expensive when investors are paying a high price for current fundamentals.",
        language,
    )
    return ReportSection("valuation", title, body, rows)


def risk_section(risks: dict[str, Any], title: str, language: str) -> ReportSection:
    rows = [
        {"Risk": risk_label(str(item.get("id"))), "Status": "Triggered"}
        for item in risks.get("risk_checks", [])
        if isinstance(item, dict) and item.get("status") == "triggered"
    ]
    if not rows:
        rows.append({"Risk": "Quantitative checks", "Status": "No triggered risk checks"})
    return ReportSection(
        "risks",
        title,
        localized("Material risks are prioritized rather than dumped.", language),
        rows,
    )


def scenario_section(
    key: str, title: str, value: dict[str, Any], risks: dict[str, Any], language: str
) -> ReportSection:
    valuation_label = str(value.get("conclusion") or "")
    triggered = any(
        isinstance(item, dict) and item.get("status") == "triggered"
        for item in risks.get("risk_checks", [])
    )
    rows = [{"Point": "Profitability and cash generation remain durable"}]
    if key == "bear":
        rows = [{"Point": "Valuation multiple compresses"}]
        if triggered:
            rows.append({"Point": "Triggered financial risks worsen"})
    elif "ATTRACTIVE" in valuation_label:
        rows.append({"Point": "Valuation leaves room for upside"})
    return ReportSection(
        key,
        title,
        localized("Scenario points are evidence-led, not recommendations.", language),
        rows,
    )


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


def quality_section(
    company: dict[str, Any], value: dict[str, Any], title: str, language: str
) -> ReportSection:
    rows = [
        {"Item": "Financial data", "Value": "SEC Company Facts"},
        {"Item": "Market data", "Value": market_data_label(company)},
        {
            "Item": "Revenue basis",
            "Value": basis_label(metadata_for(company, "revenue").get("basis")),
        },
        {
            "Item": "Net income basis",
            "Value": basis_label(metadata_for(company, "net_income").get("basis")),
        },
        {"Item": "EPS basis", "Value": basis_label(metadata_for(company, "eps").get("basis"))},
        {
            "Item": "FCF basis",
            "Value": basis_label(metadata_for(company, "free_cash_flow").get("basis")),
        },
        {
            "Item": "TTM coverage",
            "Value": str(company.get("data_quality", {}).get("ttm_coverage", "unknown")).title(),
        },
    ]
    warnings = [human_warning(item, company) for item in value.get("warnings", [])]
    body = (
        "Warnings: " + "; ".join(warnings)
        if warnings
        else localized("No material warnings.", language)
    )
    return ReportSection("quality", title, body, rows)


def business_assessment(research_context: dict[str, Any] | None) -> str:
    if research_context is None:
        return "Insufficient evidence"
    coverage = research_context.get("evidence_coverage", {})
    business = coverage.get("business") if isinstance(coverage, dict) else None
    if business == "HIGH":
        return "Strong"
    if business == "MEDIUM":
        return "Evidence-linked"
    return "Insufficient evidence"


def profitability_assessment(health: dict[str, Any]) -> str:
    metrics = health.get("metrics", {})
    margin = decimal_or_none(metrics.get("net_margin", {}).get("value"))
    if margin is None:
        return "Insufficient data"
    if margin >= Decimal("20"):
        return "Very Strong"
    if margin >= Decimal("10"):
        return "Strong"
    if margin >= Decimal("0"):
        return "Moderate"
    return "Weak"


def financial_assessment(health: dict[str, Any], risks: dict[str, Any]) -> str:
    current_ratio = decimal_or_none(health.get("metrics", {}).get("current_ratio", {}).get("value"))
    high_triggered = any(
        isinstance(item, dict)
        and item.get("severity") == "high"
        and item.get("status") == "triggered"
        for item in risks.get("risk_checks", [])
    )
    if high_triggered:
        return "Stressed"
    if current_ratio is None:
        return "Insufficient data"
    if current_ratio >= Decimal("1"):
        return "Healthy"
    return "Tight"


def risk_assessment(risks: dict[str, Any]) -> str:
    triggered = [
        item
        for item in risks.get("risk_checks", [])
        if isinstance(item, dict) and item.get("status") == "triggered"
    ]
    if not triggered:
        return "Moderate"
    if any(item.get("severity") == "high" for item in triggered):
        return "High"
    return "Elevated"


def evidence_assessment(company: dict[str, Any], research_context: dict[str, Any] | None) -> str:
    coverage = str(company.get("data_quality", {}).get("ttm_coverage", "")).lower()
    confidence = str(research_context.get("research_confidence", "")) if research_context else ""
    if coverage == "complete" and confidence in {"HIGH", "MEDIUM"}:
        return "High"
    if coverage in {"complete", "partial"}:
        return "Medium"
    return "Low"
