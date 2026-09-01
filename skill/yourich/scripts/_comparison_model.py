from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Final

from _core import decimal_or_none

MARGIN_GAP: Final = Decimal("5")
PE_GAP: Final = Decimal("10")
YIELD_GAP: Final = Decimal("1")
MAX_POINTS: Final = 4
MIN_COMPARISON_ENTRIES: Final = 2
MIN_SUBSTANTIVE_WORDS: Final = 5
BUSINESS_CLAIM_TYPES: Final = (
    "industry_position",
    "key_dependencies",
    "segments",
    "revenue_drivers",
    "business_model",
)
FILING_ITEM_HEADING = re.compile(r"^(item\s+\d+[a-z]?\.?|business|risk factors)\.?$", re.IGNORECASE)
TOC_FRAGMENT = re.compile(r"^[a-z ]+\d+[a-z0-9 ]*$", re.IGNORECASE)


def build_comparison_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    entries = [comparison_entry(row) for row in rows]
    differences = key_differences(entries)
    return {
        "title": " vs ".join(entry["ticker"] for entry in entries),
        "entries": entries,
        "key_differences": differences,
        "conclusion": conclusion_points(entries, differences),
        "what_changed": what_changed_points(entries),
    }


def comparison_entry(row: dict[str, Any]) -> dict[str, Any]:
    research = research_context(row)
    return {
        "ticker": str(row.get("ticker", "")),
        "valuation": row.get("valuation", {}),
        "financial_quality": row.get("financial_quality", {}),
        "risk": row.get("risk", {}),
        "comparison_basis": row.get("comparison_basis", {}),
        "business_quality": business_quality(research),
        "evidence_quality": evidence_quality(research),
        "earnings": earnings_context(research),
        "bull_case": bull_case(row, research),
        "bear_case": bear_case(row, research),
        "what_changed": what_changed(research),
    }


def research_context(row: dict[str, Any]) -> dict[str, Any] | None:
    context = row.get("research_context")
    return context if isinstance(context, dict) else None


def business_quality(research: dict[str, Any] | None) -> str | None:
    return first_available_evidence(research, BUSINESS_CLAIM_TYPES)


def evidence_quality(research: dict[str, Any] | None) -> str:
    if research is None:
        return "LOW"
    confidence = research.get("research_confidence")
    return str(confidence) if confidence else "LOW"


def earnings_context(research: dict[str, Any] | None) -> dict[str, Any] | None:
    if research is None:
        return None
    context = research.get("earnings_context")
    return context if isinstance(context, dict) else None


def bull_case(row: dict[str, Any], research: dict[str, Any] | None) -> list[str]:
    points = []
    business = business_quality(research)
    if business:
        points.append(business)
    net_margin = financial_metric(row, "net_margin")
    if net_margin is not None and net_margin >= Decimal("20"):
        points.append("Profitability is already strong on reported financial metrics.")
    fcf_margin = financial_metric(row, "fcf_margin")
    if fcf_margin is not None and fcf_margin >= Decimal("10"):
        points.append("Free cash flow generation supports the upside case.")
    fcf_yield = valuation_metric(row, "fcf_yield")
    if fcf_yield is not None and fcf_yield >= Decimal("3"):
        points.append("Cash-flow yield is stronger than the comparison peer.")
    return points[:MAX_POINTS]


def bear_case(row: dict[str, Any], research: dict[str, Any] | None) -> list[str]:
    points = []
    risk = evidence_excerpt(research, "qualitative_risk")
    if risk:
        points.append(risk)
    triggered = triggered_risks(row)
    points.extend(triggered)
    pe = valuation_metric(row, "pe")
    if pe is not None and pe >= Decimal("45"):
        points.append("P/E multiple already reflects elevated expectations.")
    return points[:MAX_POINTS]


def key_differences(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    if len(entries) < MIN_COMPARISON_ENTRIES:
        return []
    first = entries[0]
    second = entries[1]
    points = []
    points.extend(metric_difference(first, second, "net_margin", MARGIN_GAP))
    points.extend(metric_difference(first, second, "fcf_margin", MARGIN_GAP))
    points.extend(valuation_difference(first, second, "pe", PE_GAP, higher_is_burden=True))
    points.extend(
        valuation_difference(first, second, "fcf_yield", YIELD_GAP, higher_is_burden=False)
    )
    points.extend(evidence_difference(first, second))
    return points


def metric_difference(
    first: dict[str, Any], second: dict[str, Any], metric: str, threshold: Decimal
) -> list[dict[str, str]]:
    first_value = entry_financial_metric(first, metric)
    second_value = entry_financial_metric(second, metric)
    if first_value is None or second_value is None or abs(first_value - second_value) < threshold:
        return []
    leader, laggard = ordered_entries(first, second, first_value, second_value)
    return [{"kind": metric, "leader": leader["ticker"], "laggard": laggard["ticker"]}]


def valuation_difference(
    first: dict[str, Any],
    second: dict[str, Any],
    metric: str,
    threshold: Decimal,
    *,
    higher_is_burden: bool,
) -> list[dict[str, str]]:
    first_value = entry_valuation_metric(first, metric)
    second_value = entry_valuation_metric(second, metric)
    if first_value is None or second_value is None or abs(first_value - second_value) < threshold:
        return []
    leader, laggard = ordered_entries(first, second, first_value, second_value)
    burden = leader if higher_is_burden else laggard
    stronger = leader if not higher_is_burden else laggard
    return [{"kind": metric, "leader": stronger["ticker"], "laggard": burden["ticker"]}]


def evidence_difference(first: dict[str, Any], second: dict[str, Any]) -> list[dict[str, str]]:
    first_score = evidence_score(first["evidence_quality"])
    second_score = evidence_score(second["evidence_quality"])
    if first_score == second_score:
        return []
    leader, laggard = ordered_entries(first, second, first_score, second_score)
    return [{"kind": "evidence_quality", "leader": leader["ticker"], "laggard": laggard["ticker"]}]


def ordered_entries(
    first: dict[str, Any], second: dict[str, Any], first_value: Decimal, second_value: Decimal
) -> tuple[dict[str, Any], dict[str, Any]]:
    return (first, second) if first_value >= second_value else (second, first)


def evidence_score(value: str) -> Decimal:
    scores = {"HIGH": Decimal("3"), "MEDIUM": Decimal("2"), "LOW": Decimal("1")}
    return scores.get(value, Decimal("1"))


def conclusion_points(
    entries: list[dict[str, Any]], differences: list[dict[str, str]]
) -> list[dict[str, str]]:
    evidence = [item for item in differences if item.get("kind") == "evidence_quality"]
    metrics = [item for item in differences if item.get("kind") != "evidence_quality"]
    points = [*metrics[:3], *evidence[:1]]
    if points:
        return points
    if all(entry["business_quality"] is None for entry in entries):
        return [{"kind": "insufficient_evidence", "leader": "", "laggard": ""}]
    return []


def what_changed_points(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {"ticker": entry["ticker"], "change": entry["what_changed"]}
        for entry in entries
        if entry["what_changed"]
    ]


def what_changed(research: dict[str, Any] | None) -> str | None:
    if research is None:
        return None
    change = research.get("risk_analysis", {}).get("risk_factor_change")
    if not isinstance(change, dict):
        return None
    status = change.get("status")
    if status in {None, "INSUFFICIENT_EVIDENCE"}:
        return None
    return str(status)


def evidence_excerpt(research: dict[str, Any] | None, claim_type: str) -> str | None:
    if research is None:
        return None
    evidence = research.get("evidence")
    if not isinstance(evidence, list):
        return None
    for item in evidence:
        if isinstance(item, dict) and item.get("claim_type") == claim_type:
            excerpt = item.get("excerpt")
            if excerpt:
                return first_sentence(str(excerpt))
    return None


def first_available_evidence(
    research: dict[str, Any] | None, claim_types: tuple[str, ...]
) -> str | None:
    for claim_type in claim_types:
        evidence = evidence_excerpt(research, claim_type)
        if evidence is not None:
            return evidence
    return None


def first_sentence(text: str) -> str:
    normalized = " ".join(text.split())
    for sentence in normalized.split("."):
        candidate = sentence.strip()
        if candidate and not is_heading_fragment(candidate):
            return candidate + "."
    return normalized


def is_heading_fragment(candidate: str) -> bool:
    words = candidate.split()
    return (
        FILING_ITEM_HEADING.fullmatch(candidate) is not None
        or TOC_FRAGMENT.fullmatch(candidate) is not None
        or "item " in candidate.lower()
        or len(words) < MIN_SUBSTANTIVE_WORDS
    )


def triggered_risks(row: dict[str, Any]) -> list[str]:
    checks = row.get("risk", {}).get("risk_checks", [])
    if not isinstance(checks, list):
        return []
    return [
        str(item.get("id", "risk"))
        for item in checks
        if isinstance(item, dict) and item.get("status") == "triggered"
    ]


def financial_metric(row: dict[str, Any], metric: str) -> Decimal | None:
    return decimal_or_none(
        row.get("financial_quality", {}).get("metrics", {}).get(metric, {}).get("value")
    )


def valuation_metric(row: dict[str, Any], metric: str) -> Decimal | None:
    return decimal_or_none(row.get("valuation", {}).get("metrics", {}).get(metric, {}).get("value"))


def entry_financial_metric(entry: dict[str, Any], metric: str) -> Decimal | None:
    return decimal_or_none(
        entry.get("financial_quality", {}).get("metrics", {}).get(metric, {}).get("value")
    )


def entry_valuation_metric(entry: dict[str, Any], metric: str) -> Decimal | None:
    return decimal_or_none(
        entry.get("valuation", {}).get("metrics", {}).get(metric, {}).get("value")
    )
