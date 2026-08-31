# Valuation

Valuation scripts return independent metrics, not a single truth.

Implemented formulas:

- P/E = market price / TTM diluted EPS when available
- P/B = market cap / latest shareholder equity, or price / latest BVPS
- P/S = market cap / TTM revenue
- Market Cap = current price * shares outstanding
- FCF yield = TTM free cash flow / market cap * 100
- Earnings yield = TTM net income / market cap * 100
- NCAV = current assets - total liabilities
- NCAV per share = NCAV / shares outstanding
- Price/NCAV = price / NCAV per share
- Graham Number = sqrt(22.5 * normalized EPS * book value per share)
- Margin of Safety = (reference value - price) / reference value * 100
- Conservative intrinsic value = normalized EPS * 12

Graham Number is a conservative reference point, not a precise intrinsic value.
If market price is unavailable, price-dependent metrics must remain `null`.
Each metric includes available inputs, periods, and field sources so the host
agent can explain what data was used. If financial and market currencies differ,
price-sensitive valuation metrics remain `null`.
