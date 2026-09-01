from __future__ import annotations

import html
import re
from typing import Final

from _filing_types import FilingSection

HTML_TAG: Final = re.compile(r"<[^>]+>")
NOISE_BLOCK: Final = re.compile(
    r"<(?:script|style|ix:hidden|xbrli:[^>\s]+)[^>]*>[\s\S]*?</(?:script|style|ix:hidden|xbrli:[^>]+)>",
    re.IGNORECASE,
)
SPACE: Final = re.compile(r"[ \t\r\f\v]+")
BLANKS: Final = re.compile(r"\n{3,}")
MIN_PARSED_SECTIONS: Final = 2

FORM_10K_SECTION_PATTERNS: Final = {
    "business": (r"item\s+1[.\s]+business", "Item 1. Business"),
    "risk_factors": (r"item\s+1a[.\s]+risk\s+factors", "Item 1A. Risk Factors"),
    "properties": (r"item\s+2[.\s]+properties", "Item 2. Properties"),
    "legal_proceedings": (r"item\s+3[.\s]+legal\s+proceedings", "Item 3. Legal Proceedings"),
    "mda": (
        r"item\s+7[.\s]+management['`\u2019s\s]+discussion\s+and\s+analysis",
        "Item 7. MD&A",
    ),
    "financial_statements": (
        r"item\s+8[.\s]+financial\s+statements",
        "Item 8. Financial Statements",
    ),
    "controls": (r"item\s+9a[.\s]+controls\s+and\s+procedures", "Item 9A. Controls"),
}
FORM_10Q_SECTION_PATTERNS: Final = {
    "financial_statements": (
        r"item\s+1[.\s]+financial\s+statements",
        "Item 1. Financial Statements",
    ),
    "mda": (
        r"item\s+2[.\s]+management['`\u2019s\s]+discussion\s+and\s+analysis",
        "Item 2. MD&A",
    ),
    "risk_factors": (r"item\s+1a[.\s]+risk\s+factors", "Item 1A. Risk Factors"),
    "controls": (r"item\s+4[.\s]+controls\s+and\s+procedures", "Item 4. Controls"),
}


def clean_filing_html(raw_html: str) -> str:
    stripped = NOISE_BLOCK.sub(" ", raw_html)
    text = HTML_TAG.sub("\n", stripped)
    text = html.unescape(text)
    text = SPACE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return BLANKS.sub("\n\n", text).strip()


def extract_sections(text: str, form: str) -> tuple[list[FilingSection], list[str]]:
    markers = sorted(section_markers(text, form), key=lambda item: item[0])
    if not markers:
        return [FilingSection("full_filing", "Full Filing", text)], ["SECTION_PARSE_INCOMPLETE"]
    sections = []
    for index, (start, name, item) in enumerate(markers):
        end = markers[index + 1][0] if index + 1 < len(markers) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append(FilingSection(name=name, item=item, text=body))
    warnings = [] if len(sections) >= MIN_PARSED_SECTIONS else ["SECTION_PARSE_INCOMPLETE"]
    return sections, warnings


def section_markers(text: str, form: str) -> list[tuple[int, str, str]]:
    patterns = (
        FORM_10Q_SECTION_PATTERNS if form in {"10-Q", "10-Q/A"} else FORM_10K_SECTION_PATTERNS
    )
    markers = []
    for name, (pattern, item) in patterns.items():
        matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
        if matches:
            markers.append((matches[-1].start(), name, item))
    return markers
