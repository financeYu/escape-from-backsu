# Quant Backtest GUI

`Quant_mvp/backtest_gui` is a local, evaluation-only GUI sidecar for the
canonical conservative backtest engine in `Quant_mvp/backtest_mvp`.

This is MVP v0.1 pre-freeze support work only. It does not open Step 21 or
change the frozen Step 20 scoring/ranking boundary.

Run from the repository root:

```powershell
python -m Quant_mvp.backtest_gui
```

The GUI lets you:

- select an upstream ranking snapshot CSV
- select an OHLCV price CSV
- adjust allowed `BacktestConfig` parameters
- run the existing conservative backtest
- inspect summary, period, security, and equity-curve views
- export generated result files to a user-selected local directory

Boundary:

- The GUI does not define scores.
- The GUI does not redefine ranking criteria.
- The GUI does not update upstream ranking/report outputs.
- The GUI does not perform valuation/fundamental scoring.
- Backtest results remain evaluation-only.

Generated exports should stay local, normally under ignored output paths such
as `reports/backtest/generated/`.
