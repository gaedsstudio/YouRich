---
name: yourich
description: >
  Analyze public companies and stocks using structured fundamental research,
  deterministic valuation scripts, SEC filing research, financial quality checks,
  risk analysis, and evidence verification. Use when the user asks to analyze, value,
  compare, investigate, or research a stock or public company as an investment.
license: MIT
---

# YouRich

YouRich is an investment research framework for Claude Code and Codex. It does
not provide an AI model and it is not a standalone stock-analysis product. Use
the host agent for reasoning, qualitative business analysis, industry context,
and final writing. Use the bundled scripts for deterministic quantitative work
and primary-source filing evidence.

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
3. Gather SEC filing evidence with `scripts/fetch_filings.py` or
   `scripts/research_context.py`.
4. Normalize data and list missing fields.
5. Analyze business fundamentals only from returned evidence or cited sources.
6. Run deterministic valuation with `scripts/valuation.py`.
7. Run financial quality checks with `scripts/financial_health.py`.
8. Run quantitative risk checks with `scripts/risk.py`.
9. Verify important claims using the evidence rules in
   `references/evidence-framework.md`.
10. Render the authoritative human-readable report with
    `python scripts/report.py <ticker> --language <user-language>`.
11. Use the rendered report as the final presentation source.
12. Expose raw technical details only when explicitly requested.

For narrower requests, execute the relevant subset:

- `analyze`: run the full workflow.
- `valuation`: run valuation metrics and valuation-oriented conclusion.
- `financials`: fetch and normalize company financials.
- `risk`: run quantitative risk checks and SEC filing risk review.
- `compare`: run the same methodology for each ticker using
  `scripts/compare.py --format markdown --language <user-language>` and
  research context as needed.
- `thesis`: run full analysis, then combine quantitative evidence with filing evidence.
- `filings`: fetch and summarize 10-K or 10-Q filing metadata and sections.
- `business`: focus on business model, revenue drivers, segments, geography,
  cost structure, capital intensity, industry position, and dependencies.
- `management`: focus on management and capital allocation from official evidence.

## Deterministic Tools

Use Python 3.11+ and run scripts from this skill directory:

```bash
python scripts/fetch_financials.py AAPL
python scripts/valuation.py --ticker AAPL
python scripts/financial_health.py --ticker AAPL
python scripts/risk.py --ticker AAPL
python scripts/report.py AAPL --language en
python scripts/report.py AAPL --format json
python scripts/compare.py AAPL MSFT
python scripts/compare.py --format markdown --language en AAPL MSFT
python scripts/fetch_filings.py AAPL --form 10-K --form 10-Q --limit 2
python scripts/research_context.py AAPL --mode thesis
python scripts/filing_parser.py --input filing.html --form 10-K
python scripts/evidence.py
```

All scripts emit JSON. Use YouRich-derived financial metrics instead of
recalculating market cap, NCAV, Price/NCAV, Graham Number, ratios, margins,
trend calculations, or scoring in model reasoning. If a script returns `null` or
lists a missing field, state that the data is unavailable instead of filling it.
`scripts/report.py` is the exception: it emits Markdown by default for normal
consumer-readable reports, and JSON only when `--format json` is requested.

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
Never describe a metric as TTM unless the metric JSON basis is `ttm`. Do not
infer TTM status from the existence of a numeric value.

`fetch_filings.py` uses SEC EDGAR submissions and archive documents. Filing
metadata is cached for 24 hours; primary documents are cached for seven days.
Set `YOURICH_SEC_USER_AGENT` to configure the EDGAR User-Agent with your own
requester identifier. Do not invent a fake contact address. If a filing section
cannot be parsed, preserve the warning `SECTION_PARSE_INCOMPLETE` and avoid
pretending the missing section was reviewed.

`research_context.py` builds a context-budget-aware evidence bundle. It must not
dump full filings into the final prompt. Every qualitative claim follows
`Claim -> Evidence -> Interpretation`; filing evidence may be summarized, but
must not be fabricated.

For normal investment-analysis requests, do not respond with a long continuous
investment essay. Use YouRich's report structure, prefer concise tables and
sections, explain important financial terms in plain language, and keep
technical basis/provenance available without making it the primary reading
experience.

Treat the YouRich rendered report structure as authoritative. Do not discard its
section ordering and rewrite the analysis as a free-form essay. You may improve
wording inside sections, but preserve the report hierarchy. For Korean requests,
run report and comparison presentation commands with `--language ko` and keep
all visible report section headings in Korean.

Do not add direct action guidance such as how much, when, or in what pattern to
buy or sell. Prefer research language about valuation, risk, evidence quality,
and scenarios.

Use `python scripts/fetch_financials.py AAPL --debug` when developing or
auditing why a field was selected. Debug output may include selected and
rejected SEC concepts with rejection reasons.

## References

Read only what the request needs:

- `references/methodology.md` for the full research workflow and evidence rules.
- `references/filing-research.md` for SEC filing retrieval, parsing, and cache rules.
- `references/evidence-framework.md` for claim status and source-linking rules.
- `references/business-quality.md` for business and moat analysis.
- `references/management-analysis.md` for management and capital allocation review.
- `references/valuation.md` for valuation formulas and limits.
- `references/financial-quality.md` for quality and balance-sheet checks.
- `references/risk-framework.md` for quantitative versus qualitative risk handling.
- `references/output-schema.md` for the JSON contract and final-answer structure.

## Final Research Shape

Use this default structure for a full investment note:

```text
Company / Ticker

Overall Assessment
At a Glance
Investment Summary
Key Metrics
Business Quality
Financial Quality
Valuation
Key Risks
Bull Case
Bear Case
What Changed
Conclusion
Data Quality & Methodology
```

Conclusions must not be direct buy/sell instructions. Prefer valuation-oriented
language such as `ATTRACTIVE VALUATION`, `FAIRLY VALUED`, `EXPENSIVE`,
`HIGH FINANCIAL RISK`, `INSUFFICIENT DATA`, `HIGH QUALITY / EXPENSIVE`, or
`LOW QUALITY / CHEAP`.
