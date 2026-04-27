# v0.2 Candidate ML Production Activation Root Approval Packet

Status: root approval review packet only. This document prepares root decision
material for a possible future production activation review of
`prob_up_1d_candidate`. It does not activate production ranking, replace
`final_composite_score`, change reports, or convert the candidate artifact into
order-action strategy behavior.

## Review State

- decision state: `approval_review_ready_not_decided`
- activation executed: false
- root approval required before any runtime behavior changes: true
- candidate-only state preserved by this packet: true
- implementation authorization granted by this packet: false

This packet is not an activation verdict. It only defines the evidence,
validation, audit, and disable plan that root needs before a later decision.

## Current Candidate-Only Output Summary

Current `prob_up_1d_candidate` outputs are candidate-only sidecar artifacts:

- `prob_up_1d_candidate` as a modeled probability field
- candidate sidecar output under
  `reports/v0_2_predictive_probability/candidate_sidecar/`
- candidate sidecar selection packet under
  `reports/v0_2_predictive_probability/candidate_sidecar/selection_packet/`
- deterministic selection packet ordering:
  `prob_up_1d_candidate desc, ticker asc`
- model and feature metadata fields for versioned inspection
- data quality, coverage, adjusted-close source, and feature schema metadata

The candidate artifact does not feed production ranking, production reports,
`technical_composite_score`, or `final_composite_score`.

## Model Evaluation Summary

Current evaluation scope is candidate-only model quality diagnostics:

- fold style: time-ordered expanding-window walk-forward evaluation
- metrics: `brier_score`, `log_loss`, `calibration_error`, `coverage`,
  `nan_missing_rate`, and `feature_stability_mean_abs_shift`
- artifact root:
  `reports/v0_2_predictive_probability/evaluation/`
- interpretation: evaluation diagnostics only, not automatic runtime adoption

Required evidence before any activation review can proceed:

- representative metric summary artifact for the intended production universe
- fold coverage and missing-data summary
- calibration and stability notes
- documented metric acceptance criteria owned by root or Quant governance
- confirmation that evaluation diagnostics do not update model, feature,
  score, ranking, report, or composite paths

Exact diagnostic evidence attached for this packet:

- candidate artifact:
  `reports/v0_2_predictive_probability/candidate_sidecar/selection_packet/prob_up_1d_candidate_selection_packet_20260210.csv`
- candidate artifact manifest:
  `reports/v0_2_predictive_probability/candidate_sidecar/selection_packet/prob_up_1d_candidate_selection_packet_20260210.manifest.json`
- evaluation-only diagnostic artifact:
  `reports/v0_2_predictive_probability/evaluation_only_backtest/prob_up_1d_candidate_evaluation_only_backtest_diagnostic_20260210.csv`
- evaluation-only diagnostic manifest:
  `reports/v0_2_predictive_probability/evaluation_only_backtest/prob_up_1d_candidate_evaluation_only_backtest_20260210.manifest.json`
- walk-forward metric summary:
  `reports/v0_2_predictive_probability/evaluation/prob_up_1d_candidate_walk_forward_metric_summary_20260210.csv`
- walk-forward fold metrics:
  `reports/v0_2_predictive_probability/evaluation/prob_up_1d_candidate_walk_forward_fold_metrics_20260210.csv`
- walk-forward calibration table:
  `reports/v0_2_predictive_probability/evaluation/prob_up_1d_candidate_walk_forward_calibration_20260210.csv`
- walk-forward feature stability table:
  `reports/v0_2_predictive_probability/evaluation/prob_up_1d_candidate_walk_forward_feature_stability_20260210.csv`
- walk-forward manifest:
  `reports/v0_2_predictive_probability/evaluation/prob_up_1d_candidate_walk_forward_evaluation_20260210.manifest.json`

Observed diagnostic summary from the generated packet:

- candidate artifact rows: 3
- evaluation-only probability coverage: 1.0
- evaluation-only mean candidate probability: 0.7723890563639558
- walk-forward fold count: 5
- walk-forward mean `brier_score`: 0.3331559210806938
- walk-forward mean `log_loss`: 0.9607361941454862
- walk-forward mean `coverage`: 1.0

These artifacts were produced by the candidate-only route for review evidence.
They remain generated diagnostic artifacts and are not connected to production
ranking, reports, `technical_composite_score`, or `final_composite_score`.

## Leakage And No-Lookahead Audit Summary

Current gate result:

- no HIGH issue recorded in the latest leakage/no-lookahead review
- no blocker recorded for candidate-only sidecar generation
- MEDIUM follow-up remains: explicit source availability timestamp enforcement
  is not yet a production activation validator

Before activation can be reviewed, the audit must be repeated against the exact
activation candidate and must verify:

- feature observation time is on or before `decision_time`
- `label_time` is after `decision_time`
- `label_availability_time` is after `decision_time`
- labels and label-derived values are excluded from features
- future, forward, realized-return, evaluation, report, cache, and generated
  output columns are excluded from features
- backtest or evaluation diagnostics do not feed model, feature, score,
  ranking, report, or composite paths

## Adjusted Close Canonical Source

Current canonical source contract:

- canonical label source field: `adjusted_close`
- approved alias: `adj_close`
- `close` fallback: not approved
- new ingestion or new vendor assumption: not approved
- label definition: `adjusted_close[t+1] > adjusted_close[t]`
- missing canonical adjusted close before label construction: fail fast

Activation review must include a data provenance check proving that the
intended runtime input uses `adjusted_close` or the approved `adj_close` alias
under the existing contract.

## Sidecar Packet Validation Summary

Current sidecar packet contract:

- packet type: `candidate_sidecar_selection_packet`
- required field: `prob_up_1d_candidate`
- required timing field: `decision_time` or `as_of_date`
- required metadata: model, feature schema, label contract, adjusted-close
  source, and data-quality or coverage flags
- forbidden fields: production `rank`, `prob_up_1d_candidate_sidecar_rank`,
  `technical_composite_score`, `final_composite_score`, report output fields,
  and return-derived output fields
- sorting rule: `prob_up_1d_candidate desc, ticker asc`

Activation review requires a fresh schema validation on the exact artifact
proposed for review.

## Evaluation-Only Backtest Approval State

Evaluation-only backtest connection state:

- approval packet exists:
  `Quant_mvp/docs/v0_2_candidate_ml_evaluation_backtest_approval_packet.md`
- approval state: approved for diagnostic-only implementation
- implementation state: implemented as diagnostic-only adapter
- expansion state: any use beyond diagnostic-only still requires a separate
  root gate

Production activation review remains blocked until evaluation-only diagnostics are generated for the exact candidate artifact under review and audited as diagnostic only.

## Additional Gates Required Before Production Activation

The following gates are required before any production activation can be opened:

- root production activation decision gate
- score runtime semantics gate for ranking, report, and composite meaning
- candidate ML gate contract validator
- quant review gate validator
- leakage/no-lookahead audit on the exact activation candidate
- candidate artifact schema validation
- sidecar packet schema and sorting validation
- evaluation-only backtest approval and diagnostic-only validation
- generated-output and cache boundary audit
- cross-step conflict checkpoint
- disable plan review
- post-change runtime isolation review

No single metric artifact or sidecar packet is sufficient to open activation.

## Activation Acceptance Criteria

Activation review may proceed only if all criteria below are true for the exact
candidate artifact under review:

- schema: selection packet schema validation passes, required metadata is
  present, and forbidden production, report, composite, label, future, realized,
  and feedback fields are absent
- timing: `decision_time` is present, execution and label availability fields
  are after `decision_time` when present, and evaluation rows are time-ordered
- lineage: the label source is canonical `adjusted_close` or the approved
  `adj_close` alias normalized to `adjusted_close`; `close` fallback remains
  blocked
- diagnostic artifact: evaluation-only diagnostic export and manifest exist for
  the exact candidate artifact, validate as diagnostic-only, and do not update
  model, feature, score, ranking, report, or composite configuration
- runtime isolation: production ranking, report, chart runtime, and composite
  surfaces show no unintended diff from the frozen MVP v0.1 path
- production mutation: no production ranking/report/final score mutation is
  included in this packet
- rollback readiness: disable path, affected files, and non-affected production
  surfaces are documented before any later runtime change
- feedback boundary: backtest/evaluation diagnostics are not used for model
  selection, feature selection, cutoff selection, ranking rules, score weights,
  report behavior, or composite definitions

## Required Activation Evidence Packet

A future activation request must provide:

- exact candidate artifact path and manifest
- exact model version and feature schema version
- full walk-forward metric summary
- calibration, coverage, missing-data, and stability summaries
- leakage/no-lookahead audit result
- adjusted-close provenance evidence
- sidecar schema validation output
- evaluation-only diagnostic output and its boundary audit
- runtime diff showing no unintended changes outside the approved activation
  surface
- disable plan and rollback rehearsal evidence

## Blockers Before Activation Review

Current blockers:

- root activation approval has not been granted
- source availability timestamp validator is not production-ready
- generated-output and cache boundary validator ownership is not assigned
- rollback rehearsal is documented below but has not been executed as a
  production runtime dry run
- production runtime isolation review is not complete
- root must still accept or reject the attached diagnostic evidence before any
  production activation gate opens

## Rollback And Disable Plan Draft

Default state remains disabled. A future activation must be controlled by a
single config flag or equivalent root-owned switch, with the default value set
to disabled until root approval is recorded.

Disable plan draft:

- set activation flag to disabled
- stop reading `prob_up_1d_candidate` in any production ranking path
- keep candidate sidecar generation available only as diagnostic output
- restore production ranking to the existing `final_composite_score` path
- remove report exposure for the candidate field if any approved future report
  surface had been opened
- rerun score runtime semantics checks and candidate ML gate validator
- preserve generated diagnostic artifacts as non-source-controlled evidence
  only when the release process explicitly requests them

Rollback must not require model retraining. It must return runtime behavior to
the MVP v0.1 frozen baseline semantics plus candidate-only sidecar artifacts.

Rollback rehearsal checklist:

- confirm any future activation flag defaults to disabled before and after the
  rehearsal
- confirm production ranking code path ignores `prob_up_1d_candidate`
- confirm report generation does not read the candidate selection packet or
  evaluation-only diagnostic artifacts
- confirm `technical_composite_score` and `final_composite_score` definitions
  remain unchanged
- confirm generated candidate artifacts can remain present without changing
  runtime output
- rerun candidate ML gate validator and quant review gate validator
- record the runtime diff and verify that only the approved activation surface
  changed during the rehearsal

Expected rollback path:

1. set the future root-owned activation switch back to disabled
2. remove candidate field exposure from any future approved runtime surface
3. keep `reports/v0_2_predictive_probability/` artifacts diagnostic-only
4. restore production ranking/report/composite calls to the MVP v0.1 path
5. rerun schema, timing, feedback-boundary, candidate ML gate, and review gate
   validators

Affected files for a future activation or rollback review:

- `Quant_mvp/config/v0_2_candidate_ml_score.toml`
- `src/scores/prob_up_1d_candidate.py`
- `src/validation/v0_2_candidate_ml_guardrails.py`
- `Quant_mvp/docs/v0_2_candidate_ml_production_activation_root_approval_packet.md`
- generated diagnostic artifacts under
  `reports/v0_2_predictive_probability/`

Non-affected production surfaces for this packet:

- MVP v0.1 score formulas and score normalization
- production ranking generation
- report runtime behavior
- chart runtime behavior
- `technical_composite_score`
- `final_composite_score`
- data ingestion and universe definitions

## Next Root Decision Items

Root must decide whether to:

1. keep `prob_up_1d_candidate` candidate-only with no additional activation
   work
2. approve only the evaluation-only backtest integration gate first
3. request more model evaluation evidence before any activation review
4. assign owners for no-lookahead, generated-output boundary, and rollback
   validators
5. open a separate production activation review gate after all blockers are
   closed
