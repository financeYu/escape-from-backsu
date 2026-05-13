# v1.0-rc selector/evaluator contract

Phase 7 adds an evidence-only selector/evaluator. It consumes allowlisted
`EvaluationEvidenceV1` summaries and emits `AdoptionCandidate` review
prioritization only.

The selector output is not a buy/sell/hold recommendation, trade signal, live
execution signal, order instruction, automatic rebalance instruction,
production ranking replacement, future-return prediction, expected-return
estimate, or proven-alpha claim.

## Artifacts

- `SelectorInputManifestV1` records evidence refs, selected allowlisted
  feature fields, blocked fields, candidate counts, and evidence-only flags.
- `SelectorFeatureMatrixV1` preserves `candidate_id`, `evidence_id`,
  `horizon_policy_id`, optional `weight_config_id`, and allowlisted feature
  values.
- `SelectorTrainabilityReportV1` checks candidate count, feature coverage, and
  approved label availability. If labels are absent or insufficient, training
  is skipped and the output remains `trainability_check_only`.
- `SelectorScoreManifestV1` records deterministic rule-based review priority
  output with `manual_review_required = true`.

## Baseline behavior

The current v1.0-rc baseline is deterministic rule-based review
prioritization. Optional ML training is safely skipped unless a later approved
historical review/adoption label manifest exists and trainability checks pass.

Rebalancing metadata may be used as evidence context. If evidence materially
depends on rebalancing, the selector emits a review reason such as
`rebalance_material_to_evidence`; it does not emit a rebalance instruction.
