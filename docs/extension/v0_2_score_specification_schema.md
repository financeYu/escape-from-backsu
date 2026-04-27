# v0.2 Score Specification Schema

Status: approved schema contract for the post-MVP `v0.2 predictive probability
score route` contract-freeze Step. This document defines the fields required
before `prob_up_1d_candidate` may be considered for implementation approval. It
does not approve candidate-specific implementation, production ranking,
backtest feedback, valuation activation, or data-ingestion changes.

## Purpose

The `v0.2` predictive candidate and its old-score feature inputs must have a
complete specification before code work starts. The schema keeps probability
target, label timing, model-input lineage, normalization/calibration,
diagnostics, and review gates explicit so MVP v0.1 remains frozen until a
separately approved post-MVP implementation gate opens.

## Required Top-Level Fields

| field | required | allowed values / format | purpose |
| --- | --- | --- | --- |
| `schema_version` | yes | `v0.2-score-spec-draft-1` | Version of this candidate spec schema. |
| `candidate_id` | yes | stable snake_case identifier | Candidate score identifier. |
| `candidate_status` | yes | `active_predictive_candidate`, `old_score_feature`, `diagnostic_old_score_feature`, `approved_for_implementation`, `implemented_candidate`, `technical_reviewed`, `adopted`, `rejected`, `blocked_by_data`, `out_of_scope` | Current lifecycle state. |
| `production_status` | yes | `not_activated`, `candidate_only`, `production_adopted` | Production activation state. Default must be `not_activated` or `candidate_only`. |
| `score_branch` | yes | `predictive_probability`, `old_score_feature`, `diagnostic_old_score_feature`, `out_of_scope` | Branch classification. |
| `score_family` | yes | short controlled label | Family such as supervised probability, old technical score, diagnostic. |
| `purpose` | yes | concise text | Candidate purpose without recommendation language. |
| `owner_role` | yes | `Score Architect`, `Research Tester`, `Technical Selection Reviewer` | Responsible role for the current stage. |
| `review_required` | yes | list | Required reviews before state changes. |
| `freeze_prerequisites` | yes | mapping | Freeze status for schema, lineage, boundary, config, validation, and rollback contracts. |

## Candidate Definition Fields

Each candidate must define:

- `prediction_target` for `predictive_probability` candidates
- `label_definition` for supervised probability candidates
- `market_regime_where_it_helps`
- `raw_input_features`
- `raw_formula_design`
- `normalization_candidates`
- `minimum_history_needed`
- `expected_overlap_risk`
- `failure_modes`
- `data_requirements`
- `notes_on_interpretability`

The `raw_formula_design` or model-design field must be specific enough for
implementation review but must not be tuned after seeing evaluation results
without a new versioned research protocol.

## Data And Lineage Fields

Required fields:

- `input_data_scope`: must name the approved data boundary, normally daily
  OHLCV-derived technical data.
- `source_lineage`: source tables or derived fields expected by the candidate.
- `raw_feature_lineage`: exact mapping from approved raw inputs to raw candidate
  features, including source availability timing and exclusion rules.
- `feature_lineage`: how raw inputs become candidate features.
- `adjustment_policy`: adjusted close, split adjustment, and missing adjustment
  handling when relevant.
- `universe_scope`: default `KOSPI200_only`.
- `data_exclusions`: rows or symbols excluded before computation.
- `point_in_time_requirements`: must state `not_applicable` for technical-only
  candidates or route to valuation review if fundamentals are needed.
- `model_input_boundary`: approved feature families for predictive candidates.
- `label_lineage`: label construction path for supervised probability
  candidates.

Forbidden in this schema:

- new market data ingestion
- KOSDAQ150, futures/options, Nasdaq/overseas, or multi-universe activation
- valuation or fundamental data in `technical_composite_score`
- valuation or fundamental data in `final_composite_score` in this draft; any
  later valuation-aware final-composite route requires separate versioned
  approval, point-in-time availability proof, and updated contracts

## Timing And No-Lookahead Fields

Required fields:

- `decision_time_rule`
- `decision_time_field`
- `source_availability_time_rule`
- `source_data_availability_time_field`
- `feature_window_end_rule`
- `feature_construction_time_rule`
- `normalization_population_time_rule`
- `report_generation_time_rule`
- `evaluation_label_time_rule`
- `label_separation_rule`
- `train_validation_test_split_rule`
- `model_training_cutoff_rule`

Minimum constraints:

- A candidate implementation request is incomplete until every required timing
  field has a concrete rule or an explicit non-evaluable exclusion rule.
- Score inputs must be available at or before `decision_time_rule`; information
  after the decision time must not be used as score input.
- Cross-sectional normalization must use only the eligible same-date population
  available at the decision time.
- Time-series normalization must use only prior and current eligible values.
- Evaluation labels must not feed scoring, ranking, normalization,
  report-generation, or adoption inputs.
- Backtest result metrics must not feed model feature construction.
- Model training must respect the documented training cutoff and split rule.
- Rows with unresolved timing or availability ambiguity must be excluded or
  marked non-evaluable.

## Normalization Fields

Required fields:

- `raw_score_output` or `raw_probability_output`
- `raw_score_output_schema`
- `normalized_score_output_schema`
- `normalized_score_lineage`
- `cross_sectional_normalization`
- `cross_sectional_normalization_rules`
- `time_series_normalization`
- `time_series_normalization_rules`
- `normalized_score_range`
- `missing_value_policy`
- `warmup_policy`
- `insufficient_history_policy`
- `outlier_policy`
- `neutral_shrinkage_policy`
- `coverage_metric`
- `calibration_policy` for predictive probability candidates
- `probability_score_range` for predictive probability candidates

Normalization must be reviewable before implementation. Parameters such as
windows, thresholds, weights, toggles, and branch enablement should be
config-owned rather than hardcoded.

For `prob_up_1d_candidate`, the approved candidate output semantics are:

- `prob_up_1d_candidate`: probability-like value in `[0, 1]`
- `prob_up_1d_score`: optional `0-100` presentation of
  `prob_up_1d_candidate`
- higher values mean higher model-estimated probability of `up_1d_label`
- output remains candidate-only until validation and adoption gates pass

## Config Ownership Fields

Required fields:

- `config_artifact_path`
- `window_config_owner`
- `threshold_config_owner`
- `weight_config_owner`
- `toggle_config_owner`
- `branch_config_owner`
- `default_config_values`
- `config_change_review_rule`

Windows, thresholds, weights, toggles, and branch enablement must have a
recorded owner role and review rule before implementation approval. Code must
not silently replace these contracts with hardcoded production behavior.

## Diagnostics Fields

Required fields:

- `coverage_diagnostics`
- `nan_ratio_check`
- `warmup_coverage_check`
- `missing_data_behavior_check`
- `outlier_sensitivity_check`
- `rank_stability_check`
- `turnover_proxy_check`
- `score_correlation_redundancy_check`
- `score_correlation_check`
- `family_overlap_check`
- `rank_overlap_check`
- `data_quality_flags`

Diagnostics are not ranking signals by default. Any diagnostic promoted into a
ranking signal requires explicit adoption review.

## Research Tester Plan Fields

Before implementation approval, each candidate spec must include a Research
Tester plan with:

- `raw_score_output_schema`: raw output columns, units, directionality,
  invalid-state representation, and row timing fields.
- `normalized_score_output_schema`: normalized columns, range, orientation,
  neutral shrinkage behavior, and data-quality flags.
- `cross_sectional_normalization_rules`: same-date eligible population,
  exclusions, minimum population size, tie handling, and missing-value rule.
- `time_series_normalization_rules`: per-symbol lookback window, rolling method,
  warmup rule, and current/prior-only data rule.
- `nan_warmup_insufficient_history_policy`: explicit behavior for NaN, warmup,
  and insufficient-history rows.
- `outlier_policy`: clipping, winsorization, robust scaling, exclusion, or
  diagnostic-only handling for extreme price, range, and volume observations.
- `coverage_diagnostics`: per-symbol and per-date valid-row ratios, warmup
  coverage, and missing-input counts.
- `rank_stability_diagnostics`: rank movement, rolling rank stability, and
  missing-component sensitivity.
- `turnover_proxy_diagnostics`: rank-change or top-bucket membership-change
  proxy for review only.
- `score_correlation_redundancy_diagnostics`: score-to-score correlation,
  family overlap, rank overlap, and redundancy flags.
- `generated_output_boundary`: generated path, source-control exclusion rule,
  fixture promotion rule, and cleanup responsibility.

The Research Tester plan must not use evaluation labels, backtest outputs, or
future information to redefine candidate formulas, normalization choices, or
ranking use.

## Output Boundary Fields

Required fields:

- `raw_output_columns`
- `normalized_output_columns`
- `diagnostic_output_columns`
- `diagnostic_output_schema`
- `generated_output_location`
- `source_control_policy`
- `reporting_boundary`
- `composite_handoff_boundary`

Generated outputs, runtime reports, caches, and local market data remain outside
source control unless a later review promotes small fixtures explicitly.

## Backtest And Evaluation Boundary Fields

Required fields when any backtest, simulation, or evaluation report is produced:

- `evaluation_only_status`
- `no_feedback_to_scoring`
- `no_parameter_optimization_feedback`
- `candidate_only_report_status`
- `data_window`
- `eligibility_rules`
- `timing_assumptions`
- `leakage_check`
- `limitations`
- `generated_output_boundary`
- `no_result_only_adoption`

Backtest and simulation output must not change score formulas, input features,
normalization, weights, score branches, composite membership, ranking behavior,
or adoption state by itself. Evaluation results are evidence for review, not an
approval mechanism.

## Freeze Prerequisite Fields

Required fields:

- `freeze_status`
- `score_specification_schema_contract`
- `raw_feature_lineage_contract`
- `normalized_score_lineage_contract`
- `composite_handoff_boundary_contract`
- `diagnostic_output_schema_contract`
- `generated_output_source_control_policy_contract`
- `config_ownership_contract`
- `validation_profile_required_tests_contract`
- `rollback_deactivation_rule_contract`
- `freeze_change_trigger`

Allowed `freeze_status` values:

- `not_frozen`
- `frozen`
- `superseded`

Each contract must include:

- `status`
- `version`
- `owner_role`
- `artifact_path`
- `required_fields`
- `validation_checks`
- `approval_reference`
- `change_review_required`

Implementation approval must be blocked while any required freeze contract is
`not_frozen`. A frozen contract can be changed only by creating a new versioned
approval review.

## Review Gate Fields

Required fields:

- `score_architect_verdict`
- `schema_lineage_freeze_verdict`
- `scope_watchdog_verdict`
- `research_tester_verdict`
- `technical_selection_verdict`
- `technical_relevance`
- `technical_distinctiveness`
- `technical_stability`
- `technical_complexity_cost`
- `regime_fit`
- `redundancy_risk`
- `implementation_clarity`
- `data_sufficiency`
- `final_candidate_state`
- `review_mvp_required`
- `cross_step_conflict_checkpoint`
- `master_up_summary_required`

No candidate can move to implementation until required gates are completed or a
root/master decision explicitly records the remaining risk.

Allowed `final_candidate_state` values:

- `core_adopted`
- `conditional_adopted`
- `technical_only`
- `regime_only`
- `diagnostic_only`
- `research_only`
- `rejected`
- `blocked_by_data`

These states can be assigned only after implementation diagnostics and
Technical Selection Review are complete. A draft specification must use
`pending`.

## Minimal Draft Template

```yaml
schema_version: v0.2-score-spec-draft-1
candidate_id: prob_up_1d_candidate
candidate_status: active_predictive_candidate
production_status: not_activated
score_branch: predictive_probability
score_family: supervised_probability
purpose: "Candidate one-day adjusted-close up probability; no recommendation language."
owner_role: Score Architect
review_required:
  - schema_lineage_freeze_review
  - scope_watchdog
  - technical_selection_review
  - master_integration

candidate_definition:
  prediction_target: adjusted_close_next_trading_day_greater_than_current_adjusted_close
  label_definition: up_1d_label
  market_regime_where_it_helps: unknown_until_review
  raw_input_features: []
  raw_formula_design: unresolved
  normalization_candidates: []
  minimum_history_needed: unresolved
  expected_overlap_risk: unresolved
  failure_modes: []
  data_requirements: daily_ohlcv_only
  notes_on_interpretability: unresolved

data_and_lineage:
  input_data_scope: daily_ohlcv_technical_only
  source_lineage: []
  raw_feature_lineage: unresolved
  feature_lineage: unresolved
  adjustment_policy: unresolved
  universe_scope: KOSPI200_only
  data_exclusions: []
  point_in_time_requirements: not_applicable
  model_input_boundary: old_score_features_only_until_review
  label_lineage: docs/extension/v0_2_prob_up_1d_label_contract.md

timing:
  decision_time_rule: unresolved
  decision_time_field: unresolved
  source_availability_time_rule: unresolved
  source_data_availability_time_field: unresolved
  feature_window_end_rule: unresolved
  feature_construction_time_rule: unresolved
  normalization_population_time_rule: unresolved
  report_generation_time_rule: unresolved
  evaluation_label_time_rule: evaluation_only
  label_separation_rule: labels_do_not_feed_scoring_or_ranking
  train_validation_test_split_rule: unresolved
  model_training_cutoff_rule: unresolved

normalization:
  raw_score_output: unresolved
  raw_probability_output: prob_up_1d_candidate
  raw_score_output_schema: []
  normalized_score_output_schema: []
  normalized_score_lineage: unresolved
  cross_sectional_normalization: unresolved
  cross_sectional_normalization_rules: unresolved
  time_series_normalization: unresolved
  time_series_normalization_rules: unresolved
  normalized_score_range: 0_to_100_candidate
  missing_value_policy: unresolved
  warmup_policy: unresolved
  insufficient_history_policy: unresolved
  outlier_policy: unresolved
  neutral_shrinkage_policy: unresolved
  coverage_metric: unresolved
  calibration_policy: unresolved
  probability_score_range: 0_to_1_probability_candidate_and_optional_0_to_100_score

config_ownership:
  config_artifact_path: unresolved
  window_config_owner: unresolved
  threshold_config_owner: unresolved
  weight_config_owner: unresolved
  toggle_config_owner: unresolved
  branch_config_owner: unresolved
  default_config_values: unresolved
  config_change_review_rule: unresolved

diagnostics:
  coverage_diagnostics: required
  nan_ratio_check: required
  warmup_coverage_check: required
  missing_data_behavior_check: required
  outlier_sensitivity_check: required
  rank_stability_check: required
  turnover_proxy_check: required
  score_correlation_redundancy_check: required
  score_correlation_check: required
  family_overlap_check: required
  rank_overlap_check: required
  data_quality_flags: required

research_tester_plan:
  raw_score_output_schema: []
  normalized_score_output_schema: []
  cross_sectional_normalization_rules: unresolved
  time_series_normalization_rules: unresolved
  nan_warmup_insufficient_history_policy: unresolved
  outlier_policy: unresolved
  coverage_diagnostics: required
  rank_stability_diagnostics: required
  turnover_proxy_diagnostics: required
  score_correlation_redundancy_diagnostics: required
  generated_output_boundary: unresolved

output_boundary:
  raw_output_columns: []
  normalized_output_columns: []
  diagnostic_output_columns: []
  diagnostic_output_schema: []
  generated_output_location: unresolved
  source_control_policy: generated_outputs_not_committed_by_default
  reporting_boundary: no_report_behavior_change_without_approval
  composite_handoff_boundary: no_composite_change_without_approval

backtest_evaluation_boundary:
  evaluation_only_status: required
  no_feedback_to_scoring: required
  no_parameter_optimization_feedback: required
  candidate_only_report_status: required
  data_window: unresolved
  eligibility_rules: unresolved
  timing_assumptions: unresolved
  leakage_check: required
  limitations: required
  generated_output_boundary: unresolved
  no_result_only_adoption: required

freeze_prerequisites:
  freeze_status: not_frozen
  score_specification_schema_contract:
    status: not_frozen
    version: unresolved
    owner_role: Score Architect
    artifact_path: unresolved
    required_fields: []
    validation_checks: []
    approval_reference: unresolved
    change_review_required: true
  raw_feature_lineage_contract:
    status: not_frozen
    version: unresolved
    owner_role: Score Architect
    artifact_path: unresolved
    required_fields: []
    validation_checks: []
    approval_reference: unresolved
    change_review_required: true
  normalized_score_lineage_contract:
    status: not_frozen
    version: unresolved
    owner_role: Research Tester
    artifact_path: unresolved
    required_fields: []
    validation_checks: []
    approval_reference: unresolved
    change_review_required: true
  composite_handoff_boundary_contract:
    status: not_frozen
    version: unresolved
    owner_role: Technical Selection Reviewer
    artifact_path: unresolved
    required_fields: []
    validation_checks: []
    approval_reference: unresolved
    change_review_required: true
  diagnostic_output_schema_contract:
    status: not_frozen
    version: unresolved
    owner_role: Research Tester
    artifact_path: unresolved
    required_fields: []
    validation_checks: []
    approval_reference: unresolved
    change_review_required: true
  generated_output_source_control_policy_contract:
    status: not_frozen
    version: unresolved
    owner_role: master_integration
    artifact_path: unresolved
    required_fields: []
    validation_checks: []
    approval_reference: unresolved
    change_review_required: true
  config_ownership_contract:
    status: not_frozen
    version: unresolved
    owner_role: Score Architect
    artifact_path: unresolved
    required_fields: []
    validation_checks: []
    approval_reference: unresolved
    change_review_required: true
  validation_profile_required_tests_contract:
    status: not_frozen
    version: unresolved
    owner_role: Research Tester
    artifact_path: unresolved
    required_fields: []
    validation_checks: []
    approval_reference: unresolved
    change_review_required: true
  rollback_deactivation_rule_contract:
    status: not_frozen
    version: unresolved
    owner_role: master_integration
    artifact_path: unresolved
    required_fields: []
    validation_checks: []
    approval_reference: unresolved
    change_review_required: true
  freeze_change_trigger: new_review_required_for_semantic_lineage_config_validation_or_rollback_change

review_gates:
  score_architect_verdict: pending
  schema_lineage_freeze_verdict: pending
  scope_watchdog_verdict: pending
  research_tester_verdict: pending
  technical_selection_verdict: pending
  technical_relevance: pending
  technical_distinctiveness: pending
  technical_stability: pending
  technical_complexity_cost: pending
  regime_fit: pending
  redundancy_risk: pending
  implementation_clarity: pending
  data_sufficiency: pending
  final_candidate_state: pending
  review_mvp_required: conditional
  cross_step_conflict_checkpoint: pending
  master_up_summary_required: true
```

## Current Approval State

`v0.2` predictive probability specification schema status: approved for
candidate specification authoring.

This schema can be used to freeze candidate specs, but it does not authorize
runtime code, score adoption, ranking changes, report changes, backtest feedback
loops, valuation activation, or data-ingestion changes.
