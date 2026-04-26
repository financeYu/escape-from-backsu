# Quant Backtest GUI Agent

## Purpose

This sidecar owns local GUI execution and inspection for the existing
evaluation-only conservative backtest engine.

This is MVP v0.1 pre-freeze support work. It must not be treated as Step 21
entry or as a new backtest/scoring roadmap phase.

It may:

- load user-selected ranking snapshot CSV files
- load user-selected OHLCV price CSV files
- adjust allowed `BacktestConfig` parameters through a GUI
- run `src.backtest.run_conservative_backtest`
- display summary, period, security, and equity-curve views
- export generated evaluation artifacts to a user-selected local directory

It must not:

- change score definitions, score formulas, normalization, adoption, ranking,
  report semantics, valuation/fundamental activation, or data ingestion
- feed realized backtest results into upstream score, ranking, report, or
  selection criteria
- claim alpha, profitability, expected return, valuation, target price, or
  trading recommendation
- commit generated output files, raw market data, caches, chart images, or
  ad-hoc local reports

## Validation

Preferred focused validation:

```powershell
python -m pytest -q tests/quant_backtest_gui tests/backtest
```
