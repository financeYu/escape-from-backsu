# v0.1n Implementation Approval-Prep Packet

Status: approval-prep only. This packet does not approve implementation,
activate production scoring or ranking, or change the frozen MVP v0.1 baseline.

## Purpose

`v0.1n` is a candidate-only experimental line for a future `v0.2` candidate.
It exists to define the minimum approval contract that must be satisfied before
any implementation can begin.

The frozen MVP v0.1 baseline remains unchanged:

- KOSPI200-only.
- Technical-only.
- `technical_composite_score` and `final_composite_score` semantics unchanged.
- No valuation, fundamental, ML, or backtest output enters production scoring,
  ranking, reports, or recommendation language.

## Candidate ML Boundary

The only allowed ML target for this approval-prep packet is:

- candidate output: `prob_up_1d_candidate`
- candidate label: `adjusted_close[t+1] > adjusted_close[t]`

This candidate output is experimental metadata only. It must not be adopted into
production scoring, ranking, report ordering, final composite fields, valuation
verdicts, or user-facing recommendation language.

Before implementation approval, the candidate line must define:

- feature schema and source lineage
- allowed training rows and exclusion rules
- label construction and missing-label behavior
- model artifact naming and version lineage
- evaluation metrics and reporting boundaries
- generated-output retention policy

## Timing Contract

Every candidate row must carry explicit timing fields:

- `decision_time`: time at which all candidate features are considered known.
- `execution_time`: simulated next actionable time after `decision_time`.
- `label_time`: time represented by `adjusted_close[t+1]`.
- `label_availability_time`: time at which the label can be known and used for
  evaluation.

No-lookahead requirement:

- Features available at `decision_time` must not use values, derived values, or
  availability assumptions from after `decision_time`.
- Labels must not be visible to training, scoring, ranking, selection, report
  generation, or candidate simulation before `label_availability_time`.
- Any row with ambiguous timing, missing availability metadata, or unresolved
  calendar alignment must be excluded or marked non-evaluable.

## Candidate Backtest Simulation Contract

Any `v0.1n` candidate simulation is evaluation-only.

Allowed:

- offline diagnostics for candidate behavior
- timing-contract validation
- leakage checks
- stability and calibration review
- comparison against frozen MVP v0.1 outputs as a read-only reference

Forbidden:

- feedback from simulation output into scoring or ranking
- score formula, weight, normalization, adoption, or report behavior changes
- trading recommendation language
- production portfolio construction or execution guidance
- use of backtest results as approval by themselves

## Schema And Lineage Freeze Before Approval

Implementation approval requires a frozen candidate contract before code work:

- candidate dataset schema
- required and optional columns
- timing fields and timezone/calendar assumptions
- feature lineage and source availability rules
- label lineage and adjustment policy
- train/evaluation split policy
- artifact lineage for models, datasets, metrics, and reports
- generated-output boundary and source-control policy
- rollback and deactivation rule

Any later change to schema, timing semantics, label definition, feature
availability, or candidate output meaning must trigger a new approval review.

## Review And Audit Gate Checklist

Before implementation can begin, the approval packet must pass:

- root/master scope confirmation for `v0.1n`
- explicit statement that MVP v0.1 frozen baseline remains unchanged
- no-lookahead timing review
- schema and lineage freeze review
- generated-output and cache boundary review
- score/ranking/report/backtest feedback hard-stop review
- valuation/fundamental activation hard-stop review
- trading-recommendation language review
- cross-step conflict checkpoint when an implementation Step is proposed
- `review_mvp` specialist review if code, schemas, generated-output boundaries,
  or cross-project handoffs are included in the later implementation request

## Remaining Risks And Blockers

Implementation cannot begin until these are resolved:

- candidate schema and lineage contract is not yet frozen
- timing calendar and availability rules are not yet validated
- data provenance for adjusted close and feature availability is not yet
  approved for candidate use
- leakage and train/evaluation split policy is not yet reviewed
- model artifact and generated-output boundary is not yet approved
- no post-MVP implementation Step has been opened for `v0.1n`
- no production adoption path exists for `prob_up_1d_candidate`

## Approval Verdict

`v0.1n` status: not approved for implementation.

This packet is approval-prep only. It may be used to route a future `v0.2`
candidate proposal, but it does not authorize models, features, pipelines,
ranking changes, report changes, score changes, data ingestion, or backtest
feedback loops.
