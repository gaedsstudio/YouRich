from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Filing:
    ticker: str
    company_name: str
    form: str
    filing_date: str
    period_end: str | None
    accession_number: str
    primary_document: str
    filing_url: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "form": self.form,
            "filing_date": self.filing_date,
            "period_end": self.period_end,
            "accession_number": self.accession_number,
            "primary_document": self.primary_document,
            "filing_url": self.filing_url,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class FilingDocument:
    filing: Filing
    html: str


@dataclass(frozen=True, slots=True)
class FilingSection:
    name: str
    item: str
    text: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "item": self.item, "text": self.text}
