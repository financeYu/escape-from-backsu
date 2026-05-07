# v0.4 Selector Model Manifest Contract

Status: active v0.4 model and score manifest contract.
Route: `docs/extension/v0_4_ml_selector_application_route.md`.

## Model Manifest

When a model is trained, the model manifest must record:

- `selector_model_version`
- `model_stage`
- `baseline_model`
- `model_type` or `model_family` as `logistic_regression`
- `model_library`
- `model_library_version`
- `training_feature_columns`
- `feature_columns`
- `feature_column_count`
- `training_row_count`
- `training_eligible_rows`
- `positive_rows`
- `negative_rows`
- `label_column` or `label_source`
- `class_weight`
- `max_iter`
- `random_state` or deterministic training metadata
- `model_artifact_path`
- `artifact_path`
- `trainability_manifest_path`
- `leakage_check_manifest_path`
- `coefficient_diagnostics_path`
- `has_ml_dependencies`
- `model_artifact_created`
- `warnings`
- `performance_claim_allowed`
- `evaluation_mode`
- `training_input_digest_sha256` or equivalent input digest
- `allowed_use`
- `prediction_claim`
- `trade_signal_claim`

If training is blocked, `model_artifact_created` must be `false`.

The absence of a pre-existing model artifact is not a trainability blocker. A
missing artifact only blocks ML scoring when no successful training run has
created one.

## Score Manifest

The scorer manifest must include:

- `selector_model_version`
- `selector_score_source`
- `scorer_version`
- `scored_candidate_count`
- `prediction_value_row_count`
- `model_artifact_path`
- `model_manifest_path`
- `trainability_manifest_path`
- `score_rows_path`
- `warnings`
- `fallback_used`
- `fallback_reason`
- `blocked_reason`
- `generated_at` or `generated_at_utc`
- `allowed_use`
- `trade_signal_claim`

Allowed selector score sources:

- `ml_model`
- `rule_only`
- `blocked_no_model_artifact`
- `blocked_train_status`

ML scores are review-prioritization scores only. They must not be described as
trading recommendations, expected return forecasts, or production activation
signals.

## Blocked States

When no model artifact exists, the scorer must not silently report `ml_model`.
It should report a rule baseline fallback, record `fallback_used = true`, and
keep `prediction_value_row_count = 0` unless a valid ML model is loaded.

When the training manifest has a blocked train status, the scorer must keep
`prediction_value_row_count = 0`.

When the model manifest and model artifact disagree on model version, model
family/type, feature columns, training row count, dependency status, or artifact
path, the scorer must fail closed or record a warning plus fallback. It must
not emit `selector_score_source = ml_model` for mismatched artifacts.

## Warning Policy

The frozen v0.4 LogisticRegression baseline has two known diagnostic warnings:

- `limited_insufficient_training_rows`
- `high_feature_correlation_warning`

These warnings are not failures, but they must not disappear silently.
`limited_insufficient_training_rows` requires
`performance_claim_allowed = false`. `high_feature_correlation_warning` limits
coefficient interpretation to diagnostics.

## v0.4.1 Diagnostic Ranking Manifest

The v0.4.1 ranking manifest compares model scores across the same candidate
set for diagnostics only. It must include:

- `evaluation_mode = diagnostic_ranking_only`
- `baseline_model_id`
- `compared_model_ids`
- `candidate_count`
- `per_model_score_available_count`
- `ranking_schema_version`
- `selector_score_source_unchanged = true`
- `performance_claim_allowed = false`
- `trading_signal_allowed = false`

Ranking rows may expose model-specific score, rank, availability, and
baseline-relative delta fields. The baseline-relative reference remains the
frozen LogisticRegression baseline. RandomForest remains
`nonlinear_challenger` only and must not replace the baseline selector score
source.

The ranking manifest may be linked from AdoptionCandidate review packets only
as a diagnostic reference. It must not change selector scores, selector ranks,
review packet ordering, adoption decisions, trading behavior, or production
activation state.
