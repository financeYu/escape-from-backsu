# Next Horizon Up Probability Score Design

## Purpose

This document defines a post-MVP candidate score family for estimating whether a
KOSPI200 stock closes higher after a fixed future horizon. It is a Score
Architect design artifact only.

This document does not implement model training, create runtime ranking output,
change `technical_composite_score`, change `final_composite_score`, activate
backtest feedback, or add valuation/fundamental inputs.

## Candidate Scores

| score_name | horizon | display_column | label |
| --- | ---: | --- | --- |
| `next_1d_up_probability_score` | 1 trading day | `next_1d_up_probability_score` | `close[t+1] / close[t] - 1 > 0` |
| `next_5d_up_probability_score` | 5 trading days | `next_5d_up_probability_score` | `close[t+5] / close[t] - 1 > 0` |
| `next_20d_up_probability_score` | 20 trading days | `next_20d_up_probability_score` | `close[t+20] / close[t] - 1 > 0` |

All three scores share one candidate family:

- `score_family`: `directional_probability`
- `score_branch`: `technical`
- `status`: `candidate_only`
- `runtime_enabled`: `false`
- `ranking_integration`: `not_allowed_without_later_adoption_step`

## Prediction Timing

For an as-of date `t`, the prediction must be made after the market close of
`t` using only data available at or before `close[t]`.

Allowed input cutoff:

```text
input_cutoff = close_t
```

Forbidden inputs:

```text
close[t+h]
high[t+h]
low[t+h]
volume[t+h]
future_return
realized_forward_return
backtest_result
PER
PBR
ROE
financial_statement_fields
valuation_fields
```

## Label Definitions

For each stock and date:

```text
forward_return_h = close[t+h] / close[t] - 1
target_h = 1 if forward_return_h > 0 else 0
```

where `h` is one of `1`, `5`, or `20` trading days. Calendar days must not be
used as a substitute for trading-day horizons.

Rows without a complete future label are excluded from supervised training and
evaluation for that horizon. They must not be filled with `0`, neutral values,
or inferred outcomes.

## Score Scale

The model output should be a calibrated probability. For GUI display, use a
0-100 scale:

```text
display_score_h = calibrated_probability_h * 100
```

Interpretation:

- `60.0` means the candidate model estimates a 60 percent probability for the
  corresponding horizon label.
- It is not an expected return estimate.
- It is not a trading recommendation.
- It is not proven alpha.
- It is not valuation support.

## Feature Scope

Allowed feature families are technical-only and must be computed at or before
`close[t]`:

- trailing close-to-close returns
- trailing intraday range statistics
- trailing volatility and realized volatility percentiles
- RSI and oscillator-style technical features
- moving-average distance and trend slope features
- breakout distance and rolling high/low distance features
- volume and price-volume participation proxies from daily OHLCV
- existing MVP normalized technical score columns when their own as-of timing is
  no later than `t`

Any feature that depends on future bars, financial statements, valuation
metrics, market-cap fundamentals, analyst data, filings, or backtest outcomes is
out of scope for this candidate family.

## Validation Protocol

Use walk-forward validation. Random row shuffling is not acceptable because it
can leak future market regimes into training.

Minimum validation expectations:

- date-ordered train, validation, and test splits
- no future labels or future features in the training feature matrix
- horizon-specific evaluation for 1, 5, and 20 trading days
- purged or embargoed validation when overlapping labels could leak adjacent
  outcomes, especially for 5-day and 20-day horizons
- per-date diagnostics rather than only pooled metrics
- class-balance checks by horizon
- calibration checks by horizon

Primary model-quality metrics:

- ROC AUC
- Brier score
- calibration curve
- log loss
- top-bucket hit rate
- top-N hit rate as evaluation-only diagnostics

Secondary diagnostics:

- feature coverage
- missingness by ticker and date
- turnover of high-probability buckets
- stability across market regimes
- correlation with existing MVP technical composite score

## Model Policy

The first implementation candidate should prefer transparent or inspectable
models:

- logistic regression with regularization
- calibrated gradient boosting only if the simpler baseline is insufficient

Probability calibration is required before displaying values as probabilities.
Uncalibrated model scores must use `model_score`, not `probability`, in their
column names.

## Output Columns

Candidate output tables should use explicit horizon-specific names:

```text
ticker
date
next_1d_up_probability_score
next_5d_up_probability_score
next_20d_up_probability_score
next_1d_probability_bucket
next_5d_probability_bucket
next_20d_probability_bucket
probability_model_version
prediction_asof
input_cutoff
label_horizon_set
ranking_validity_flag
evaluation_only_notice
```

Suggested notice:

```text
KOSPI200 technical-only candidate up-probability scores; evaluation-only, no trading recommendation.
```

## Relationship To Existing MVP Scores

These candidates must remain separate from the MVP v0.1 ranking contract.

- Do not overwrite `technical_composite_score`.
- Do not overwrite `final_composite_score`.
- Do not use these scores for production ranking without a later adoption step.
- Do not compare them as valuation signals.
- Do not feed backtest diagnostics into the score definition.

The safe first integration point is a sidecar evaluation table, not the GUI's
current `점수` column.

## Failure Modes

- Direction labels may be noisy and close to random at one trading day.
- Five-day and twenty-day labels overlap, so naive validation can overstate
  stability.
- Market-wide drift can dominate stock-specific technical signals.
- Transaction costs and slippage are not captured by a binary close-to-close
  label.
- A higher probability can still map to a low or negative expected return if
  the payoff distribution is asymmetric.
- Model calibration can decay across regimes.

## Required Next Steps Before Implementation

1. Add a versioned config stub for horizons, split dates, model family, and
   calibration method.
2. Add leakage guardrail tests for feature cutoff and label construction.
3. Build an evaluation-only dataset generator.
4. Run horizon-specific walk-forward validation.
5. Submit technical review and adoption review before any ranking or GUI
   integration.
