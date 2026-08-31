# Filing Research

Use SEC EDGAR filings as primary-source evidence for public-company research.
The SEC submissions endpoint provides filing metadata; SEC archive URLs provide
the primary filing document.

## Provider Contract

`FilingProvider.get_filings(ticker, forms, limit)` returns recent filings for
the requested forms. `FilingProvider.get_document(filing)` returns the primary
document HTML for that filing.

Each filing record includes ticker, company name, form, filing date, period end,
accession number, primary document, filing URL, and source.

## SEC Behavior

The SEC provider uses:

- `https://www.sec.gov/files/company_tickers.json`
- `https://data.sec.gov/submissions/CIK##########.json`
- `https://www.sec.gov/Archives/edgar/data/...`

Set `YOURICH_SEC_USER_AGENT` to configure the SEC User-Agent. Do not hardcode a
personal contact string into the repository.

## Cache

Use `YOURICH_CACHE_DIR` for all SEC cache files. Filing metadata is refreshed
after 24 hours. Primary filing documents are cached for seven days and should be
treated as effectively immutable by accession number.

## Sections

For 10-K filings, parse Business, Risk Factors, Properties, Legal Proceedings,
MD&A, Financial Statements, and Controls. For 10-Q filings, parse Financial
Statements, MD&A, Risk Factors, and Controls. If parsing fails or yields too few
sections, return `SECTION_PARSE_INCOMPLETE` and continue with available text.
