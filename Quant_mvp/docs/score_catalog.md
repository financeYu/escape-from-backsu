# Score Catalog

## Purpose

This document is the Step 5 Score Architect catalog for MVP technical score
candidates.

It defines candidate roles only. It does not implement scores, enable runtime
ranking, approve adoption, create a composite score, run a backtest, or provide
valuation support.

## Guardrails

- All MVP candidates use daily OHLCV or derived technical/statistical inputs.
- `enabled = true` in `Quant_mvp/config/scores.toml` means candidate visibility
  only.
- `runtime_enabled = false` remains the controlling runtime setting.
- Financial or fundamental fields must not enter `technical_composite_score` or
  `final_composite_score`.
- Price-only evidence must not be described as cheapness, value, undervaluation,
  or bargain evidence.
- Research Tester implementation begins no earlier than Step 9.
- Backtesting begins no earlier than Step 17.

## Candidate Set

| score_name | score_family | score_branch | score_role | first_pass_status | source_basis |
| --- | --- | --- | --- | --- | --- |
| `short_term_overreaction` | `mean_reversion` | `technical` | core candidate | define for MVP testing | Korea reversal evidence plus short-horizon reversal literature |
| `atr_adjusted_oversold_distance` | `mean_reversion` | `technical` | robustness variant | define for MVP testing with redundancy warning | volatility-scaled oversold proxy |
| `donchian_breakout_distance` | `breakout` | `technical` | core candidate | define for MVP testing | trading range breakout evidence |
| `bollinger_width_squeeze` | `squeeze_expansion` | `technical` | regime/conditional candidate | define for MVP testing as technical-only context | volatility compression and expansion setup |
| `cmf_confirmation` | `flow` | `technical` | confirmation candidate | define for MVP testing | price-volume participation evidence |
| `rsi_price_divergence` | `oscillator_divergence` | `technical` | cautious pattern proxy | define only as deterministic proxy | oscillator divergence, with pattern-mining warning |
| `realized_vol_percentile` | `volatility_regime` | `diagnostic` | regime diagnostic | keep out of direct alpha ranking until reviewed | risk/regime context and testing discipline |
| `efficiency_ratio_trend` | `trend_efficiency` | `technical` | distinctness candidate | define for MVP testing | smooth-trend versus noisy-trend proxy |

## Non-MVP Or Folded Ideas

| upstream idea | Step 5 routing | reason |
| --- | --- | --- |
| `medium_term_relative_strength` | folded into trend/breakout review queue | Korea evidence is mixed and overlap with breakout, 52-week high, and trend return is high |
| `moving_average_trend_structure` | folded into `efficiency_ratio_trend` or later trend review | high overlap with breakout and relative strength |
| `price_near_52w_high` | folded into `donchian_breakout_distance` as longer-window alternative | concept is useful but redundant in first MVP set |
| `time_series_trend_return` | folded into `efficiency_ratio_trend` review | too close to relative strength unless separate use is proven later |
| `volume_participation_momentum_filter` | future conditional filter / diagnostic backlog | strict turnover may require shares outstanding; OHLCV proxy needs review |
| `trading_activity_variability_penalty` | diagnostic backlog | risk/liquidity context, not first-pass ranking alpha |
| chart-pattern geometry | out of scope for MVP | subjective boundaries and high parameter-mining risk |

## Catalog Notes

- The first MVP set intentionally keeps more than one mean-reversion candidate
  because Korea-specific evidence makes reversal worth testing, but the pair has
  a high redundancy risk.
- The first MVP set intentionally keeps only one breakout candidate and one
  trend-efficiency candidate to avoid a cluster of near-duplicate trend signals.
- `realized_vol_percentile` remains useful, but its Step 5 role is diagnostic or
  regime context, not standalone stock-selection alpha.
- `rsi_price_divergence` is allowed only as a deterministic formula proxy. It
  must not become a subjective chart-pattern recognizer.
