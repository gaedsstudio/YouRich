from __future__ import annotations

from dataclasses import dataclass
from typing import Final

DEFAULT_FORMS: Final = ("10-K", "10-Q")
RESEARCH_MODES: Final = (
    "analyze",
    "valuation",
    "financials",
    "risk",
    "compare",
    "thesis",
    "filings",
    "business",
    "management",
)


@dataclass(frozen=True, slots=True)
class ResearchRequest:
    ticker: str
    mode: str = "thesis"
    filing_limit: int = 2
    evidence_limit: int = 12

    @property
    def forms(self) -> list[str]:
        return list(DEFAULT_FORMS)
