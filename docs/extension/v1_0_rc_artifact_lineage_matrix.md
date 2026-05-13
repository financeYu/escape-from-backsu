# v1.0-rc Artifact Lineage Matrix

| source_artifact | target_artifact | allowed_dependency | read_only_or_mutating | selector_allowlist_required | rebalancing_disclosure_required | production_ranking_update_allowed | live_execution_allowed | validation_status |
|---|---|---|---|---|---|---|---|---|
| HorizonPolicy | SimulationRunManifest | snapshot_copy | read_only | False | True | False | False | COMPLETE |
| SimulationRunManifest | WeightConfigRunPlan / WeightConfigRunRecord | candidate_only_run_context | candidate_only_builder | False | True | False | False | COMPLETE |
| WeightConfigRunPlan / WeightConfigRunRecord | LayerRegistry validation status | active_weight_layer_validation | read_only_validation | False | False | False | False | COMPLETE |
| LayerRegistry validation status | EvaluationEvidenceV1 | validation_summary_reference | read_only | False | False | False | False | COMPLETE |
| EvaluationEvidenceV1 | SelectorFeatureMatrixV1 / SelectorScoreManifestV1 | allowlisted_evidence_summary_only | read_only | True | True | False | False | COMPLETE |
| SelectorScoreManifestV1 | AdoptionCandidateReviewPriorityV1 | review_prioritization_only | candidate_only_builder | True | True | False | False | COMPLETE |
| AdoptionCandidateReviewPriorityV1 | ManualReviewPacket | manual_review_support | read_only | True | True | False | False | COMPLETE |
| ManualReviewPacket | v1.0-rc freeze readiness packet | validation_summary_reference | read_only | False | True | False | False | COMPLETE |
