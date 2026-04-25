# WORKSPACE_MANIFEST

workspace_id: codex_step16-detail-report-guardrails
branch: codex/step16-detail-report-guardrails
task_type: step_implementation
active_step: Step 16 Detail Report Guardrails
owner_or_worker: Worker B
created_from_commit: 8479159d487642713ff22ea2828597b1bfcf9c51

## Purpose

Implement Step 16 detail report validation guardrails and boundary documentation without backtest, valuation, trading signal, or ranking generation.

## Allowed write paths

- WORKSPACE_MANIFEST.md
- src/validation/step16_detail_report_guardrails.py
- tests/validation/test_step16_detail_report_guardrails.py
- tests/reports/test_step16_report_boundary_integration.py
- reports/security/README.md
- docs/architecture/step16_report_backtest_boundary.md

## Read-only paths

- AGENTS.md
- docs/project_checklist.md
- docs/roadmap_status.md
- docs/workspace_parallel_work_policy.md
- docs/architecture/research_backtest_boundary_design.md
- src/scanner/latest_ranking.py
- src/validation/step15_latest_ranking_guardrails.py
- docs/step14_adoption_synthesis.md
- src/selection/adoption_synthesis_contracts.py
- reports/selection/README.md
- src/reports/security_detail_report_contracts.py
- src/reports/security_detail_report.py
- tests/reports/test_step16_security_detail_report_contracts.py
- tests/reports/test_step16_security_detail_report.py
- docs/step16_security_detail_report.md

## Forbidden actions

- roadmap status or final Step verdict changes unless explicitly assigned
- ranking output, composite scoring, backtest, valuation/fundamental scoring, or trading signals unless explicitly assigned by the active Step
- financial/fundamental data in technical_composite_score or final_composite_score
- generated market-data output commits unless explicitly promoted as review fixtures
- unrelated worktree cleanup, staging, committing, merging, or reset operations
- editing Worker A owned Step 16 files
- Step 17 backtest implementation
- future return labels or performance metrics
- valuation/fundamental scoring
- buy/sell/hold or trading signal generation
- new ranking or re-ranking generation

## Expected output

- Step 16 guardrail validator
- focused toy-data tests
- boundary documentation
- worker handoff summary

## Required validation

- python -m pytest tests/validation -q
- python -m pytest tests/reports -q if integration test is added
- forbidden-scope search
- git status review

## Handoff notes

Update this manifest before editing outside the allowed write paths.
After focused validation passes, commit source-controlled branch changes by default and report the commit SHA.
Do not stage the local WORKSPACE_MANIFEST.md unless the master explicitly promotes it.
