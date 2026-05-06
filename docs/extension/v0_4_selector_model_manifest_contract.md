# v0.4 Selector Model Manifest Contract

Status: active v0.4 model and score manifest contract.
Route: `docs/extension/v0_4_ml_selector_application_route.md`.

## Model Manifest

When a model is trained, the model manifest must record:

- `selector_model_version`
- `model_stage`
- `baseline_model`
- `training_feature_columns`
- `training_eligible_rows`
- `positive_rows`
- `negative_rows`
- `class_weight`
- `max_iter`
- `model_artifact_path`
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
- `scored_candidate_count`
- `prediction_value_row_count`
- `blocked_reason`
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

When no model artifact exists, the scorer must not fail the route. It should
report `blocked_no_model_artifact` or `rule_only_available` and keep
`prediction_value_row_count = 0` unless a valid ML model is loaded.

When the training manifest has a blocked train status, the scorer must keep
`prediction_value_row_count = 0`.
