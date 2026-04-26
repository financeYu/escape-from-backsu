# MVP v0.1 Quickstart

This guide is a compact release aid for the KOSPI200 technical MVP v0.1
pre-freeze baseline.

## What It Does

- Provides an explainable KOSPI200 daily OHLCV technical multi-score scanner.
- Produces technical-only latest ranking context for MVP v0.1.
- Preserves coverage, warmup, neutral shrinkage, validity, direct component,
  family score, and technical-only explanation fields.
- Supports detail/report and evaluation-only backtest boundaries already
  documented by Step 16 and Step 17.
- Keeps Step 19 pipeline orchestration deterministic and local by default.

## What It Does Not Do

- It does not support KOSDAQ150, futures, options, or multi-universe ranking.
- It does not activate valuation or fundamental scoring.
- It does not add new market data ingestion behavior.
- It does not use backtest results to alter score definitions, weights, or
  ranking.
- Technical MVP ranking is not a trading recommendation.
- It is not a live production readiness claim.

## Expected Main Outputs

- Latest ranking snapshot from the approved Step 15/20 ranking contract.
- Per-security technical detail report context from the Step 16 report contract.
- Evaluation-only backtest outputs under the Step 17 boundary when explicitly
  run.
- Pipeline summaries under the Step 19 generated-output boundary when explicitly
  requested.
- Source-controlled release evidence under `docs/releases/` and contracts under
  `docs/contracts/`.

## Pre-Freeze Evidence Now Available

- Local market-cache readiness:
  `reports/validation/mvp_v0_1_local_market_data_readiness.md`.
- Config/status interpretation: `docs/config_policy.md`.
- Duplicate-work handoff:
  `docs/release/PREFREEZE_OPTIMIZATION_HANDOFF.md`.

Do not repeat the local cache discovery by default. Repeat it only when
`chart_mvp/data/`, the KOSPI200 universe snapshot, or the user's request changes.

## Generated Output Locations

- Runtime security reports: `reports/security/generated/`.
- Runtime backtest reports: `reports/backtest/generated/`.
- Runtime pipeline summaries: `reports/pipeline/generated/`.
- Validation fixtures promoted for review must be small and source-controlled
  only when explicitly documented.
- Local market caches, chart images, runtime scan outputs, and generated reports
  are not default source-controlled state.

## Minimal Validation

Run the smallest relevant checks first:

```powershell
python -m pytest -q tests/context
python scripts/context/check_context_staleness.py
python scripts/context/check_context_conflicts.py
```

For scanner/report/release confidence, use the validation ladder in
`docs/release/MVP_V0_1_VALIDATION_LADDER.md`.

## Where To Look Next

- Compact baseline: `docs/context/MVP_V0_1_BASELINE.md`.
- Active pre-freeze packet:
  `docs/context/ACTIVE_PREFREEZE_OPTIMIZATION_PACKET.md`.
- Routing index: `docs/context/CONTEXT_ROUTING_INDEX.md`.
- Final Step 20 release evidence: `docs/releases/step20_mvp_final_report.md`.
- Pre-freeze handoff: `docs/release/PREFREEZE_OPTIMIZATION_HANDOFF.md`.
