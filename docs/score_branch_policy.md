# Score Branch Policy

## Purpose

This Step 4 policy fixes the boundary between technical analysis, valuation/fundamental analysis, diagnostics, and mixed ideas before Step 5 score definition work begins.

This document does not implement scores, composite scores, rankings, valuation review, or backtests.

## Allowed Branches

| branch | owner | allowed inputs now | current status |
| --- | --- | --- | --- |
| `technical` | `Quant_mvp` Score Architect | daily OHLCV, price, volume, rolling statistics, technical indicators, cross-sectional technical features | available for definition only |
| `valuation` | `.agents/skills/valuation_review/SKILL.md` | point-in-time-safe fundamentals such as earnings, revenue, book equity, cash flow, profitability, quality, PER, PBR, ROE | deferred / unavailable |
| `diagnostic` | main technical workflow or review workflow | coverage, missingness, stability, redundancy, turnover, data quality, correlation diagnostics | allowed as diagnostics only |
| `hybrid` | split review required | separable technical inputs plus separable point-in-time valuation inputs | blocked_by_data until valuation data is verified |
| `out_of_scope` | master or responsible project reviewer | intraday-only, order book, opaque ML, unsupported alternative data, or non-MVP ideas | reject or defer |

## Technical Branch

`technical` scores may only be derived from:

- daily OHLCV
- price and volume
- rolling returns
- rolling volatility
- moving averages
- drawdown and distance-from-high measures
- technical indicators
- cross-sectional technical features computed from same-date eligible universe data

`technical` evidence may support technical or diagnostic claims only.

It must not be described as cheap, value, undervalued, bargain, or valuation-supported.

## Valuation Branch

`valuation` scores require point-in-time-safe fundamental data.

Examples include:

- PER
- PBR
- ROE
- earnings
- revenue
- book equity
- cash flow
- profitability
- accounting quality
- analyst revisions

Before valuation scoring is available, the repository must have explicit:

- fundamental field definitions
- filing date, disclosure date, effective date, or availability date
- reporting lag policy
- stale data policy
- market capitalization or share-count logic where required
- sector or industry metadata where sector-relative valuation is proposed

Until these are present, valuation status remains `valuation_deferred` or `unavailable`.

## Diagnostic Branch

Diagnostics are allowed only as process, quality, or stability information.

Diagnostics must not be packaged as:

- alpha signals
- stock-selection scores
- valuation evidence
- final ranking evidence

Examples:

- NaN coverage
- warmup readiness
- score correlation diagnostics
- duplicate data checks
- rank stability diagnostics after the correct stage allows them
- data-quality flags

## Hybrid Branch

`hybrid` is allowed only as a classification or handoff state before implementation.

Hybrid use requires all of the following:

- the technical portion can be separated from the valuation portion
- the valuation portion has point-in-time-safe data
- the combination rule is explicit and config-owned
- no black-box mixing
- no valuation status of `deferred`, `unavailable`, or `blocked_by_data`

If those conditions are not met, hybrid remains `blocked_by_data` or `deferred`.

## Hard Stops

- Financial or fundamental data must not enter `technical_composite_score`.
- Financial or fundamental data must not enter `final_composite_score`.
- `PER`, `PBR`, `ROE`, or financial statement display values must not affect technical scoring or ranking.
- Low RSI, oversoldness, drawdown, recent underperformance, low absolute price, and moving-average distance are not valuation evidence.
- Step 5 may define score candidates, but must not implement production scores.
- Step 9 is the earliest Research Tester implementation step.
- Step 17 is the earliest backtest step.

## Current Verdict

Step 4 boundary status:

```text
technical_branch_status = definition_allowed_only
valuation_status = valuation_deferred
diagnostic_status = diagnostics_only
hybrid_status = blocked_by_data_until_point_in_time_valuation_is_verified
financial_data_in_technical_score = false
financial_data_in_final_composite_score = false
```
