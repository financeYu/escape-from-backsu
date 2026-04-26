# WORKSPACE_MANIFEST

workspace_id: integration_step18_valuation_fundamental_expansion_merge
branch: integration/step18-valuation-fundamental-expansion-merge
task_type: master_integration
active_step: Step 18 Valuation / Fundamental Expansion
owner_or_worker: root master agent
created_from_commit: e075ef3c31cef2bda64bb722c01d3e1f4f9e2417

## Purpose

Merge the Step 18 implementation branch, validate candidate-only valuation/fundamental boundaries, run Step-end review gates, close Step 18, and refresh the compact local Quant project context.

## Source branch

- codex/step18-valuation-fundamental-expansion

## Allowed work

- merge the Step 18 implementation branch into this integration branch
- preserve Step 18 candidate-only valuation/fundamental scope
- run full and focused pytest validation
- run forbidden-scope searches for valuation, score, ranking, backtest, alpha, and trading-signal leakage
- run the Cross-Step Conflict Checkpoint
- run required Step-end specialist review checks
- apply minimal manifest, status, or documentation corrections required by the master integration gate
- commit the validated merge result
- refresh the latest local Quant project context snapshot after the Step commit

## Read-only paths unless a validation gate requires a narrow correction

- AGENTS.md
- Quant_mvp/AGENTS.md
- Quant_mvp/agents/valuation/AGENTS.md
- docs/workspace_parallel_work_policy.md
- docs/step2_financial_validation_summary.md
- src/scanner/
- src/backtest/
- src/composite/
- src/scores/

## Forbidden actions

- active valuation/fundamental scoring
- valuation-aware composite scoring
- financial/fundamental data in technical_composite_score or final_composite_score
- ranking output changes beyond tests proving Step 18 exclusion
- Step 17 backtest behavior changes beyond tests proving Step 18 exclusion
- trading recommendations, target prices, expected returns, predictive alpha claims, or signal output
- external financial data/network collection
- Step 19 or later implementation
- unrelated cleanup, reset, stash, or history rewrite
- generated market-data, runtime report, cache, or chart commits unless explicitly promoted as review fixtures

## Expected output

- integrated Step 18 candidate-only source-controlled files
- validation and review summary
- Cross-Step Conflict Checkpoint result
- Step 18 COMPLETE roadmap/status update
- merge commit SHA
- post-commit context refresh result

## Required validation

- git status / changed-file manifest
- python -m pytest -q -p no:cacheprovider
- python -m pytest -q -p no:cacheprovider tests/valuation tests/validation/test_step18_valuation_fundamental_guardrails.py tests/scanner/test_step18_valuation_boundary.py tests/backtest/test_step18_backtest_boundary.py
- python -m pytest -q -p no:cacheprovider tests/scanner tests/reports tests/backtest tests/validation
- review_mvp static review on Step 18 changed production/test paths
- forbidden-scope search
- python scripts/build_review_packet.py --step "Step 18" --stage "master integration pre-commit"
- Cross-Step Conflict Checkpoint using docs/cross_step_conflict_check.md and the generated review packet

## Handoff notes

The implementation worktree remains `C:\Users\jjaew\Project\worktrees\step18_valuation_fundamental_expansion` on `codex/step18-valuation-fundamental-expansion`.
The root workspace at `C:\Users\jjaew\Project\master_mvp` is used only for merge, validation, Step status, and context refresh.
