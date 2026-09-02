English | [한국어](README_KO.md) | [日本語](README_JA.md) | [中文](README_ZH.md)

# YouRich

**Investment research for Claude Code and Codex.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-0.9.0-informational)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

SEC filings in. Structured financials, valuation, earnings, peer research,
events, and traceable evidence out.

YouRich is an open-source investment research skill that gives AI coding agents
a reproducible financial research workflow.

Claude Code or Codex handles reasoning and writing.

YouRich handles the financial discipline underneath.

<!--
<p align="center">
  <img src="assets/yourich-demo.gif" width="850" alt="YouRich terminal demo">
</p>
-->

## Examples

- [NVIDIA full investment research](examples/nvidia-full-analysis.md)
- [Apple valuation intelligence](examples/apple-valuation.md)
- [AMD vs NVIDIA comparison](examples/amd-vs-nvidia.md)
- [Earnings analysis](examples/earnings-analysis.md)
- [Thesis tracking](examples/thesis-tracking.md)

## Why YouRich?

AI can explain a business, summarize filings, and write a useful research note.
The risk is that financial periods, derived metrics, missing data, and evidence
quality can blur together.

YouRich gives the host agent deterministic tools for the parts that should not
depend on prose generation: SEC period handling, metric provenance, valuation
math, quality checks, and evidence tracking.

| Dimension | Raw AI answer | AI + YouRich |
| --- | --- | --- |
| Financial calculations | Model-generated | Deterministic Python |
| SEC periods | Easy to mix | Period-aware |
| TTM reconstruction | Often unclear | Explicit reconstruction |
| Missing data | Easy to fill implicitly | Stays missing |
| Metric provenance | Conversation-dependent | Preserved |
| Earnings / guidance | Summary-oriented | Structured evidence |
| Valuation | Narrative estimate | Reverse DCF + scenarios |
| Peer analysis | Often broad | Basis-aware comparison |
| Previous research | Conversation-dependent | Local research snapshots |
| Events | Ad hoc summary | Primary-source event intelligence |

## Quick Start

Requirements:

- Python 3.11+
- Claude Code or OpenAI Codex
- Git

```bash
git clone https://github.com/gaedsstudio/YouRich.git
cd YouRich
```

macOS / Linux:

```bash
chmod +x install.sh
./install.sh
```

Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

After installation, use the skill from Claude Code or Codex:

```text
$yourich Analyze NVIDIA as an investment.
```

```text
$yourich Is Apple expensive at the current price?
```

```text
$yourich Compare AMD and NVIDIA.
```

Claude Code examples:

```text
Use YouRich to analyze NVIDIA as an investment.
```

```text
Use YouRich to compare AMD, NVIDIA, and Broadcom.
```

```text
Use YouRich to show what changed in NVIDIA since my previous analysis.
```

## What YouRich Can Do

### Company Research

Builds evidence-backed company research using SEC filings, normalized
financials, risk checks, and plain-language report structure.

### Financial Data Correctness

Normalizes SEC Company Facts into selected financial fields with explicit basis,
source, filing period, and quality metadata.

### Valuation Intelligence

Computes deterministic valuation metrics, reverse DCF context, scenario ranges,
and valuation warnings without turning them into price targets.

### Earnings & Guidance

Uses official earnings materials and SEC 8-K evidence to separate reported
results, guidance, management commentary, and thesis-change signals.

### Industry & Peer Research

Compares companies against explicit or conservatively discovered peers while
preserving basis mismatches and comparability warnings.

### Thesis Tracking

Stores local research snapshots, compares current evidence with previous
research, and produces compact change reports.

### Catalyst & Event Intelligence

Classifies primary-source events, deduplicates overlapping evidence, maps
material events to thesis dimensions, and lists upcoming catalysts only when an
official source confirms the date.

## Example Research Flow

```text
User asks investment question
        ↓
YouRich fetches SEC financials and filing evidence
        ↓
Deterministic scripts compute valuation, quality, risk, peers, events
        ↓
Host agent interprets the evidence
        ↓
Structured report with provenance and warnings
```

## Example Output

YouRich's report layer is designed for consumer-readable research:

```text
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

For representative structure without invented live values, see
[examples/](examples/).

## Evidence First

Every important claim should follow:

```text
Claim -> Evidence -> Interpretation
```

Evidence states are explicit:

```text
SUPPORTED
PARTIALLY_SUPPORTED
CONTRADICTED
INSUFFICIENT_EVIDENCE
```

Financial values are separated from interpretation:

```text
reported_fact
derived_metric
qualitative interpretation
```

## Missing Data Stays Missing

If YouRich cannot verify a value, it returns `null`, a warning, or an
insufficient-data state. It does not turn missing data into zero, guess a market
price, or quietly fill unsupported fields.

## Data Sources

YouRich uses SEC Company Facts, SEC EDGAR submissions, SEC archive documents,
official earnings materials, and optional delayed market quote providers. Market
provider failures are reported as warnings, not hidden by guessed prices.

Set `YOURICH_SEC_USER_AGENT` to configure the EDGAR User-Agent with your own
requester identifier. Do not invent a fake contact address.

## Data Quality

SEC quarterly values are often reported as year-to-date figures. YouRich keeps
the period math explicit:

```text
Q2 = 6M YTD - Q1
Q3 = 9M YTD - 6M YTD
Q4 = Annual - 9M YTD
```

This matters for TTM correctness. A last-twelve-month figure may require:

```text
Latest annual
+ current year-to-date
- comparable prior year-to-date
= reconstructed TTM
```

That reconstructed value is a derived metric, not a directly reported SEC fact.
The report JSON preserves provenance so downstream agents can distinguish
reported facts from YouRich-derived metrics.

## Internal Tools

The skill includes deterministic scripts under
[`skill/yourich/scripts/`](skill/yourich/scripts/):

```bash
python scripts/fetch_financials.py AAPL
python scripts/valuation_intelligence.py NVDA --format markdown
python scripts/earnings_context.py AAPL --format markdown
python scripts/peer_research.py NVDA --format markdown
python scripts/event_intelligence.py NVDA --format markdown
python scripts/thesis_tracker.py NVDA compare --format markdown
python scripts/report.py AAPL --language en
python scripts/compare.py AAPL MSFT --format markdown
```

Run scripts from the installed skill directory or from
`skill/yourich/scripts/` during development.

## Project Structure

```text
skill/yourich/              Skill instructions and deterministic scripts
skill/yourich/references/   Research methodology references
tests/                      Regression tests for financial correctness and reports
examples/                   Public example report structures
assets/                     Demo recording guidance and future demo media
.github/                    Issue, pull request, and CI templates
docs/                       Repository metadata and maintainer notes
```

## Design Principles

- Deterministic calculations over model arithmetic.
- SEC period handling before valuation interpretation.
- Missing data remains visible.
- Provenance is preserved for important metrics.
- Primary sources are preferred for filings, earnings, and events.
- Reports should be readable without hiding methodology.
- No direct buy/sell instructions.

## Current Milestone

Current milestone: **v0.9.0 — Catalyst & Event Intelligence**.

The next major focus is v1.0 stability, not broad new investment-analysis
features.

## Roadmap

The v1.0 roadmap is intentionally stability-focused:

- stable schemas
- installation reliability
- regression coverage
- documentation
- example reports
- release packaging
- CI
- contributor workflow

## What YouRich Is Not

YouRich is not:

- a stock-picking product
- a trading bot
- a brokerage tool
- a guarantee of returns
- a buy/sell engine
- a replacement for professional judgment

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Financial correctness bugs have higher
priority than adding new metrics.

## Development

Install development tools from the repository configuration, then run:

```bash
python -m ruff check .
python -m basedpyright
python -m pytest -q
```

Use `python -m ruff format .` before committing Python changes.

## Disclaimer

YouRich is a research tool. It is not financial advice and does not recommend
when, whether, or how much to buy or sell. Verify important information against
primary sources before making decisions.

## License

[MIT License](LICENSE)
