# v0.3 Local Price Inputs

This directory is the approved Quant-local drop zone for candidate-only daily
price CSV files used by `Quant_mvp/scripts/run_v0_3_momentum_evaluation_evidence_cohort.py`.

These files are local evidence inputs, not source-controlled market data. Keep
actual `*_daily_prices.csv` files untracked.

The active local build source for this directory is
`chart_mvp/data/historical_kospi200/prices`. Run
`chart_mvp/scripts/build_quant_local_price_inputs.py` to synchronize all
available `*_daily_prices.csv` files into this directory and regenerate the
aggregate source/feature tables. The builder processes forward and reverse
shards in parallel, and reuses unchanged existing target files when that is
faster than copying them again.

Generated aggregate tables in this directory:

- `quant_local_price_source_rows.csv`: normalized OHLCV source rows for every
  synchronized daily-price file.
- `kospi200_price_ml_feature_table.csv`: ML-useful processed price features for
  candidate/evidence review only.
- `local_price_input_inventory.csv`: synchronized file inventory.
- `local_price_input_manifest.json`: build counts, boundaries, shard results,
  and reuse/copy status.
- `adjusted_close_need_candidates.csv`: ticker-level adjusted-close triage
  including raw jump/gap priority, corporate-action event match status, and
  the next review bucket.
- `adjusted_close_need_summary.json`: compact counts for adjusted-close
  readiness and remaining investigation buckets.

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
