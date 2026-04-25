# Step 16 Per-Security Reports

This directory is reserved for Step 16 generated per-security detail report
artifacts.

Intended generated report directory:

```text
reports/security/generated/
```

Generated report files are runtime artifacts. They are not canonical source
documents, roadmap status, adoption decisions, ranking outputs, backtest
outputs, or valuation outputs. Do not commit generated report files by default.

Required generated report notice:

```text
technical-only detail report
```

## Purpose

Step 16 reports explain the current per-security technical snapshot for safe
downstream use. They may display Step 15 ranking fields only as read-only
snapshot context and may preserve technical score, coverage, data-quality,
adoption, and diagnostic limitations.

## Allowed Content

- ticker, date, and as-of-date identifiers
- read-only Step 15 `rank`
- Step 15 `technical_composite_score` and `final_composite_score`
- technical score and normalized technical score context
- coverage, warmup, validity, and data-quality status
- adoption synthesis traceability
- diagnostic/context fields as explanatory context only

## Forbidden Content

- forward, future, next-period, realized, or backtest returns
- hit rate, CAGR, MDD, Sharpe, turnover, slippage, fees, or portfolio results
- buy/sell/hold decisions, trading signals, target prices, expected returns, or
  position sizing
- PER/PBR/ROE, financial/fundamental columns, valuation scores, or valuation
  verdicts
- valuation language such as cheap, bargain, undervalued, or value stock
- diagnostic/context fields described as direct alpha signals
- new ranking, re-ranking, rank deltas, or Step 16-generated rank fields

No backtest is implemented or evidenced by Step 16 reports.

No valuation or fundamental scoring is implemented or evidenced by Step 16
reports.
