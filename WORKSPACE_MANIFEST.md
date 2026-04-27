# WORKSPACE_MANIFEST

workspace_id: quant_post20_primary_score_migration
branch: quant/post20-primary-score-migration
task_type: quant_score_migration_contract
active_step: Post-MVP exception branch
owner_or_worker: Codex
created_from_commit: 32e608d

## Purpose

Document and configure the exception-managed migration from the MVP v0.1
technical composite score to the post-MVP up-probability candidate score while
preserving the old score as archived legacy material.

## Allowed write paths

- Quant_mvp/docs/primary_score_migration_contract.md
- Quant_mvp/docs/next_horizon_up_probability_score_design.md
- Quant_mvp/config/up_probability.toml
- Quant_mvp/config/README.md
- tests/features/test_primary_score_migration_config.py

## Read-only paths

- docs/root_hard_stops.md
- docs/roadmap_status.md
- Quant_mvp/AGENTS.md
- src/
- chart_mvp/
- gui_mvp/

## Forbidden actions

- change runtime ranking code
- change GUI score display code
- overwrite `technical_composite_score` or `final_composite_score`
- activate production ranking cutover
- remove old score outputs
- add financial/fundamental or valuation inputs
- claim buy/sell/hold, expected return, or proven alpha

## Expected output

- Migration contract naming old score archive aliases and new primary score.
- Config flags that keep cutover disabled until model validation and review.
- Focused tests for migration config safety.

## Required validation

- `python -m pytest -q tests/features/test_primary_score_migration_config.py`
- `git diff --check`
- forbidden-scope grep for production activation and investment claims

## Handoff notes

This branch records the exception plan only. It does not perform the production
cutover.
