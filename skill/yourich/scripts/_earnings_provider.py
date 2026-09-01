from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urljoin

from _core import FILING_DOCUMENT_TTL_SECONDS, clean_ticker, fetch_text
from _earnings_types import EarningsDocument
from _filing_parser import clean_filing_html
from _filing_provider import SecFilingProvider

if TYPE_CHECKING:
    from _filing_types import Filing

EARNINGS_TERMS = (
    "earnings",
    "quarterly results",
    "quarter results",
    "financial results",
    "shareholder letter",
    "guidance",
)
HREF_PATTERN: re.Pattern[str] = re.compile(r'href="(?P<href>[^"]+)"', re.IGNORECASE)
SEC_8K_FORMS = ["8-K"]
SEC_EARNINGS_LOOKBACK = 12
MIN_TITLE_LENGTH = 12
MAX_TITLE_LENGTH = 120


class EarningsProvider(Protocol):
    def get_documents(self, _ticker: str, _history: int) -> list[EarningsDocument]: ...

    def get_document_text(self, _document: EarningsDocument) -> str: ...


@dataclass(frozen=True, slots=True)
class SecEarningsProvider:
    filing_provider: SecFilingProvider = field(default_factory=SecFilingProvider)

    def get_documents(self, ticker: str, history: int) -> list[EarningsDocument]:
        symbol = clean_ticker(ticker)
        filings = self.filing_provider.get_filings(symbol, SEC_8K_FORMS, SEC_EARNINGS_LOOKBACK)
        company = filings[0].company_name if filings else symbol
        return [
            document
            for filing in filings
            if (document := self.earnings_document_from_filing(symbol, company, filing)) is not None
        ][:history]

    def get_document_text(self, document: EarningsDocument) -> str:
        return fetch_text(
            document.source_url,
            FILING_DOCUMENT_TTL_SECONDS,
            f"earnings/document_{document.ticker}_{document_digest(document.source_url)}",
        )

    def earnings_document_from_filing(
        self, ticker: str, company: str, filing: Filing
    ) -> EarningsDocument | None:
        primary_html = self.filing_provider.get_document(filing).html
        source_url = earnings_source_url(filing, primary_html)
        document_text = fetch_text(
            source_url,
            FILING_DOCUMENT_TTL_SECONDS,
            f"earnings/document_{ticker}_{document_digest(source_url)}",
        )
        if not is_earnings_document(filing, document_text):
            return None
        return EarningsDocument(
            ticker=ticker,
            company=company,
            document_type=document_type(source_url, document_text),
            published_at=filing.filing_date,
            period_end=filing.period_end,
            source_url=source_url,
            source_type="SEC_8K_EXHIBIT" if source_url != filing.filing_url else "SEC_8K",
            title=document_title(company, document_text),
            retrieved_at=retrieved_at(),
        )


def detected_earnings_documents(
    ticker: str,
    company: str,
    filings: list[Filing],
    document_texts: dict[str, str],
) -> list[EarningsDocument]:
    retrieved = retrieved_at()
    documents = []
    for filing in filings:
        if filing.form != "8-K":
            continue
        text = document_texts.get(filing.accession_number, "")
        if not is_earnings_document(filing, text):
            continue
        documents.append(
            EarningsDocument(
                ticker=ticker,
                company=company,
                document_type=document_type(filing.primary_document, text),
                published_at=filing.filing_date,
                period_end=filing.period_end,
                source_url=filing.filing_url,
                source_type="SEC_8K",
                title=document_title(company, text),
                retrieved_at=retrieved,
            )
        )
    return documents


def earnings_source_url(filing: Filing, html: str) -> str:
    for match in HREF_PATTERN.finditer(html):
        href = match.group("href")
        if is_earnings_exhibit_href(href):
            return urljoin(filing.filing_url, href)
    return filing.filing_url


def is_earnings_exhibit_href(href: str) -> bool:
    lowered = href.lower()
    return any(
        term in lowered for term in ("ex99", "ex-99", "ex_99", "earnings", "release", "pr.htm")
    )


def is_earnings_document(filing: Filing, text: str) -> bool:
    source = f"{filing.primary_document} {text}".lower()
    return any(term in source for term in EARNINGS_TERMS)


def document_type(primary_document: str, text: str) -> str:
    source = f"{primary_document} {text}".lower()
    if "presentation" in source:
        return "earnings_presentation"
    if "shareholder letter" in source:
        return "shareholder_letter"
    return "earnings_release"


def document_title(company: str, text: str) -> str:
    first_sentence = " ".join(clean_filing_html(text).split()).split(".")[0].strip()
    if MIN_TITLE_LENGTH <= len(first_sentence) <= MAX_TITLE_LENGTH:
        return first_sentence
    return f"{company} earnings release"


def document_digest(source_url: str) -> str:
    return hashlib.sha256(source_url.encode()).hexdigest()[:16]


def retrieved_at() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
