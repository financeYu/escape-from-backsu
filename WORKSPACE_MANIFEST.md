# WORKSPACE_MANIFEST

workspace_id: step18_valuation_fundamental_expansion
branch: codex/step18-valuation-fundamental-expansion
task_type: step_implementation
active_step: Step 18 Valuation / Fundamental Expansion
owner_or_worker: Codex
created_from_commit: e075ef3c31cef2bda64bb722c01d3e1f4f9e2417

## Purpose

Implement Step 18 candidate valuation/fundamental schema, registry, guardrails, documentation, candidate-only report, and tests without activating valuation/fundamental scoring or changing technical ranking/backtest semantics.

## Allowed write paths

- src/valuation/
- src/validation/step18_valuation_fundamental_guardrails.py
- tests/valuation/
- tests/validation/test_step18_valuation_fundamental_guardrails.py
- tests/scanner/test_step18_valuation_boundary.py
- tests/backtest/test_step18_backtest_boundary.py
- docs/architecture/step18_valuation_fundamental_boundary.md
- reports/step18_valuation_fundamental_candidates.md
- config/valuation_fundamental_metrics.toml
- docs/roadmap_status.md
- docs/project_checklist.md
- quant_project_reference_for_chatgpt_project_current.md
- Quant_mvp/config/context_snapshot.toml

## Read-only paths

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

- roadmap status or final Step verdict changes unless explicitly assigned
- ranking output, composite scoring, backtest, valuation/fundamental scoring, or trading signals unless explicitly assigned by the active Step
- financial/fundamental data in technical_composite_score or final_composite_score
- generated market-data output commits unless explicitly promoted as review fixtures
- unrelated worktree cleanup, staging, committing, merging, or reset operations
- modifying technical_composite_score or final_composite_score semantics
- injecting valuation/fundamental fields into production ranking outputs
- changing Step 17 backtest logic except tests proving boundary safety
- using external network calls
- claiming valuation/fundamental alpha or predictive power
- starting Step 19 or later work

## Expected output

- Step 18 candidate-only valuation/fundamental contracts and guardrails
- candidate-only report and boundary documentation
- focused tests proving no leakage into technical scores, ranking, or backtest
- master-up handoff summary

## Required validation

- existing technical scoring tests
- existing normalization tests
- existing Step 17 backtest boundary tests
- new Step 18 tests
- forbidden-scope search

## Handoff notes

Update this manifest before editing outside the allowed write paths.
After focused validation passes, commit source-controlled branch changes by default and report the commit SHA.
Do not stage the local WORKSPACE_MANIFEST.md unless the master explicitly promotes it.
