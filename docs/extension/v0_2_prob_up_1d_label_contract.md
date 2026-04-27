# v0.2 `prob_up_1d_candidate` Label Contract

Status: frozen label and no-lookahead contract for v0.2 predictive probability
contract preparation. This contract does not approve runtime implementation or
production ranking.

## Label

```text
up_1d_label = adjusted_close[t+1] > adjusted_close[t]
```

Interpretation:

- `true`: next trading day's adjusted close is greater than the current
  decision-date adjusted close.
- `false`: next trading day's adjusted close is less than or equal to the
  current decision-date adjusted close.
- non-evaluable: next trading-day adjusted close is unavailable, symbol is not
  eligible, or adjustment/timing is unresolved.

## Timing Fields

Required row-level fields:

- `decision_time`
- `symbol`
- `current_adjusted_close`
- `next_trading_day`
- `next_adjusted_close`
- `label_available_time`
- `source_data_availability_time`
- `feature_construction_time`

## No-Lookahead Rules

- Features for a row must be computed only from information available at or
  before `decision_time`.
- `next_adjusted_close`, `up_1d_label`, and any realized future performance are
  forbidden as live scoring inputs.
- The label may be used only in training, validation, calibration, and
  evaluation artifacts.
- Train/validation/test splits must be time-ordered or otherwise documented as
  leakage-safe before model implementation.

## Split And Adjustment Rules

- Label construction must use the same approved adjusted-close policy as the
  feature route.
- Rows with unresolved split, adjustment, or trading-calendar ambiguity must be
  excluded or marked non-evaluable.

## Remaining Dependency

This contract freezes label semantics only. It does not freeze model type,
features, hyperparameters, validation thresholds, generated-output paths, or
production adoption.
