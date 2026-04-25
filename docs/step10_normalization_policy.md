# Step 10 Normalization Policy

## 1. Purpose

Step 10 implements normalization policy for the Step 9 Research Tester raw score
output. The purpose is to make normalized candidates and diagnostics available
for later review while preserving the roadmap boundary.

Step 10 covers:

- ticker-local time-series normalization primitives
- same-date cross-sectional normalization primitives
- robust z-score behavior
- deterministic tie handling without rank output
- normalization diagnostics for review material
- documentation of forbidden outputs and Step 11 handoff items

Part A owns ticker-local time-series normalization. Part B owns same-date
cross-sectional normalization and diagnostics. Step 10 completion means the
normalization layer is ready for review; it does not enable ranking, composite
scoring, backtesting, or valuation/fundamental scoring.

## 2. Step 9 Raw Score Input Contract

Required identity columns:

- `ticker`
- `date`

Required Step 9 raw score columns:

- `short_term_overreaction_raw`
- `atr_adjusted_oversold_distance_raw`
- `donchian_breakout_distance_raw`
- `bollinger_width_squeeze_raw`
- `cmf_confirmation_raw`
- `rsi_price_divergence_raw`
- `realized_vol_percentile_raw`
- `efficiency_ratio_trend_raw`

Required Step 9 metadata columns:

- `score_warmup_state`
- `score_coverage_status`
- `score_data_quality_flag`
- `minimum_history_required`

Score-specific missing reason columns may be present and should remain available
for review, but Step 10 normalization does not require them for denominator
construction.

Input guardrails:

- `ticker` must remain a six-character string with leading zeros preserved.
- `ticker` / `date` pairs must be unique.
- `date` must be parseable and normalized only within the same calendar date.
- valuation/fundamental fields such as `PER`, `PBR`, `ROE`, valuation scores, or
  financial/fundamental prefixes must not enter normalization.
- Step 9 raw score formulas are not redefined in Step 10.

## 3. Part A / Part B Boundary

Part A owns ticker-local time-series normalization.

Part B owns same-date cross-sectional normalization and diagnostics.

Part A does not implement:

- same-date universe normalization
- cross-sectional diagnostics
- ranking or relative same-date ordering output

Part B does not implement:

- ticker-local rolling or expanding normalization
- per-ticker historical percentiles
- time-series robust z-score core
- chart overlay semantics for a single ticker

The Part A and Part B outputs are separate scope-specific tables that share
Step 9 identity and metadata contracts.

## 4. Time-Series Normalization Policy

Time-series normalization uses only ticker-local observations with
`date <= current date`.

Policy:

- group key is `ticker`
- sort key is `ticker`, `date`
- duplicate `ticker` / `date` rows are rejected
- leading-zero tickers are preserved as strings
- future rows are not referenced
- ticker boundaries are never crossed
- the current row is included in its own normalization context
- minimum observation count is config-first:

```text
Quant_mvp/config/thresholds.toml -> [quality].min_non_nan_observations
```

- default rolling context is config-first:

```text
Quant_mvp/config/windows.toml -> [normalization].time_series_window
```

Public APIs:

- `normalize_timeseries_score(...)`
- `normalize_timeseries_scores(...)`
- `robust_zscore_expanding(...)`
- `apply_winsorization(...)`
- `apply_clipping(...)`
- `load_timeseries_normalization_config(...)`

Time-series output columns use the `{score_name}_ts_*` namespace:

- `{score_name}_ts_robust_zscore`
- `{score_name}_ts_status`
- `{score_name}_ts_coverage_status`
- `{score_name}_ts_data_quality_flag`
- `{score_name}_ts_observation_count`
- `{score_name}_ts_scale`
- `{score_name}_ts_scale_method`
- `{score_name}_ts_winsorized_value`
- `{score_name}_ts_was_winsorized`
- `{score_name}_ts_was_clipped`

Status values:

- `ok`
- `warmup`
- `insufficient_history`
- `missing_raw_score`
- `invalid_raw_score`
- `zero_scale`

Coverage status is `adequate` only for `ok` rows and `blocked` otherwise.
Data-quality flags use Step 8 names such as `valid`, `warmup`,
`insufficient_history`, `missing_required_input`, `invalid_numeric`,
`zero_dispersion`, and `clipped_outlier`.

## 5. Cross-Sectional Normalization Policy

Cross-sectional normalization uses only rows with the exact same `date`.

Eligibility for the same-date denominator:

- raw score value must be finite numeric
- `score_warmup_state` must be `ready`
- `score_coverage_status` must be `adequate`, `partial`, or `sparse`
- hard data-quality flags such as invalid ticker, lost leading zero, invalid
  date, future date, or duplicate ticker/date must block denominator inclusion

Rows excluded from the denominator keep visible quality flags. Missing, warmup,
insufficient-history, or blocked coverage rows are not filled with optimistic
values.

Default minimum cross-sectional count is config-driven:

```text
Quant_mvp/config/thresholds.toml -> [quality].min_cross_section_count
```

The reference value is `20`. Tests may pass smaller toy-data values explicitly.

Public APIs:

- `normalize_cross_sectional_score(...)`
- `normalize_cross_sectional_scores(...)`
- `robust_zscore_cross_sectional(...)`
- `load_cross_sectional_normalization_config(...)`

Cross-sectional output columns use the `{score_name}_cross_sectional_*`
namespace:

- `{score_name}_cross_sectional_robust_z`
- `{score_name}_cross_sectional_valid_count`
- `{score_name}_cross_sectional_status`
- `{score_name}_cross_sectional_scale_method`
- `{score_name}_cross_sectional_quality_flag`
- `{score_name}_cross_sectional_winsorized`
- `{score_name}_cross_sectional_clipped`

Cross-sectional status values are `adequate` for eligible normalized rows and
`blocked` for rows that cannot receive a same-date normalized value.

## 6. Robust Z-Score / Winsorization / Clipping

Implemented primitive:

```text
robust_z = (value - same_date_median) / (1.4826 * same_date_MAD)
MAD = median(abs(value - same_date_median))
```

Policy:

- median and MAD are calculated only within the active context
- time-series context is ticker-local current/prior rows
- cross-sectional context is the same date only
- future dates are not referenced
- unrelated dates are not referenced
- NaN and infinite raw values are excluded
- insufficient observation count leaves the normalized value missing
- zero MAD uses documented IQR fallback only when IQR is positive
- all-tie / zero-dispersion contexts leave the normalized value missing
- optional winsorization and z-score clipping are counted in diagnostics
- tied raw values receive identical normalized values
- no rank column is produced

Config sources:

```text
Quant_mvp/config/thresholds.toml -> [outliers].winsorize_lower_pct
Quant_mvp/config/thresholds.toml -> [outliers].winsorize_upper_pct
```

Robust z-score clipping is not configured yet. It remains opt-in through
explicit caller config and is not silently activated.

## 7. Diagnostics Schema

Diagnostics are review material only. They are not alpha evidence, not an
adoption decision, not a buy/sell signal, and not valuation evidence.

Implemented public APIs:

- `build_normalization_diagnostics(...)`
- `summarize_normalization_coverage(...)`

Diagnostic tables:

- `score_coverage`
- `date_cross_sectional_valid_count`
- `ticker_available_observation_count`
- `normalization_event_counts`
- `warmup_distribution`
- `data_quality_flag_distribution`
- `coverage_status_distribution`

Required diagnostic fields include, where applicable:

- `diagnostic_name`
- `score_name`
- `raw_column`
- `normalization_scope`
- `date`
- `ticker`
- `ticker_count`
- `row_count`
- `valid_observation_count`
- `cross_sectional_valid_count`
- `available_observation_count`
- `missing_count`
- `coverage_ratio`
- `warmup_count`
- `insufficient_history_count`
- `blocked_coverage_count`
- `winsorized_count`
- `clipped_count`
- `zero_scale_fallback_count`
- `zero_dispersion_count`
- `insufficient_cross_section_count`
- `diagnostic_status`
- `notes`

## 8. Forbidden Outputs

Forbidden Outputs / no ranking / no composite / no backtest boundary:

- no ranking
- no latest ranking
- no rank column
- no composite score
- no `technical_composite_score`
- no `final_composite_score`
- no backtest
- no forward return
- no future return
- no buy/sell/signal output
- no valuation/fundamental scoring
- no financial/fundamental data merge
- no PER/PBR/ROE use

Step 10B normalized values must not be described as production rankings,
investment recommendations, alpha signals, valuation opinions, or final
selection outputs.

## 9. Step 11 Handoff

Step 11 composite design remains waiting after Step 10. It must begin only
under a separate explicit instruction.

Handoff items for Step 11:

- list of available normalized cross-sectional columns
- list of available time-series normalized columns
- diagnostics summary and unresolved coverage risks
- zero-dispersion and insufficient-cross-section counts
- winsorization/clipping event counts
- confirmation that no ranking, composite, backtest, forward-return, or
  valuation/fundamental output was created
- explicit statement that diagnostics are review material only

Step 10 final COMPLETE status requires Part A + Part B integration validation,
focused tests, regression tests, and hard-stop review.
