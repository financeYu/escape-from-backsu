# v0.2 Model Input Handoff Contract

Status: frozen model-input handoff contract for the post-MVP `v0.2 predictive
probability score route`. This contract does not approve runtime model
implementation.

## Approved Model Input Families

The model may use only features available at or before `decision_time` from:

- `old_score_features`
- `diagnostic_old_score_features`
- coverage, missingness, warmup, and validity flags
- same-date KOSPI200 eligibility metadata
- approved daily OHLCV-derived technical features from
  `docs/extension/v0_2_raw_feature_lineage_contract.md`

## Forbidden Model Inputs

- `up_1d_label`
- `adjusted_close[t+1]`
- future returns or forward labels
- backtest returns, hit rates, realized alpha, or post-hoc evaluation metrics
- valuation/fundamental/accounting/analyst/filing/market-capitalization data
- generated report prose, chart images, manual notes, local caches, or secrets

## Handoff Columns

Every model-input row must include:

- `decision_time`
- `symbol`
- `feature_set_version`
- `source_data_availability_time`
- `feature_construction_time`
- one or more approved feature columns
- feature validity flags

Training/evaluation rows may include `up_1d_label` only in label-separated
training/evaluation datasets. Live or candidate scoring rows must not include
the label column.

## Old Score Rule

Old scores must be frozen before use as model features. If an old score formula,
window, threshold, or normalization changes, the feature-set version must
change and the validation profile must be rerun.

## Backtest Metric Rule

Backtest metrics may be joined only into evaluation reports. They must not be
joined into the model-input table.
