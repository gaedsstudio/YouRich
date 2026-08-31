# Financial Quality

Use `scripts/financial_health.py` for quantitative quality checks.

Implemented checks include revenue growth, earnings growth, free cash flow,
gross margin, operating margin, net margin, ROE, ROA, ROIC, current ratio, quick
ratio, debt/equity, debt/assets, earnings consistency, and FCF consistency.

Financial quality claims should distinguish:

- Profitability: margins, ROE, ROA, ROIC.
- Balance-sheet strength: liquidity, leverage, asset coverage.
- Durability: multi-year growth and consistency.

Missing data is not negative data. Treat unavailable metrics as limitations.
