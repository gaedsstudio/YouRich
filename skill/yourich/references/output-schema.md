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

Full research responses should use:

```text
Company
Ticker

Investment Summary

Business
Financial Quality
Valuation
Risks

Bull Case
Bear Case

Key Evidence

Conclusion
```
