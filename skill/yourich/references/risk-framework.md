# Risk Framework

Quantitative risk checks come from `scripts/risk.py`. Qualitative risk analysis
comes from public evidence gathered by the host agent.

Quantitative checks include liquidity risk, debt risk, negative equity, earnings
deterioration, FCF deterioration, margin deterioration, share dilution, and
valuation risk.

Qualitative checks may include customer concentration, cyclicality, accounting
red flags, regulation, product concentration, competitive pressure, or
management quality. Mark qualitative risks as evidence-backed only when public
sources support them.

Risk output uses:

```json
{
  "id": "debt_risk",
  "severity": "medium",
  "status": "triggered",
  "value": "1.82",
  "threshold": "1.5",
  "explanation": "Debt/equity is above the configured threshold."
}
```
