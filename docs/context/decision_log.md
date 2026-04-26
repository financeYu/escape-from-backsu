# Context Decision Log

This log records changed context-routing decisions only. It is not a full project
history and should not be used as default Step evidence.

| Date | Decision | Reason | Default-read impact |
| --- | --- | --- | --- |
| 2026-04-26 | Created `docs/context/current_context.md` as the latest-only context entry point. | Reduce repeated reasoning from long completed-Step history. | Default readers start from compact current facts instead of Step 1-19 detail. |
| 2026-04-26 | Created `docs/context/archive/step01_to_step19_summary.md` for completed-Step history. | Keep provenance available without loading it by default. | Archive is read only for conflict, regression, or provenance checks. |
| 2026-04-26 | Created `docs/context/active_step20_packet.md` for Step 20 final-validation routing. | Step 20 needs a narrow packet that does not embed Step 1-19 history. | Step 20 workers read the active packet plus default control files. |
| 2026-04-26 | Added explicit fresh-reasoning requirements to `docs/context/context_usage_policy.md`. | Future responses should produce current critique/options instead of restating roadmap summaries. | Ordinary planning answers repeat no more than three context facts. |
| 2026-04-26 | Updated context routing names around review tasks and Step 20 final validation. | Post-Step19 work needs routing by current review surface. | Routes now include `step20_final_validation`, `scoring_review`, `ranking_review`, `report_review`, `backtest_review`, `valuation_boundary_review`, `research_ingestion`, `code_review`, and `planning_only`. |
| 2026-04-26 | Updated Step 20 context from pre-start routing to completed final-validation provenance. | Step 20 release evidence is now integrated and roadmap status is COMPLETE. | Default context now says no roadmap Step is in progress after MVP v0.1 freeze readiness. |
| 2026-04-26 | Added Step 20.5 pre-freeze baseline, active packet, routing index, quickstart, and validation ladder. | Preserve MVP v0.1 with lower default context load before final freeze. | Default prompt context is now compact baseline + exactly one active packet + optional routing index. |
