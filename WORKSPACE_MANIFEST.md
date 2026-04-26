# WORKSPACE_MANIFEST

workspace_id: master_up_post20_pending
branch: codex/master-up-post20-pending
role: root-master-integration
task_type: master_up_integration_preparation
active_step: post-Step20 / Step 20 COMPLETE follow-up
owner_or_worker: root master agent
created_from_commit: f6f51e9eaa15562899611124646859031cc0533e

## Purpose

Prepare the unmerged post-Step20 support branches for root/master review by
integrating their branch commits into one conflict-resolved master-up branch.

This branch preserves Step 20 COMPLETE status and does not reopen completed
roadmap implementation. It collects:

1. post-Step20 runtime and validation optimizations
2. pre-freeze config, release, and local market-data readiness notes
3. review_mvp worktree-exclusion and modification-boundary repair
4. research ingestion operations optimization handoff

## Allowed Write Paths

- WORKSPACE_MANIFEST.md
- Quant_mvp/config/
- chart_mvp/README.md
- chart_mvp/TEMPORARY_TOP5_OVERRIDE.md
- chart_mvp/src/stock_core/cache/
- chart_mvp/src/stock_core/pipeline/
- chart_mvp/src/stock_core/providers/
- chart_mvp/src/stock_core/ranking/
- chart_mvp/tests/
- config/
- docs/config_policy.md
- docs/context/
- docs/development_environment.md
- docs/release/
- docs/releases/
- docs/review_mvp_policy.md
- quant_project_reference_for_chatgpt_project_current.md
- reports/validation/
- reserch_mvp/config/research_queries.toml
- reserch_mvp/reports/research_ingestion/
- reserch_mvp/research_ingestion/
- reserch_mvp/src/research_ingestion/
- reserch_mvp/tests/research_ingestion/
- review_mvp/
- scripts/
- src/backtest/
- src/reports/
- tests/context/
- tests/reports/

## Read-Only Paths

- AGENTS.md
- docs/project_checklist.md
- docs/roadmap_status.md
- completed Step artifacts except targeted handoff, context, config, and
  validation references needed by the four collected support branches
- generated market caches
- generated runtime report roots except explicit validation/handoff reports
- secrets and local environment files

## Forbidden Actions

- KOSDAQ150, futures, options, or multi-universe implementation
- new external market-data source ingestion
- score formula, score weight, score adoption, normalization, ranking,
  report, backtest, or valuation semantic changes beyond already committed
  support-branch patches
- `technical_composite_score` or `final_composite_score` semantic changes
- valuation/fundamental scoring activation or financial/fundamental data in
  technical/final composite scoring
- backtest-driven score optimization or return feedback into upstream ranking
- trading recommendations, buy/sell/hold wording, or proven-alpha claims
- committing raw local market caches, chart images, secrets, `.env` files, or
  nested worktree artifacts
- unrelated cleanup, reset, history rewrite, or broad refactor

## Expected Handoff Output

- one conflict-resolved master-up integration branch
- retained branch-local handoff documents for post-Step20, pre-freeze,
  review_mvp, and research ingestion support work
- focused validation summary
- latest local Quant project context snapshot refresh
- remaining risk summary for root/master final merge

## Required Validation

- python scripts/run_local_validation.py chart
- python scripts/run_local_validation.py context
- python scripts/run_local_validation.py reports-backtest
- python -m pytest -q -p no:cacheprovider reserch_mvp/tests/research_ingestion
- python -m pytest -q -p no:cacheprovider tests/context tests/test_step11_composite_schema.py
- python -m unittest discover -s review_mvp/tests -v
- python scripts/context/check_context_staleness.py
- python scripts/context/check_context_conflicts.py
- python scripts/build_review_packet.py --step "Post-Step20" --stage "master-up-pending"
- python scripts/refresh_quant_project_context.py
- git diff --check

## Handoff Notes

This branch is intended as a master-up waiting branch. Root/master may inspect
the focused handoff documents first and avoid repeating completed Step 1-20
history unless validation or conflict checks point to a specific risk.
