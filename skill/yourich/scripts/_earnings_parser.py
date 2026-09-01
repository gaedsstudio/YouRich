from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from typing import Final

from _earnings_types import (
    EarningsDocument,
    EarningsMetric,
    EarningsRelease,
    GuidanceItem,
    ManagementStatement,
)
from _filing_parser import clean_filing_html

MONEY = r"\$?\s*([+-]?\d+(?:\.\d+)?)\s*(billion|million|%)?"
METRIC_PATTERNS: Final[dict[str, tuple[str, str]]] = {
    "revenue": (rf"revenue (?:was|of|reached)\s+{MONEY}", "USD"),
    "revenue_growth": (r"revenue .*?up\s+([+-]?\d+(?:\.\d+)?)%", "percent"),
    "gross_margin": (r"gross margin (?:was|of)\s+([+-]?\d+(?:\.\d+)?)%", "percent"),
    "operating_margin": (r"operating margin (?:was|of)\s+([+-]?\d+(?:\.\d+)?)%", "percent"),
    "net_income": (rf"net income (?:was|of)\s+{MONEY}", "USD"),
    "eps": (r"(?:diluted )?eps (?:was|of)\s+\$?\s*([+-]?\d+(?:\.\d+)?)", "USD/share"),
    "operating_cash_flow": (rf"operating cash flow (?:was|of)\s+{MONEY}", "USD"),
    "free_cash_flow": (rf"free cash flow (?:was|of)\s+{MONEY}", "USD"),
}
GUIDANCE_REGEX: Final = "".join(
    (
        r"(?P<period>next quarter|full year|current quarter).*?",
        r"(?P<metric>revenue|gross margin|operating expense|tax rate|capex|segment).*?",
        rf"guidance (?:is|of)\s+{MONEY}\s+(?:to|-|\u2013)\s+{MONEY}",
    )
)
GUIDANCE_PATTERN: Final = re.compile(GUIDANCE_REGEX, re.IGNORECASE)
SEGMENT_PATTERN: Final = re.compile(
    rf"(?P<segment>[A-Za-z ]+?) segment revenue (?:was|of)\s+{MONEY}",
    re.IGNORECASE,
)
ROLE_PATTERN: Final = r"(?P<role>CEO|CFO|Chief Executive Officer|Chief Financial Officer)"
SPEAKER_PATTERN: Final = r"(?P<speaker>[A-Z][A-Za-z .'-]+?)"
STATEMENT_REGEX: Final = rf"{ROLE_PATTERN}\s+{SPEAKER_PATTERN}\s+said\s+(?P<statement>[^.]+)"
STATEMENT_PATTERN: Final = re.compile(STATEMENT_REGEX, re.IGNORECASE)
COMMENTARY_CATEGORIES: Final[dict[str, tuple[str, ...]]] = {
    "demand": ("demand", "customer demand"),
    "pricing": ("pricing", "price"),
    "margin": ("margin",),
    "AI": ("ai", "artificial intelligence"),
    "capacity": ("capacity",),
    "supply": ("supply",),
    "inventory": ("inventory",),
    "competition": ("competition",),
    "regulation": ("regulation",),
    "capital spending": ("capital spending", "capex"),
    "product cycle": ("product cycle", "product"),
    "geography": ("geography", "international"),
}


def extract_earnings_release(document: EarningsDocument, raw_text: str) -> EarningsRelease:
    text = " ".join(clean_filing_html(raw_text).split())
    metrics = extract_metrics(document, text)
    guidance = extract_guidance(document, text)
    commentary = extract_management_commentary(document, text)
    evidence = [
        evidence_record(document, item.evidence, item.metric)
        for item in [*metrics.values(), *guidance]
    ]
    warnings = []
    if not guidance:
        warnings.append("GUIDANCE_NOT_PROVIDED")
    if not metrics:
        warnings.append("EARNINGS_DOCUMENT_PARSE_INCOMPLETE")
    return EarningsRelease(document, metrics, guidance, commentary, evidence, warnings)


def extract_metrics(document: EarningsDocument, text: str) -> dict[str, EarningsMetric]:
    metrics = {}
    for metric, spec in METRIC_PATTERNS.items():
        pattern, unit = spec
        match = re.search(pattern, text, re.IGNORECASE)
        if match is None:
            continue
        value = match.group(1)
        evidence = sentence_containing(text, match.start())
        metrics[metric] = EarningsMetric(
            metric=metric,
            value=value,
            unit=unit,
            source=document.source_url,
            source_type="reported_earnings_metric",
            evidence=evidence,
        )
    for match in SEGMENT_PATTERN.finditer(text):
        segment = "_".join(match.group("segment").strip().lower().split())
        key = f"segment_revenue:{segment}"
        metrics[key] = EarningsMetric(
            metric=key,
            value=match.group(2),
            unit="USD",
            source=document.source_url,
            source_type="reported_earnings_metric",
            evidence=sentence_containing(text, match.start()),
        )
    return metrics


def extract_guidance(document: EarningsDocument, text: str) -> list[GuidanceItem]:
    items = []
    for match in GUIDANCE_PATTERN.finditer(text):
        metric = match.group("metric").lower().replace(" ", "_")
        low = match.group(3)
        high = match.group(5)
        items.append(
            GuidanceItem(
                metric=metric,
                period=match.group("period").lower().replace(" ", "_"),
                low=low,
                high=high,
                midpoint=midpoint(low, high),
                unit="percent" if metric in {"gross_margin", "tax_rate"} else "USD",
                source=document.source_url,
                status="reported",
                evidence=sentence_containing(text, match.start()),
            )
        )
    return items


def extract_management_commentary(
    document: EarningsDocument, text: str
) -> list[ManagementStatement]:
    statements = []
    for match in STATEMENT_PATTERN.finditer(text):
        statement = match.group("statement").strip()
        statements.append(
            ManagementStatement(
                statement=statement,
                speaker=match.group("speaker").strip(),
                role=match.group("role").upper(),
                category=statement_category(statement),
                source=document.source_url,
                evidence=evidence_record(document, statement, "management_commentary"),
            )
        )
    return statements


def statement_category(statement: str) -> str:
    lowered = statement.lower()
    for category, terms in COMMENTARY_CATEGORIES.items():
        if any(term in lowered for term in terms):
            return category
    return "management"


def midpoint(low: str | None, high: str | None) -> str | None:
    if low is None or high is None:
        return None
    return str((Decimal(low) + Decimal(high)) / Decimal("2"))


def sentence_containing(text: str, index: int) -> str:
    start = text.rfind(". ", 0, index)
    end = text.find(". ", index)
    return text[(0 if start < 0 else start + 2) : (len(text) if end < 0 else end + 1)].strip()


def evidence_record(document: EarningsDocument, excerpt: str, claim_type: str) -> dict[str, str]:
    digest = hashlib.sha256(f"{document.source_url}:{claim_type}:{excerpt}".encode()).hexdigest()[
        :12
    ]
    return {
        "id": f"earn_{digest}",
        "source": document.source_url,
        "document": document.title,
        "published_at": document.published_at,
        "evidence": excerpt,
        "support_status": "SUPPORTED" if excerpt else "INSUFFICIENT_EVIDENCE",
    }
