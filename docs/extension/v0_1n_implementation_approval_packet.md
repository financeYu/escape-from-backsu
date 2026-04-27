# v0.1n Implementation Approval Preparation Packet

Status: planning/approval preparation only. This packet does not grant
implementation approval, does not freeze v0.2, and does not modify MVP v0.1
production behavior.

## Purpose

Define the narrow implementation scope that may be reviewed for a later
root/master approval decision. This packet is a checklist and routing artifact,
not an authorization to implement registry files, schemas, configs, source
helpers, tests, model training, reports, GUI display, or backtest code.

## Approval Scope Proposal

The next implementation scope may be considered only as `v0.1n_candidate`
work. It should be limited to:

1. Candidate-only base strategy registry draft under a separately approved
   Quant implementation branch.
2. Candidate-only schema constants or validators for base strategy signals,
   composition features, labels, prediction output, diagnostics, and lineage.
3. Candidate-only table builders that emit sidecar evaluation tables and never
   overwrite MVP v0.1 ranking/report/backtest outputs.
4. Candidate-only validation harness for date-ordered walk-forward split,
   calibration diagnostics, leakage checks, and reproducibility checks.
5. Candidate-only simulation contract document before any backtest run.

Approval must be explicit and must name the allowed files, branch/worktree,
validation commands, review gates, and generated-output boundary.

## Stage A Approval Candidate

Recommended next approval unit:

```text
stage_id = "v0.1n-stage-a-schema-registry-contract"
approval_status = "APPROVED_STAGE_A_DOC_CONTRACT_ONLY"
approval_source = "user explicit approval in current thread"
```

Purpose:

- freeze schema names, timing fields, lineage fields, and registry contract
  shape before any data-producing or model-training implementation begins
- keep the work reviewable without touching MVP v0.1 runtime behavior
- create a handoff that later implementation workers can follow without
  reopening score semantics

Approved Stage A write scope:

| path | proposed action | boundary |
| --- | --- | --- |
| `WORKSPACE_MANIFEST.md` | update | Narrow Stage A write manifest only. |
| `docs/extension/v0_1n_implementation_approval_packet.md` | update | Approval checklist refinement only. |
| `Quant_mvp/docs/v0_1n_strategy_signal_schema.md` | create | Contract document only, no runtime code. |
| `Quant_mvp/docs/v0_1n_strategy_registry_contract.md` | create | Registry contract document only, no production config activation. |
| `Quant_mvp/docs/next_horizon_up_probability_score_design.md` | update | Align naming/timing references only. |

Stage A forbidden scope:

- creating or editing production config files
- creating source helpers, table builders, validators, tests, model training,
  report builders, GUI display, or backtest code
- emitting generated candidate data, reports, caches, charts, or backtest
  outputs
- changing MVP v0.1 score, ranking, report, GUI, or backtest behavior

Stage A exit criteria:

- schema/timing/lineage documents list all required fields and blocked fields
- diagnostic-only fields are explicitly excluded from predictive model inputs
- `v0.1n_candidate` naming is used consistently
- `v0.2` remains future freeze-only language
- review/audit gate confirms no implementation or production activation

Stage A validation profile:

- `git diff --check`
- TOML parse for any changed TOML files
- verify no `src/`, `tests/`, `Quant_mvp/config/`, runtime, report, GUI, or
  backtest files changed
- targeted grep for production activation and forbidden claim language
- refresh cross-step review packet

Stage A decision options for root/master:

```text
APPROVE_STAGE_A_DOC_CONTRACT_ONLY
HOLD_STAGE_A
REJECT_STAGE_A
```

Current Stage A decision:

```text
stage_a_decision = "APPROVE_STAGE_A_DOC_CONTRACT_ONLY"
implementation_runtime_approval = false
```

## Explicitly Forbidden Implementation Scope

The next implementation approval must not include:

- changes to MVP v0.1 `technical_composite_score`, `final_composite_score`,
  ranking behavior, report behavior, GUI score behavior, or backtest behavior
- production config activation for `prob_up_1d_candidate`
- source helpers, model training, tests, registry, config, report, GUI, or
  backtest code unless the approval explicitly assigns that exact artifact
- KOSDAQ150, futures/options, overseas, multi-universe, or new market data
  source behavior
- valuation/fundamental/research data in final or ranking scores
- use of backtest output to tune score formula, model, registry, threshold, or
  ranking behavior
- trading recommendation, buy/sell/hold, proven-alpha, expected-return, or
  guaranteed-performance language
- treating calibration, turnover, hit rate, or regime diagnostics as alpha
  signals
- candidate backtests before simulation contract freeze

## Schema, Timing, And Lineage Freeze Checklist

Required before implementation approval:

- [ ] Every candidate table has `candidate_line = "v0.1n"`.
- [ ] Every candidate artifact uses `candidate_status = "v0.1n_candidate"`
      until a later freeze gate.
- [ ] Prediction output columns are fixed:
      `prob_up_1d_candidate`,
      `prob_up_1d_candidate_score_0_100`,
      `prediction_validity_flag`.
- [ ] Label column is fixed as `label_up_1d_candidate`.
- [ ] Label definition is fixed as
      `adjusted_close[t+1] > adjusted_close[t]`.
- [ ] Prediction/display tables are physically separate from label/evaluation
      tables.
- [ ] Feature/composition tables exclude label, future return, PnL, backtest
      result, valuation, and fundamental fields.
- [ ] Diagnostic-only strategy outputs have `model_input_allowed = false`.
- [ ] Required timing fields are present:
      `decision_time`, `execution_time`, `feature_cutoff_time`,
      `label_time`, `label_availability_time`, `prediction_time`.
- [ ] Required timing inequalities are testable:
      `feature_cutoff_time <= decision_time`,
      `decision_time <= execution_time`,
      `execution_time < label_availability_time`,
      `label_time <= label_availability_time`.
- [ ] Required lineage fields are present:
      `run_id`, `registry_version`, `config_version`,
      `input_data_snapshot_id`, `feature_table_version`,
      `model_version`, `calibration_method`, `training_window_id`.
- [ ] Candidate output records include `production_enabled = false` and
      `ranking_enabled = false`.

Blocking criteria:

- BLOCK if any future label, future OHLCV, realized return, PnL, backtest
  result, valuation, or fundamental field appears in feature/model inputs.
- BLOCK if any candidate artifact uses frozen `v0.2` release language before
  freeze criteria pass.
- BLOCK if output schemas can overwrite MVP v0.1 ranking, report, or backtest
  contracts.

## Candidate Backtest Simulation Contract Checklist

Required before any candidate backtest:

- [ ] `simulation_contract_version` is frozen before the evaluation window.
- [ ] `candidate_recipe_id`, `registry_version`, `feature_table_version`,
      `model_version`, and `calibration_version` are fixed.
- [ ] `universe_snapshot_id` is KOSPI200-only.
- [ ] `decision_time_policy`, `execution_time_policy`, and
      `execution_price_policy` are fixed.
- [ ] `rebalance_cadence` is fixed.
- [ ] `selection_rule` is fixed as a predeclared top-N, bucket, or threshold
      rule.
- [ ] `threshold_freeze_time` is before the evaluation window.
- [ ] `tie_handling_policy` is deterministic.
- [ ] `cost_model_id` and `slippage_model_id` are fixed.
- [ ] `position_sizing_policy`, `max_turnover_policy`, and
      `missing_prediction_policy` are fixed.
- [ ] `evaluation_window_id` is out-of-sample.
- [ ] `result_usage_policy = "evaluation_only_no_upstream_feedback"`.

Blocking criteria:

- BLOCK if a candidate backtest is run before this contract is frozen.
- BLOCK if test-period results change the same-period model, features,
  thresholds, registry, score formula, or selection rule in place.
- BLOCK if backtest results enter score, ranking, report, model-selection, or
  production configuration inputs.

## Model And Validation Readiness Checklist

Required before implementation approval:

- [ ] Primary split is date-ordered walk-forward.
- [ ] Random row shuffle is not primary evidence.
- [ ] Training, validation, calibration, and test windows are versioned.
- [ ] Test windows are out-of-sample and not used for feature selection,
      imputation fitting, calibration fitting, threshold setting, or model
      selection.
- [ ] Calibration diagnostics include Brier score, log loss, calibration curve,
      expected calibration error, maximum calibration error, and reliability
      table.
- [ ] Coverage diagnostics include missingness, invalid rows, warmup rows,
      class balance, and per-fold/per-date counts.
- [ ] Strategy diagnostics include turnover, bucket stability, regime
      sensitivity, and correlation with existing MVP technical composite only
      as diagnostics.
- [ ] First model family is inspectable, preferably regularized logistic
      regression over base strategy features.
- [ ] More complex models require feature importance, stability, calibration,
      and leakage review before remaining in scope.
- [ ] Probability display is blocked unless calibration passes review.

Blocking criteria:

- BLOCK if calibration is absent but output is named as probability.
- BLOCK if diagnostics are used as alpha proof or trading advice.
- BLOCK if validation evidence is pooled only and lacks per-fold or per-date
  diagnostics.

## Review And Audit Gate Risks

Required review gates before implementation approval:

- scope review against this packet and `WORKSPACE_MANIFEST.md`
- Quant local review for score semantics, schemas, and technical-only boundary
- scope/audit watchdog review when implementation paths are proposed
- review_mvp specialist review if code, tests, config, schemas,
  generated-output boundaries, cross-project handoffs, or backtest design are
  included in the proposed scope
- cross-step conflict checkpoint before any gate-critical handoff

Blocking risks:

- v0.1 regression risk: any overwrite of frozen MVP columns or behavior
- lookahead risk: future labels or availability ambiguity in feature inputs
- data-snooping risk: same-window backtest or test diagnostics tuning upstream
  artifacts
- claim hygiene risk: expected return, proven alpha, recommendation, or
  guaranteed-performance wording
- production activation risk: ranking, GUI, report, backtest, or config enable
  flags changing from false to true
- scope creep risk: new markets, new data sources, valuation/fundamental
  fields, or multi-universe behavior

## Approval Decision Rule

This packet can support later implementation decisions only if all checklists
are answered and all blocking criteria are either absent or explicitly
resolved. Stage A doc-contract work is approved, but runtime implementation is
not approved. The implementation approval status remains:

```text
implementation_approval_status = "HOLD"
```

No line in this packet should be read as implementation approval by itself.
