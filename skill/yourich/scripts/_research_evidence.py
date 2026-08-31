from __future__ import annotations

from typing import Final

from _evidence import HIGH, MEDIUM, ResearchEvidence, evidence_from_section
from _filing_types import Filing, FilingSection
from _research_text import has_topic, section_excerpt

BUSINESS_TOPICS: Final = (
    "revenue_drivers",
    "customer_structure",
    "segments",
    "geography",
    "recurring_vs_transactional",
    "cost_structure",
    "capital_intensity",
    "industry_position",
    "key_dependencies",
)


def section_evidence(filing: Filing, sections: list[FilingSection]) -> list[ResearchEvidence]:
    evidence = []
    for section in sections:
        evidence.extend(core_section_evidence(filing, section))
        if section.name in {"business", "mda"} and has_topic(section, "capital_allocation"):
            evidence.append(topic_evidence(filing, section, "capital_allocation"))
        if section.name in {"business", "mda"} and has_topic(section, "management"):
            evidence.append(topic_evidence(filing, section, "management"))
    return evidence


def core_section_evidence(filing: Filing, section: FilingSection) -> list[ResearchEvidence]:
    if section.name == "business":
        business = [evidence_from_section(filing, section, "business_model", HIGH)]
        business.extend(
            topic_evidence(filing, section, topic)
            for topic in BUSINESS_TOPICS
            if has_topic(section, topic)
        )
        return business
    if section.name == "risk_factors":
        return [evidence_from_section(filing, section, "qualitative_risk", HIGH)]
    if section.name == "mda":
        return [evidence_from_section(filing, section, "mda_financial_narrative", HIGH)]
    if section.name == "financial_statements":
        return [evidence_from_section(filing, section, "financial_statement_context", MEDIUM)]
    if section.name == "controls":
        return [evidence_from_section(filing, section, "controls", MEDIUM)]
    return []


def topic_evidence(filing: Filing, section: FilingSection, claim_type: str) -> ResearchEvidence:
    excerpt = section_excerpt(section, (claim_type.replace("_", " "), claim_type.split("_")[0]))
    narrowed = FilingSection(name=section.name, item=section.item, text=excerpt)
    return evidence_from_section(filing, narrowed, claim_type, MEDIUM)
