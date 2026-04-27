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
| `short_term_overreaction` | `mean_reversion` | `technical` | core candidate | research-prioritized for first-pass review | Korea reversal evidence plus short-horizon reversal literature |
| `atr_adjusted_oversold_distance` | `mean_reversion` | `technical` | secondary robustness variant | keep only as redundancy check | volatility-scaled oversold proxy |
| `donchian_breakout_distance` | `breakout` | `technical` | capped core candidate | keep, but cap trend-overlap exposure | trading range breakout evidence |
| `bollinger_width_squeeze` | `squeeze_expansion` | `technical` | regime context | context-only until directional link is defined | volatility compression and expansion setup |
| `cmf_confirmation` | `flow` | `technical` | filter candidate | simplify to filter before direct use | price-volume participation evidence |
| `rsi_price_divergence` | `oscillator_divergence` | `technical` | deferred pattern proxy | defer pending simple proxy review | oscillator divergence, with pattern-mining warning |
| `realized_vol_percentile` | `volatility_regime` | `diagnostic` | regime diagnostic | keep out of direct alpha ranking until reviewed | risk/regime context and testing discipline |
| `efficiency_ratio_trend` | `trend_efficiency` | `technical` | limited trend-quality candidate | keep as the limited trend representative | smooth-trend versus noisy-trend proxy |

## Non-MVP Or Folded Ideas

| upstream idea | Step 5 routing | reason |
| --- | --- | --- |
| `prob_up_1d_candidate` / `next_horizon_up_probability_score` | post-MVP v0.1n candidate-only design in `Quant_mvp/docs/next_horizon_up_probability_score_design.md` and `docs/extension/v0_1n_strategy_composition_v0_2_plan.md` | future v0.2 semantic candidate for calibrated 1-day-ahead adjusted-close up probability; strategy-composition design only, not MVP v0.1 ranking, backtest, or GUI activation |
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
- 2026-04-26 research-informed adjustment: provisional family weights now tilt
  slightly toward the reversal family and away from standalone squeeze, flow,
  and oscillator-divergence candidates. This is candidate governance only;
  runtime activation and MVP v0.1 composite semantics remain unchanged.
