# Next Horizon Up Probability Score Design

## Purpose

This document defines a post-MVP candidate score family for estimating whether a
KOSPI200 stock closes higher after a fixed future horizon. It is a Score
Architect design artifact only.

This document does not implement model training, create runtime ranking output,
change `technical_composite_score`, change `final_composite_score`, activate
backtest feedback, or add valuation/fundamental inputs.

## Candidate Score

This design uses one parameterized score instead of hardcoded 1-day, 1-week, or
1-month score names.

| field | value |
| --- | --- |
| `score_name` | `next_horizon_up_probability_score` |
| `display_column` | `next_horizon_up_probability_score` |
| `horizon_parameter` | `horizon_trading_days` |
| `default_horizon_trading_days` | `1` |
| `user_facing_label_template` | `{horizon_trading_days}거래일 뒤 상승확률 후보` |
| `default_user_facing_label` | `1거래일 뒤 상승확률 후보` |
| `label_template` | `close[t + horizon_trading_days] / close[t] - 1 > 0` |
| `usage_status` | `primary_candidate_for_default_1_trading_day_horizon` |

The score family is:

- `score_family`: `directional_probability`
- `score_branch`: `technical`
- `status`: `candidate_only`
- `runtime_enabled`: `false`
- `ranking_integration`: `not_allowed_without_later_adoption_step`

Initial operating selection:

- `default_horizon_trading_days`: `1`
- `active_horizon_source`: config value, not a hardcoded score name
- `non_default_horizons`: not active until a later review step approves them
- `non_default_horizon_reason`: first pass should validate the default
  1-trading-day close-to-close directional label before expanding to longer,
  overlapping labels.
- `gui_main_display_candidate`: `next_horizon_up_probability_score` with
  `horizon_trading_days = 1` only after a later implementation and review step
  approves evaluation-only display.

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

where `h = horizon_trading_days`. The default first-pass value is `h = 1`.
Calendar days must not be used as a substitute for trading-day horizons.

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
- horizon-specific evaluation for the configured horizon, starting with the
  default 1-trading-day horizon
- purged or embargoed validation when overlapping labels could leak adjacent
  outcomes before enabling longer non-default horizons
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
next_horizon_up_probability_score
next_horizon_probability_bucket
horizon_trading_days
horizon_usage_status
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
- Use `next_horizon_up_probability_score` with `horizon_trading_days = 1` as the
  only first-pass main candidate.
- Keep non-default horizons disabled until a later review step explicitly
  enables them.

The safe first integration point is a sidecar evaluation table, not the GUI's
current `점수` column.

## Failure Modes

- The default 1-trading-day direction label may be noisy and close to random.
- Longer non-default labels can overlap, so naive validation can overstate
  stability when those horizons are later evaluated.
- Market-wide drift can dominate stock-specific technical signals.
- Transaction costs and slippage are not captured by a binary close-to-close
  label.
- A higher probability can still map to a low or negative expected return if
  the payoff distribution is asymmetric.
- Model calibration can decay across regimes.

## Required Next Steps Before Implementation

1. Add a versioned config stub with `horizon_trading_days = 1` as the default
   active main horizon and non-default horizons disabled.
2. Add leakage guardrail tests for feature cutoff and label construction.
3. Build an evaluation-only dataset generator.
4. Run walk-forward validation for the default 1-trading-day horizon first.
5. Submit technical review and adoption review before any ranking or GUI
   integration.
