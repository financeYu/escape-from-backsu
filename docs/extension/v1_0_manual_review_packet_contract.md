# v1.0-rc ManualReviewPacket contract

Phase 8 adds `ManualReviewPacket` for private manual-review support. It
consumes `EvaluationEvidenceV1`, selector review-prioritization output,
candidate metadata, `HorizonPolicy`, `SimulationRunManifest`, optional
`WeightConfig`, and optional `LayerRegistry` summaries.

It emits evidence summaries, risk flags, coverage gaps, data quality flags,
rebalancing disclosure, limitations, manual checklists, follow-up questions,
and source artifact references.

It does not emit order instructions, buy/sell/hold recommendations, trade
signals, automatic position sizing, automatic live rebalance instructions,
move-to-cash commands, expected-return claims, future-return predictions,
production ranking replacement, or valuation/fundamental active scoring.

## Review framing

`manual_review_required` is always true. Selector priority is treated as review
triage only, not as an action. Any current-condition status is optional
diagnostic/reference context and is never fetched or invented by this builder.

## Rebalancing disclosure

When evidence contains a `rebalance_frequency` or non-`none`
`rebalancing_role`, the packet preserves the disclosure. If rebalancing
materially affects evidence, the packet surfaces that as a risk/review flag.
The disclosure is not an instruction to rebalance.

Phase 9 final v1.0-rc freeze-readiness validation remains separate and is not
implemented by this contract.
