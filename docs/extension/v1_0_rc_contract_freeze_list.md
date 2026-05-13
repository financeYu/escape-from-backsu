# v1.0-rc Contract Freeze List

| freeze_item | owner_phase | covered_contracts | frozen_boundary | status | blockers |
|---|---|---|---|---|---|
| HorizonPolicy | Phase 2 | HorizonPolicy | explicit multi-horizon policy config; no live execution or trading output | COMPLETE | none |
| SimulationRunManifest | Phase 3 | SimulationRunManifest | candidate-only run metadata and HorizonPolicy snapshot; no production run activation | COMPLETE | none |
| WeightConfigRunPlan / RunRecord boundary | Phase 4 | WeightConfigRunPlan | planned candidate runs and run records remain evidence context; no best-weight selection or feedback optimization | COMPLETE | none |
| LayerRegistry status/category model | Phase 5 | LayerRegistry, LayerAdapter, LayerValidation | status/category semantics validate layer availability; valuation, futures, index, macro, and regime active scoring remain disabled | COMPLETE | none |
| EvaluationEvidenceV1 | Phase 6 | EvaluationEvidenceV1 | allowlisted historical evidence summary only; no future labels, orders, or active ranking update | COMPLETE | none |
| SelectorFeatureMatrix / SelectorScoreManifest | Phase 7 | SelectorFeatureMatrixV1, SelectorScoreManifestV1 | selector consumes allowlisted evidence and emits review-prioritization only | COMPLETE | none |
| AdoptionCandidateReviewPriority | Phase 7 | AdoptionCandidateReviewPriorityV1 | review priority only; no buy/sell/hold framing or production ranking replacement | COMPLETE | none |
| ManualReviewPacket | Phase 8 | ManualReviewPacket | private manual-review support only; no order generation, position sizing, or transaction instruction | COMPLETE | none |
| Phase 9 FreezeReadinessPacket | Phase 9 | FreezeReadinessPacket | validation packet for pre-freeze review only; no final freeze, tag, release, push, or production readiness declaration | COMPLETE | none |
