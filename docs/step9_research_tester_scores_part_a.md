# Step 9 Research Tester Scores Part A

## Scope

This document records Codex worker A's Step 9 Part A raw score implementation.
It covers only:

- `short_term_overreaction`
- `atr_adjusted_oversold_distance`
- `rsi_price_divergence`
- `realized_vol_percentile`

It does not implement Part B scores, normalized score output, ranking,
composite scores, backtests, valuation scoring, or adoption decisions.

## Input Contract

Input is the Step 7 raw indicator output, normally:

```text
data/processed/technical_indicators.csv
```

Required shared fields:

- `ticker`
- `date`
- `history_count`
- `minimum_history_required`
- `warmup_state`

The implementation preserves six-character string tickers, sorts by
`ticker`/`date`, rejects duplicate `ticker`/`date` rows, and rejects
valuation/fundamental input columns such as `PER`, `PBR`, and `ROE`.

## Output Contract

Identity columns:

- `ticker`
- `date`

Raw score columns:

- `short_term_overreaction_raw`
- `atr_adjusted_oversold_distance_raw`
- `rsi_price_divergence_raw`
- `realized_vol_percentile_raw`

Metadata columns:

- `score_warmup_state`
- `score_coverage_status`
- `score_data_quality_flag`
- `minimum_history_required`

Score-specific missing reason columns:

- `short_term_overreaction_missing_reason`
- `atr_adjusted_oversold_distance_missing_reason`
- `rsi_price_divergence_missing_reason`
- `realized_vol_percentile_missing_reason`

Forbidden outputs remain absent: rank/ranking/latest rank, normalized score
columns, `technical_composite_score`, `final_composite_score`, forward/future
returns, backtest returns, alpha/signal/buy/sell fields, and valuation scores.

## Implementation Status

| score_name | status | reason |
| --- | --- | --- |
| `short_term_overreaction` | `implemented_for_research` | MVP locked variant: `-return_N`, where `N = [returns].short`. |
| `atr_adjusted_oversold_distance` | `implemented_for_research` | MVP locked variant: `(bollinger_mid_N - close) / ATR_M`, using configured Bollinger and ATR windows. |
| `rsi_price_divergence` | `implemented_for_research` | MVP locked deterministic proxy: `max(0, -return_N) * max(0, RSI_t - RSI_{t-N})`, where `N = [returns].short`. |
| `realized_vol_percentile` | `implemented_for_research` | Uses ticker-local trailing percentile of `realized_vol_20` with current/prior rows only. Diagnostic context only, not alpha. |

## Locked Technical Formula Variants

- `short_term_overreaction_raw` uses the configured short return window from
  `Quant_mvp/config/windows.toml -> [returns].short`.
- `atr_adjusted_oversold_distance_raw` uses the configured Bollinger middle band
  as the reference anchor and divides by configured ATR. Zero or invalid ATR
  leaves the raw value missing.
- `rsi_price_divergence_raw` keeps the MVP deterministic proxy only. It does not
  perform swing-point or discretionary chart-pattern detection.

## Realized Volatility Diagnostic Formula

`realized_vol_percentile_raw` is calculated as the average percentile rank of
the current `realized_vol_20` inside the same ticker's trailing context.

Default config sources:

- realized volatility source window:
  `Quant_mvp/config/windows.toml -> [volatility].realized_vol`
- trailing context window:
  `Quant_mvp/config/windows.toml -> [normalization].time_series_window`
- minimum observations:
  `Quant_mvp/config/scores.toml -> realized_vol_percentile.minimum_history`

This raw diagnostic is not a Step 10 normalized output. It is not a ranking,
not a stock-selection signal, and not valuation evidence.

## Tests

Part A tests live in:

```text
tests/test_step9_scores_part_a.py
```

They cover deterministic toy calculation, ticker group boundaries, date
sorting, leading-zero preservation, insufficient history/warmup handling,
NaN-aware behavior, no-lookahead behavior, forbidden output checks,
valuation/fundamental input rejection, and Part A isolation from Part B.
