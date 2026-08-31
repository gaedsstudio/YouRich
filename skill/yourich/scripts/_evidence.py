from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from _filing_types import Filing, FilingSection

MAX_EXCERPT_CHARS: Final = 900
HIGH_CONFIDENCE_EVIDENCE_COUNT: Final = 2
SUPPORTED: Final = "SUPPORTED"
PARTIALLY_SUPPORTED: Final = "PARTIALLY_SUPPORTED"
CONTRADICTED: Final = "CONTRADICTED"
INSUFFICIENT_EVIDENCE: Final = "INSUFFICIENT_EVIDENCE"
HIGH: Final = "HIGH"
MEDIUM: Final = "MEDIUM"
LOW: Final = "LOW"


@dataclass(frozen=True, slots=True)
class ResearchEvidence:
    id: str
    ticker: str
    claim_type: str
    source_type: str
    filing_form: str | None
    filing_date: str | None
    period_end: str | None
    section: str | None
    source_url: str
    excerpt: str
    support_status: str
    confidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ticker": self.ticker,
            "claim_type": self.claim_type,
            "source_type": self.source_type,
            "filing_form": self.filing_form,
            "filing_date": self.filing_date,
            "period_end": self.period_end,
            "section": self.section,
            "source_url": self.source_url,
            "excerpt": self.excerpt,
            "support_status": self.support_status,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class ResearchClaim:
    claim: str
    category: str
    status: str
    confidence: str
    evidence_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "category": self.category,
            "status": self.status,
            "confidence": self.confidence,
            "evidence_ids": self.evidence_ids,
        }


def evidence_from_section(
    filing: Filing, section: FilingSection, claim_type: str, confidence: str = MEDIUM
) -> ResearchEvidence:
    excerpt = section.text[:MAX_EXCERPT_CHARS].strip()
    digest = hashlib.sha256(
        f"{filing.accession_number}:{section.name}:{claim_type}".encode()
    ).hexdigest()[:12]
    return ResearchEvidence(
        id=f"ev_{digest}",
        ticker=filing.ticker,
        claim_type=claim_type,
        source_type="SEC_FILING",
        filing_form=filing.form,
        filing_date=filing.filing_date,
        period_end=filing.period_end,
        section=section.name,
        source_url=filing.filing_url,
        excerpt=excerpt,
        support_status=SUPPORTED if excerpt else INSUFFICIENT_EVIDENCE,
        confidence=confidence if excerpt else LOW,
    )


def unsupported_claim(claim: str, category: str) -> ResearchClaim:
    return ResearchClaim(
        claim=claim,
        category=category,
        status=INSUFFICIENT_EVIDENCE,
        confidence=LOW,
        evidence_ids=[],
    )


def linked_claim(claim: str, category: str, evidence: list[ResearchEvidence]) -> ResearchClaim:
    if not evidence:
        return unsupported_claim(claim, category)
    confidence = HIGH if len(evidence) >= HIGH_CONFIDENCE_EVIDENCE_COUNT else MEDIUM
    return ResearchClaim(
        claim=claim,
        category=category,
        status=SUPPORTED,
        confidence=confidence,
        evidence_ids=[item.id for item in evidence],
    )


def detect_source_conflicts(evidence: list[ResearchEvidence]) -> list[ResearchClaim]:
    grouped: dict[str, set[str]] = {}
    for item in evidence:
        grouped.setdefault(item.claim_type, set()).add(item.support_status)
    conflicts = []
    for claim_type, statuses in grouped.items():
        if SUPPORTED in statuses and CONTRADICTED in statuses:
            conflicts.append(
                ResearchClaim(
                    claim=f"Evidence conflicts for {claim_type}.",
                    category=claim_type,
                    status=CONTRADICTED,
                    confidence=MEDIUM,
                    evidence_ids=[item.id for item in evidence if item.claim_type == claim_type],
                )
            )
    return conflicts
