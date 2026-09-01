English | [한국어](README_KO.md) | [日本語](README_JA.md) | [中文](README_ZH.md)

# YouRich — Investment Research Framework for Claude Code and Codex

> Structured research. Deterministic finance. Traceable evidence.

**YouRich** is an open-source investment research skill for Claude Code and Codex. It gives coding agents a repeatable workflow for public-company research, deterministic financial calculations, valuation, financial-quality analysis, risk checks, and evidence verification.

YouRich does not provide its own AI model and it is not a standalone stock app. Claude Code or Codex handles reasoning and qualitative research; YouRich supplies the financial discipline underneath.

**Current milestone: v0.6.0 — Valuation Intelligence**

v0.6.0 adds reverse DCF, scenario valuation, sensitivity analysis, and
scenario-based margin-of-safety context while preserving official earnings and
guidance evidence.

[Why YouRich?](#why-not-just-ask-ai-directly) · [Architecture](#architecture) · [Capabilities](#capabilities) · [Quick Start](#quick-start) · [Research Layer](#v040-research-layer) · [Methodology](#methodology)

---

## Why Not Just Ask AI Directly?

You can ask an AI model whether a stock looks attractive. The problem is not whether it can produce an answer — it is whether the answer is financially consistent, reproducible, and traceable.

### 1. Important Financial Math Is Deterministic

YouRich runs important financial calculations in Python and uses `Decimal` where precision matters.

```text
Market data + SEC fundamentals
            ↓
    deterministic scripts
            ↓
 valuation / quality / risk
            ↓
      Claude or Codex
            ↓
   final research note
```

The agent should use YouRich-derived values instead of mentally recalculating market cap, NCAV, Graham Number, margins, ratios, trends, or risk flags.

### 2. Missing Data Stays Missing

If YouRich cannot verify a value, it returns `null`, a warning, or an insufficient-data state.

It does not turn missing data into zero, guess a market price, or silently fill gaps.

```json
{
  "price": null,
  "warnings": ["MARKET_PROVIDER_FAILED"]
}
```

### 3. Every Important Metric Has Provenance

YouRich records where values came from and how derived metrics were calculated.

Typical metadata includes:

- SEC concept
- unit
- fiscal year / fiscal period
- filing form
- filing date
- accession number
- period start / end
- market provider
- mapping confidence
- restatement status
- metric inputs

This lets the host agent distinguish **reported facts**, **derived metrics**, and **qualitative interpretation**.

### 4. Research Is Reproducible

The same workflow is reused for company analysis, valuation, financial quality, risk, comparison, and thesis construction.

### 5. It Lives Inside Claude Code and Codex

Install it once, then ask your agent normally:

```text
Analyze NVIDIA using YouRich.
Compare AMD and Intel as investments.
Is Microsoft expensive?
Check Tesla's financial risks.
```

---

## Architecture

```text
User
  ↓
Claude Code / Codex
  ↓
YouRich Skill
  ↓
Structured Research Workflow
  ├─ Financial Data
  ├─ Valuation
  ├─ Financial Quality
  ├─ Risk Checks
  ├─ Filing Research
  └─ Evidence Verification
  ↓
Deterministic Python Tools
  ↓
Agent Reasoning + Public Qualitative Research
  ↓
Final Investment Research
```

The same canonical skill is used across both environments.

```text
skill/yourich/
├── SKILL.md
├── scripts/
├── references/
└── assets/
```

`SKILL.md` is the source of truth.

---

## Capabilities

### Research Modes

| Mode | Purpose |
|---|---|
| Full analysis | Business, financials, valuation, risks, bull case, bear case, conclusion |
| Valuation | Price-sensitive valuation metrics |
| Financials | Fetch and normalize company financial data |
| Filings | Fetch SEC 10-K / 10-Q metadata and parse sections |
| Business | Filing-backed business-model and quality review |
| Management | Official-evidence management and capital-allocation review |
| Risk | Financial quality, quantitative risk checks, and filing risk review |
| Compare | Apply the same methodology to multiple tickers |
| Thesis | Combine quantitative evidence with qualitative research |

### Valuation Metrics

When the required data exists:

- Market Cap
- TTM P/E
- latest P/B
- TTM P/S
- TTM FCF Yield
- TTM Earnings Yield
- NCAV
- NCAV per share
- Price / NCAV
- Graham Number
- Margin of Safety
- Normalized EPS

### Financial Quality

- revenue growth
- earnings growth
- gross / operating / net margins
- FCF margin
- ROE
- ROA
- ROIC
- current ratio
- quick ratio
- debt / equity
- debt / assets
- earnings consistency
- FCF consistency
- share dilution

### Risk Checks

- weak liquidity
- excessive debt
- negative equity
- earnings deterioration
- FCF deterioration
- margin deterioration
- dilution
- valuation risk

Qualitative risks are handled by the host agent using filing or public evidence
and kept separate from deterministic results.

---

## v0.4.0 Research Layer

v0.4 turns SEC filings into compact, source-linked research context for the
host agent. YouRich is still not a standalone stock app or chatbot; it provides
deterministic tools and evidence discipline inside Claude Code and Codex.

New scripts:

```bash
cd skill/yourich
python scripts/fetch_filings.py AAPL --form 10-K --form 10-Q --limit 2
python scripts/research_context.py AAPL --mode thesis
python scripts/filing_parser.py --input filing.html --form 10-K
python scripts/evidence.py
```

The SEC provider uses EDGAR submissions metadata and primary archive documents.
Set `YOURICH_SEC_USER_AGENT` to configure the SEC User-Agent. Filing metadata is
cached for 24 hours and primary documents are cached for seven days under
`YOURICH_CACHE_DIR`.

Research context includes filings, parsed section inventory, selected evidence
excerpts, claim statuses, business analysis, business quality, moat analysis,
management and capital allocation, filing risk, risk-factor text change
detection, MD&A cross-checks, evidence coverage, confidence, warnings, and a
non-advisory conclusion.

---

## v0.3.0 Financial Data Correctness

v0.3 focuses on correctness of financial inputs rather than adding more surface features.

### SEC Fact Selection

SEC Company Facts are normalized using:

```text
concept
unit
FY / FP
form
filed date
start / end
frame
accession number
amendment status
```

Duplicate facts are resolved with filing recency and reporting context in mind. Restatements are detected on a best-effort basis.

### Annual, Quarterly, TTM, and Snapshot Data

Income-statement and cash-flow values are period-aware.

```text
Revenue
Operating Income
Net Income
EPS
Operating Cash Flow
CapEx
Free Cash Flow
        ↓
       TTM
```

Balance-sheet values use the latest appropriate snapshot.

```text
Cash
Current Assets
Current Liabilities
Total Assets
Total Liabilities
Debt
Equity
Shares Outstanding
        ↓
 latest balance-sheet snapshot
```

### Valuation Basis

```text
P/E       = Market Price / TTM Diluted EPS
P/S       = Market Cap / TTM Revenue
FCF Yield = TTM FCF / Market Cap
P/B       = Market Cap / Latest Equity
```

If periods, currencies, or share data are not comparable, YouRich returns missing data or a warning instead of forcing a result.

### Data Quality

```json
{
  "data_quality": {
    "market_data": "delayed",
    "fundamentals": "current",
    "ttm_coverage": "complete",
    "mapping_confidence": "high",
    "currency_match": true
  }
}
```

---

## Data Sources

### Fundamentals

YouRich uses **SEC Company Facts** for public-company fundamentals.

### Market Price

Default fallback chain:

1. Yahoo chart endpoint — unofficial / delayed
2. Stooq CSV endpoint — unofficial / delayed
3. Alpha Vantage Global Quote — optional API-key provider

```text
YOURICH_MARKET_PROVIDER=alpha_vantage
YOURICH_MARKET_API_KEY=...
```

Provider failures are returned as warnings. Prices are never fabricated.

### Cache

- market quotes: 15 minutes
- SEC fundamentals: 24 hours

```text
YOURICH_CACHE_DIR=...
```

---

## Quick Start

### Requirements

- Python 3.11+
- Claude Code or OpenAI Codex
- Git

### 1. Clone

```bash
git clone https://github.com/gaedsstudio/YouRich.git
cd YouRich
```

### 2. Install

macOS / Linux:

```bash
./install.sh
```

Windows PowerShell:

```powershell
./install.ps1
```

### 3. Claude Code

```text
Analyze NVIDIA using YouRich.
Compare AMD and Intel.
Value Microsoft.
Check the financial risks of Tesla.
```

### 4. Codex

```text
$yourich Analyze NVIDIA.
```

or:

```text
Use YouRich to compare AAPL and MSFT as investments.
```

---

## Internal Tools

```bash
cd skill/yourich

python scripts/fetch_financials.py AAPL
python scripts/fetch_financials.py AAPL --debug
python scripts/valuation.py --ticker AAPL
python scripts/financial_health.py --ticker AAPL
python scripts/risk.py --ticker AAPL
python scripts/compare.py AAPL MSFT
```

All scripts emit structured JSON.

---

## Methodology

```text
1. Identify company / ticker
2. Gather financial data
3. Gather SEC filing evidence when business, risk, management, or thesis work needs it
4. Normalize periods and fields
5. Check missing data and data quality
6. Research business fundamentals when needed
7. Run deterministic valuation
8. Run financial-quality checks
9. Run quantitative risk checks
10. Verify important claims with evidence
11. Build bull case
12. Build bear case
13. Produce investment thesis
```

Priority:

```text
YouRich deterministic data
        ↓
YouRich evidence / provenance
        ↓
public qualitative research
        ↓
Claude Code / Codex interpretation
```

### Default Research Output

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

Preferred conclusion language:

- `ATTRACTIVE VALUATION`
- `FAIRLY VALUED`
- `EXPENSIVE`
- `HIGH FINANCIAL RISK`
- `INSUFFICIENT DATA`
- `HIGH QUALITY / EXPENSIVE`
- `LOW QUALITY / CHEAP`

---

## Development

```bash
python -m pip install pytest ruff basedpyright

python -m ruff format .
python -m ruff check .
python -m basedpyright
python -m pytest -q
```

Current v0.4 baseline: **35 tests passing**.

---

## Design Principles

1. Do not fabricate financial data.
2. Use deterministic tools for important calculations.
3. Keep reported facts and derived metrics separate.
4. Track periods, units, currencies, and sources.
5. Expose uncertainty instead of hiding it.
6. Keep YouRich agent-native rather than turning it into a standalone stock app.

---

## Future Direction

- deeper 10-K / 10-Q research workflows
- richer qualitative evidence templates
- improved multiple-share-class handling
- broader financial-data mappings
- stronger comparison and audit workflows

---

## Disclaimer

YouRich is for educational and investment-research support purposes only.

It does not provide personalized financial advice, guarantee returns, execute trades, or issue definitive buy/sell instructions. Market data can be delayed or unavailable. Always verify important information and make your own investment decisions.

---

## License

MIT License

---

If YouRich is useful to you, consider starring the repository.

**Repository:** https://github.com/gaedsstudio/YouRich
