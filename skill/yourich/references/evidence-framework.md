# Evidence Framework

Every qualitative assertion follows:

```text
Claim -> Evidence -> Interpretation
```

Never skip the evidence step. If a filing does not support a claim, mark it as
`INSUFFICIENT_EVIDENCE` rather than filling the gap with model knowledge.

## Claim Status

- `SUPPORTED`: evidence directly supports the claim.
- `PARTIALLY_SUPPORTED`: evidence supports only part of the claim.
- `CONTRADICTED`: evidence conflicts with the claim.
- `INSUFFICIENT_EVIDENCE`: available evidence does not support the claim.

## Confidence

- `HIGH`: multiple strong sources or direct filing support.
- `MEDIUM`: one relevant source or partial direct support.
- `LOW`: sparse, indirect, stale, or missing evidence.

Use evidence IDs, filing URLs, section names, accession numbers, and filing dates
when explaining claims. Do not quote long filing passages; summarize the
evidence and keep excerpts compact.
