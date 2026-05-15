# v1.6 Confidence Robustness Review Priority Integration

## Purpose

v1.6 integrates upstream v1.1 through v1.5 evidence and readiness status into a
conservative manual review priority packet. It is a contract layer for review
support only. It does not create a production ranking, trading instruction,
order instruction, rebalance instruction, valuation score, fundamental score,
future-return claim, expected-return claim, or proven-alpha claim.

The layer may consume readiness and status flags from profitability, ML,
cost/liquidity, revision, valuation/quality, and stability diagnostics. It must
not consume numeric valuation scores, final composite scores, technical
composite scores, production ranks, or active trading outputs.

## Implementation

- Contract module: `Quant_mvp/backtest_mvp/confidence_review_priority_v1_6.py`
- Runner module: `src/review_priority/v1_6_confidence_review_priority.py`
- Ensemble search module:
  `Quant_mvp/backtest_mvp/ensemble_weight_search_v1_6.py`
- Tests: `tests/backtest/test_v1_6_confidence_review_priority.py`,
  `tests/backtest/test_v1_6_ensemble_weight_search.py`
- Owner lane: ML/evaluator plus root governance
- Completion gate: `.agents/skills/quant-review-gate/SKILL.md`

The runner reads a merged v1.1 through v1.5 evidence/status CSV and emits
manual-review-only diagnostics. It may run in `project_artifacts` or `fixture`
mode. The mode is lineage metadata only; it does not relax guardrails.

## Allowed Inputs

Required identity columns are:

- `candidate_id`
- `ticker`
- `evaluation_date`

Recommended diagnostic columns are:

- `horizon_id`
- `split_id`
- `seed`
- `layer_id`
- `evidence_status`
- `coverage`
- `data_quality`
- `stability`
- `evidence_value`
- `source_artifact`
- `lineage_ref`

v1.6 may consume status and readiness values such as:

- `diagnostic_ready`
- `partial_diagnostic_ready`
- `blocked_by_reconciliation`
- `vendor_reference_only`
- `reference_only_after_evaluation_date`
- `after_evaluation_date`
- `skipped_missing_baseline_artifacts`
- `insufficient_data`
- `missing_artifact`
- `pass`
- `warn`
- `block`

Allowed sources are read-only upstream artifacts from v1.1 through v1.5,
including selector score manifests, reliability status packets, revision
diagnostic status, v1.5 feature readiness rows, and the v1.5-to-v1.6 readiness
handoff. When an upstream artifact is missing, v1.6 must record
`missing_artifact` or `config_missing` rather than fabricating confidence.

## Forbidden Inputs And Outputs

The following names are forbidden as input or output columns:

- `valuation_score`
- `fundamental_score`
- `technical_composite_score`
- `final_composite_score`
- `production_rank`
- `production_ranking`
- `trade_signal`
- `signal`
- `order_instruction`
- `rebalance_instruction`
- `forward_return`
- `expected_return`
- `future_return`
- `alpha`
- `proven_alpha`

The v1.6 packet may contain `manual_review_priority`, but that field is a
review queue category only. It is not a production rank or execution signal.

## Output Artifacts

The contract defines these artifact keys:

- `v1_6_confidence_score_manifest`
- `v1_6_horizon_stability_report`
- `v1_6_split_stability_report`
- `v1_6_layer_redundancy_report`
- `v1_6_composite_review_priority_manifest`
- `v1_6_v2_0_readiness_packet`

All artifacts must include a manual-review-only notice, prohibited-action
notice, and disabled production/valuation activation flags.

## Reason Codes

Allowed reason codes include:

- `strong_multi_layer_coverage`
- `stable_across_horizons`
- `stable_across_splits`
- `blocked_by_upstream_reconciliation`
- `insufficient_baseline_artifact`
- `redundant_layer_warning`
- `limited_quality_evidence`
- `manual_review_only`

Reason codes must describe evidence coverage and review limitations. They must
not describe trade actions or future performance certainty.

## Readiness Verdicts

The v2.0 readiness packet may use only these verdicts:

- `V2_0_READY_FOR_LIMITED_REVIEW`
- `V2_0_LIMITED_REVIEW_PACKET_READY_NOT_FULL_READY`
- `V2_0_NOT_READY`

These are readiness verdicts for later human review. They are not release,
trading, ranking, or production activation decisions.

## Config Policy

v1.6 is config-first. Numeric thresholds, if introduced later, must come from an
approved project config file. This contract layer does not define fallback
numeric thresholds. If a required config source is missing, the runner must
emit `config_missing` and fail closed for that threshold-dependent decision.

Candidate config sources include:

- `config/thresholds.toml`
- `Quant_mvp/config/thresholds.toml`

## Generated Output Paths

The runner writes generated artifacts under:

- `Quant_mvp/data/v1_6/review_priority/v1_6_confidence_score_manifest_latest.csv`
- `Quant_mvp/data/v1_6/review_priority/v1_6_horizon_stability_report_latest.csv`
- `Quant_mvp/data/v1_6/review_priority/v1_6_split_stability_report_latest.csv`
- `Quant_mvp/data/v1_6/review_priority/v1_6_layer_redundancy_report_latest.csv`
- `Quant_mvp/data/v1_6/review_priority/v1_6_composite_review_priority_manifest_latest.csv`
- `Quant_mvp/data/v1_6/review_priority/v1_6_v2_0_readiness_packet_latest.json`

Generated outputs remain local evidence/review artifacts and are not production
activation artifacts.

## Runner Behavior

The confidence score is a bounded diagnostic average of `coverage`,
`data_quality`, and `stability`. Missing or out-of-range components are treated
as missing evidence and reduce support rather than being guessed.

Horizon stability compares whatever `horizon_id` values exist. Fewer than two
horizons produce `insufficient_horizon_coverage`.

Split or seed stability uses `split_id` and `seed` when present. Fewer than two
split or seed observations produce `insufficient_split_or_seed_coverage`.

Layer redundancy requires `layer_id`, numeric `evidence_value`, and sufficient
shared candidates. It reads Spearman thresholds from approved threshold config.
If config is missing, the runner emits `config_missing` and does not use a
fallback threshold.

Composite output is `manual_review_priority` only, with values for human
review queue handling. It is not a live system output or execution input.

The ensemble weight search is a separate v1.6 evaluation helper. It can consume
already-approved model return rows and search non-negative, sum-to-one mixture
weights. To reduce data contamination risk, candidate weights come from a
predeclared grid, retained ensembles are selected on the validation split, and
the test split is reported only as untouched final review evidence. The test
split must not be used to pick or revise weights.

## Completion Criteria

v1.6 contract/design is complete when:

- allowed status values are explicit
- forbidden input and output columns are explicit
- all six output schemas are defined
- reason-code and readiness-verdict vocabularies are fixed
- threshold config behavior fails closed when config is missing
- focused contract and runner tests pass
- fixture execution emits all required CSV and JSON files
- forbidden column and wording guards reject unsafe inputs
- ensemble weight search keeps train, validation, and test roles separated
  when model-mixture weights are evaluated
