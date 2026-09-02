# Apple Valuation Intelligence

Example structure - values omitted.

## User Request

```text
$yourich Is Apple expensive at the current price?
```

## Workflow Used

- Fetch SEC financials and delayed market quote data.
- Run deterministic valuation metrics.
- Run reverse DCF and scenario valuation.
- Surface historical valuation and data-quality warnings when available.

## Representative Output

```text
Current valuation
Reverse DCF
Scenario valuation
Historical valuation context
Warnings
```

## Why This Is Useful

The result frames valuation as required growth and scenario context instead of a
buy/sell instruction or unsupported price target.
