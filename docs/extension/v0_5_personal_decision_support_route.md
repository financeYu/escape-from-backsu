# v0.5 Personal Decision Support Route

Status: active contract-only personal decision support route.
Pre-entry assessment: `docs/extension/v0_5_pre_entry_gap_assessment.md`.
Parent evidence route: `docs/extension/v0_3_research_to_strategy_adoption_route.md`.
Parent selector route: `docs/extension/v0_4_ml_selector_application_route.md`.

## Purpose

v0.5 turns the current v0.3/v0.4 review artifacts into a private, local
decision-support packet for human judgment. It is not a public product, not
investment advice automation, not order generation, and not production
activation.

The route may answer:

- what evidence exists for a candidate
- what evidence is missing
- whether the candidate is inside the KOSPI/KOSPI200 boundary
- what risk, cost, stability, leakage, or coverage flags remain
- what the user should manually verify before forming a personal view

The route must not answer with an instruction to transact.

## Allowed Inputs

All inputs are read-only:

- v0.3 `StrategyCandidate` registry
- v0.3 `EvaluationEvidence` packets and manifests
- v0.3 ML-ready candidate input and selector feature matrix manifests
- v0.3 `AdoptionCandidate` review packets
- v0.4 trainability, model, score, comparison, and ranking manifests
- approved local KOSPI/KOSPI200 current-condition snapshots, only after their
  owner lane validates no new market-data ingestion or universe expansion

## PersonalDecisionSupportPacket

The first v0.5 output is `PersonalDecisionSupportPacket`. Required fields:

- `packet_id`
- `candidate_id`
- `candidate_version`
- `support_scope`
- `input_artifact_refs`
- `evidence_status`
- `selector_diagnostic_refs`
- `current_condition_status`
- `risk_flags`
- `cost_sensitivity_flags`
- `coverage_gaps`
- `manual_review_checklist`
- `decision_boundary`
- `no_order_generation_check`
- `no_position_sizing_check`
- `no_prediction_claim_check`
- `no_production_activation_check`

Allowed packet states:

- `evidence_supported_review`
- `needs_more_evidence`
- `blocked_out_of_scope`
- `blocked_missing_current_condition`
- `blocked_validation_incomplete`

Allowed support language:

- `review_supported`
- `watchlist_candidate`
- `needs_manual_check`
- `evidence_insufficient`
- `risk_flagged`
- `out_of_scope`

Forbidden support language:

- `buy`
- `sell`
- `hold`
- `rebalance`
- `move_to_cash`
- `target_price`
- `expected_return`
- `profit_expected`
- `position_size`
- `order`

## Guardrails

v0.5 must preserve:

- KOSPI/KOSPI200 boundary only
- no new market-data ingestion
- no universe expansion
- no live trading or brokerage integration
- no order generation
- no automatic position sizing
- no automatic cash move or rebalance instruction
- no future return prediction claim
- no selector score source change
- no RandomForest baseline replacement
- no automatic adoption or production activation

## v0.4 Artifact Interpretation

LogisticRegression remains the frozen baseline selector score source for
review-prioritization diagnostics. RandomForest remains a nonlinear challenger
and reference-only diagnostic comparison artifact.

v0.5 may cite the LR/RF comparison and ranking manifests only as diagnostic
references. They must not determine packet ordering, transaction action, or
position size.

## Initial Validation

Before a v0.5 packet can be accepted:

- v0.4.2 evidence coverage validators must pass
- selector feature matrix leakage checks must pass
- the v0.5 packet must contain no forbidden action language
- all source artifacts must be read-only inputs
- KOSPI/KOSPI200 boundary checks must pass
- every packet must include manual review checklist items

## Next Required Work

The first packet builder is
`Quant_mvp/scripts/build_v0_5_personal_decision_support_packets.py`. It emits
fail-closed packets until an approved current-condition snapshot is available.
Future work may add current-condition inputs only through an approved
KOSPI/KOSPI200 local lane without new market-data ingestion or universe
expansion.
