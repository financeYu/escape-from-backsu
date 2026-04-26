# WORKSPACE_MANIFEST

workspace_id: integration_step19_automatic_execution_pipeline_merge
branch: integration/step19-automatic-execution-pipeline-merge
task_type: master_integration
active_step: Step 19 Automatic Execution Pipeline
owner_or_worker: root master agent
created_from_commit: be1b07f218c0621a2e3640705cb391798973ff2f

## Purpose

Merge the Step 19 automatic execution pipeline branch, validate orchestration
and generated-output boundaries, run Step-end review gates, close Step 19, and
refresh the compact local Quant project context.

## Source branch

- codex/step19-automatic-execution-pipeline

## Allowed work

- merge the Step 19 implementation branch into this integration branch
- preserve Step 15 ranking, Step 16 report, Step 17 backtest, and Step 18
  candidate-only valuation/fundamental boundaries
- run focused and full pytest validation
- run generated-output ignore checks for Step 19 report roots
- run the Cross-Step Conflict Checkpoint
- run required Step-end specialist review checks
- apply minimal Step 19 CLI, status, manifest, or generated-output boundary
  corrections required by the master integration gate
- commit the validated Step 19 merge result
- refresh the latest local Quant project context snapshot after the Step commit

## Read-only paths unless a validation gate requires a narrow correction

- AGENTS.md
- Quant_mvp/AGENTS.md
- Quant_mvp/agents/valuation/AGENTS.md
- docs/workspace_parallel_work_policy.md
- docs/cross_step_conflict_check.md
- docs/context/
- src/scanner/
- src/reports/
- src/backtest/
- src/valuation/
- src/composite/
- src/scores/

## Forbidden actions

- new score formulas
- ranking semantic changes
- detail report semantic changes
- backtest semantic changes
- active valuation/fundamental scoring
- valuation-aware composite scoring
- financial/fundamental data in technical_composite_score or final_composite_score
- KOSDAQ150, futures, or options expansion
- external financial data/network collection
- trading recommendations, target prices, expected returns, predictive alpha
  claims, or signal output
- Step 20 final validation or completion claims
- unrelated cleanup, reset, stash, or history rewrite
- generated market-data, runtime report, cache, or chart commits unless
  explicitly promoted as review fixtures

## Expected output

- integrated Step 19 automatic execution pipeline source-controlled files
- validation and review summary
- Cross-Step Conflict Checkpoint result
- Step 19 COMPLETE roadmap/status update
- final integrated commit SHA
- post-commit context refresh result

## Required validation

- git status / changed-file manifest
- python -m pytest -q -p no:cacheprovider tests/pipeline tests/validation/test_step19_pipeline_guardrails.py
- python -m pytest -q -p no:cacheprovider tests/scanner tests/reports tests/backtest tests/validation
- python -m pytest -q -p no:cacheprovider
- review_mvp static review on Step 19 changed production/test Python paths
- python -m unittest discover -s review_mvp/tests -v
- git check-ignore for Step 19 and related generated report roots
- python scripts/build_review_packet.py --step "Step 19" --stage "post-review-fix validation"
- Cross-Step Conflict Checkpoint using docs/cross_step_conflict_check.md and the generated review packet

## Handoff notes

The implementation worktree remains
`C:\Users\jjaew\Project\worktrees\step19_automatic_execution_pipeline` on
`codex/step19-automatic-execution-pipeline`.
The root workspace at `C:\Users\jjaew\Project\master_mvp` is used only for
merge, validation, Step status, and context refresh.
