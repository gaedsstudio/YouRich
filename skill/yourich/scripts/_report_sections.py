from __future__ import annotations

from decimal import Decimal
from typing import Any

from _core import decimal_or_none
from _report_changes import changed_section
from _report_earnings import earnings_context, earnings_section
from _report_format import (
    localized,
    localized_metric_rows,
    localized_valuation_row,
    money,
    number,
    pct,
    risk_label,
)
from _report_localization import (
    korean_area_label,
    korean_assessment_label,
    risk_row,
    scenario_row,
)
from _report_methodology import quality_section
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
    display_assessments = assessment_rows(company, value, health, risks, research_context, language)
    sections = [
        ReportSection("overall", heading["overall"], overall_summary(overall, language), []),
        ReportSection("glance", heading["glance"], "", display_assessments),
        ReportSection(
            "summary", heading["summary"], investment_summary(overall, value, language), []
        ),
        ReportSection(
            "metrics", heading["metrics"], "", localized_metric_rows(key_metrics, language)
        ),
        business_section(research_context, heading["business"], language),
        financial_section(company, health, heading["financial"], language),
        valuation_section(value, heading["valuation"], language),
        risk_section(risks, heading["risks"], language),
        scenario_section("bull", heading["bull"], value, risks, language),
        scenario_section("bear", heading["bear"], value, risks, language),
        changed_section(research_context, heading["changed"], language),
    ]
    if earnings_context(research_context) is not None:
        sections.append(earnings_section(research_context, heading["earnings"], language))
    sections.extend(
        [
            ReportSection(
                "conclusion",
                heading["conclusion"],
                investment_summary(overall, value, language),
                [],
            ),
            quality_section(company, value, heading["quality"], language),
        ]
    )
    return sections


def assessment_rows(
    company: dict[str, Any],
    value: dict[str, Any],
    health: dict[str, Any],
    risks: dict[str, Any],
    research_context: dict[str, Any] | None,
    language: str = "en",
) -> list[dict[str, str]]:
    rows = [
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
    if language != "ko":
        return rows
    return [
        {
            "항목": korean_area_label(row["Area"]),
            "평가": korean_assessment_label(row["Assessment"]),
        }
        for row in rows
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
        metric_row("Gross Margin", pct(metrics.get("gross_margin", {}).get("value")), language),
        metric_row(
            "Operating Margin",
            pct(metrics.get("operating_margin", {}).get("value")),
            language,
        ),
        metric_row("Net Margin", pct(metrics.get("net_margin", {}).get("value")), language),
        metric_row(
            "Current Ratio", number(metrics.get("current_ratio", {}).get("value")), language
        ),
        metric_row(
            "Debt / Assets",
            number(metrics.get("debt_to_assets", {}).get("value")),
            language,
        ),
        metric_row("Free Cash Flow", money(company.get("free_cash_flow")), language),
    ]
    body = localized(
        "Profitability, liquidity, leverage, and cash generation are shown before interpretation.",
        language,
    )
    return ReportSection("financial", title, body, rows)


def valuation_section(value: dict[str, Any], title: str, language: str) -> ReportSection:
    metrics = value.get("metrics", {})
    rows = [
        localized_valuation_row(metrics, "P/E", "pe", language),
        localized_valuation_row(metrics, "P/S", "ps", language),
        localized_valuation_row(metrics, "FCF Yield", "fcf_yield", language),
        localized_valuation_row(metrics, "Earnings Yield", "earnings_yield", language),
    ]
    body = localized(
        "Valuation is expensive when investors are paying a high price for current fundamentals.",
        language,
    )
    return ReportSection("valuation", title, body, rows)


def risk_section(risks: dict[str, Any], title: str, language: str) -> ReportSection:
    rows = [
        risk_row(risk_label(str(item.get("id"))), "Triggered", language)
        for item in risks.get("risk_checks", [])
        if isinstance(item, dict) and item.get("status") == "triggered"
    ]
    if not rows:
        rows.append(risk_row("Quantitative checks", "No triggered risk checks", language))
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
    rows = [scenario_row("Profitability and cash generation remain durable", language)]
    if key == "bear":
        rows = [scenario_row("Valuation multiple compresses", language)]
        if triggered:
            rows.append(scenario_row("Triggered financial risks worsen", language))
    elif "ATTRACTIVE" in valuation_label:
        rows.append(scenario_row("Valuation leaves room for upside", language))
    return ReportSection(
        key,
        title,
        localized("Scenario points are evidence-led, not recommendations.", language),
        rows,
    )


def metric_row(label: str, value: str, language: str) -> dict[str, str]:
    if language == "ko":
        from _report_format import korean_metric_label

        return {"지표": korean_metric_label(label), "값": value}
    return {"Metric": label, "Value": value}


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
