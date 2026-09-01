from __future__ import annotations

from typing import Any, Final

from _industry import classify_industry

HIGH_SCORE: Final = 85
COMPARABLE_SCORE: Final = 70
PARTIAL_SCORE: Final = 50
WEAK_SCORE: Final = 30
HIGH_OVERLAP: Final = 0.25
MEDIUM_OVERLAP: Final = 0.1
HIGH_SCALE_RATIO: Final = 2
MEDIUM_SCALE_RATIO: Final = 5


def candidate_for(
    company: dict[str, Any], peer: dict[str, Any], selection_mode: str
) -> dict[str, Any]:
    company_industry = classify_industry(company)
    peer_industry = classify_industry(peer)
    classification = classification_match(company_industry, peer_industry)
    overlap = business_overlap(company, peer)
    scale = scale_similarity(company, peer)
    score = comparability_score(classification, overlap, scale)
    return {
        "ticker": peer.get("ticker"),
        "company": peer.get("company"),
        "reason_selected": reason_selected(selection_mode, classification, overlap),
        "classification_match": classification,
        "business_overlap": overlap,
        "scale_similarity": scale,
        "available_data": available_data(peer),
        "comparability_score": score,
        "comparability_status": comparability_status(score),
    }


def classification_match(company_industry: dict[str, Any], peer_industry: dict[str, Any]) -> str:
    if company_industry.get("industry") == peer_industry.get("industry"):
        return "same_industry"
    if company_industry.get("sector") == peer_industry.get("sector"):
        return "same_sector"
    return "different_sector"


def business_overlap(company: dict[str, Any], peer: dict[str, Any]) -> str:
    first = token_set(str(company.get("business_description") or ""))
    second = token_set(str(peer.get("business_description") or ""))
    if not first or not second:
        return "insufficient_data"
    overlap = len(first & second) / len(first | second)
    if overlap >= HIGH_OVERLAP:
        return "high"
    if overlap >= MEDIUM_OVERLAP:
        return "medium"
    return "low"


def scale_similarity(company: dict[str, Any], peer: dict[str, Any]) -> str:
    company_revenue = numeric(company.get("revenue"))
    peer_revenue = numeric(peer.get("revenue"))
    if company_revenue is None or peer_revenue is None or min(company_revenue, peer_revenue) <= 0:
        return "insufficient_data"
    ratio = max(company_revenue, peer_revenue) / min(company_revenue, peer_revenue)
    if ratio <= HIGH_SCALE_RATIO:
        return "high"
    if ratio <= MEDIUM_SCALE_RATIO:
        return "medium"
    return "low"


def comparability_score(classification: str, overlap: str, scale: str) -> int:
    score = {
        "same_industry": 45,
        "same_sector": 25,
        "different_sector": 0,
    }[classification]
    score += {"high": 30, "medium": 18, "low": 8, "insufficient_data": 0}[overlap]
    score += {"high": 25, "medium": 15, "low": 5, "insufficient_data": 0}[scale]
    return score


def comparability_status(score: int) -> str:
    if score >= HIGH_SCORE:
        return "HIGHLY_COMPARABLE"
    if score >= COMPARABLE_SCORE:
        return "COMPARABLE"
    if score >= PARTIAL_SCORE:
        return "PARTIALLY_COMPARABLE"
    if score >= WEAK_SCORE:
        return "WEAK_COMPARABLE"
    return "INSUFFICIENT_DATA"


def reason_selected(selection_mode: str, classification: str, overlap: str) -> str:
    if selection_mode == "explicit":
        return "explicit_peer"
    return f"{classification}+{overlap}_business_overlap"


def available_data(peer: dict[str, Any]) -> str:
    fields = ("revenue", "net_income", "free_cash_flow", "market_cap", "current_price")
    return "complete" if all(peer.get(field) is not None for field in fields) else "partial"


def token_set(text: str) -> set[str]:
    ignored = {"and", "the", "with", "for", "inc", "corporation", "company"}
    return {
        token.lower() for token in text.replace(",", " ").split() if token.lower() not in ignored
    }


def numeric(value: Any) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None
