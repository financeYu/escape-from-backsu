# WORKSPACE_MANIFEST

workspace_id: step20_final_integration_merge
branch: main
role: root-master-integration
task_type: master_integration
active_step: Step 20 KOSPI200 MVP Completeness Hardening & Final Done Validation
owner_or_worker: root master agent
created_from_commit: dd0066112f5dd773f86cc6765795b0b9ffc46ca9

## Purpose

Integrate the Step 20 KOSPI200 MVP completeness hardening branch, Step 20
review-noise repair branch, pre-Step20 development-environment branch, and the
context-compression patch into one validated main-branch commit.

Step 20 closes the KOSPI200 daily OHLCV technical scanner MVP as v0.1
freeze-ready. The context patch keeps future Step 20+ work routed through
latest-only context rather than repeated completed-Step history.

## Allowed write paths

- WORKSPACE_MANIFEST.md
- docs/project_checklist.md
- docs/roadmap_status.md
- docs/context/
- docs/contracts/step20_composite_contract.md
- docs/contracts/step20_ranking_contract.md
- docs/development_environment.md
- docs/releases/
- pyproject.toml
- requirements-dev.txt
- quant_project_reference_for_chatgpt_project_current.md
- reports/validation/step20_ranking_sanity_report.md
- review_mvp/
- scripts/context/
- src/scanner/
- src/composite/
- src/reports/
- src/validation/
- tests/context/
- tests/scanner/
- tests/integration/
- tests/reports/
- tests/validation/
- tests/step20_fixtures.py

## Read-only paths

- AGENTS.md
- completed Step artifacts except for targeted hard-stop, context, and contract checks
- generated market data caches
- generated report roots except the explicit Step 20 validation fixture report
- secrets and local environment files
- post-MVP universe expansion material except as forbidden-scope references

## Forbidden actions

- KOSDAQ150 implementation, config, ticker list, data ingestion, or universe schema
- futures/options data or logic
- multi-universe ranking
- valuation/fundamental scoring activation
- valuation_score, fundamental_score, undervalued_score, cheap_score, target_price,
  or valuation-aware final ranking
- financial/fundamental data in `technical_composite_score` or `final_composite_score`
- backtest-driven score optimization
- realized, future, or backtest output feedback into upstream scoring/ranking
- trading recommendations or buy/sell/hold language
- proven alpha claims
- new external data ingestion
- network-dependent tests
- committing generated market caches, secrets, .env files, chart images, local
  runtime artifacts, or nested worktree directories
- unrelated cleanup, reset, stash deletion, or history rewrite

## Expected output

- integrated Step 20 score lineage manifest, composite contract, ranking contract,
  MVP gap audit, ranking sanity report, final MVP report, and v0.1 baseline manifest
- latest-only context files, Step 20 context packet, archive summary, usage policy,
  decision log, and context routing updates
- development environment declaration files
- Step 20 review_mvp static-review-noise repair
- focused and full validation summary
- one integration commit on `main`
- post-commit context snapshot refresh

## Required validation

- python -m pytest -q tests/context
- python -m pytest -q tests/scanner tests/reports tests/validation
- python -m pytest -q tests/integration
- python -m pytest -q
- python scripts/context/check_context_staleness.py
- python scripts/context/check_context_conflicts.py
- python scripts/build_review_packet.py --step "Step 20" --stage "final-integration-merge"
- python review_mvp/review.py on Step 20 changed Python paths with `--fail-on medium`
- python -m unittest discover -s review_mvp/tests -v
- git diff --check

## Handoff notes

Step 20 remains KOSPI200-only. KOSDAQ150, futures, and options are post-MVP
extension tracks. Valuation/fundamental data remains candidate-only and inactive.
Backtest output must not tune or feed upstream scoring or ranking.

The `worktrees/` directory under this workspace is local workspace state and
must not be staged or committed.
