# Feature Discrimination Audit

## Purpose

`feature_discrimination_audit` is an evidence-only contract for reviewing
candidate-level selector inputs before any ML selector behavior is changed. It
does not train a model, produce selector scores, change ranking behavior, alter
backtest semantics, activate valuation or fundamental scoring, or ingest new
data.

The audit asks three narrow questions for each candidate feature:

1. Does the feature have enough non-null candidate coverage?
2. Does the feature vary across candidates?
3. For numeric fields, is there a simple label mean difference between positive
   and negative review labels?

The result is a manifest with one row per feature and a conservative decision:
`keep`, `review`, `exclude`, or `diagnostic_only`.

## Readiness And Status Fields

Readiness and status fields such as `diagnostic_ready`,
`partial_diagnostic_ready`, `blocked_by_reconciliation`, and related flags are
useful review metadata, but they are weak ML inputs when they mostly describe
pipeline state instead of candidate-specific evidence magnitude.

These fields often have low variation, repeat across many candidates, or encode
whether an upstream artifact exists. They can help explain why a row is blocked
or incomplete, but they should not automatically become model features. The
contract therefore marks status features as `diagnostic_only`.

## Numeric Feature Review

Numeric features are evaluated with deterministic, model-free metrics:

- `non_null_ratio`: non-null values divided by total rows.
- `unique_count`: distinct non-null values across candidates.
- `positive_label_mean`: average feature value for label `1`.
- `negative_label_mean`: average feature value for label `0`.
- `label_mean_difference`: positive mean minus negative mean.
- `label_mean_abs_difference`: absolute label mean difference.

A numeric feature is marked `keep` only when it passes coverage, variation, and
minimum label-separation thresholds. A numeric feature with enough coverage and
variation but weak label separation is marked `review`, not rejected outright.

## Exclusions

The audit excludes:

- constant features
- high-null features
- label-derived columns
- post-label timing columns

Excluded features remain available for diagnostics. The manifest keeps
`diagnostic_available=true` for excluded rows so reviewers can inspect why the
feature was rejected without turning it into an ML input.

## Boundary

The manifest includes explicit false flags for:

- `ml_training_changed`
- `selector_ranking_changed`
- `backtest_behavior_changed`
- `valuation_activation_changed`
- `data_ingestion_changed`

These flags are part of the contract shape. If any flag is not false, manifest
validation fails.

## ML-Ready Candidate Features v2

`ml_ready_candidate_features_v2` is the filtered matrix that consumes the audit
manifest. It includes only features with `decision=keep`,
`ml_input_allowed=true`, finite numeric candidate values, and covered feature
lineage.

Status/readiness fields, sparse fields, constant fields, label-derived fields,
post-label fields, and review-only numeric fields remain in the v2 manifest as
excluded diagnostic metadata. They are not copied into `feature_values` or
`model_input_columns`.

The v2 trainability gate is fail-closed:

- missing `label_manifest_id` blocks ML-ready status
- any missing candidate label blocks ML-ready status
- missing lineage for an audit-passing feature blocks or downgrades the matrix
  to review-only
- insufficient candidate, positive-label, or negative-label coverage blocks
  ML-ready status

The v2 builder does not train or tune a selector, emit selector scores, change
ranking behavior, alter backtest behavior, activate valuation or fundamental
scoring, or ingest new data.

## Builder Runner

`Quant_mvp/scripts/build_ml_ready_candidate_features_v2.py` is the local runner
for connecting the v2 matrix inputs into one reproducible artifact set. It
reads:

- candidate rows
- a `feature_discrimination_audit` manifest
- a label manifest or explicit `label_manifest_id`
- a feature lineage manifest
- optional leakage findings

Dry-run mode builds the same in-memory artifact and trainability report without
writing files. Write mode emits:

- `ml_ready_candidate_features_v2.jsonl`
- `ml_ready_candidate_features_v2_manifest.json`
- `baseline_selector_trainability_v2_report.json`

The runner is intentionally a connector only. It preserves source artifact IDs,
feature lineage manifest IDs, and leakage finding counts in the output report,
but it does not train a selector or connect the matrix to ranking, reports, or
backtests.

## Baseline Selector Trainability v2

`baseline_selector_trainability_v2` consumes the
`ml_ready_candidate_features_v2` artifact before any baseline selector fitting
is allowed. It checks only whether the filtered matrix has enough input quality
for a later manual-review ML run.

The gate records:

- candidate count
- positive and negative label counts
- usable numeric feature count
- constant or near-constant feature ratio
- leakage finding count
- label manifest presence
- feature lineage manifest presence

Allowed statuses are:

- `trainable`
- `blocked_by_insufficient_features`
- `blocked_by_insufficient_labels`
- `blocked_by_leakage_risk`
- `blocked_by_lineage_gap`
- `review_only`

`trainable` means only that the v2 matrix passed the local input-quality gate.
It does not mean a strategy is adopted, does not support a performance claim,
does not change selector ranking behavior, and does not authorize production
use. The report keeps `model_training_performed=false` and
`ml_training_performed=false`; a separate explicitly approved task is required
before any selector training can run.
