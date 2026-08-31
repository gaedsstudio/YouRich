# YouRich

Open-source investment research skills for Claude Code and Codex.

Current milestone: v0.3.0 Financial Data Correctness.

YouRich adds a structured fundamental research workflow, deterministic financial
calculations, delayed market quotes, valuation tools, risk checks, and evidence
verification to coding agents.

## Installation

```bash
git clone <repo>
cd yourich
./install.sh
```

Windows PowerShell:

```powershell
./install.ps1
```

The installer checks for Python 3.11+, then installs the same `skill/yourich`
source into detected Claude Code and Codex user skill locations. Existing
unrelated settings are not overwritten.

## Claude Code

After installation, ask Claude Code in your normal workflow:

```text
Analyze NVIDIA using YouRich.
Compare AMD and Intel.
Value Microsoft.
Check the financial risks of Tesla.
```

The Claude plugin metadata is in `integrations/claude/.claude-plugin/plugin.json`.

## Codex

After installation, invoke the skill explicitly or through natural language:

```text
$yourich Analyze NVIDIA.
Compare AAPL and MSFT as investments.
```

Codex display metadata is in `integrations/codex/agents/openai.yaml`.

## Skill Structure

```text
skill/yourich/
├── SKILL.md
├── scripts/
├── references/
└── assets/
```

`SKILL.md` is the source of truth. Platform-specific files only package or
describe that same skill.

## Deterministic Scripts

The scripts are internal tools for agents:

```bash
cd skill/yourich
python scripts/fetch_financials.py AAPL
python scripts/fetch_financials.py AAPL --debug
python scripts/valuation.py --ticker AAPL
python scripts/financial_health.py --ticker AAPL
python scripts/risk.py --ticker AAPL
python scripts/compare.py AAPL MSFT
```

They emit JSON and use `Decimal` for financial calculations. Agents should not
recalculate NCAV, Graham Number, margins, ratios, trend calculations, or risk
flags in model reasoning.

`fetch_financials.py` combines SEC Company Facts fundamentals with a delayed
market quote when a free provider is available. The default market providers are
free endpoints and should be treated as unofficial unless noted:

- Yahoo chart endpoint, cached for 15 minutes.
- Stooq CSV endpoint, cached for 15 minutes.
- Alpha Vantage Global Quote when `YOURICH_MARKET_PROVIDER=alpha_vantage` and
  `YOURICH_MARKET_API_KEY` are set.

Fundamental data is cached for 24 hours. Set `YOURICH_CACHE_DIR` to control the
cache location. If providers fail, YouRich leaves price-dependent fields `null`
and records warnings; it never guesses a market price.

v0.3 separates annual, quarterly, TTM, and latest balance-sheet snapshot facts.
SEC fact metadata records concept, unit, form, filing date, fiscal period,
accession number, confidence, and best-effort restatement status.

## Metrics

YouRich supports Market Cap, TTM P/E, latest P/B, TTM P/S, TTM FCF yield, TTM
earnings yield, NCAV, NCAV per share, Price/NCAV, Graham Number, margin of safety, normalized EPS,
revenue growth, earnings growth, margins, ROE, ROA, ROIC, current ratio, quick
ratio, debt/equity, debt/assets, earnings consistency, FCF consistency, share
dilution, and quantitative risk checks when data exists.

## Methodology

The default workflow identifies the company, gathers financial data, normalizes
it, runs deterministic valuation and risk scripts, verifies claims with
evidence, builds bull and bear cases, and produces an investment thesis.

## JSON Format

See `skill/yourich/references/output-schema.md`.

## Development

```bash
python -m pip install pytest ruff basedpyright
python -m pytest
python -m ruff check .
python -m basedpyright
```

## Disclaimer

YouRich is for investment research support only. It does not provide financial
advice, guarantee returns, or issue definitive buy or sell instructions.
