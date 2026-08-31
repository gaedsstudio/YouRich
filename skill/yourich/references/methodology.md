# Methodology

YouRich separates deterministic calculation from agent reasoning.

Use scripts for SEC financial normalization, delayed market quotes, financial
ratios, valuation metrics, margin calculations, multi-year growth, financial
health checks, and quantitative risk checks. Use Claude Code or Codex for
user-intent detection, qualitative business analysis, industry structure,
competitive advantage, management interpretation, bull and bear cases, and final
thesis writing.

Analysis priority is:

1. Deterministic YouRich data.
2. Metric evidence and field provenance.
3. Public qualitative research for claims scripts cannot answer.
4. Claude Code or Codex interpretation.

## Evidence States

- `SUPPORTED`: the claim is backed by returned data or cited public evidence.
- `PARTIALLY_SUPPORTED`: only part of the claim is supported.
- `CONTRADICTED`: returned data or cited evidence conflicts with the claim.
- `INSUFFICIENT_EVIDENCE`: the claim cannot be supported from available data.

Do not invent numbers. When script output has `null` values or `missing_fields`,
state the limitation.

## Research Steps

1. Identify the company and ticker.
2. Fetch financial data and market quote data.
3. Check `missing_fields`, `field_sources`, `fact_metadata`, `data_quality`,
   `data_freshness`, and provider warnings.
4. Run valuation, quality, and risk scripts.
5. Gather qualitative public evidence only for claims the scripts cannot answer.
6. Build bull and bear cases from evidence.
7. Produce a valuation-oriented conclusion, not an automated trade signal.

Treat evidence as one of three kinds:

- `reported_fact`: a value directly selected from SEC Company Facts.
- `derived_metric`: a deterministic YouRich calculation from reported facts or market quotes.
- `qualitative_interpretation`: Claude Code or Codex reasoning from public evidence.
