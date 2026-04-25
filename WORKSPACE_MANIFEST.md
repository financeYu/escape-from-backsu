# WORKSPACE_MANIFEST

workspace_id: step16_detail_report_integration
branch: integration/step16-detail-report-merge
task_type: master_integration
active_step: Step 16 security detail report implementation
owner_or_worker: Step 16 Recovery / Integration Owner
created_from_commit: 8479159d487642713ff22ea2828597b1bfcf9c51

## Purpose

Recover and verify the Step 16 per-security detail report integration by
merging the Worker A report core and Worker B guardrail/documentation branches
without broadening the roadmap scope.

## Source branches

- codex/step16-detail-report-core
- codex/step16-detail-report-guardrails

## Consumed worker manifests

- Worker A: step16_detail_report_core / codex/step16-detail-report-core / Step 16 security detail report core
- Worker B: codex_step16-detail-report-guardrails / codex/step16-detail-report-guardrails / Step 16 detail report guardrails

## Allowed work

- merge Worker A and Worker B Step 16 branches
- resolve merge conflicts conservatively
- integrate Step 16 detail report core, guardrails, docs, and tests
- add minimal integration glue only when required by validation
- run focused Step 16 tests, related compatibility tests, broad tests, and forbidden-term inspection
- run the Cross-Step Conflict Checkpoint
- report Step 16 readiness for status-control closure

## Forbidden work

- Step 17 backtest implementation
- forward, future, realized, portfolio, benchmark, CAGR, MDD, Sharpe, Sortino, hit-rate, win-rate, turnover, slippage, fee, or performance logic
- Step 18 valuation/fundamental scoring
- PER, PBR, ROE, EPS, BPS, or financial-statement inputs in Step 16 report logic
- financial/fundamental data in technical_composite_score or final_composite_score
- buy, sell, hold, entry, exit, target price, expected return, position sizing, trading signal, or investment advice language
- new ranking, re-ranking, or Step 15 ranking behavior changes unless strictly required for compatibility and validated
- roadmap status or final Step verdict changes unless explicitly instructed
- generated market-data report commits unless explicitly promoted as review fixtures
- unrelated cleanup, refactoring, staging, reset, or branch history rewrites

## Expected output

- integrated Step 16 source-controlled files
- validation summary for focused, related, broad, and static checks
- Cross-Step Conflict Checkpoint result
- Korean recovery integration report

## Required validation

- git status / branch / recent log
- python -m pytest tests/reports -q
- python -m pytest tests/validation/test_step16_detail_report_guardrails.py -q
- python -m pytest tests/scanner tests/reports tests/validation -q
- python -m pytest -q when feasible
- forbidden-term grep review
- python scripts/build_review_packet.py --step "Step 16" --stage "recovery integration validation"

## Handoff notes

Do not mark Step 16 COMPLETE in roadmap docs unless explicitly instructed.
This integration branch is ready for status-control closure only if Worker A/B
merges are clean, validation passes, generated-output boundaries are clean, and
no unresolved Step 16 boundary violation remains.
