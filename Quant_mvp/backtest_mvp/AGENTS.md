# Quant Backtest MVP Agent

## Purpose

`Quant_mvp/backtest_mvp` owns the conservative, evaluation-only backtest module
for the Quant project.

This is a Quant-dependent subproject. It may evaluate frozen technical ranking
snapshots against OHLCV price inputs and produce backtest-specific result
objects or generated evaluation artifacts. It must not redefine scores,
normalization, adoption decisions, ranking semantics, report semantics,
valuation/fundamental scoring, or data ingestion.

Legacy imports through `src.backtest` are compatibility facades only. New code
should import `Quant_mvp.backtest_mvp`.

## Allowed Work

- maintain `BacktestConfig`, input contracts, result objects, and the
  conservative runner
- validate ranking and price inputs for the evaluation-only boundary
- preserve KOSPI200/Naver six-character alphanumeric ticker handling by default
  while allowing explicit injected symbol policies for extension contracts
- expose generated evaluation artifacts only under generated-output paths

## Forbidden Work

- feeding realized backtest results into score, adoption, ranking, or report
  construction
- tuning score formulas, weights, thresholds, or ranking criteria from
  backtest results
- activating valuation/fundamental scoring or point-in-time financial data
- claiming alpha, profitability, expected returns, valuation, target prices, or
  trading recommendations
- committing generated reports, raw market data, caches, chart images, or
  ad-hoc local exports

## Validation

Preferred focused validation from the repository root:

```powershell
python -m pytest -q tests/backtest tests/validation/test_step19_pipeline_guardrails.py
```
