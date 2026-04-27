# v0.1n Strategy Composition Plan For Future v0.2

Status: planning/design only. This document creates a post-MVP candidate track
for a possible future v0.2 score semantic. It does not change MVP v0.1 scoring,
ranking, reports, backtests, valuation status, data ingestion, GUI behavior, or
release status.

## Lifecycle

`v0.1n` is the experimental candidate line for post-MVP score research. It is
not a frozen release, not a production ranking contract, and not an adoption
decision.

Allowed `v0.1n` work:

- define candidate contracts, schemas, and validation expectations
- create reproducible candidate tables under evaluation-only boundaries
- compare inspectable base strategy signals and meta-level composition rules
- document calibration, leakage, and backtest diagnostics
- reject, rename, or revise candidate contracts before freeze

Forbidden `v0.1n` work:

- changing MVP v0.1 `technical_composite_score` or `final_composite_score`
- overwriting v0.1 ranking, report, or backtest contracts
- activating KOSDAQ150, futures/options, overseas, or multi-universe scope
- introducing new market data sources
- using backtest results from the same period to silently redefine formulas
- claiming proven alpha, expected return, buy/sell/hold, or guaranteed
  superiority
- treating diagnostics as alpha signals

`v0.2` is reserved for a future frozen release only after contracts,
validation, review, and release gates pass. Until that gate closes, all work in
this direction must be labeled `v0.1n_candidate`.

## Future v0.2 Freeze Criteria

Before any `v0.2` freeze, the project must have all of the following:

1. A versioned score contract that names the target semantic as 1-day-ahead
   price-up probability, not generic attractiveness.
2. Frozen schemas for base strategy signals, composition features, labels,
   predictions, diagnostics, and backtest evaluation outputs.
3. Proof that MVP v0.1 columns and behavior remain reproducible or explicitly
   archived as a separate frozen line.
4. No-lookahead validation covering `decision_time`, `execution_time`, and
   `label_time`.
5. Walk-forward and out-of-sample validation with no random row-shuffle split as
   the primary evidence.
6. Probability calibration diagnostics, including Brier score, log loss,
   calibration curve, and expected calibration error.
7. A backtest boundary review proving evaluation results did not feed upstream
   score definitions or model selection in the same period.
8. Review/audit approval for leakage risk, data snooping, claim hygiene, and
   v0.1 regression risk.
9. Release notes that state limitations and avoid investment recommendation
   language.

## Score Semantic Boundary

MVP v0.1 remains the frozen KOSPI200 technical-only baseline. Its score is not
redefined by this design.

The future candidate semantic is:

```text
prob_up_1d_candidate = P(adjusted_close[t+1] > adjusted_close[t] | features available at decision_time)
```

Required status fields:

```text
candidate_line = "v0.1n"
target_release_line = "v0.2"
candidate_status = "v0.1n_candidate"
production_enabled = false
ranking_enabled = false
```

`prob_up_1d_candidate` is a calibrated probability candidate, not an expected
return, valuation score, trading recommendation, or proven alpha claim.

## Base Strategy Registry

The preferred ML direction is strategy composition: predefined, inspectable
base strategy signals are computed first, then a meta-model learns a
composition, weighting, or gating rule. The candidate must not become a single
opaque black-box alpha model.

Suggested registry file, if implemented later:

```text
Quant_mvp/config/v0_1n_strategy_registry.toml
```

Registry schema:

| field | required | purpose |
| --- | --- | --- |
| `strategy_id` | yes | Stable identifier, e.g. `mean_reversion_rsi_5d`. |
| `strategy_family` | yes | One of `mean_reversion`, `breakout`, `trend`, `volatility`, `flow`, `regime`, `diagnostic`. |
| `strategy_role` | yes | `base_signal`, `gate`, `risk_filter`, or `diagnostic_only`. |
| `version` | yes | Candidate strategy contract version. |
| `input_columns` | yes | Technical-only input fields available by `decision_time`. |
| `parameters` | yes | Windows, thresholds, and transforms, config-owned. |
| `output_columns` | yes | Signal columns emitted by the strategy. |
| `minimum_history` | yes | Minimum bars required before the signal is valid. |
| `warmup_policy` | yes | How invalid early rows are marked. |
| `model_input_allowed` | yes | False for `diagnostic_only`; true only for approved base/gate/risk inputs. |
| `allowed_universe` | yes | Must remain `KOSPI200` for this candidate line. |
| `data_sources` | yes | Existing approved OHLCV/technical inputs only. |
| `lookahead_review_status` | yes | `pending`, `passed`, or `blocked`. |
| `candidate_status` | yes | `v0.1n_candidate`, `rejected`, or `frozen_v0.2`. |

Diagnostics may exist in the registry, but `strategy_role = "diagnostic_only"`
must prevent their use as predictive strategy inputs unless a later approved
contract explicitly promotes them.

## Base Strategy Signal Schema

Each base strategy emits one row per ticker and decision date:

| field | type | notes |
| --- | --- | --- |
| `candidate_line` | string | Always `v0.1n` before freeze. |
| `strategy_id` | string | Registry key. |
| `strategy_version` | string | Versioned base strategy definition. |
| `ticker` | string | Existing KOSPI200 symbol policy only. |
| `decision_date` | date | Trading date for the decision. |
| `decision_time` | timestamp | Time when inputs are cut off. |
| `execution_time` | timestamp | Hypothetical next executable time for simulation. |
| `feature_cutoff_time` | timestamp | Latest timestamp allowed in inputs. |
| `signal_raw` | float | Native signal value. |
| `signal_score_0_100` | float | Optional normalized signal, if specified. |
| `signal_direction` | string | `long_bias`, `avoid_bias`, `neutral`, or `context_only`. |
| `rule_quality_score` | float | Optional rule-quality diagnostic, not alpha proof or prediction confidence. |
| `model_input_allowed` | boolean | False for diagnostics and any blocked strategy output. |
| `validity_flag` | string | `valid`, `warmup`, `missing_input`, `invalid`, or `diagnostic_only`. |
| `missing_input_count` | integer | Count of required missing fields. |
| `warmup_bars_remaining` | integer | Zero when valid. |
| `data_quality_flag` | string | Conservative data quality marker. |

Base strategies must not emit realized forward returns, label values, backtest
profit, or future OHLCV fields as signal inputs.

## Composition Feature Table

The composition feature table is the only permitted input to the meta-model. It
joins base strategy outputs at the same `decision_time` and remains separate
from label and backtest result tables.

Rows or columns with `strategy_role = "diagnostic_only"` or
`model_input_allowed = false` may appear only as audit metadata or diagnostics.
They must be excluded from the predictive feature matrix used to fit or score
the meta-model.

Suggested table name:

```text
v0_1n_strategy_composition_features
```

Required fields:

| field | type | notes |
| --- | --- | --- |
| `candidate_line` | string | `v0.1n`. |
| `feature_table_version` | string | Frozen for each candidate experiment. |
| `run_id` | string | Reproducible candidate-table build identifier. |
| `registry_version` | string | Base strategy registry version used for the build. |
| `config_version` | string | Candidate config version used for the build. |
| `input_data_snapshot_id` | string | Existing approved input snapshot identifier. |
| `ticker` | string | KOSPI200 only. |
| `decision_date` | date | Date of decision. |
| `decision_time` | timestamp | Input availability timestamp. |
| `execution_time` | timestamp | First hypothetical execution timestamp. |
| `feature_cutoff_time` | timestamp | Must be <= `decision_time`. |
| `strategy_<id>_signal_raw` | float | Base strategy raw signal. |
| `strategy_<id>_score_0_100` | float | Base strategy normalized score. |
| `strategy_<id>_validity_flag` | string | Base strategy validity. |
| `strategy_<id>_family` | string | Strategy family for interpretability. |
| `strategy_<id>_model_input_allowed` | boolean | Must be false for diagnostic-only columns. |
| `strategy_count_valid` | integer | Count of usable base signals. |
| `strategy_family_count_valid` | integer | Count of usable families. |
| `composition_missingness_rate` | float | Missing strategy feature ratio. |
| `data_quality_flag` | string | Combined quality flag. |

Forbidden composition fields:

```text
adjusted_close[t+1]
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

## Label Candidate

The first candidate label is:

```text
label_up_1d_candidate = adjusted_close[t+1] > adjusted_close[t]
```

Required label table fields:

| field | type | notes |
| --- | --- | --- |
| `candidate_line` | string | `v0.1n`. |
| `ticker` | string | KOSPI200 only. |
| `decision_date` | date | Same decision date as features. |
| `label_time` | timestamp | Adjusted close event timestamp for trading day `t+1`. |
| `label_availability_time` | timestamp | Time when the `t+1` adjusted close label is final and usable. |
| `adjusted_close_t` | float | Adjusted close at `t`. |
| `adjusted_close_t_plus_1` | float | Adjusted close at `t+1`. |
| `label_up_1d_candidate` | boolean | True if `adjusted_close_t_plus_1 > adjusted_close_t`. |
| `label_validity_flag` | string | `valid`, `missing_future_bar`, `corporate_action_gap`, or `invalid`. |

Rows without a valid `t+1` adjusted close are excluded from supervised training
and evaluation. They must not be filled with false, neutral, or inferred labels.

## Timing Contract

Timing must be explicit in every candidate table:

```text
decision_time <= execution_time
execution_time < label_availability_time
label_time <= label_availability_time
feature_cutoff_time <= decision_time
```

Default daily-bar interpretation:

- `decision_time`: after all inputs for trading day `t` are final and available
- `execution_time`: next approved hypothetical execution time after the
  decision, such as next open or next close, depending on the simulation
  contract
- `label_time`: adjusted close event timestamp for trading day `t+1`
- `label_availability_time`: later timestamp when the adjusted close and any
  corporate-action adjustment needed for the label are final

The label may be used only after `label_availability_time` and must not appear
in the composition feature table.

## Meta-Model Output

The candidate meta-model output is:

| field | type | notes |
| --- | --- | --- |
| `prob_up_1d_candidate` | float | Calibrated probability in `[0, 1]`. |
| `prob_up_1d_candidate_score_0_100` | float | Display transform: probability times 100. |
| `model_family` | string | Inspectable family, e.g. `logistic_regression`, `explainable_gbm`. |
| `model_version` | string | Versioned training recipe. |
| `calibration_method` | string | `platt`, `isotonic`, `none_unapproved`, etc. |
| `training_window_id` | string | Walk-forward training window identifier. |
| `run_id` | string | Reproducible prediction run identifier. |
| `registry_version` | string | Registry version used to build model inputs. |
| `config_version` | string | Candidate config version used to build model inputs. |
| `input_data_snapshot_id` | string | Input snapshot used for the prediction run. |
| `prediction_time` | timestamp | Time prediction is emitted. |
| `prediction_validity_flag` | string | `valid`, `insufficient_features`, `uncalibrated`, or `invalid`. |

The first acceptable model family should be simple and inspectable, such as
regularized logistic regression over base strategy features. More complex
models require feature importance, stability, calibration, and leakage review
before they can remain in the candidate line.

## No-Lookahead And Leakage Guardrails

Required checks:

- No feature column may be derived from bars later than `feature_cutoff_time`.
- `label_up_1d_candidate`, `adjusted_close_t_plus_1`, and forward returns must
  never appear in feature, normalization, imputation, or selection inputs.
- Cross-sectional transforms must use same-date data only, and their
  availability must be no later than `decision_time`.
- Rolling features must use trailing windows only.
- Imputation statistics must be fit inside each training window only.
- Feature selection must be performed inside each training window only.
- Calibration must be fit on validation data that is later than training data
  and earlier than test data.
- Any embargo or purge rule must be documented when adjacent labels overlap.
- Backtest evaluation from a test window must not be used to redefine the
  model, feature set, thresholds, or strategy registry for that same window.

## Walk-Forward Validation

Minimum validation design:

| component | requirement |
| --- | --- |
| split type | Date-ordered walk-forward. |
| primary holdout | Out-of-sample test windows not used for training or calibration. |
| training window | Explicit start/end dates per fold. |
| validation window | Later than training; used for calibration and model selection only. |
| test window | Later than validation; used for final diagnostics only. |
| random shuffle | Not acceptable as primary evidence. |
| per-date diagnostics | Required. |
| per-fold diagnostics | Required. |
| class balance | Required per fold and full candidate set. |
| regime sensitivity | Required as diagnostic, not alpha proof. |

## Calibration Diagnostics

Probability outputs require calibration diagnostics before display or release:

- Brier score
- log loss
- calibration curve by probability bucket
- expected calibration error
- maximum calibration error
- reliability table with observed frequency by bucket
- prediction coverage and invalid row count
- stability of calibration across folds and market regimes

Calibration diagnostics are quality controls. They must not be marketed as alpha
signals or trading recommendations.

## Backtest Strategy-Selection Boundary

Backtests for `v0.1n` are evaluation-only. They may answer whether a frozen
candidate recipe behaves poorly under a stated simulation rule, but they must
not silently become the recipe optimizer.

Allowed:

- simulate predeclared candidate selection rules, such as top probability
  bucket, top N, or probability threshold
- use a predeclared simulation contract for rebalance cadence, execution price,
  cost/slippage model, threshold freeze timestamp, universe snapshot, and tie
  handling
- report turnover, drawdown, hit rate, slippage sensitivity, and cost
  sensitivity
- compare frozen candidate recipes across out-of-sample windows
- reject a candidate for instability or leakage risk

Forbidden:

- feeding realized returns or PnL back into feature construction
- tuning the score formula, model, threshold, or strategy registry on the same
  test-period backtest result
- replacing calibration diagnostics with return metrics
- presenting output as buy/sell/hold advice
- claiming expected return or guaranteed superiority

### Required Simulation Contract Before Any Candidate Backtest

Before any `v0.1n` candidate simulation runs, a frozen simulation contract must
be written and reviewed. Without this contract, backtest work remains blocked.

Required contract fields:

| field | required rule |
| --- | --- |
| `simulation_contract_version` | Versioned before any run and never inferred from results. |
| `candidate_recipe_id` | Frozen candidate model/feature recipe being evaluated. |
| `registry_version` | Base strategy registry version used to build inputs. |
| `feature_table_version` | Composition feature table version. |
| `model_version` | Meta-model training recipe version. |
| `calibration_version` | Calibration recipe and calibration window identifier. |
| `universe_snapshot_id` | KOSPI200-only universe snapshot used for the run. |
| `decision_time_policy` | When candidate probabilities are considered available. |
| `execution_time_policy` | First allowed hypothetical execution time after decision. |
| `execution_price_policy` | Open, close, VWAP proxy, or other predeclared price rule. |
| `rebalance_cadence` | Daily, weekly, or other cadence fixed before the test window. |
| `selection_rule` | Top N, bucket, or threshold rule frozen before the test window. |
| `threshold_freeze_time` | Time before the test window when thresholds are fixed. |
| `tie_handling_policy` | Deterministic handling of equal probabilities. |
| `cost_model_id` | Transaction cost assumption identifier. |
| `slippage_model_id` | Slippage assumption identifier. |
| `position_sizing_policy` | Conservative sizing rule; not optimized on test returns. |
| `max_turnover_policy` | Optional cap fixed before the test window. |
| `missing_prediction_policy` | How invalid or missing predictions are handled. |
| `evaluation_window_id` | Out-of-sample window identifier. |
| `result_usage_policy` | Must state `evaluation_only_no_upstream_feedback`. |

The simulation contract must be created before the evaluation window is scored.
Changing it after viewing test-period results creates a data-snooping risk and
requires a new candidate recipe/version rather than an in-place edit.

## Implementation Approval Gates

This document resolves planning/design risk only. The following work remains
blocked until separately assigned in a post-MVP implementation scope:

| future artifact | current status | prerequisite |
| --- | --- | --- |
| `Quant_mvp/config/v0_1n_strategy_registry.toml` | proposed only | Root/master-approved implementation scope and registry schema review. |
| `Quant_mvp/docs/v0_1n_strategy_signal_schema.md` | optional split | Needed only if schema detail outgrows this design. |
| `Quant_mvp/docs/v0_1n_walk_forward_validation.md` | optional split | Needed before ML validation implementation. |
| `Quant_mvp/backtest_mvp/docs/v0_1n_strategy_selection_boundary.md` | optional split | Needed before candidate backtest implementation. |
| source helpers, tests, configs, model training | not authorized here | Separate role branch/worktree and validation plan. |

No implementation artifact may use `v0.2` naming as a frozen release line until
the freeze criteria above pass.

## Proposed Files

Create or update for this planning track:

| path | action | purpose |
| --- | --- | --- |
| `docs/extension/v0_1n_strategy_composition_v0_2_plan.md` | create | Root extension design and lifecycle boundary. |
| `docs/context/EXTENSION_REGISTRY.toml` | update | Route-only registry entry for `v0.1n_strategy_composition`. |
| `Quant_mvp/docs/next_horizon_up_probability_score_design.md` | update | Align existing candidate probability notes with `prob_up_1d_candidate` and adjusted-close label naming. |
| `Quant_mvp/config/v0_1n_strategy_registry.toml` | propose later | Candidate-only base strategy registry; not created until implementation scope is approved. |
| `Quant_mvp/docs/v0_1n_strategy_signal_schema.md` | propose later | Detailed schema split if this document grows too large. |
| `Quant_mvp/docs/v0_1n_walk_forward_validation.md` | propose later | Validation protocol split for ML/validation implementation. |
| `Quant_mvp/backtest_mvp/docs/v0_1n_strategy_selection_boundary.md` | propose later | Backtest-specific simulation boundary, if backtest work is assigned. |

## Validation And Guardrail Checklist

- [ ] Every candidate table carries `candidate_line = "v0.1n"`.
- [ ] Candidate status values use `v0.1n_candidate` until freeze.
- [ ] `v0.2` is not used until freeze criteria pass.
- [ ] Diagnostic-only strategy outputs have `model_input_allowed = false`.
- [ ] Candidate tables include lineage fields such as `run_id`,
      `registry_version`, `config_version`, and `input_data_snapshot_id`.
- [ ] MVP v0.1 score/ranking/backtest columns are not overwritten.
- [ ] `prob_up_1d_candidate` is documented as probability, not expected return.
- [ ] Label uses `adjusted_close[t+1] > adjusted_close[t]`.
- [ ] `decision_time`, `execution_time`, and `label_time` are separate.
- [ ] Feature cutoff is no later than `decision_time`.
- [ ] Labels and realized returns are absent from feature and model inputs.
- [ ] Walk-forward splits are date-ordered and out-of-sample.
- [ ] Calibration diagnostics are reported separately from alpha claims.
- [ ] Backtest results remain evaluation-only.
- [ ] No valuation/fundamental fields enter technical or final composite score.
- [ ] No new market, asset class, universe, or data source is activated.
