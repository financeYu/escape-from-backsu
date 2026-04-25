# WORKSPACE_MANIFEST

workspace_id: integration_step17_conservative_backtest_merge
branch: integration/step17-conservative-backtest-merge
task_type: master_integration
active_step: Step 17 conservative backtest
owner_or_worker: Step 17 Integration Agent
created_from_commit: 564db56

## Purpose

Merge Worker A and Worker B Step 17 branches, resolve integration conflicts,
run validation, perform the Cross-Step Conflict Checkpoint, and update Step 17
status only if the merged result passes the required gates.

## Source branches

- codex/step17-backtest-core
- codex/step17-backtest-guardrails

## Scope

Merge Worker A and Worker B, resolve integration conflicts, run validation, and
update Step 17 status only if complete.

## Allowed work

- merge Worker A first, then Worker B
- preserve Worker A ownership for backtest core paths
- preserve Worker B ownership for Step 17 guardrail, report-boundary, and
  backtest generated-output boundary paths
- apply minimal deterministic compatibility fixes when validation requires them
- run focused backtest and guardrail tests
- run related scanner, report, validation, and full test suites
- run the Cross-Step Conflict Checkpoint
- update Step 17 roadmap/status docs only after all required validation passes
- refresh the local project context after Step-end validation and commit

## Forbidden actions

- new feature implementation
- score formula changes
- normalized score formula changes
- ranking formula changes
- composite score changes
- valuation/fundamental scoring
- PER, PBR, ROE, EPS, BPS, financial statement, or market-cap fundamental inputs
- trading recommendation language
- buy, sell, hold-as-recommendation, target price, expected return, or signal output
- silent upstream schema rewrites
- Step 15 ranking rewrite
- Step 16 report rewrite beyond read-only compatibility
- return feedback into scoring, adoption, ranking, or report logic
- strategy optimization or parameter tuning from results
- generated runtime report/cache commits unless explicitly promoted as fixtures
- unrelated cleanup, reset, stash, or branch history rewrites

## Expected output

- integrated Step 17 source-controlled files
- conservative conflict-resolution summary
- focused and broad validation summary
- Cross-Step Conflict Checkpoint result
- roadmap status update only if Step 17 passes
- commit SHA when the final integrated Step state is committed

## Required validation

- git status / branch / recent log
- python -m pytest -q tests/backtest
- python -m pytest -q tests/validation/test_step17_backtest_guardrails.py
- python -m pytest -q tests/reports if report tests exist
- python -m pytest -q tests/scanner tests/reports tests/validation
- python -m pytest -q
- python scripts/build_review_packet.py --step "Step 17" --stage "post-merge integration validation"
- Cross-Step Conflict Checkpoint using docs/cross_step_conflict_check.md and
  the generated review packet

## Handoff notes

The master workspace at `C:\Users\jjaew\Project\master_mvp` contains Step 16
completion-related dirty files that are intentionally excluded from this Step
17 integration worktree. Do not copy, restore, stage, or absorb those changes
into this branch.
