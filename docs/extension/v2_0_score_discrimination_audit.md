# v2.0 Score Discrimination Audit

Status: diagnostic layer for manual-review evidence support.
Owner lane: root governance plus ML/evaluator review.

## Purpose

This audit diagnoses why v0.4 selector scores or v1.6 review-priority scores
may have weak discrimination across candidates. It reads existing score rows or
manifests and emits a small diagnostic JSON report for manual review.

The audit does not change score semantics, production ranking,
`final_composite_score`, `technical_composite_score`, backtest behavior, route
status, valuation or fundamental scoring activation, or any automated action
layer.

## Implementation

- Script: `scripts/audit_review_priority_score_discrimination.py`
- Focused test: `tests/selector/test_score_discrimination_audit.py`
- Fixture directory: `tests/fixtures/score_discrimination/`
- Suggested generated report name: `score_discrimination_summary.json`

Generated runtime reports should stay local unless a later review explicitly
promotes a small sample fixture. Source-controlled coverage uses only small
fixtures under `tests/fixtures/score_discrimination/`.

## Inputs

Supported input shapes:

- JSONL score rows such as v0.4 selector score rows.
- CSV review-priority outputs such as v1.6 confidence or composite diagnostics.
- JSON row lists.
- JSON manifests with `candidate_review_priorities`, `rows`, `score_rows`, or
  `score_rows_path`.

The script may infer common score columns such as `review_priority_score`,
`selector_score`, `confidence_score`, `manual_review_priority_score`, or
`diagnostic_tiebreak_score`. A caller can pass an explicit score column when a
file contains more than one candidate score-like field.

## Metrics

The report includes:

- `record_count`
- `score_column`
- `n_unique_scores`
- `effective_unique_score_count`
- `max_tie_group_size`
- `max_tie_group_share`
- `zero_score_share`
- `null_score_share`
- `status_bucket_counts`
- `score_entropy`
- `component_missing_share`
- `component_variance`
- `top_tie_groups`
- `deterministic_sort_fields`

`zero_score_share` and `null_score_share` are separate so missing evidence is
not silently treated as a numeric zero. Component diagnostics preserve missing
coverage as a root-cause signal instead of changing any upstream formula.

## Root-Cause Candidates

The audit can flag these diagnostic candidates:

- `missing_components_collapsed_to_zero`
- `binary_probability_output`
- `insufficient_feature_variance`
- `deterministic_string_tiebreak_only`
- `status_bucket_too_coarse`
- `label_or_feature_matrix_too_sparse`

These are review hypotheses only. They do not authorize weight changes,
formula changes, or production behavior changes.

## Example

```powershell
.venv\Scripts\python.exe scripts\audit_review_priority_score_discrimination.py `
  --input Quant_mvp\data\v0_4\selector_scores\v0_4_selector_scores.jsonl `
  --output .pytest_tmp\score_discrimination_summary.json `
  --score-column selector_score `
  --component-columns coverage,data_quality,stability `
  --sort-fields selector_score,candidate_id
```

The output path above is intentionally local scratch space. Keep generated
reports out of source control by default.
