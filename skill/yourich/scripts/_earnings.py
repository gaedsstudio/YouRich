from __future__ import annotations

from typing import Any

from _core import ToolError, clean_ticker
from _earnings_analysis import (
    actual_comparisons,
    earnings_changes,
    guidance_changes,
    management_tone_changes,
    metric_mismatches,
    thesis_change,
)
from _earnings_parser import extract_earnings_release
from _earnings_provider import EarningsProvider, SecEarningsProvider
from _earnings_types import EarningsRelease, EarningsRequest

VERSION = "0.7.0"


def build_earnings_context(
    request: EarningsRequest,
    provider: EarningsProvider | None = None,
) -> dict[str, Any]:
    ticker = clean_ticker(request.ticker)
    selected_provider = provider or SecEarningsProvider()
    documents = selected_provider.get_documents(ticker, max(1, request.history))
    releases = [
        extract_earnings_release(document, selected_provider.get_document_text(document))
        for document in documents
    ]
    latest = releases[0] if releases else None
    previous = releases[1] if len(releases) > 1 else None
    guidance_delta = guidance_changes(latest, previous)
    actual_delta = actual_comparisons(latest, previous)
    changes = earnings_changes(latest, previous, guidance_delta)
    mismatches = metric_mismatches(latest, request.deterministic_financials)
    warnings = context_warnings(releases, previous, guidance_delta, mismatches)
    return {
        "version": VERSION,
        "ticker": ticker,
        "latest_earnings": latest.document.to_dict() if latest is not None else None,
        "previous_earnings": previous.document.to_dict() if previous is not None else None,
        "reported_metrics": metric_payload(latest),
        "guidance": guidance_payload(latest),
        "guidance_changes": guidance_delta,
        "guidance_vs_actual": actual_delta,
        "management_commentary": commentary_payload(latest),
        "management_tone_changes": management_tone_changes(latest, previous),
        "changes": changes,
        "thesis_change": thesis_change(changes, latest),
        "evidence": evidence_payload(latest),
        "warnings": warnings,
        "data_quality": {
            "source_count": len(releases),
            "official_source_available": bool(releases),
            "mismatches": mismatches,
        },
    }


def parse_earnings_request(
    ticker: str,
    history: int,
    deterministic_financials: dict[str, Any] | None = None,
) -> EarningsRequest:
    if history < 1:
        raise ToolError("history must be at least 1")
    return EarningsRequest(
        ticker=clean_ticker(ticker),
        history=history,
        deterministic_financials=deterministic_financials,
    )


def metric_payload(release: EarningsRelease | None) -> dict[str, Any]:
    if release is None:
        return {}
    return {key: metric.to_dict() for key, metric in release.reported_metrics.items()}


def guidance_payload(release: EarningsRelease | None) -> list[dict[str, Any]]:
    if release is None:
        return []
    return [item.to_dict() for item in release.guidance]


def commentary_payload(release: EarningsRelease | None) -> list[dict[str, Any]]:
    if release is None:
        return []
    return [item.to_dict() for item in release.management_commentary]


def evidence_payload(release: EarningsRelease | None) -> list[dict[str, Any]]:
    if release is None:
        return []
    return release.evidence


def context_warnings(
    releases: list[EarningsRelease],
    previous: EarningsRelease | None,
    guidance_delta: list[dict[str, Any]],
    mismatches: list[dict[str, str]],
) -> list[str]:
    warnings = []
    if not releases:
        warnings.append("NO_OFFICIAL_EARNINGS_RELEASE")
    for release in releases:
        warnings.extend(release.warnings)
    if previous is None:
        warnings.append("PREVIOUS_GUIDANCE_UNAVAILABLE")
    if any(item.get("status") == "NOT_COMPARABLE" for item in guidance_delta):
        warnings.append("GUIDANCE_PERIOD_NOT_COMPARABLE")
    if mismatches:
        warnings.append("EARNINGS_SEC_VALUE_MISMATCH")
    return sorted(set(warnings))
