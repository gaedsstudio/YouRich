from __future__ import annotations

import re
from typing import Any

from _filing_provider import SecFilingProvider
from _sec import fetch_financials


def build_source_context(ticker: str, days: int = 90) -> dict[str, Any]:
    company = fetch_financials(ticker)
    provider = SecFilingProvider()
    filings = []
    for filing in provider.get_filings(ticker, ["8-K"], 12):
        document = provider.get_document(filing)
        filings.append(
            {
                "form": filing.form,
                "filing_date": filing.filing_date,
                "period_end": filing.period_end,
                "accession": filing.accession_number,
                "filing_url": filing.filing_url,
                "source_url": filing.filing_url,
                "item": filing_item(document.html),
                "text": filing_text(document.html),
            }
        )
    return {"ticker": ticker, "company": company, "filings": filings, "days": days}


def filing_item(html: str) -> str:
    match = re.search(r"Item\s+[0-9]\.[0-9][0-9]?", html, re.IGNORECASE)
    return match.group(0) if match is not None else ""


def filing_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text[:12000]
