from __future__ import annotations

from typing import TYPE_CHECKING, Any

from _core import ToolError, clean_ticker
from _filing_parser import clean_filing_html, extract_sections
from _filing_provider import FilingProvider, SecFilingProvider
from _research_analysis import (
    business_analysis,
    business_quality,
    capital_allocation,
    conclusion,
    evidence_coverage,
    management_analysis,
    mda_cross_check,
    moat_analysis,
    research_claims,
    research_confidence,
    risk_analysis,
)
from _research_analysis import (
    risk_factor_change as analyze_risk_factor_change,
)
from _research_evidence import section_evidence
from _research_types import RESEARCH_MODES, ResearchRequest
from _sec import fetch_financials
from risk import risk_checks
from valuation import valuation

if TYPE_CHECKING:
    from _evidence import ResearchEvidence
    from _filing_types import Filing, FilingSection


def build_research_context(
    request: ResearchRequest,
    provider: FilingProvider | None = None,
) -> dict[str, Any]:
    ticker = clean_ticker(request.ticker)
    selected_provider = provider or SecFilingProvider()
    filings = selected_provider.get_filings(ticker, request.forms, request.filing_limit)
    warnings: list[str] = []
    parsed_sections: list[tuple[Filing, list[FilingSection]]] = []
    evidence: list[ResearchEvidence] = []
    for filing in filings:
        document = selected_provider.get_document(filing)
        sections, section_warnings = extract_sections(clean_filing_html(document.html), filing.form)
        warnings.extend(section_warnings)
        parsed_sections.append((filing, sections))
        evidence.extend(section_evidence(filing, sections))
    selected = evidence[: request.evidence_limit]
    financial_payload = load_financial_context(ticker)
    claims = research_claims(selected)
    coverage = evidence_coverage(selected)
    return {
        "version": "0.4.1",
        "ticker": ticker,
        "mode": request.mode,
        "filings": [filing.to_dict() for filing in filings],
        "sections": section_inventory(parsed_sections),
        "evidence": [item.to_dict() for item in selected],
        "claims": [item.to_dict() for item in claims],
        "business_analysis": business_analysis(selected),
        "business_quality": business_quality(selected),
        "moat_analysis": moat_analysis(selected),
        "management_analysis": management_analysis(selected),
        "capital_allocation": capital_allocation(selected),
        "risk_analysis": risk_analysis(selected, financial_payload),
        "mda_cross_check": mda_cross_check(selected, financial_payload),
        "evidence_coverage": coverage,
        "research_confidence": research_confidence(coverage, financial_payload),
        "conclusion": conclusion(coverage, financial_payload),
        "warnings": sorted(set(warnings + financial_payload["warnings"])),
    }


def section_inventory(
    parsed_sections: list[tuple[Filing, list[FilingSection]]],
) -> list[dict[str, Any]]:
    return [
        {
            "accession_number": filing.accession_number,
            "form": filing.form,
            "filing_date": filing.filing_date,
            "sections": [section.name for section in sections],
        }
        for filing, sections in parsed_sections
    ]


def load_financial_context(ticker: str) -> dict[str, Any]:
    try:
        financials = fetch_financials(ticker)
    except ToolError as exc:
        return {
            "valuation": None,
            "risk_checks": None,
            "warnings": [f"FINANCIAL_DATA_PARTIAL: {exc}"],
        }
    return {
        "valuation": valuation(financials),
        "risk_checks": risk_checks(financials).get("risk_checks"),
        "warnings": [],
    }


def risk_factor_change(risk_evidence: list[ResearchEvidence]) -> dict[str, Any]:
    return analyze_risk_factor_change(risk_evidence)


def parse_research_request(
    ticker: str, mode: str, limit: int, evidence_limit: int
) -> ResearchRequest:
    if mode not in RESEARCH_MODES:
        raise ToolError(f"unsupported research mode: {mode}")
    return ResearchRequest(
        ticker=ticker,
        mode=mode,
        filing_limit=max(1, limit),
        evidence_limit=max(1, evidence_limit),
    )
