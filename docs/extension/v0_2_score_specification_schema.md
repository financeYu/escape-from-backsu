# v0.2 Score Specification Schema

Status: draft schema only. This document defines the fields required before a
candidate score may be considered for implementation approval. It does not
approve implementation, score adoption, ranking changes, report changes,
backtest feedback, valuation activation, or data-ingestion changes.

## Purpose

Every `v0.2` score candidate must have a complete specification before code
work starts. The schema keeps score intent, timing, normalization, lineage,
diagnostics, and review gates explicit so MVP v0.1 remains frozen until a
separately approved post-MVP Step opens implementation.

## Required Top-Level Fields

| field | required | allowed values / format | purpose |
| --- | --- | --- | --- |
| `schema_version` | yes | `v0.2-score-spec-draft-1` | Version of this candidate spec schema. |
| `candidate_id` | yes | stable snake_case identifier | Candidate score identifier. |
| `candidate_status` | yes | `draft_candidate`, `approved_for_implementation`, `implemented_candidate`, `technical_reviewed`, `adopted`, `rejected`, `blocked_by_data`, `out_of_scope` | Current lifecycle state. |
| `production_status` | yes | `not_activated`, `candidate_only`, `production_adopted` | Production activation state. Default must be `not_activated` or `candidate_only`. |
| `score_branch` | yes | `technical`, `diagnostic`, `out_of_scope` | Score branch classification. |
| `score_family` | yes | short controlled label | Family such as trend, breakout, flow, volatility, diagnostic. |
| `purpose` | yes | concise text | Technical purpose without recommendation language. |
| `owner_role` | yes | `Score Architect`, `Research Tester`, `Technical Selection Reviewer` | Responsible role for the current stage. |
| `review_required` | yes | list | Required reviews before state changes. |

## Candidate Definition Fields

Each candidate must define:

- `market_regime_where_it_helps`
- `raw_input_features`
- `raw_formula_design`
- `normalization_candidates`
- `minimum_history_needed`
- `expected_overlap_risk`
- `failure_modes`
- `data_requirements`
- `notes_on_interpretability`

The `raw_formula_design` field must be specific enough for implementation
review but must not be tuned after seeing evaluation results without a new
versioned review.

## Data And Lineage Fields

Required fields:

- `input_data_scope`: must name the approved data boundary, normally daily
  OHLCV-derived technical data.
- `source_lineage`: source tables or derived fields expected by the candidate.
- `feature_lineage`: how raw inputs become candidate features.
- `adjustment_policy`: adjusted close, split adjustment, and missing adjustment
  handling when relevant.
- `universe_scope`: default `KOSPI200_only`.
- `data_exclusions`: rows or symbols excluded before computation.
- `point_in_time_requirements`: must state `not_applicable` for technical-only
  candidates or route to valuation review if fundamentals are needed.

Forbidden in this schema unless a later approval opens the scope:

- new market data ingestion
- KOSDAQ150, futures/options, Nasdaq/overseas, or multi-universe activation
- valuation or fundamental data in technical or final composite scoring

## Timing And No-Lookahead Fields

Required fields:

- `decision_time_rule`
- `source_availability_time_rule`
- `feature_window_end_rule`
- `normalization_population_time_rule`
- `report_generation_time_rule`
- `evaluation_label_time_rule`
- `label_separation_rule`

Minimum constraints:

- Score inputs must be available at or before `decision_time_rule`.
- Cross-sectional normalization must use only the eligible same-date population
  available at the decision time.
- Time-series normalization must use only prior and current eligible values.
- Evaluation labels must not feed scoring, ranking, or adoption inputs.
- Rows with unresolved timing or availability ambiguity must be excluded or
  marked non-evaluable.

## Normalization Fields

Required fields:

- `raw_score_output`
- `cross_sectional_normalization`
- `time_series_normalization`
- `normalized_score_range`
- `missing_value_policy`
- `warmup_policy`
- `outlier_policy`
- `neutral_shrinkage_policy`
- `coverage_metric`

Normalization must be reviewable before implementation. Parameters such as
windows, thresholds, weights, toggles, and branch enablement should be
config-owned rather than hardcoded.

## Diagnostics Fields

Required fields:

- `nan_ratio_check`
- `warmup_coverage_check`
- `missing_data_behavior_check`
- `outlier_sensitivity_check`
- `rank_stability_check`
- `turnover_proxy_check`
- `score_correlation_check`
- `family_overlap_check`
- `data_quality_flags`

Diagnostics are not ranking signals by default. Any diagnostic promoted into a
ranking signal requires explicit adoption review.

## Output Boundary Fields

Required fields:

- `raw_output_columns`
- `normalized_output_columns`
- `diagnostic_output_columns`
- `generated_output_location`
- `source_control_policy`
- `reporting_boundary`
- `composite_handoff_boundary`

Generated outputs, runtime reports, caches, and local market data remain outside
source control unless a later review promotes small fixtures explicitly.

## Review Gate Fields

Required fields:

- `score_architect_verdict`
- `scope_watchdog_verdict`
- `research_tester_verdict`
- `technical_selection_verdict`
- `review_mvp_required`
- `cross_step_conflict_checkpoint`
- `master_up_summary_required`

No candidate can move to implementation until required gates are completed or a
root/master decision explicitly records the remaining risk.

## Minimal Draft Template

```yaml
schema_version: v0.2-score-spec-draft-1
candidate_id: example_candidate
candidate_status: draft_candidate
production_status: not_activated
score_branch: technical
score_family: example_family
purpose: "Technical purpose only; no recommendation language."
owner_role: Score Architect
review_required:
  - scope_watchdog
  - technical_selection_review
  - master_integration

candidate_definition:
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
  feature_lineage: unresolved
  adjustment_policy: unresolved
  universe_scope: KOSPI200_only
  data_exclusions: []
  point_in_time_requirements: not_applicable

timing:
  decision_time_rule: unresolved
  source_availability_time_rule: unresolved
  feature_window_end_rule: unresolved
  normalization_population_time_rule: unresolved
  report_generation_time_rule: unresolved
  evaluation_label_time_rule: evaluation_only
  label_separation_rule: labels_do_not_feed_scoring_or_ranking

normalization:
  raw_score_output: unresolved
  cross_sectional_normalization: unresolved
  time_series_normalization: unresolved
  normalized_score_range: 0_to_100_candidate
  missing_value_policy: unresolved
  warmup_policy: unresolved
  outlier_policy: unresolved
  neutral_shrinkage_policy: unresolved
  coverage_metric: unresolved

diagnostics:
  nan_ratio_check: required
  warmup_coverage_check: required
  missing_data_behavior_check: required
  outlier_sensitivity_check: required
  rank_stability_check: required
  turnover_proxy_check: required
  score_correlation_check: required
  family_overlap_check: required
  data_quality_flags: required

output_boundary:
  raw_output_columns: []
  normalized_output_columns: []
  diagnostic_output_columns: []
  generated_output_location: unresolved
  source_control_policy: generated_outputs_not_committed_by_default
  reporting_boundary: no_report_behavior_change_without_approval
  composite_handoff_boundary: no_composite_change_without_approval

review_gates:
  score_architect_verdict: pending
  scope_watchdog_verdict: pending
  research_tester_verdict: pending
  technical_selection_verdict: pending
  review_mvp_required: conditional
  cross_step_conflict_checkpoint: pending
  master_up_summary_required: true
```

## Current Approval State

`v0.2` score specification status: not approved for implementation.

This schema can be used to draft candidate specs, but it does not authorize
runtime code, score adoption, ranking changes, report changes, backtest feedback
loops, valuation activation, or data-ingestion changes.
