# v0.1n Strategy Signal Schema

Status: Stage A doc-contract only. This document does not create runtime code,
production config, generated data, model training, ranking behavior, report
behavior, GUI behavior, or backtest behavior.

## Purpose

Freeze the candidate-only schema names and timing rules needed before any later
v0.1n implementation scope can be reviewed. The schema is for future sidecar
candidate tables only and must not overwrite MVP v0.1 outputs.

## Required Status Fields

Every v0.1n candidate row must include:

| field | required value |
| --- | --- |
| `candidate_line` | `v0.1n` |
| `candidate_status` | `v0.1n_candidate` |
| `target_release_line` | `v0.2` |
| `production_enabled` | `false` |
| `ranking_enabled` | `false` |

`target_release_line = "v0.2"` is route-only future-freeze language. It must
not be used as a release claim before v0.2 freeze criteria pass.

## Base Strategy Signal Row

Each base strategy emits one row per ticker and decision date.

| field | required | type | notes |
| --- | --- | --- | --- |
| `candidate_line` | yes | string | Must be `v0.1n`. |
| `candidate_status` | yes | string | Must be `v0.1n_candidate`. |
| `strategy_id` | yes | string | Registry key. |
| `strategy_version` | yes | string | Versioned strategy contract. |
| `strategy_family` | yes | string | Registry family. |
| `strategy_role` | yes | string | `base_signal`, `gate`, `risk_filter`, or `diagnostic_only`. |
| `ticker` | yes | string | KOSPI200 symbol only. |
| `decision_date` | yes | date | Trading date for decision. |
| `decision_time` | yes | timestamp | Time inputs are cut off. |
| `execution_time` | yes | timestamp | First hypothetical execution time. |
| `feature_cutoff_time` | yes | timestamp | Latest allowed input timestamp. |
| `signal_raw` | yes | float | Native signal value. |
| `signal_score_0_100` | no | float | Optional normalized signal. |
| `signal_direction` | yes | string | `long_bias`, `avoid_bias`, `neutral`, or `context_only`. |
| `rule_quality_score` | no | float | Rule-quality diagnostic only, not prediction confidence. |
| `model_input_allowed` | yes | boolean | False for diagnostics or blocked outputs. |
| `validity_flag` | yes | string | `valid`, `warmup`, `missing_input`, `invalid`, or `diagnostic_only`. |
| `missing_input_count` | yes | integer | Required missing input count. |
| `warmup_bars_remaining` | yes | integer | Zero when valid. |
| `data_quality_flag` | yes | string | Conservative data-quality marker. |
| `run_id` | yes | string | Reproducible build identifier. |
| `registry_version` | yes | string | Registry contract version. |
| `config_version` | yes | string | Candidate config version. |
| `input_data_snapshot_id` | yes | string | Existing approved input snapshot identifier. |

## Composition Feature Row

The composition feature table is the only allowed model-input table for the
future meta-model. It must be physically separate from label, evaluation, and
backtest result tables.

Required row-level fields:

```text
candidate_line
candidate_status
production_enabled
ranking_enabled
feature_table_version
run_id
registry_version
config_version
input_data_snapshot_id
ticker
decision_date
decision_time
execution_time
feature_cutoff_time
strategy_count_valid
strategy_family_count_valid
composition_missingness_rate
data_quality_flag
```

Allowed strategy-derived column pattern:

```text
strategy_<strategy_id>_signal_raw
strategy_<strategy_id>_score_0_100
strategy_<strategy_id>_validity_flag
strategy_<strategy_id>_family
strategy_<strategy_id>_model_input_allowed
```

Columns with `strategy_<strategy_id>_model_input_allowed = false` must be
excluded from the predictive matrix. They may be retained only as audit
metadata or diagnostics.

Forbidden composition feature fields:

```text
adjusted_close[t+1]
adjusted_close_t_plus_1
forward_return_1d
label_up_1d_candidate
backtest_return
realized_pnl
future_rank
PER
PBR
ROE
valuation_score
```

## Label Row

The first candidate label is:

```text
label_up_1d_candidate = adjusted_close[t+1] > adjusted_close[t]
```

Required fields:

```text
candidate_line
candidate_status
run_id
ticker
decision_date
label_time
label_availability_time
adjusted_close_t
adjusted_close_t_plus_1
label_up_1d_candidate
label_validity_flag
```

Rows without a valid `adjusted_close_t_plus_1` must be excluded from supervised
training and evaluation. They must not be filled with false, neutral, or
inferred labels.

## Prediction Row

Prediction/display tables must stay separate from labels and evaluation
outcomes.

Required fields:

```text
candidate_line
candidate_status
production_enabled
ranking_enabled
run_id
registry_version
config_version
input_data_snapshot_id
feature_table_version
model_version
calibration_method
training_window_id
ticker
decision_date
decision_time
execution_time
feature_cutoff_time
prediction_time
prob_up_1d_candidate
prob_up_1d_candidate_score_0_100
horizon_trading_days
prediction_validity_flag
evaluation_only_notice
```

`prob_up_1d_candidate` must be calibrated before it can be displayed as a
probability. Uncalibrated values must not use probability naming.

## Timing Rules

All implementation proposals must make these inequalities directly testable:

```text
feature_cutoff_time <= decision_time
decision_time <= execution_time
execution_time < label_availability_time
label_time <= label_availability_time
```

The label may be used only after `label_availability_time` and must never
appear in the composition feature table.

## Blocking Criteria

- BLOCK if any field from the forbidden composition list appears in model
  inputs.
- BLOCK if `production_enabled` or `ranking_enabled` is true.
- BLOCK if candidate rows can overwrite MVP v0.1 ranking, report, GUI, or
  backtest outputs.
- BLOCK if `v0.2` is used as a frozen release label before freeze criteria
  pass.
- BLOCK if trading recommendation, expected-return, proven-alpha, or
  guaranteed-performance wording appears in candidate outputs.

