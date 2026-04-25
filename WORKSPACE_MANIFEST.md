# WORKSPACE_MANIFEST

workspace_id: step15_worker_a_core
branch: step15-worker-a-core
task_type: step_implementation
active_step: Step 15 latest ranking output implementation
owner_or_worker: Worker A
created_from_commit: 8de10055e4989da603cd143f0b744114024aaeda

## Purpose

Implement the core Step 15 latest-ranking output logic strictly from the roadmap/source-of-truth, without expanding into Step 16+ reports, Step 17 backtesting, or Step 18 valuation/fundamental scoring.

## Allowed write paths

- WORKSPACE_MANIFEST.md
- src/scanner/
- tests/scanner/

## Read-only paths

- AGENTS.md
- README.md
- docs/project_checklist.md
- docs/roadmap_status.md
- docs/workspace_parallel_work_policy.md
- docs/roadmap_archive/
- Quant_mvp/AGENTS.md
- Quant_mvp/docs/
- Quant_mvp/config/
- Quant_mvp/agents/
- src/composite/
- src/selection/
- src/scores/
- tests/selection/
- tests/diagnostics/
- tests/data_validation/
- tests/indicators/
- tests/preprocess/
- chart_mvp/
- reserch_mvp/
- review_mvp/
- reports/

## Forbidden actions

- roadmap status changes
- project checklist completion status changes
- integration report edits
- audit agent definition edits
- research ingestion agent definition edits
- Worker B owned broad integration test edits
- Step 16+ detailed stock reports
- Step 17 backtest or realized-return validation
- Step 18 valuation/fundamental scoring
- financial/fundamental data in technical_composite_score or final_composite_score
- production ranking activation beyond the explicit Step 15 source-of-truth
- forward-looking labels, alpha validation, future returns, buy/sell/trading signals

## Expected output

- Minimal core implementation files for Step 15 latest ranking output
- Focused unit tests directly covering Worker A core logic
- Korean worker handoff report with guardrail and integration notes

## Required validation

- Focused Step 15 unit tests for changed files
- Forbidden-scope search for backtest, valuation/fundamental scoring, future-return leakage, and trading-signal language in changed files

## Handoff notes

- Step 15 scope must be confirmed from repository source files before any implementation beyond this manifest.
