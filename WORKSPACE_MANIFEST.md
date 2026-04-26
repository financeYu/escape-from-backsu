# WORKSPACE_MANIFEST

workspace_id: step20_post_mvp_optimization
branch: codex-step20-post-mvp-optimization
role: post-mvp optimization worker
task_type: cross_project_runtime_validation_optimization
active_step: post-Step20 / Step 20 COMPLETE follow-up
owner_or_worker: Codex
created_from_commit: 1ad7727d7f73a5eac3b1a20f02967eb12a11a177

## Purpose

Implement the user's five requested optimization follow-ups from the
post-Step20 review without changing quant score formulas, score weights,
ranking semantics, valuation/fundamental activation, backtest feedback policy,
or market-data scope.

This worktree exists so the master/root workspace does not repeat the same
implementation or broad review pass. The handoff output must list the five
completed items, changed files, validation commands, and remaining risks.

Branch note: the preferred `codex/` namespace could not be created in this
local repository from the sandboxed shell. This branch follows the existing
local codex hyphen pattern used by `codex-step20-prefreeze-optimization`.

## Five Assigned Optimization Items

1. Clarify and harden the boundary between `chart_mvp` legacy Top-N runtime
   output and canonical Step 20 latest ranking output so root does not treat
   the legacy placeholder path as canonical ranking evidence.
2. Reduce avoidable Naver runtime I/O by separating price refresh from
   financial-statement refresh cadence and documenting the behavior.
3. Avoid redundant chart-data refetches when the already processed Top-N row
   contains enough indicator data for rendering.
4. Stabilize Windows pytest/temp validation by adding a repository-local test
   runner path instead of requiring repeated manual temp-root troubleshooting.
5. Reduce Step 16/17 scaling overhead by caching repeated report metadata work
   and speeding Step 17 price-date lookup without changing selection or
   realized-return semantics.

## Allowed Write Paths

- WORKSPACE_MANIFEST.md
- chart_mvp/README.md
- chart_mvp/TEMPORARY_TOP5_OVERRIDE.md
- chart_mvp/docs/
- chart_mvp/src/stock_core/cache/
- chart_mvp/src/stock_core/pipeline/
- chart_mvp/src/stock_core/ranking/
- chart_mvp/tests/
- docs/context/
- docs/development_environment.md
- docs/releases/
- reports/validation/
- scripts/
- src/backtest/
- src/reports/
- tests/backtest/
- tests/context/
- tests/reports/

## Read-Only Paths

- AGENTS.md
- docs/project_checklist.md
- docs/roadmap_status.md
- completed Step docs except targeted references needed for boundaries
- generated market caches
- generated runtime report roots
- secrets and local environment files

## Forbidden Actions

- KOSDAQ150, futures, options, or multi-universe implementation
- new external market-data source ingestion
- score formula, score weight, score adoption, or normalization semantic changes
- `technical_composite_score` or `final_composite_score` semantic changes
- valuation/fundamental scoring activation or financial/fundamental data in
  technical/final composite scoring
- backtest-driven score optimization or return feedback into upstream ranking
- trading recommendations, buy/sell/hold wording, or proven-alpha claims
- committing generated market caches, chart images, local runtime outputs, or
  nested worktree artifacts

## Expected Handoff Output

- A concise optimization handoff document that maps each of the five requested
  items to changed files, implementation notes, tests, and residual risks.
- Focused tests for each behavioral optimization.
- A final validation summary suitable for root/master review without rereading
  completed Step history.

## Required Validation

- python scripts/run_local_validation.py chart
- python scripts/run_local_validation.py context
- python scripts/run_local_validation.py reports-backtest
- python scripts/context/check_context_staleness.py
- python scripts/context/check_context_conflicts.py
- python scripts/build_review_packet.py --step "Post-Step20" --stage "post-mvp-optimization"
- git diff --check
