from __future__ import annotations

from collections import Counter
from typing import Any, Final

from _industry import classify_industry
from _peer_comparability import candidate_for
from _peer_discovery import automatic_peer_tickers
from _peer_metrics import normalized_metrics, peer_aggregates

VERSION: Final = "0.9.0"
MIN_PEERS: Final = 2
PREMIUM_THRESHOLD: Final = 20.0
SUPPORT_THRESHOLD: Final = 10.0
SUPPORTED_DRIVER_COUNT: Final = 2
SHARED_RISK_MIN_SOURCES: Final = 2


def build_peer_research(
    company: dict[str, Any],
    peers: list[dict[str, Any]],
    *,
    earnings_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mode = "explicit" if peers else "automatic"
    selected_peers = peers or automatic_placeholder_peers(company)
    candidates = [candidate_for(company, peer, mode) for peer in selected_peers]
    company_metrics = normalized_metrics(company)
    peer_metrics = [normalized_metrics(peer) for peer in selected_peers]
    aggregates = peer_aggregates(company_metrics, peer_metrics)
    warnings = peer_warnings(candidates, aggregates["warnings"], company, selected_peers)
    relative = relative_valuation(aggregates["aggregates"])
    return {
        "version": VERSION,
        "ticker": company.get("ticker"),
        "company": company.get("company"),
        "industry": classify_industry(company),
        "peer_set": peer_set(mode, candidates, warnings),
        "company_metrics": company_metrics,
        "peer_metrics": peer_metrics,
        "peer_aggregates": aggregates["aggregates"],
        "relative_valuation": relative,
        "premium_justification": premium_justification(aggregates["aggregates"]),
        "business_comparison": business_comparison(company, selected_peers),
        "segment_comparison": segment_comparison(company, selected_peers),
        "industry_risks": industry_risks(company, selected_peers),
        "industry_changes": industry_changes(company, selected_peers),
        "earnings_context": earnings_context,
        "evidence": evidence(company, selected_peers),
        "warnings": warnings,
        "data_quality": data_quality(candidates, aggregates["warnings"]),
    }


def automatic_placeholder_peers(company: dict[str, Any]) -> list[dict[str, Any]]:
    ticker = str(company.get("ticker") or "")
    return [
        {
            "ticker": peer,
            "company": peer,
            "sic": company.get("sic"),
            "sic_description": company.get("sic_description"),
            "business_description": company.get("business_description"),
        }
        for peer in automatic_peer_tickers(ticker)
    ]


def peer_warnings(
    candidates: list[dict[str, Any]],
    aggregate_warnings: list[str],
    company: dict[str, Any],
    peers: list[dict[str, Any]],
) -> list[str]:
    warnings = list(aggregate_warnings)
    if len(candidates) < MIN_PEERS:
        warnings.append("PEER_SET_TOO_SMALL")
    if any(candidate["comparability_status"] == "INSUFFICIENT_DATA" for candidate in candidates):
        warnings.append("PEER_SET_LOW_COMPARABILITY")
    if classify_industry(company)["confidence"] != "HIGH":
        warnings.append("INDUSTRY_CLASSIFICATION_WEAK")
    if any(candidate["available_data"] != "complete" for candidate in candidates):
        warnings.append("PEER_DATA_INCOMPLETE")
    if has_segment_mismatch(company, peers):
        warnings.append("SEGMENT_NOT_COMPARABLE")
    if industry_changes(company, peers)["status"] == "INSUFFICIENT_EVIDENCE":
        warnings.append("INDUSTRY_SIGNAL_INSUFFICIENT")
    return sorted(set(warnings))


def peer_set(mode: str, candidates: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    weak = any(candidate["comparability_status"] == "INSUFFICIENT_DATA" for candidate in candidates)
    quality = "HIGH"
    if len(candidates) < MIN_PEERS or weak:
        quality = "LOW"
    elif mode == "automatic" or any(
        candidate["comparability_status"] == "WEAK_COMPARABLE" for candidate in candidates
    ):
        quality = "MEDIUM"
    return {
        "selection_mode": mode,
        "peer_count": len(candidates),
        "quality": quality,
        "warnings": [warning for warning in warnings if warning.startswith("PEER_SET")],
        "candidates": candidates,
    }


def relative_valuation(aggregates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in aggregates if item["metric"] in {"pe", "ps", "pb", "fcf_yield"}]


def premium_justification(aggregates: list[dict[str, Any]]) -> dict[str, Any]:
    pe = aggregate_for(aggregates, "pe")
    if pe is None or pe.get("premium_percent") is None:
        return {"status": "INSUFFICIENT_EVIDENCE", "drivers": []}
    premium = float(str(pe["premium_percent"]))
    support = supported_drivers(aggregates)
    if premium > PREMIUM_THRESHOLD and len(support) >= SUPPORTED_DRIVER_COUNT:
        return {"status": "PREMIUM_SUPPORTED", "drivers": support}
    if premium > PREMIUM_THRESHOLD and support:
        return {"status": "PREMIUM_PARTIALLY_SUPPORTED", "drivers": support}
    if premium > PREMIUM_THRESHOLD:
        return {"status": "PREMIUM_NOT_SUPPORTED", "drivers": []}
    if premium < -PREMIUM_THRESHOLD:
        return {"status": "DISCOUNT_UNEXPLAINED", "drivers": support}
    return {"status": "NO_MEANINGFUL_PREMIUM", "drivers": support}


def supported_drivers(aggregates: list[dict[str, Any]]) -> list[str]:
    drivers = []
    for metric in ("revenue_growth", "net_margin", "fcf_margin"):
        aggregate = aggregate_for(aggregates, metric)
        if (
            aggregate is not None
            and float(str(aggregate.get("premium_percent") or 0)) >= SUPPORT_THRESHOLD
        ):
            drivers.append(metric)
    return drivers


def aggregate_for(aggregates: list[dict[str, Any]], metric: str) -> dict[str, Any] | None:
    for aggregate in aggregates:
        if aggregate["metric"] == metric:
            return aggregate
    return None


def business_comparison(
    company: dict[str, Any], peers: list[dict[str, Any]]
) -> list[dict[str, str]]:
    rows = [business_row(company)]
    rows.extend(business_row(peer) for peer in peers)
    return rows


def business_row(company: dict[str, Any]) -> dict[str, str]:
    return {
        "ticker": str(company.get("ticker") or ""),
        "business_model": str(company.get("business_description") or "Insufficient evidence"),
        "evidence": str(
            company.get("field_sources", {}).get("business_description") or "Insufficient evidence"
        ),
    }


def segment_comparison(company: dict[str, Any], peers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "SEGMENT_NOT_COMPARABLE" if has_segment_mismatch(company, peers) else "COMPARABLE"
    }


def has_segment_mismatch(company: dict[str, Any], peers: list[dict[str, Any]]) -> bool:
    company_segments = segment_names(company)
    return any(company_segments.isdisjoint(segment_names(peer)) for peer in peers)


def segment_names(company: dict[str, Any]) -> set[str]:
    segments = company.get("segments")
    if not isinstance(segments, list):
        return set()
    return {
        str(item.get("name")) for item in segments if isinstance(item, dict) and item.get("name")
    }


def industry_risks(company: dict[str, Any], peers: list[dict[str, Any]]) -> dict[str, Any]:
    counts = risk_counts(company, peers)
    shared = [risk for risk, count in counts.items() if count >= SHARED_RISK_MIN_SOURCES]
    specific = [risk for risk, count in counts.items() if count == 1]
    return {"industry_wide": shared, "company_specific": specific}


def industry_changes(company: dict[str, Any], peers: list[dict[str, Any]]) -> dict[str, Any]:
    shared = industry_risks(company, peers)["industry_wide"]
    return {"status": "EMERGING" if shared else "INSUFFICIENT_EVIDENCE", "signals": shared}


def risk_counts(company: dict[str, Any], peers: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for item in [company, *peers]:
        risks = item.get("industry_risks")
        if isinstance(risks, list):
            counts.update(str(risk) for risk in risks)
    return counts


def evidence(company: dict[str, Any], peers: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "ticker": str(item.get("ticker") or ""),
            "source": str(item.get("field_sources", {}).get("business_description") or "SEC:SIC"),
            "excerpt": str(item.get("business_description") or item.get("sic_description") or ""),
        }
        for item in [company, *peers]
    ]


def data_quality(candidates: list[dict[str, Any]], aggregate_warnings: list[str]) -> dict[str, Any]:
    return {
        "comparability_available": bool(candidates),
        "basis_warnings": aggregate_warnings,
        "evidence_quality": "MEDIUM" if candidates else "LOW",
    }
