# Quant Backtest MVP Agent

## Purpose

`Quant_mvp/backtest_mvp` owns the conservative, evaluation-only backtest module
for the Quant project.

This is a Quant-dependent subproject. In the active v0.3 route, it may evaluate
approved `StrategyCandidate` inputs or frozen technical ranking snapshots
against OHLCV price inputs and produce evidence-only `EvaluationEvidence`
artifacts. It must not make adoption decisions, activate valuation/fundamental
scoring, expand data ingestion, or trigger production activation.

Legacy imports through `src.backtest` are compatibility facades only. New code
should import `Quant_mvp.backtest_mvp`.

## Allowed Work

- maintain `BacktestConfig`, input contracts, result objects, and the
  conservative runner
- validate ranking and price inputs for the evaluation-only boundary
- preserve KOSPI200/Naver six-character alphanumeric ticker handling by default
  while allowing explicit injected symbol policies for extension contracts
- expose generated `EvaluationEvidence` artifacts only under generated-output
  paths

## Forbidden Work

- feeding realized backtest results into automatic production activation
- tuning production behavior from backtest results
- activating valuation/fundamental scoring or point-in-time financial data
- activating valuation conclusions or target-price workflows
- committing generated reports, raw market data, caches, chart images, or
  ad-hoc local exports

## Validation

Preferred focused validation from the repository root:

```powershell
.venv\Scripts\python.exe -m pytest -q tests/backtest tests/validation/test_step19_pipeline_guardrails.py
```

Use the parent root `.venv`; do not install pytest in this subproject.

For repository text search on Windows, do not rely on bare `rg` if it resolves
to a Codex WindowsApps bundled executable. From the repository root, use:

```powershell
powershell -ExecutionPolicy Bypass -File Quant_mvp\scripts\quant_rg.ps1 ...
```

If bare `rg` fails with access denied, record it as a blocked cheap check under
the root cost-aware protocol and continue with the Quant wrapper above.
