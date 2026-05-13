# v1.0-rc Rebalance Disclosure Audit

- historical_simulated_rebalancing_allowed: True
- rebalance_frequency_retained_across_artifacts: True
- material_rebalancing_disclosure_present: True
- live_user_facing_rebalance_instruction_introduced: False

| artifact | rebalance_frequency_present | rebalancing_role_present | materiality_disclosure_present | wording_is_disclosure_not_instruction | status | notes |
|---|---|---|---|---|---|---|
| HorizonPolicy | True | not_applicable | True | True | COMPLETE | historical/simulated rebalancing disclosure retained |
| SimulationRunManifest | True | not_applicable | True | True | COMPLETE | historical/simulated rebalancing disclosure retained |
| EvaluationEvidenceV1 | True | True | True | True | COMPLETE | historical/simulated rebalancing disclosure retained |
| SelectorScoreManifestV1 | True | True | True | True | COMPLETE | selector keeps rebalancing as reason_code/context only |
| ManualReviewPacket | True | True | True | True | COMPLETE | manual packet includes disclosure without instruction wording |
