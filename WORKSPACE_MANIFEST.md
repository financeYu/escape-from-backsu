# WORKSPACE_MANIFEST

workspace_id: step15_a_b_integration_verifier
branch: integration/step15-a-b-merge
task_type: master_integration
active_step: Step 15 latest ranking output implementation
owner_or_worker: Step 15 A/B Integration Verifier
created_from_commit: 8de10055e4989da603cd143f0b744114024aaeda

## Purpose

Integrate and verify Worker A core latest-ranking output and Worker B validation guardrail outputs without weakening repository, roadmap, valuation, backtest, or future-return guardrails.

## Source branches

- step15-worker-a-core
- step15-worker-b-validation

## Consumed worker manifests

- Worker A: step15_worker_a_core / step15-worker-a-core / Step 15 latest ranking output implementation
- Worker B: step15_worker_b_validation / step15-worker-b-validation / Step 15 Latest Ranking Output validation support

## Allowed work

- merge Worker A and Worker B branches
- resolve merge conflicts minimally
- validate Step 15 contracts and guardrails
- run focused and broad tests
- produce final integration report
- commit source-controlled integration state if validation allows

## Forbidden work

- new feature invention
- Step 16 detailed stock report implementation
- Step 17 backtest, realized-return validation, Sharpe, MDD, win-rate, or alpha validation
- Step 18 valuation/fundamental scoring
- financial/fundamental data in technical_composite_score or final_composite_score
- buy, sell, trading signal, or investment advice language
- roadmap bypass or Step completion status update without passing the required gates

## Expected output

- integrated Step 15 source and validation files
- focused and broad validation summary
- Cross-Step Conflict Checkpoint result
- Korean integration report

## Required validation

- Worker A focused tests after merge
- Worker B focused tests after merge
- Step 15 integration compatibility checks
- changed-file forbidden-term search
- broad pytest run when feasible
- Cross-Step Conflict Checkpoint

## Handoff notes

This integration branch is ready for master-up review only if A/B merges are clean, focused validation passes, broad validation passes or any limitation is justified, generated-output boundaries are clean, and no unresolved Step 15 contract conflict remains.
