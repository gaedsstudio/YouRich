from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from _core import (
    FILING_DOCUMENT_TTL_SECONDS,
    FILING_METADATA_TTL_SECONDS,
    ToolError,
    clean_ticker,
    fetch_json,
    fetch_text,
)
from _filing_types import Filing, FilingDocument
from _sec import lookup_cik


class FilingProvider(Protocol):
    def get_filings(self, _ticker: str, _forms: list[str], _limit: int) -> list[Filing]: ...

    def get_document(self, _filing: Filing) -> FilingDocument: ...


@dataclass(frozen=True, slots=True)
class SecFilingProvider:
    def get_filings(self, ticker: str, forms: list[str], limit: int) -> list[Filing]:
        symbol = clean_ticker(ticker)
        ticker_map = fetch_json(
            "https://www.sec.gov/files/company_tickers.json",
            FILING_METADATA_TTL_SECONDS,
            "filings/company_tickers",
        )
        cik, company_name = lookup_cik(symbol, ticker_map)
        source = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
        payload = fetch_json(source, FILING_METADATA_TTL_SECONDS, f"filings/submissions_{cik}")
        recent = payload.get("filings", {}).get("recent", {})
        if not isinstance(recent, dict):
            raise ToolError(f"SEC submissions payload missing recent filings for {symbol}")
        return filing_rows(FilingQuery(symbol, company_name, cik, recent, forms, limit, source))

    def get_document(self, filing: Filing) -> FilingDocument:
        accession = filing.accession_number.replace("-", "")
        cache_key = f"filings/document_{filing.ticker}_{accession}_{filing.primary_document}"
        html = fetch_text(filing.filing_url, FILING_DOCUMENT_TTL_SECONDS, cache_key)
        return FilingDocument(filing=filing, html=html)


@dataclass(frozen=True, slots=True)
class FilingQuery:
    ticker: str
    company_name: str
    cik: int
    recent: dict[str, Any]
    forms: list[str]
    limit: int
    source: str


@dataclass(frozen=True, slots=True)
class FilingLists:
    accessions: list[str]
    forms: list[str]
    filed_dates: list[str]
    report_dates: list[str]
    primary_documents: list[str]


def filing_rows(query: FilingQuery) -> list[Filing]:
    rows: list[Filing] = []
    lists = filing_lists(query.recent)
    for wanted_form in query.forms:
        row = first_matching_row(query, lists, wanted_form, rows)
        if row is not None:
            rows.append(row)
        if len(rows) >= query.limit:
            return rows
    for index in range(len(lists.accessions)):
        row = row_at(query, lists, index)
        if row is None or any(item.accession_number == row.accession_number for item in rows):
            continue
        rows.append(row)
        if len(rows) >= query.limit:
            return rows
    return rows


def filing_lists(recent: dict[str, Any]) -> FilingLists:
    return FilingLists(
        accessions=list_value(recent, "accessionNumber"),
        forms=list_value(recent, "form"),
        filed_dates=list_value(recent, "filingDate"),
        report_dates=list_value(recent, "reportDate"),
        primary_documents=list_value(recent, "primaryDocument"),
    )


def first_matching_row(
    query: FilingQuery,
    lists: FilingLists,
    wanted_form: str,
    existing: list[Filing],
) -> Filing | None:
    for index in range(len(lists.accessions)):
        row = row_at(query, lists, index)
        if row is None or row.form != wanted_form:
            continue
        if any(item.accession_number == row.accession_number for item in existing):
            continue
        return row
    return None


def row_at(query: FilingQuery, lists: FilingLists, index: int) -> Filing | None:
    form = item_at(lists.forms, index)
    primary_document = item_at(lists.primary_documents, index)
    if form not in set(query.forms) or not primary_document:
        return None
    accession = item_at(lists.accessions, index)
    accession_path = accession.replace("-", "")
    url = (
        f"https://www.sec.gov/Archives/edgar/data/{query.cik}/{accession_path}/"
        f"{primary_document}"
    )
    return Filing(
        ticker=query.ticker,
        company_name=query.company_name,
        form=form,
        filing_date=item_at(lists.filed_dates, index),
        period_end=item_at(lists.report_dates, index) or None,
        accession_number=accession,
        primary_document=primary_document,
        filing_url=url,
        source=query.source,
    )


def list_value(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def item_at(values: list[str], index: int) -> str:
    return values[index] if index < len(values) else ""
