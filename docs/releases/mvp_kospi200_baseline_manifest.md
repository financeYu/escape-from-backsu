# KOSPI200 MVP v0.1 Baseline Manifest

Notice: kospi200_mvp_technical_scanner_v0_1_scope

## Scope

- MVP universe: KOSPI200 only.
- Data basis: daily OHLCV-derived technical and statistical fields.
- Scanner type: explainable technical multi-score latest ranking scanner.
- Ranking score: technical-only `final_composite_score`.
- Freeze target: v0.1 baseline after Step 20 validation.

## Included v0.1 Direct Score Inputs

- `short_term_overreaction_cross_sectional_robust_z`
- `donchian_breakout_distance_cross_sectional_robust_z`
- `efficiency_ratio_trend_cross_sectional_robust_z`

## Review-Routed Or Context Material

- `atr_adjusted_oversold_distance`
- `rsi_price_divergence`
- `bollinger_width_squeeze`
- `cmf_confirmation`
- `realized_vol_percentile`

## Composite Baseline

- Family aggregation first.
- Missing direct score values shrink to neutral `0.0`.
- `technical_composite_score` is the mean of direct family scores.
- `final_composite_score` equals `technical_composite_score` in v0.1.

## Exclusions

- KOSDAQ150 was not implemented.
- Futures/options were not implemented.
- Multi-universe ranking was not implemented.
- Valuation/fundamental scoring remains inactive.
- Backtest outputs did not feed upstream scoring or ranking.
- No external data ingestion was added.

## Release Readiness Checks

- Score lineage documented.
- Composite contract documented.
- Ranking contract documented.
- Fixture-based ranking sanity report documented.
- Focused Step 20 tests added.
- Existing guardrails for Step 15, Step 16, Step 17, Step 18, and Step 19 remain active.
