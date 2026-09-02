# Contributing

Thanks for helping improve YouRich.

## Setup

Use Python 3.11 or newer.

```bash
python -m pip install -e .
python -m pip install ruff basedpyright pytest
```

## Testing

Before opening a pull request, run:

```bash
python -m ruff format .
python -m ruff check .
python -m basedpyright
python -m pytest -q
```

## Coding Standards

- Preserve deterministic financial behavior.
- Keep missing data visible.
- Preserve metric provenance.
- Prefer focused modules and focused tests.
- Do not add direct buy/sell guidance.

## Correctness First

Financial correctness bugs have higher priority than adding new metrics or new
report sections.

## Reporting Financial-Data Bugs

For a financial-value bug, include:

- ticker
- metric
- reported YouRich value
- expected value
- basis or period
- source filing
- reproduction command
- debug JSON if available

## Adding SEC Mappings

Add mappings conservatively. Include tests for the selected concept, rejected
alternatives, period basis, provenance, and fallback behavior.

## Adding Tests

Prefer deterministic fixtures or real SEC-shaped fixtures. Do not invent
financial values when real deterministic fixtures are appropriate.
