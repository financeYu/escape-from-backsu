# WORKSPACE_MANIFEST

workspace_id: step20_prefreeze_optimization_support
branch: codex-step20-prefreeze-optimization
role: minor-support-prefreeze
task_type: post_step20_prefreeze_optimization
active_step: Step 20.5 pre-freeze optimization support
owner_or_worker: Codex support worker
created_from_commit: 1ad7727d7f73a5eac3b1a20f02967eb12a11a177

## Purpose

Complete the user's three requested pre-freeze optimization tasks without
changing quant logic:

1. record read-only local KOSPI200 market-cache readiness evidence
2. clarify config/status wording so Step 20 source contracts are not confused
   with disabled config-driven runtime switches
3. finish release quickstart / validation ladder notes and a duplicate-work
   handoff so the root agent does not repeat the same inspection

This support branch exists because the main workspace is root/master
integration-only.

## Allowed write paths

- WORKSPACE_MANIFEST.md
- config/global.toml
- config/scores.toml
- docs/config_policy.md
- docs/context/ACTIVE_PREFREEZE_OPTIMIZATION_PACKET.md
- docs/context/CONTEXT_ROUTING_INDEX.md
- docs/context/decision_log.md
- docs/release/MVP_V0_1_QUICKSTART.md
- docs/release/MVP_V0_1_VALIDATION_LADDER.md
- docs/release/PREFREEZE_OPTIMIZATION_HANDOFF.md
- Quant_mvp/config/README.md
- Quant_mvp/config/scores.toml
- reports/validation/mvp_v0_1_local_market_data_readiness.md

## Read-only paths

- AGENTS.md
- docs/project_checklist.md
- docs/roadmap_status.md
- docs/contracts/
- docs/releases/
- src/
- tests/
- review_mvp/
- chart_mvp/data/
- generated market data caches and runtime report roots

## Forbidden actions

- score formula, score weight, indicator, normalization, ranking, report,
  backtest, valuation, or data-ingestion logic changes
- KOSDAQ150, futures, options, or multi-universe implementation
- valuation/fundamental scoring activation
- financial/fundamental data in `technical_composite_score` or
  `final_composite_score`
- backtest output feedback into upstream scoring or ranking
- trading recommendations, buy/sell/hold wording, proven-alpha claims, or
  performance claims
- committing raw local market caches, chart images, secrets, or generated
  runtime outputs
- broad cleanup, reset, history rewrite, or unrelated edits

## Expected output

- A small read-only local market-cache readiness report with no ranking or
  performance claim.
- Config/status wording that distinguishes source-implemented MVP contracts
  from disabled config-driven activation switches.
- Quickstart and validation ladder updates that route future work directly to
  the completed pre-freeze evidence.
- A handoff explicitly saying which work is already done and when root should
  or should not repeat it.

## Required validation

- python -m pytest -q tests/context
- python scripts/context/check_context_staleness.py
- python scripts/context/check_context_conflicts.py
- git diff --check

Broader scanner/report validation is not required unless this patch touches
runtime source, tests, contracts, ranking semantics, or report semantics.

## Handoff notes

Root/master should consume `docs/release/PREFREEZE_OPTIMIZATION_HANDOFF.md`
instead of re-reading broad Step history or re-running the same cache discovery.
Repeat the local market-cache inspection only if `chart_mvp/data/` changes, the
universe snapshot changes, or the user explicitly asks for fresh runtime data
validation.
