# v0.3 KOSPI200 Price ML Feature Table Contract

Status: active candidate/evidence support contract.
Parent route: `docs/extension/v0_3_research_to_strategy_adoption_route.md`.
Source project: `chart_mvp`.
Owner lane: ML/evaluator selector with root no-feedback review.

This contract identifies the `chart_mvp` processed price table as an
ML-useful KOSPI200 price feature table for `master_mvp` v0.3 review workflows.
It is a feature-table handoff contract, not production activation.

## Master Marker

Every generated row must carry:

- `schema_version = "v0_3_kospi200_price_ml_feature_table_0_1"`
- `feature_table_kind = "kospi200_price_ml_feature_table"`
- `master_mvp_context_marker = "master_mvp_ml_useful_processed_price_table"`
- `source_project = "chart_mvp"`
- `source_universe = "KOSPI200_candidate_only"`
- `owner_route = "master_mvp_v0_3_strategy_adoption"`

These fields let `master_mvp` recognize the artifact as processed stock price
data shaped for ML review, rather than raw cache data, runtime ranking output,
chart output, or trading output.

## Row Meaning

One row represents one stock on one feature-as-of date:

```text
ticker + feature_as_of_date -> price features observed up to that date
```

The row may include labels only under the label policy below. Feature columns
must use information available on or before `feature_as_of_date`.

## Required Columns

Identity and boundary columns:

- `schema_version`
- `feature_table_kind`
- `master_mvp_context_marker`
- `row_boundary`
- `source_project`
- `source_universe`
- `owner_route`
- `ticker`
- `feature_as_of_date`

Price and feature columns:

- `open`
- `high`
- `low`
- `close`
- `volume`
- `return_1d`
- `return_5d`
- `return_20d`
- `ma5`
- `ma20`
- `close_to_ma5`
- `close_to_ma20`
- `volatility_20d`
- `volume_ma20`
- `volume_to_ma20`
- `rsi14`

Label and split columns:

- `label_horizon_days`
- `label_start_date`
- `label_end_date`
- `label_forward_return_1d`
- `label_up_1d`
- `label_source`
- `supervised_label_eligible`
- `split_policy`
- `split_name`
- `random_split_allowed`

Safety columns:

- `no_lookahead_check`
- `no_feedback_check`
- `activation_boundary`
- `generated_output_boundary`
- `table_generated_at_utc`

## Label Policy

Supervised labels are eligible only when `adjusted_close` is present in the
source input.

If `adjusted_close` is missing:

- `label_source` must be `missing_adjusted_close`
- `supervised_label_eligible` must be false
- supervised label values must remain empty

This keeps ML training labels separate from raw close-price proxies and avoids
silently treating unadjusted price moves as approved outcomes.

## Boundary

Allowed:

- build ML-useful price feature rows from already available KOSPI200 price data
- write generated CSV tables under `chart_mvp/outputs/ml_ready_price_features/`
- use rows for evidence-only ML/evaluator review
- keep split assignment time-ordered before training

Blocked without later root approval:

- new market data ingestion or universe expansion
- live trading, order generation, or brokerage integration
- runtime ranking, report, or scanner score changes
- automatic backtest feedback into production behavior
- valuation or fundamental scoring activation
- production activation from model output

## Implementation Reference

Implementation entry point:

```powershell
python scripts\build_ml_price_feature_table.py --input <price_csv> --output outputs\ml_ready_price_features\kospi200_price_ml_feature_table.csv
```

Generated CSV files are runtime/generated artifacts and are not source-controlled
by default.
