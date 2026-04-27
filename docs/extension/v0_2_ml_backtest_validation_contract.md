# v0.2 ML Backtest Validation Contract

## Purpose

이 계약은 candidate-only `prob_up_1d_candidate` ML artifact와
evaluation-only backtest 사이의 경계를 고정한다. Backtest는 모델의
out-of-sample prediction artifact를 평가할 수 있지만, 평가 결과를 scoring,
ranking, model features, production behavior로 되돌릴 수 없다.

## ML / Backtest Boundary

허용되는 architecture:

```text
feature_table
-> label_table separated
-> walk-forward / purged split
-> model training
-> calibration
-> out-of-sample prob_up_1d_candidate
-> candidate-only sidecar artifact
-> evaluation-only backtest report
```

Backtest evaluator 입력은 frozen out-of-sample `prob_up_1d_candidate`
sidecar artifact와 evaluation-only metadata로 제한한다.

Backtest evaluator 출력은 diagnostic report, validation table, audit note로만
남긴다. 출력은 `technical_composite_score`, `final_composite_score`,
production rank, production report order, model feature construction, model
selection automation을 변경하지 않는다.

## Contract Version And Ownership

- Contract id: `v0_2_ml_backtest_validation_contract`.
- Candidate output: `prob_up_1d_candidate`.
- Owner boundary: Quant candidate ML gate / research reference package.
- Backtest status: evaluation-only.
- Production activation: false.
- Score formula change: false.
- Report behavior change: false.
- Trading language: false.

Any future implementation packet must reference this contract and declare which
fields are implemented, stubbed, or blocked. Missing timing, split, calibration,
or overfitting controls are gate blockers, not TODOs that can be silently
resolved during model training.

## Out-Of-Sample Prediction Artifact Rule

`prob_up_1d_candidate` sidecar artifact는 fold별 out-of-sample 예측만 포함해야
한다.

필수 필드:

- `ticker`
- `date`
- `decision_time`
- `execution_time`
- `prob_up_1d_candidate`
- `prob_up_1d_candidate_status`
- `prob_up_1d_candidate_sample_role`
- `split_id`
- `model_family`
- `model_version`
- `feature_table_version`
- `label_table_version`
- `calibration_method`
- `prediction_generated_at`
- `feature_max_observation_time`
- `label_availability_time_for_evaluation`
- `training_window_id`
- `calibration_window_id`
- `sidecar_schema_version`

허용되지 않는 필드:

- inference-time feature row 안의 `up_1d_label`
- realized future return field
- backtest metric field
- production rank field
- `technical_composite_score`
- `final_composite_score`
- generated report, chart, cache, runtime output field

## Feature / Label Separation Rule

`feature_table`과 `label_table`은 물리적으로 또는 schema-level로 분리한다.

- Feature row는 `decision_time` 이전 또는 그 시점에 알려진 값만 가진다.
- Label row는 `label_time`, `label_availability_time`, `up_1d_label`을 가진다.
- Training join은 split construction 이후에만 허용한다.
- Inference artifact에는 label value가 들어가지 않는다.
- Evaluation join은 out-of-sample prediction artifact와 label table 사이에서만
  수행한다.

Required table lineage:

- `feature_table_version`
- `feature_source_snapshot_id`
- `feature_allowed_list_version`
- `label_table_version`
- `adjusted_close_source_id`
- `split_manifest_version`
- `processor_fit_manifest_version`

If any lineage field is missing, the run may remain a local diagnostic draft but
cannot close the candidate ML gate.

## Decision-Time-Only Feature Rule

모든 feature는 다음 조건을 만족해야 한다.

- `feature_observation_time <= decision_time`
- rolling indicator는 window end가 `decision_time`을 넘지 않는다.
- imputation, scaling, clipping, normalization parameter는 training fold 안에서만
  fit한다.
- validation/test/inference data는 fitted processor transform만 받는다.
- `label_time`, `label_availability_time`, realized outcome, backtest result는
  feature lineage에 들어가지 않는다.

## No-Lookahead Rule

금지:

- future price, future label, future membership, future corporate-action
  adjustment knowledge를 feature로 사용하는 것.
- label이 unavailable인 latest row를 optimistic fill하는 것.
- validation/test period 정보를 feature selection, imputation, scaler fit,
  calibration fit에 사용하는 것.
- backtest report 또는 generated output을 다음 training artifact 입력으로 쓰는 것.

필수 audit:

- `feature_max_observation_time`
- `decision_time`
- `label_time`
- `label_availability_time`
- `feature_time_violation_count`
- `label_leakage_violation_count`
- `processor_fit_scope`
- `feature_allowlist_violation_count`
- `future_membership_violation_count`
- `latest_unlabeled_row_count`

## Decision-Time Control Matrix

Each run must produce or validate a timing matrix with these relationships.

| Field | Required relationship | Gate action on violation |
| --- | --- | --- |
| `feature_observation_time` | `<= decision_time` | fail |
| `feature_processor_fit_end` | `<= train_end` or calibration-scope equivalent | fail |
| `decision_time` | `< label_availability_time` for labeled rows | fail |
| `execution_time` | `>= decision_time` | warning unless evaluation convention is invalid |
| `label_time` | after `decision_time` for `up_1d_label` | fail |
| `label_availability_time` | known only after `adjusted_close[t+1]` is available | fail |
| latest inference row | no label value, `candidate_unlabeled` status | fail if labeled optimistically |

## Label Availability Rule

`up_1d_label`은 `adjusted_close[t+1] > adjusted_close[t]`가 확인된 뒤에만
사용 가능하다.

- `label_time`은 `adjusted_close[t+1]`이 대표하는 timestamp다.
- `label_availability_time`은 해당 label을 알 수 있는 timestamp다.
- `label_availability_time`은 labeled training/evaluation row에서
  `decision_time`보다 늦어야 한다.
- latest unlabeled row는 training/evaluation label에서 제외하고
  `candidate_unlabeled`로 남긴다.
- `adjusted_close` canonical source가 확인되지 않으면 label construction은
  fail-fast로 멈춘다.

## Walk-Forward Split Contract

기본 split은 chronological walk-forward다.

필수 조건:

- random shuffle split을 time-dependent evaluation에 사용하지 않는다.
- train period는 validation/test period보다 앞선다.
- expanding window 또는 rolling window 중 하나를 config로 명시한다.
- 각 split은 `train_start`, `train_end`, `validation_start`,
  `validation_end`, `test_start`, `test_end`를 기록한다.
- model fit, feature processor fit, calibration fit은 각 split의 training 또는
  calibration sub-window 안에서만 수행한다.
- validation/test metric은 model selection evidence가 아니라 diagnostic field로
  기록한다.

Split manifest required fields:

- `split_id`
- `split_method`: `walk_forward_expanding` or `walk_forward_rolling`
- `train_start`
- `train_end`
- `calibration_start`
- `calibration_end`
- `validation_start`
- `validation_end`
- `test_start`
- `test_end`
- `embargo_start`
- `embargo_end`
- `purge_window`
- `embargo_window`
- `split_gap_days`
- `sample_role_counts`

Hyperparameter selection must use only the allowed training/validation scope
declared in the split manifest. Test/backtest output cannot choose the model
family, feature set, label variant, threshold, or calibration method.

## Purged / Embargo Rule

Label horizon이 겹치거나 feature/label window overlap이 생길 수 있으면 purge와
embargo를 적용한다.

필수 기록:

- `label_horizon`
- `purge_window`
- `embargo_window`
- `purged_training_row_count`
- `embargoed_row_count`
- `overlap_policy`
- `split_gap_days`

scikit-learn `TimeSeriesSplit(gap=...)`은 gap handling reference로 사용할 수
있지만, financial overlap label purging 전체를 자동으로 대체하지 않는다.
Purging logic은 label horizon과 label availability contract로 별도 검증한다.

## Calibration Metrics

Candidate probability는 classification accuracy만으로 판단하지 않는다.

필수 calibration 기록 후보:

- `brier_score`
- `log_loss`
- `calibration_curve_bins`
- `observed_positive_rate_by_bin`
- `mean_predicted_probability_by_bin`
- `calibration_method`: `none`, `sigmoid`, `isotonic`, `temperature_scaling`
- `calibration_fit_window`
- `calibration_sample_count`

Calibration model은 training fold 또는 별도 calibration sub-window에서만 fit한다.
Validation/test/inference labels로 calibration parameter를 fit하지 않는다.
Isotonic calibration은 small sample overfit risk를 `risk_notes`에 기록한다.

Calibration artifact required fields:

- `calibration_artifact_id`
- `calibration_method`
- `calibration_fit_scope`
- `calibration_fit_start`
- `calibration_fit_end`
- `calibration_sample_count`
- `calibration_positive_count`
- `pre_calibration_brier_score`
- `post_calibration_brier_score`
- `pre_calibration_log_loss`
- `post_calibration_log_loss`
- `calibration_curve_bin_count`
- `small_sample_warning`

Calibration improvement is diagnostic only. It does not activate production
ranking, trading language, or automatic model promotion.

## Overfitting Audit Fields

각 experiment/run은 다음 audit fields를 남긴다.

- `run_id`
- `split_id`
- `model_family`
- `model_version`
- `hyperparameter_source`
- `hyperparameter_trial_count`
- `feature_set_version`
- `label_version`
- `selection_metric`
- `selection_metric_scope`
- `selected_by_backtest_metric`: false by default
- `pbo_estimate`: null until project_validated
- `cscv_used`: false by default
- `deflated_metric_used`: false by default
- `data_snooping_warning`: true when multiple trials are compared
- `manual_review_required`

PBO, CSCV, Deflated Sharpe Ratio, Reality Check 계열 reference는 diagnostic
audit 설계 후보일 뿐이다. 이 값들은 production score나 rank에 들어가지 않는다.

## Multiple-Testing Warning Fields

다음 조건 중 하나라도 있으면 warning을 남긴다.

- multiple model families compared.
- multiple feature sets compared.
- multiple label variants compared.
- hyperparameter trials exceed configured threshold.
- selection metric chosen after seeing validation/test/backtest output.
- any evaluation result is reused as a training input candidate.

필수 warning fields:

- `model_family_count`
- `feature_set_count`
- `label_variant_count`
- `trial_count`
- `post_hoc_selection_risk`
- `selection_bias_risk`
- `data_snooping_risk`
- `backtest_feedback_risk`

Multiple-testing control fields:

- `experiment_registry_id`
- `predeclared_trial_budget`
- `actual_trial_count`
- `familywise_comparison_count`
- `feature_set_comparison_count`
- `label_variant_comparison_count`
- `metric_family_count`
- `selection_rule_predeclared`
- `holdout_reuse_count`
- `human_override_reason`

If the actual trial count exceeds the predeclared budget, set
`manual_review_required: true` and block gate closure until the excess search is
documented as exploratory rather than confirmatory.

## Forbidden Feedback Rule

다음 feedback은 금지한다.

- backtest metric as model feature.
- backtest metric as score weight.
- backtest metric as production ranking input.
- backtest metric as automatic model-selection trigger.
- evaluation report field as next training feature.
- candidate probability sidecar rank as production rank.
- research paper result as project validation.

Backtest evaluator may consume out-of-sample prediction artifacts. Backtest
evaluator must not produce upstream model features, score weights, ranking
changes, final composite changes, or production report changes.

## Candidate-Only Sidecar Rule

`prob_up_1d_candidate`는 sidecar candidate artifact다.

- Production ranking activation: false.
- `technical_composite_score` change: false.
- `final_composite_score` change: false.
- Production report order change: false.
- Trading claim: false.
- Expected-return claim: false.
- Buy/sell/hold recommendation: false.

Sidecar rank가 필요하면 `prob_up_1d_candidate_sidecar_rank`로만 기록하고,
production rank와 이름/경로/schema를 분리한다.

Future model families must enter through a reference manifest before training.
The manifest must state model family, intended feature set, label version,
calibration plan, trial budget, and forbidden downstream uses. Adding a model
family reference is not authorization to train, deploy, rank, or report it.

## Acceptance Checklist

Gate를 닫기 전 필요한 조건:

- feature_table과 label_table separation이 검증됨.
- canonical `adjusted_close` source가 확인됨.
- `decision_time`, `execution_time`, `label_time`,
  `label_availability_time`이 분리됨.
- walk-forward split이 chronological이며 shuffle이 없음.
- overlap label에는 purge/embargo/gap policy가 기록됨.
- calibration metrics가 fold 밖 label leakage 없이 계산됨.
- calibration artifact가 training/calibration scope 안에서만 fit됨.
- multiple-testing trial budget과 actual trial count가 기록됨.
- post-hoc model/feature/label selection risk가 warning 또는 blocker로 남음.
- backtest evaluator는 out-of-sample sidecar artifact만 읽음.
- backtest output이 scoring/ranking/model feature/production report로 feedback하지
  않는다는 grep/check가 통과됨.
- EvidenceCard 근거가 `full_text_reviewed` 또는 `project_validated`가 되기 전에는
  implementation gate decision을 닫지 않음.
- future model-family reference가 model training, API client, download script,
  ingestion expansion, score formula, production rank, report behavior, trading
  language를 활성화하지 않음.

## Review Status

이 문서는 research/contract artifact다. 코드 구현, model training,
production ranking activation, score formula 변경을 포함하지 않는다.
