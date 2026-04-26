# WORKSPACE_MANIFEST

workspace_id: step19_automatic_execution_pipeline
branch: codex/step19-automatic-execution-pipeline
task_type: step_implementation
active_step: Step 19 Automatic Execution Pipeline
owner_or_worker: Codex
created_from_commit: be1b07f218c0621a2e3640705cb391798973ff2f
base_branch: integration/step18-valuation-fundamental-expansion-merge

## Purpose

Implement Step 19 automatic execution pipeline without changing scoring, ranking, report, backtest, or valuation semantics.

role: step19-automatic-execution-pipeline

allowed scope: Step 19 orchestration/pipeline code, pipeline config, pipeline validation, tests, docs.

forbidden scope: new scoring formulas, ranking semantic changes, report semantic changes, backtest semantic changes, valuation/fundamental scoring activation, KOSDAQ150/futures/options expansion, external data ingestion, Step 20 final done validation.

expected output: deterministic automatic execution pipeline, guardrails, tests, docs, validation report.

## Allowed write paths

- WORKSPACE_MANIFEST.md
- docs/step19_automatic_execution_pipeline.md
- docs/architecture/step19_pipeline_boundary.md
- reports/pipeline/README.md
- config/step19_pipeline.toml
- src/pipeline/
- src/validation/step19_pipeline_guardrails.py
- scripts/run_step19_pipeline.py
- tests/pipeline/
- tests/validation/test_step19_pipeline_guardrails.py

## Read-only paths

- AGENTS.md
- docs/project_checklist.md
- docs/roadmap_status.md
- docs/context/
- docs/workspace_parallel_work_policy.md
- docs/cross_step_conflict_check.md
- src/scanner/
- src/reports/
- src/backtest/
- src/valuation/
- src/composite/
- src/scores/

## Forbidden actions

- roadmap status or final Step verdict changes unless explicitly assigned
- ranking output, composite scoring, backtest, valuation/fundamental scoring, or trading signals unless explicitly assigned by the active Step
- financial/fundamental data in technical_composite_score or final_composite_score
- generated market-data output commits unless explicitly promoted as review fixtures
- unrelated worktree cleanup, staging, committing, merging, or reset operations
- new scoring formulas
- ranking semantic changes
- detail report semantic changes
- backtest semantic changes
- valuation/fundamental scoring activation
- KOSDAQ150/futures/options expansion
- external data ingestion
- Step 20 final validation or completion claims
- network calls or secret usage

## Expected output

- deterministic automatic execution pipeline
- pipeline guardrails
- focused tests
- pipeline docs
- validation and handoff report

## Required validation

- python -m pytest -q tests/pipeline tests/validation/test_step19_pipeline_guardrails.py
- python -m pytest -q tests/scanner tests/reports tests/backtest tests/validation
- python -m pytest -q
- python scripts/build_review_packet.py --step "Step 19" --stage "automatic-execution-pipeline-ready"

## Handoff notes

Update this manifest before editing outside the allowed write paths.
After focused validation passes, commit source-controlled branch changes by default and report the commit SHA.
This Step 19 assignment explicitly requires the root WORKSPACE_MANIFEST.md update; include it with the branch-local handoff unless master integration later chooses a different manifest policy.
