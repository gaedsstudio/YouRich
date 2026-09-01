from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from _filing_types import FilingSection

WORD: Final = re.compile(r"[a-z0-9]+")
MIN_TOKEN_LENGTH: Final = 2
TOPIC_TERMS: Final[dict[str, tuple[str, ...]]] = {
    "business_model": ("revenue", "sales", "services", "products", "platform"),
    "revenue_drivers": ("demand", "volume", "price", "growth", "customers"),
    "customer_structure": ("customer", "client", "consumer", "enterprise"),
    "segments": ("segment", "division", "product line"),
    "geography": ("international", "geographic", "region", "country"),
    "recurring_vs_transactional": ("subscription", "recurring", "transaction"),
    "cost_structure": ("cost", "margin", "expense", "supply"),
    "capital_intensity": ("capital expenditure", "property", "equipment"),
    "industry_position": ("competition", "market", "industry"),
    "key_dependencies": ("supplier", "dependency", "regulation", "license"),
    "management": ("executive", "officer", "director", "compensation"),
    "capital_allocation": ("dividend", "repurchase", "acquisition", "capital allocation"),
}
STOP_WORDS: Final = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "from",
    "this",
    "were",
    "are",
    "our",
    "may",
    "will",
    "has",
    "have",
    "not",
    "can",
}


def section_excerpt(section: FilingSection, terms: tuple[str, ...]) -> str:
    lower = section.text.lower()
    for term in terms:
        index = lower.find(term)
        if index >= 0:
            start = max(0, index - 220)
            end = min(len(section.text), index + 680)
            return section.text[excerpt_start(section.text, start, index) : end].strip()
    return section.text[:900].strip()


def excerpt_start(text: str, start: int, index: int) -> int:
    sentence = text.rfind(". ", start, index)
    if sentence >= 0:
        return sentence + 2
    while start < index and not text[start].isspace():
        start += 1
    return start


def has_topic(section: FilingSection, topic: str) -> bool:
    terms = TOPIC_TERMS[topic]
    lower = section.text.lower()
    return any(term in lower for term in terms)


def normalized_tokens(text: str) -> set[str]:
    return {
        token
        for token in WORD.findall(text.lower())
        if len(token) > MIN_TOKEN_LENGTH and token not in STOP_WORDS
    }
