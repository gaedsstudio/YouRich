---
name: yourich
description: >
  Analyze public companies and stocks using structured fundamental research,
  deterministic valuation scripts, financial quality checks, risk analysis,
  and evidence verification. Use when the user asks to analyze, value,
  compare, investigate, or research a stock or public company as an investment.
license: MIT
---

# YouRich

YouRich is an investment research framework for Claude Code and Codex. It does
not provide an AI model and it is not a standalone stock-analysis product. Use
the host agent for reasoning, qualitative business analysis, industry context,
and final writing. Use the bundled scripts for important quantitative work.

The bundled scripts require Python 3.11 or newer.

## Trigger Boundary

Use YouRich for requests about public companies, stocks, equity valuation,
financial quality, financial risk, investment theses, bull and bear cases, or
company comparisons.

Do not use YouRich for ordinary programming, CSS, debugging, unrelated finance
questions, personal budgeting, crypto trading, portfolio tracking, brokerage
actions, or automated trading.

## Workflow

For a full analysis, follow this order. Priority is deterministic YouRich data,
metric evidence, public qualitative research, then Claude Code or Codex
interpretation.

1. Identify the company or ticker.
2. Gather financial data with `scripts/fetch_financials.py`.
3. Normalize data and list missing fields.
4. Analyze business fundamentals using public sources when needed.
5. Run deterministic valuation with `scripts/valuation.py`.
6. Run financial quality checks with `scripts/financial_health.py`.
7. Run quantitative risk checks with `scripts/risk.py`.
8. Verify important claims using the evidence rules in `references/methodology.md`.
9. Construct a bull case.
10. Construct a bear case.
11. Produce an investment thesis.
12. Produce the final structured conclusion.

For narrower requests, execute the relevant subset:

- `financials`: fetch and normalize company financials.
- `valuation`: run valuation metrics and valuation-oriented conclusion.
- `risk`: run financial quality and risk checks.
- `compare`: run the same methodology for each ticker using `scripts/compare.py`.
- `thesis`: run full analysis, then combine quantitative evidence with public qualitative research.

## Deterministic Tools

Use Python 3.11+ and run scripts from this skill directory:

```bash
python scripts/fetch_financials.py AAPL
python scripts/valuation.py --ticker AAPL
python scripts/financial_health.py --ticker AAPL
python scripts/risk.py --ticker AAPL
python scripts/compare.py AAPL MSFT
```

All scripts emit JSON. Use YouRich-derived financial metrics instead of
recalculating market cap, NCAV, Price/NCAV, Graham Number, ratios, margins,
trend calculations, or scoring in model reasoning. If a script returns `null` or
lists a missing field, state that the data is unavailable instead of filling it.

`fetch_financials.py` uses SEC Company Facts for fundamentals and delayed market
quotes from configured free providers. Yahoo chart and Stooq CSV are unofficial
free endpoints; Alpha Vantage can be enabled with `YOURICH_MARKET_PROVIDER` and
`YOURICH_MARKET_API_KEY`. Provider failures must be reported from JSON warnings,
not hidden by guessed prices.

For valuation claims, check `data_quality`, `fact_metadata`, `field_sources`,
and provider warnings first. Mention incomplete TTM coverage, stale financial
data, restatements, currency mismatch, and low-confidence mappings. Do not
present low-confidence SEC mappings as certain facts. Distinguish reported SEC
facts from derived metrics and qualitative interpretation.

Use `python scripts/fetch_financials.py AAPL --debug` when developing or
auditing why a field was selected. Debug output may include selected and
rejected SEC concepts with rejection reasons.

## References

Read only what the request needs:

- `references/methodology.md` for the full research workflow and evidence rules.
- `references/valuation.md` for valuation formulas and limits.
- `references/financial-quality.md` for quality and balance-sheet checks.
- `references/risk-framework.md` for quantitative versus qualitative risk handling.
- `references/output-schema.md` for the JSON contract and final-answer structure.

## Final Research Shape

Use this default structure for a full investment note:

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

Conclusions must not be direct buy/sell instructions. Prefer valuation-oriented
language such as `ATTRACTIVE VALUATION`, `FAIRLY VALUED`, `EXPENSIVE`,
`HIGH FINANCIAL RISK`, `INSUFFICIENT DATA`, `HIGH QUALITY / EXPENSIVE`, or
`LOW QUALITY / CHEAP`.
