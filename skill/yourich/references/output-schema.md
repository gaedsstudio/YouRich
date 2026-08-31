# Output Schema

Bundled scripts emit JSON. Decimal values are serialized as strings.

`fetch_financials.py` returns:

- `company`
- `ticker`
- normalized financial fields
- `field_sources`
- `fact_metadata`
- `data_freshness`
- `data_quality`
- `market_quote`
- `annuals`
- `missing_fields`
- `provider`

`valuation.py` returns:

- `ticker`
- `metrics`
- `conclusion`
- `warnings`
- `market_quote`
- `data_freshness`
- `data_quality`

`financial_health.py` returns:

- `ticker`
- `metrics`

`risk.py` returns:

- `ticker`
- `risk_checks`

`fetch_filings.py` returns:

- `ticker`
- `filings` with ticker, company name, form, filing date, period end, accession
  number, primary document, filing URL, and source.
- `latest_document` when `--debug` is passed and a filing is available.

`research_context.py` returns:

- `version`
- `ticker`
- `mode`
- `filings`
- `sections`
- `evidence`
- `claims`
- `business_analysis`
- `business_quality`
- `moat_analysis`
- `management_analysis`
- `capital_allocation`
- `risk_analysis`
- `mda_cross_check`
- `evidence_coverage`
- `research_confidence`
- `conclusion`
- `warnings`

Full research responses should use:

```text
Company
Ticker

Investment Summary

Business
Business Quality
Management / Capital Allocation
Financial Quality
Valuation
Risks

Bull Case
Bear Case

Key Evidence
Open Evidence Gaps

Conclusion
```
