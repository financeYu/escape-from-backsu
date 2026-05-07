# v0.4 Selector Model Training Contract

Status: active v0.4 training gate contract.
Route: `docs/extension/v0_4_ml_selector_application_route.md`.

## Scope

This contract governs the first v0.4 baseline trainer. The trainer consumes the
v0.3 selector feature matrix and manifest, runs trainability checks, and fits a
logistic regression baseline only when the gate passes.

The trainer does not create trading signals, buy/sell recommendations, runtime
ranking activation, order generation, or production activation.

## Required Training Features

Only these feature columns may be used:

- `total_return`
- `excess_return_vs_proxy`
- `max_drawdown_abs`
- `sharpe`
- `turnover`
- `volatility`

All candidate identity, strategy family, signal family, OOS status, label,
status, reason, adoption, selector, prediction, and proxy columns remain audit
or exclusion columns.

## Required Gate Checks

The trainer must block before fitting when:

- candidate-level metric evidence count is zero
- positive row count is zero
- negative row count is zero
- training eligible row count is zero
- any required core feature is missing
- any label/status/reason/adoption/selector/prediction column appears inside
  the training feature values
- a generic proxy row is used as a supervised label
- required ML dependencies are unavailable

The trainer must not install dependencies. Missing `sklearn` must produce
`blocked_missing_ml_dependency`.

Class-distribution guards and dependency guards are separate. Positive and
negative labels can pass while the actual fit remains blocked by a missing ML
runtime dependency.

## Baseline Fit

When the gate passes, the trainer may fit
`LogisticRegression(class_weight="balanced", max_iter=1000)`. Model artifact
creation is allowed only after successful training.

The model output is evidence-only and may be consumed only by the v0.4 selector
score scaffold for `AdoptionCandidate` review prioritization.

High correlation between `total_return` and `excess_return_vs_proxy` is a
manifest warning, not a blocker. It must remain visible for audit because the
matrix is used for selector-rule replication and review-prioritization checks,
not for a future-performance prediction claim.

The frozen v0.4 baseline treats `limited_insufficient_training_rows` and
`high_feature_correlation_warning` as intentional diagnostic warnings. They
must be written to the relevant manifests when applicable. Limited training
rows require `performance_claim_allowed = false`; high feature correlation
limits coefficient interpretation to diagnostic-only review.

## Required Manifest Fields

The trainability manifest must include:

- `total_rows`
- `candidate_level_metric_count`
- `training_eligible_rows`
- `positive_rows`
- `negative_rows`
- `null_label_rows`
- `excluded_rows`
- `required_feature_columns`
- `missing_required_feature_rows`
- `leakage_excluded_columns`
- `feature_value_leak_rows`
- `bad_max_drawdown_abs_rows`
- `generic_proxy_bad_rows`
- `total_return_excess_return_correlation`
- `warnings`
- `performance_claim_allowed`
- `evaluation_mode`
- `leakage_check_manifest_path`
- `leakage_check_result`
- `feature_value_forbidden_columns_found`
- `has_ml_dependencies`
- `train_status`
- `train_blocked_reason`
- `model_artifact_created`
- `prediction_value_row_count`
- `readiness_status`

Allowed readiness values:

- `blocked_no_positive_negative_classes`
- `blocked_no_candidate_level_evidence`
- `blocked_missing_ml_dependency`
- `limited_insufficient_training_rows`
- `ready_for_logistic_regression_baseline`
- `trained_logistic_regression_baseline`
- `limited_ready_rule_only`
