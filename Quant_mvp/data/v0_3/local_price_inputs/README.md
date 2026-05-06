# v0.3 Local Price Inputs

This directory is the approved Quant-local drop zone for candidate-only daily
price CSV files used by `Quant_mvp/scripts/run_v0_3_momentum_evaluation_evidence_cohort.py`.

These files are local evidence inputs, not source-controlled market data. Keep
actual `*_daily_prices.csv` files untracked.

## Required File Shape

- File name: `<ticker>_daily_prices.csv`
- Example ticker file: `005930_daily_prices.csv`
- Scope: approved candidate-only daily price inputs for v0.3 EvaluationEvidence
- Date range currently required by the selected cohort: rows on or before
  `2025-12-31`
- Minimum coverage currently reported by dry-run: at least `42` rows per ticker
  for the selected candidate rules

The current runner reads columns by position from each CSV:

| Position | Meaning used by runner |
| --- | --- |
| 1 | `date` |
| 2 | `close` |
| 4 | `open` |
| 5 | `high` |
| 6 | `low` |
| 7 | `volume` |

The file must have at least seven columns. The ticker is derived from the file
name prefix before `_daily_prices.csv`.

## Boundary

- Do not use this directory for live trading, production ranking, valuation, or
  model training activation.
- Do not place chart runtime outputs, caches, or external project paths here.
- After approved CSVs are added locally, rerun the dry-run readiness check before
  writing `evidence_recorded` EvaluationEvidence.
