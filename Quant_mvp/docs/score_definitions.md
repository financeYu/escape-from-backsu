# Score Definitions

## Purpose

This document is the Step 5 Score Architect definition file for MVP candidates.
It specifies intent, inputs, formula design paths, normalization candidates,
minimum history, overlap risk, failure modes, and interpretability notes.

These definitions are implementation instructions for later stages only. They do
not activate runtime score calculation.

## Shared Rules

- Use only data available at or before the scoring date.
- Use adjusted OHLCV fields when the later data layer provides them; otherwise
  document the unadjusted-data limitation before testing.
- Treat insufficient history as missing or neutral according to the later
  Research Tester protocol. Do not fabricate early-sample scores.
- Normalize to a 0-100 range only after raw feature computation.
- Keep time-series normalization and cross-sectional normalization separate.
- Use robust clipping or winsorization before percentile conversion when raw
  values can be distorted by gaps or spikes.

## `short_term_overreaction`

- `score_name`: `short_term_overreaction`
- `score_family`: `mean_reversion`
- `score_branch`: `technical`
- `purpose`: Identify stocks with unusually weak recent price action that may be
  candidates for technical mean reversion.
- `market_regime_where_it_helps`: Range-bound or choppy markets, and post-shock
  conditions where broad selling pressure may have overshot.
- `raw_input_features`: `close`, trailing daily returns, optional realized
  volatility from `close`.
- `raw_formula_design`: Compute trailing return over predefined short windows
  from `Quant_mvp/config/windows.toml`, initially 5, 10, or 20 trading days.
  Transform recent weakness into a higher candidate score, for example
  `-return_N` or `-(return_N / realized_vol_20)`. The exact variant must be
  selected before implementation.
- `normalization_candidates`: Primary `cross_sectional_percentile` for same-date
  ranking; secondary `rolling_percentile` for per-stock chart context.
- `minimum_history_needed`: 60 trading days.
- `expected_overlap_risk`: Medium to high overlap with
  `atr_adjusted_oversold_distance` and `rsi_price_divergence`.
- `failure_modes`: Persistent downtrends, negative news gaps, liquidity shocks,
  high turnover, and catching falling trends too early.
- `data_requirements`: Daily close history; adjusted close preferred.
- `notes_on_interpretability`: High values mean a technical oversold/reversal
  setup only. They do not imply valuation cheapness.

## `atr_adjusted_oversold_distance`

- `score_name`: `atr_adjusted_oversold_distance`
- `score_family`: `mean_reversion`
- `score_branch`: `technical`
- `purpose`: Measure how far price has moved below a recent technical reference
  after scaling by realized range.
- `market_regime_where_it_helps`: Mean-reverting regimes where large price moves
  relative to typical range tend to normalize.
- `raw_input_features`: `high`, `low`, `close`, ATR, moving average or recent
  reference price.
- `raw_formula_design`: Compute ATR from the configured ATR window, then measure
  distance from `close` to a trailing reference such as a 20-day moving average
  or prior rolling low. Candidate raw form:
  `(close_t - moving_average_20_t) / ATR_14_t`, inverted so deeper downside
  distance maps to a higher oversold score. Reference choice must be fixed before
  implementation.
- `normalization_candidates`: Primary `rolling_percentile` for each stock's own
  oversold context; secondary `cross_sectional_percentile` for ranking.
- `minimum_history_needed`: 60 trading days.
- `expected_overlap_risk`: High overlap with `short_term_overreaction`; one may
  later be downgraded if diagnostics show redundancy.
- `failure_modes`: ATR spikes after gaps, regime breaks, limit-like moves,
  distorted high/low data, and persistent repricing.
- `data_requirements`: Daily high, low, close; adjusted OHLC preferred if
  available.
- `notes_on_interpretability`: More interpretable than unscaled return when
  volatility differs across stocks, but still technical-only.

## `donchian_breakout_distance`

- `score_name`: `donchian_breakout_distance`
- `score_family`: `breakout`
- `score_branch`: `technical`
- `purpose`: Measure whether price is close to or above a recent trading-range
  high.
- `market_regime_where_it_helps`: Trending markets and early breakout regimes
  where continuation is plausible.
- `raw_input_features`: `high`, `close`, optional ATR.
- `raw_formula_design`: Use a prior rolling high to avoid ambiguous same-bar
  breakout logic. Candidate raw forms:
  `(close_t / rolling_max(high, N)_{t-1}) - 1` or
  `(close_t - rolling_max(high, N)_{t-1}) / ATR_M`. Initial windows should be
  20 and/or 60 trading days, fixed before testing.
- `normalization_candidates`: Primary `cross_sectional_percentile`; secondary
  clipped robust z-score if ATR scaling is used.
- `minimum_history_needed`: 60 trading days.
- `expected_overlap_risk`: High overlap with relative strength, 52-week-high
  proximity, and moving-average trend ideas.
- `failure_modes`: False breakouts, gap reversals, crowded extension, range-bound
  whipsaw, and corporate-action adjustment errors.
- `data_requirements`: Daily high and close; adjusted high/close preferred.
- `notes_on_interpretability`: High values mean technical breakout pressure, not
  fundamental quality or valuation support.

## `bollinger_width_squeeze`

- `score_name`: `bollinger_width_squeeze`
- `score_family`: `squeeze_expansion`
- `score_branch`: `technical`
- `purpose`: Identify compressed volatility states that may be useful as
  technical setup context before expansion.
- `market_regime_where_it_helps`: Low-volatility consolidation regimes that
  precede directional expansion.
- `raw_input_features`: `close`, rolling moving average, rolling standard
  deviation, Bollinger band width.
- `raw_formula_design`: Compute Bollinger band width over the configured
  Bollinger window. Candidate raw context is the inverse percentile of band
  width, optionally combined with same-date or trailing width expansion. Any
  expansion confirmation must use only data available through the scoring date.
- `normalization_candidates`: Primary `rolling_percentile` for per-stock squeeze
  context; optional `cross_sectional_percentile` after role review.
- `minimum_history_needed`: 60 trading days.
- `expected_overlap_risk`: Medium overlap with `realized_vol_percentile` and ATR
  scaled candidates.
- `failure_modes`: Squeezes can resolve downward, persist for long periods, or
  become pure volatility timing rather than stock ranking.
- `data_requirements`: Daily close history.
- `notes_on_interpretability`: This is best interpreted as a setup/regime score,
  not as standalone evidence that a stock should rank highly.

## `cmf_confirmation`

- `score_name`: `cmf_confirmation`
- `score_family`: `flow`
- `score_branch`: `technical`
- `purpose`: Capture whether price action is supported by volume-weighted
  accumulation or distribution pressure.
- `market_regime_where_it_helps`: Breakout or trend continuation regimes where
  volume participation may confirm price movement.
- `raw_input_features`: `high`, `low`, `close`, `volume`, Chaikin Money Flow.
- `raw_formula_design`: Compute CMF over the configured CMF window, initially 20
  trading days. Candidate raw score is CMF itself or CMF gated by a predefined
  trend/breakout state. If used as a confirmation interaction, the linked score
  must be named explicitly before implementation.
- `normalization_candidates`: Primary `rolling_robust_zscore`; secondary
  `cross_sectional_percentile` after clipping.
- `minimum_history_needed`: 60 trading days.
- `expected_overlap_risk`: Medium overlap with volume participation and
  liquidity diagnostics.
- `failure_modes`: Distorted high/low ranges, zero-volume rows, volume spikes,
  and misleading accumulation readings in illiquid or gap-heavy periods.
- `data_requirements`: Daily high, low, close, and volume.
- `notes_on_interpretability`: CMF is a technical participation proxy only. It
  should not be interpreted as institutional ownership or fundamental demand.

## `rsi_price_divergence`

- `score_name`: `rsi_price_divergence`
- `score_family`: `oscillator_divergence`
- `score_branch`: `technical`
- `purpose`: Provide a deterministic proxy for bullish oscillator divergence
  without subjective chart pattern labeling.
- `market_regime_where_it_helps`: Exhausted selloffs and choppy reversal
  regimes where price weakness is no longer confirmed by momentum.
- `raw_input_features`: `close`, RSI, trailing price change, trailing RSI change.
- `raw_formula_design`: Avoid discretionary swing labeling in the MVP. Candidate
  raw proxy: price return over a predefined lookback is negative while RSI change
  over the same or shorter lookback is positive, scaled by the magnitude of
  disagreement. Example design path:
  `max(0, -return_N) * max(0, RSI_t - RSI_{t-N})`. The lookback must be fixed
  before testing.
- `normalization_candidates`: Primary `rolling_percentile`; optional
  `cross_sectional_percentile` only after missingness and sparsity are reviewed.
- `minimum_history_needed`: 90 trading days.
- `expected_overlap_risk`: Medium to high overlap with mean-reversion scores.
- `failure_modes`: Sparse triggers, noisy RSI changes, late signals, parameter
  sensitivity, and accidental chart-pattern mining.
- `data_requirements`: Daily close history sufficient for RSI and divergence
  window.
- `notes_on_interpretability`: This candidate remains fragile. Any complex swing
  point version should be deferred unless specified before results are seen.

## `realized_vol_percentile`

- `score_name`: `realized_vol_percentile`
- `score_family`: `volatility_regime`
- `score_branch`: `diagnostic`
- `purpose`: Describe each stock's realized volatility regime for risk context,
  gating, shrinkage, or later diagnostic review.
- `market_regime_where_it_helps`: Stress, transition, or volatility-clustered
  markets where raw technical scores may need context.
- `raw_input_features`: `close`, daily returns, rolling realized volatility.
- `raw_formula_design`: Compute rolling realized volatility over the configured
  window, initially 20 trading days, then compute its trailing percentile over a
  longer context window such as 120 or 252 trading days.
- `normalization_candidates`: Primary `rolling_percentile`; optional
  cross-sectional diagnostic percentile for same-date reports.
- `minimum_history_needed`: 120 trading days.
- `expected_overlap_risk`: Medium overlap with `bollinger_width_squeeze`,
  ATR-adjusted scores, and later risk filters.
- `failure_modes`: Direct-alpha role confusion, high-volatility chasing,
  reaction to stale/gap data, and over-penalizing legitimate repricing.
- `data_requirements`: Daily close history.
- `notes_on_interpretability`: This is diagnostic/regime context. It must not be
  marketed as alpha or valuation evidence.

## `efficiency_ratio_trend`

- `score_name`: `efficiency_ratio_trend`
- `score_family`: `trend_efficiency`
- `score_branch`: `technical`
- `purpose`: Distinguish smooth directional trend from noisy movement with the
  same endpoint return.
- `market_regime_where_it_helps`: Directional markets where cleaner trend paths
  may be more useful than volatile paths with similar returns.
- `raw_input_features`: `close`, trailing endpoint change, sum of absolute daily
  close-to-close changes.
- `raw_formula_design`: Compute an efficiency ratio:
  `abs(close_t - close_{t-N}) / sum(abs(close_i - close_{i-1}), N)`. Convert to
  a signed trend-efficiency candidate with `sign(return_N) * efficiency_ratio_N`
  if directional ranking is desired. The signed versus unsigned role must be
  fixed before implementation.
- `normalization_candidates`: Primary `cross_sectional_percentile` for signed
  trend efficiency; secondary `rolling_percentile` for chart context.
- `minimum_history_needed`: 60 trading days.
- `expected_overlap_risk`: Medium overlap with breakout and moving-average trend
  ideas, but lower than plain trailing return.
- `failure_modes`: Smooth declines can score efficiently if sign handling is
  wrong, noisy reversals can be penalized too strongly, and flat low-volatility
  periods can look deceptively stable.
- `data_requirements`: Daily close history.
- `notes_on_interpretability`: A high signed score means a cleaner technical
  trend path, not superior business quality.
