# v2.0 Evidence Readiness Gap Report

## Purpose

The v2.0 evidence readiness gap report checks whether KOSPI200 strategy
candidate evidence is safe to hand to the ML/rule selector as evidence-only
`AdoptionCandidate` material.

The report is manual-review support only. It does not activate valuation or
fundamental scoring, change score formulas, alter runtime ordering semantics,
alter backtest semantics, create execution guidance, expand the universe, add
market data ingestion, or make performance forecast claims.

## Implementation

- Validator: `src/validation/v2_0_evidence_readiness.py`
- Test: `tests/validation/test_v2_0_evidence_readiness.py`
- Report directory note: `reports/readiness/README.md`
- Owner lane: root governance plus ML/evaluator review
- Completion gate: `.agents/skills/quant-review-gate/SKILL.md`

## Input Contract

Each candidate readiness row must include:

- `candidate_id`
- `ticker`
- `evaluation_date`
- `strategy_candidate_ref`
- `evaluation_evidence_ref`
- `adoption_candidate_ref`
- `pit_status`
- `lineage_status`
- `coverage_status`
- `feature_label_separation_status`
- `leakage_check_status`
- `no_lookahead_check_status`
- `cost_liquidity_status`
- `robustness_status`
- `manual_review_priority_status`
- `source_artifact`
- `lineage_ref`
- `manual_review_only`

Optional columns:

- `feature_columns`
- `label_columns`
- `reason_codes`
- `notes`

## Fail-Closed Checks

The validator returns `V2_0_NOT_READY` when any required field is missing, any
required status is blocked or invalid, manual-review-only status is not
confirmed, lineage is absent, feature and label columns overlap, evaluation
metrics are listed as selector features, forbidden columns are present, or
forbidden language appears in the candidate rows.

The required status checks are:

- point-in-time safety
- lineage
- evidence coverage
- feature and label separation
- leakage prevention
- no-lookahead prevention
- cost and liquidity readiness
- robustness or stability readiness
- manual-review priority readiness

Warning statuses such as `warn`, `diagnostic_ready`, or
`partial_diagnostic_ready` are allowed only as limitations. They produce
`V2_0_READY_WITH_LIMITATIONS`, not full readiness.

## Verdicts

- `V2_0_READY_FOR_LIMITED_SELECTOR_REVIEW`: all required checks pass.
- `V2_0_READY_WITH_LIMITATIONS`: no blocker exists, but at least one
  limitation remains visible.
- `V2_0_NOT_READY`: at least one blocker exists, or no candidate row is
  supplied.

These verdicts are for human review of evidence readiness. They are not release,
activation, runtime ranking, execution, or performance verdicts.

## Report Shape

The generated JSON report contains:

- `report_version`
- `generated_at`
- `scope`
- `kospi200_only`
- `manual_review_only`
- `valuation_fundamental_scoring_activation_allowed`
- `production_activation_allowed`
- `readiness_verdict`
- `global_blockers`
- `candidate_rows`
- `summary`
- `contract`

`candidate_rows` preserve the source artifact and lineage reference so missing
lineage is explicit rather than silent.

## Deferred Items

This contract does not merge real v1.1 through v1.6 artifacts by itself. A
later runner may prepare the input rows from existing artifacts only when join
keys and lineage are clear. If evidence is missing, the correct output is a
blocked readiness gap, not inferred readiness.

This contract does not resolve v1.5 valuation formula variance, promote
diagnostic valuation fields, add new market data ingestion, or connect any
selector output to production behavior.
