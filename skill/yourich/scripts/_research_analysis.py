from __future__ import annotations

from typing import Any, Final

from _evidence import (
    HIGH,
    INSUFFICIENT_EVIDENCE,
    LOW,
    ResearchClaim,
    ResearchEvidence,
    linked_claim,
    unsupported_claim,
)
from _research_text import normalized_tokens

MIN_COMPARABLE_RISK_FACTORS: Final = 2
MATERIAL_CHANGE_OVERLAP: Final = 0.82
HIGH_COVERAGE_EVIDENCE_COUNT: Final = 2
BUSINESS_FIELDS: Final = (
    "business_model",
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


def research_claims(evidence: list[ResearchEvidence]) -> list[ResearchClaim]:
    return [
        linked_claim(
            "Business model must be tied to filing evidence.",
            "business",
            filter_evidence(evidence, "business_model"),
        ),
        linked_claim(
            "Risks must separate SEC filing risk from quantitative risk.",
            "risk",
            filter_evidence(evidence, "qualitative_risk"),
        ),
        linked_claim(
            "MD&A narrative is available for financial cross-checks.",
            "mda",
            filter_evidence(evidence, "mda_financial_narrative"),
        ),
    ]


def filter_evidence(evidence: list[ResearchEvidence], claim_type: str) -> list[ResearchEvidence]:
    return [item for item in evidence if item.claim_type == claim_type]


def business_analysis(evidence: list[ResearchEvidence]) -> dict[str, Any]:
    return {
        field: claim_or_gap(field, filter_evidence(evidence, field)) for field in BUSINESS_FIELDS
    }


def claim_or_gap(field: str, evidence: list[ResearchEvidence]) -> dict[str, Any]:
    if not evidence:
        return unsupported_claim(f"No filing evidence found for {field}.", field).to_dict()
    return linked_claim(
        f"Review filing excerpts before asserting {field}.", field, evidence
    ).to_dict()


def business_quality(evidence: list[ResearchEvidence]) -> dict[str, Any]:
    business = filter_evidence(evidence, "business_model")
    risks = filter_evidence(evidence, "qualitative_risk")
    return {
        "structure": "EVIDENCE_LINKED" if business else "INSUFFICIENT_EVIDENCE",
        "durability": claim_or_gap("durability", business),
        "resilience": claim_or_gap("resilience", risks),
        "score": None,
    }


def moat_analysis(evidence: list[ResearchEvidence]) -> dict[str, Any]:
    business = filter_evidence(evidence, "business_model")
    if not business:
        return {"status": "NO_CLEAR_EVIDENCE", "claims": []}
    return {
        "status": "REQUIRES_AGENT_INTERPRETATION",
        "claims": [
            linked_claim(
                "Moat evidence requires explicit filing support.", "moat", business
            ).to_dict()
        ],
    }


def management_analysis(evidence: list[ResearchEvidence]) -> dict[str, Any]:
    management = filter_evidence(evidence, "management")
    return {
        "basis": "official filing evidence only",
        "claim": claim_or_gap("management", management),
    }


def capital_allocation(evidence: list[ResearchEvidence]) -> dict[str, Any]:
    allocation = filter_evidence(evidence, "capital_allocation")
    return {
        "basis": "official filing evidence only",
        "claim": claim_or_gap("capital_allocation", allocation),
    }


def risk_analysis(
    evidence: list[ResearchEvidence], financial_payload: dict[str, Any]
) -> dict[str, Any]:
    return {
        "qualitative_filing_risks": [
            item.to_dict() for item in filter_evidence(evidence, "qualitative_risk")
        ],
        "risk_factor_change": risk_factor_change(filter_evidence(evidence, "qualitative_risk")),
        "quantitative_risk": financial_payload.get("risk_checks"),
    }


def risk_factor_change(risk_evidence: list[ResearchEvidence]) -> dict[str, Any]:
    if len(risk_evidence) < MIN_COMPARABLE_RISK_FACTORS:
        return {"status": INSUFFICIENT_EVIDENCE}
    current = risk_evidence[0]
    previous = risk_evidence[1]
    current_tokens = normalized_tokens(current.excerpt)
    previous_tokens = normalized_tokens(previous.excerpt)
    overlap = len(current_tokens & previous_tokens)
    total = max(len(current_tokens | previous_tokens), 1)
    status = "NO_MATERIAL_TEXT_CHANGE" if overlap / total >= MATERIAL_CHANGE_OVERLAP else "CHANGED"
    return {
        "status": status,
        "current_filing": current.filing_date,
        "previous_filing": previous.filing_date,
        "evidence_ids": [current.id, previous.id],
    }


def mda_cross_check(
    evidence: list[ResearchEvidence], financial_payload: dict[str, Any]
) -> dict[str, Any]:
    mda = filter_evidence(evidence, "mda_financial_narrative")
    has_metrics = financial_payload.get("valuation") is not None
    if not mda or not has_metrics:
        return {"status": "INSUFFICIENT_DATA", "evidence_ids": []}
    return {
        "status": "NEEDS_AGENT_INTERPRETATION",
        "evidence_ids": [item.id for item in mda],
        "quantitative_context": financial_payload.get("valuation"),
    }


def evidence_coverage(evidence: list[ResearchEvidence]) -> dict[str, str]:
    return {
        "business": coverage_label(filter_evidence(evidence, "business_model")),
        "risk": coverage_label(filter_evidence(evidence, "qualitative_risk")),
        "management": coverage_label(filter_evidence(evidence, "management")),
        "capital_allocation": coverage_label(filter_evidence(evidence, "capital_allocation")),
    }


def coverage_label(evidence: list[ResearchEvidence]) -> str:
    if len(evidence) >= HIGH_COVERAGE_EVIDENCE_COUNT:
        return HIGH
    if evidence:
        return "MEDIUM"
    return LOW


def research_confidence(coverage: dict[str, str], financial_payload: dict[str, Any]) -> str:
    if (
        coverage["business"] == HIGH
        and coverage["risk"] != LOW
        and financial_payload.get("valuation")
    ):
        return HIGH
    if coverage["business"] != LOW or coverage["risk"] != LOW:
        return "MEDIUM"
    return LOW


def conclusion(coverage: dict[str, str], financial_payload: dict[str, Any]) -> str:
    valuation_context = financial_payload.get("valuation")
    if coverage["business"] == LOW and coverage["risk"] == LOW:
        return "INSUFFICIENT EVIDENCE"
    if not isinstance(valuation_context, dict):
        return "RESEARCH CONTEXT READY / FINANCIAL DATA PARTIAL"
    raw = valuation_context.get("conclusion")
    return str(raw) if raw else "RESEARCH CONTEXT READY"
