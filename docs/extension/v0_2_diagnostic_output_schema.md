# v0.2 Diagnostic Output Schema

Status: frozen diagnostic output schema for the post-MVP `v0.2 predictive
probability score route`. This schema does not approve runtime implementation.

## Required Diagnostic Families

- feature coverage and missingness
- warmup and insufficient-history flags
- old-score feature stability
- model-input leakage checks
- label availability checks
- probability calibration diagnostics
- baseline comparison diagnostics
- rank-stability diagnostics for review-only candidate ordering

## Allowed Diagnostic Outputs

- `feature_coverage_ratio`
- `missing_feature_count`
- `warmup_validity_flag`
- `label_availability_flag`
- `leakage_check_status`
- `calibration_bucket`
- `calibration_observed_rate`
- `calibration_predicted_mean`
- `brier_score`
- `auc_diagnostic`
- `baseline_comparison_metric`
- `candidate_probability_rank_stability`

## Boundary Rules

- Diagnostics are review artifacts, not production ranking signals.
- Diagnostics must not be described as alpha evidence or trading utility.
- Backtest and evaluation metrics must remain outside model-input tables.
- Any diagnostic promoted into production behavior requires a later adoption
  review and contract version bump.
