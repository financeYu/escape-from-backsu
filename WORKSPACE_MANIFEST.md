# WORKSPACE_MANIFEST

workspace_id: quant_post20_up_probability_design
branch: quant/post20-up-probability-design
task_type: quant_score_candidate_design
active_step: Post-MVP candidate design only
owner_or_worker: Codex
created_from_commit: 729be2c

## Purpose

Define a planning/design-only post-MVP candidate path and Stage A doc-contract
approval materials for next-horizon up-probability scoring without changing MVP
v0.1 scoring, ranking, GUI semantics, backtest behavior, valuation status, or
data ingestion.

## Allowed write paths

- WORKSPACE_MANIFEST.md
- docs/extension/v0_1n_strategy_composition_v0_2_plan.md
- docs/extension/v0_1n_implementation_approval_packet.md
- docs/context/EXTENSION_REGISTRY.toml
- Quant_mvp/docs/next_horizon_up_probability_score_design.md
- Quant_mvp/docs/score_catalog.md
- Quant_mvp/docs/v0_1n_strategy_signal_schema.md
- Quant_mvp/docs/v0_1n_strategy_registry_contract.md

## Read-only paths

- AGENTS.md
- docs/root_hard_stops.md
- docs/roadmap_status.md
- docs/context/POST_MVP_AGENT_TASK_PACKET.md
- docs/context/domain/technical_scoring_context.md
- Quant_mvp/AGENTS.md
- Quant_mvp/config/
- src/
- tests/
- chart_mvp/
- gui_mvp/

## Forbidden actions

- change `technical_composite_score` or `final_composite_score`
- implement model training, ranking, reports, or GUI behavior
- implement candidate helpers, source features, tests, or config changes
- activate production scoring or ranking
- create generated market data, runtime reports, chart images, or caches
- add financial/fundamental or valuation inputs
- use backtest results to redefine score semantics
- make buy/sell/hold, expected-return, or proven-alpha claims

## Expected output

- Additive root extension design for the v0.1n candidate planning line and
  future v0.2 freeze criteria.
- Additive v0.1n implementation approval preparation packet.
- Stage A doc-contract schema and registry contract documents.
- Additive Quant design updates aligning next-horizon up-probability notes with
  the v0.1n planning line.
- Route-only extension registry entry.

## Required validation

- `git diff --check`
- Confirm no source/config/test/runtime files changed
- Targeted forbidden-scope grep for production activation and investment claims
- Manual scope review of changed files

## Handoff notes

This branch is currently design-only. It must not be treated as production
ranking, GUI score replacement, model training approval, helper implementation
approval, config activation, or adoption approval.
