# Risk Framework

Quantitative risk checks come from `scripts/risk.py`. SEC filing risk comes from
`scripts/research_context.py` and must remain separate from quantitative flags.

Quantitative checks include liquidity risk, debt risk, negative equity, earnings
deterioration, FCF deterioration, margin deterioration, share dilution, and
valuation risk.

Filing risks may include customer concentration, cyclicality, accounting red
flags, regulation, product concentration, competitive pressure, cybersecurity,
litigation, supply chain exposure, or management quality. Mark qualitative risks
as evidence-backed only when a filing excerpt or cited public source supports
them.

Risk-factor change detection must begin with deterministic text preprocessing:
clean HTML, normalize tokens, compare the latest and prior risk-factor excerpts,
then let the host agent interpret whether the change is material. Do not rely on
semantic similarity alone.

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
