# WORKSPACE_MANIFEST

workspace_id: step20_mvp_completeness_hardening
branch: codex/step20-mvp-completeness-hardening
role: step20-mvp-completeness-hardening
task_type: step_implementation
active_step: Step 20 KOSPI200 MVP Completeness Hardening & Final Done Validation
owner_or_worker: Codex
created_from_commit: dd0066112f5dd773f86cc6765795b0b9ffc46ca9

## Purpose

Harden the existing KOSPI200 daily OHLCV technical multi-score scanner enough
to freeze the MVP as v0.1, then produce final Done validation evidence.

## Allowed write paths

- docs/project_checklist.md
- docs/roadmap_status.md
- docs/context/
- docs/contracts/step20_composite_contract.md
- docs/contracts/step20_ranking_contract.md
- docs/releases/
- reports/validation/step20_ranking_sanity_report.md
- src/scanner/
- src/composite/
- src/reports/
- src/validation/
- tests/scanner/
- tests/integration/
- tests/reports/
- tests/validation/
- small deterministic fixtures needed by Step 20 tests

## Read-only paths

- AGENTS.md
- completed Step artifacts except for targeted hard-stop and contract checks
- generated market data caches
- secrets and local environment files
- post-MVP universe expansion material except as forbidden-scope references

## Forbidden actions

- KOSDAQ150 implementation, config, ticker list, data ingestion, or universe schema
- futures/options data or logic
- multi-universe ranking
- valuation/fundamental scoring activation
- valuation_score, fundamental_score, undervalued_score, cheap_score, target_price,
  or valuation-aware final ranking
- backtest-driven score optimization
- realized, future, or backtest output feedback into upstream scoring/ranking
- trading recommendations or buy/sell/hold language
- proven alpha claims
- new external data ingestion
- network-dependent tests
- committing generated market caches, secrets, .env files, chart images, or local
  runtime artifacts

## Expected output

- score lineage manifest
- composite contract
- ranking contract
- MVP gap audit
- ranking sanity report
- focused Step 20 tests
- final MVP validation report
- KOSPI200 v0.1 baseline manifest

## Required validation

- python -m pytest -q tests/scanner tests/reports tests/validation
- python -m pytest -q tests/integration
- python -m pytest -q
- python scripts/context/check_context_staleness.py, if present
- python scripts/context/check_context_conflicts.py, if present
- python scripts/build_review_packet.py --step "Step 20" --stage "mvp-completeness-hardening", if present

## Handoff notes

Step 20 remains KOSPI200-only. KOSDAQ150, futures, and options are post-MVP
extension tracks. Valuation/fundamental data remains candidate-only and inactive.
Backtest output must not tune or feed upstream scoring or ranking.
