# Primary Score Migration Contract

## Purpose

This contract defines the exception-managed migration path from the MVP v0.1
technical composite score to the post-MVP up-probability candidate score.

The migration goal is to avoid two active score meanings in GUI, ranking, and
report surfaces. The old MVP score is preserved as archived legacy context, and
the new score becomes the designated primary candidate after required
validation and review.

This contract does not perform the production cutover.

## Score Roles

| role | column | status | note |
| --- | --- | --- | --- |
| `old_score` | `legacy_final_composite_score` | `archived_legacy_reference` | Archive alias for the MVP v0.1 `final_composite_score`. |
| `old_technical_score` | `legacy_technical_composite_score` | `archived_legacy_reference` | Archive alias for the MVP v0.1 `technical_composite_score`. |
| `primary_score` | `next_horizon_up_probability_score` | `primary_candidate_pending_validation` | New post-MVP candidate score with default `horizon_trading_days = 1`. |

The old aliases are namespaced archive columns. They must not be used as active
fallback ranking columns after cutover. Before cutover, they remain available
only for audit, comparison, rollback analysis, and historical explanation.

## Required Config Flags

The migration is controlled from `Quant_mvp/config/up_probability.toml`:

```text
primary_score_column = "next_horizon_up_probability_score"
legacy_score_archive_columns = [
  "legacy_technical_composite_score",
  "legacy_final_composite_score",
]
primary_score_runtime_cutover_enabled = false
legacy_score_runtime_fallback_enabled = false
```

`primary_score_runtime_cutover_enabled` must remain `false` until validation,
technical review, adoption review, and master integration approval are
complete.

## Cutover Preconditions

All of the following are required before runtime surfaces can use
`next_horizon_up_probability_score` as the active score:

1. A calibrated probability model exists for `horizon_trading_days = 1`.
2. Walk-forward validation is complete.
3. Calibration diagnostics are reviewed.
4. Leakage guardrails pass.
5. The output frame includes `candidate_validity_flag`.
6. `technical_composite_score` and `final_composite_score` are copied to legacy
   archive aliases instead of being overwritten.
7. GUI and ranking code read exactly one active `primary_score_column`.
8. `legacy_score_runtime_fallback_enabled` remains `false` unless a separate
   rollback plan is approved.

## Forbidden During Migration

- Do not silently redefine `technical_composite_score`.
- Do not silently redefine `final_composite_score`.
- Do not mix old and new score columns in one active ranking sort.
- Do not use old score fallback to fill missing new score values.
- Do not call the new score a trading recommendation.
- Do not infer valuation support from price-only data.
- Do not use backtest outcomes to tune the score definition.

## Archive Handling

The archive layer should preserve the old score under explicit names:

```text
legacy_technical_composite_score
legacy_final_composite_score
legacy_score_archive_source = "MVP v0.1 technical-only composite"
legacy_score_archive_status = "archived_legacy_reference"
```

These fields are for comparison and provenance only. They should not appear as
the active GUI `점수` after cutover.

## First Safe Implementation Slice

The first implementation slice should only add schema/config support:

- validate the migration config
- emit archive aliases in a sidecar evaluation table
- keep production ranking and GUI replacement disabled

Runtime cutover must be a later, separately reviewed branch.
