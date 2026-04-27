# v0.2 Raw Feature Lineage Contract

Status: frozen old-score feature raw lineage contract for the post-MVP `v0.2
predictive probability score route` contract-freeze Step. This contract does
not approve runtime model implementation, production ranking changes, backtest
feedback, valuation activation, data-ingestion changes, or universe expansion.

## Scope

This contract freezes the approved raw input and derived feature boundary for
old-score features in
`docs/extension/v0_2_candidate_score_list.md`.

Approved source data scope:

- daily OHLCV-derived technical data
- same-date KOSPI200 eligibility metadata for cross-sectional population
  construction
- adjusted close and split-adjustment policy already available in the MVP v0.1
  technical route

Forbidden source data:

- valuation, fundamental, accounting, analyst, filing, or market-capitalization
  data
- future returns, forward labels, realized future performance, or backtest
  outputs as score inputs
- KOSDAQ150, futures/options, Nasdaq/overseas, or multi-universe data
- new live vendor assumptions or new market-data ingestion

## Global Lineage Rules

- Every derived feature must use source rows with
  `source_data_availability_time <= decision_time`.
- Rolling windows must be trailing windows ending at or before the candidate
  `feature_window_end`.
- Cross-sectional population features must use only the same-date eligible
  KOSPI200 population available at `decision_time`.
- Prior-channel and prior-threshold features must exclude the current row when
  the feature name says `prior`.
- Missing, warmup, or insufficient-history rows must remain invalid or
  non-evaluable until the normalized score lineage contract defines the exact
  invalid-state representation.

## Candidate Raw Feature Map

| candidate_id | approved raw inputs | approved derived features |
| --- | --- | --- |
| `trend_efficiency_candidate` | `date`, `symbol`, `adjusted_close` | daily adjusted-close return, trailing cumulative return, trailing absolute-return sum, optional trailing high-low or close range diagnostic |
| `breakout_follow_through_candidate` | `date`, `symbol`, `high`, `low`, `close`, `adjusted_close`, `volume` | prior rolling channel high excluding current row, true range, ATR-style or rolling-range scale, adjusted close distance from prior channel, known-history breakout persistence count |
| `mean_reversion_exhaustion_candidate` | `date`, `symbol`, `adjusted_close` | daily return, trailing rolling mean, trailing rolling volatility, rolling drawdown, oscillator-style trailing percentile position |
| `volatility_squeeze_expansion_candidate` | `date`, `symbol`, `high`, `low`, `close`, `adjusted_close`, `volume` | true range, trailing volatility, trailing band width or range percentile, current known range expansion, volume diagnostic only |
| `price_volume_confirmation_candidate` | `date`, `symbol`, `close`, `adjusted_close`, `volume` | trailing return, rolling volume mean or median, volume surprise, up-session/down-session flags, up-volume/down-volume balance, OBV-style trailing slope |
| `relative_strength_persistence_candidate` | `date`, `symbol`, `adjusted_close`, same-date eligible KOSPI200 membership | 20-session return, 60-session return, same-date eligible population return median or percentile, trailing above-population-median persistence count |
| `downside_resilience_candidate` | `date`, `symbol`, `adjusted_close` | rolling peak, drawdown depth, downside volatility, local trough, recovery ratio from local trough, rolling-low event count |
| `serial_dependency_candidate` | `date`, `symbol`, `adjusted_close` | daily return, lagged returns, lag-1 rolling autocorrelation, lag-5 rolling autocorrelation, same-sign run count |
| `correlation_regime_candidate` | `date`, `symbol`, `adjusted_close`, same-date eligible KOSPI200 membership | adjusted-close returns, same-date eligible KOSPI200 population return proxy, trailing rolling correlation, optional residual-volatility diagnostic |
| `liquidity_stability_candidate` | `date`, `symbol`, `close`, `adjusted_close`, `volume` | zero-volume count, missing-volume count, rolling volume coefficient of variation, price-times-volume turnover proxy, volume coverage ratio |

## Explicit Exclusions

`valuation_overlay_score` is an excluded route marker. `prob_up_1d_candidate`
is the active predictive candidate and is governed by
`docs/extension/v0_2_predictive_probability_route.md` and
`docs/extension/v0_2_prob_up_1d_label_contract.md`.

## Remaining Dependent Contracts

This contract freezes raw feature lineage only. Implementation remains blocked
until these contracts are also frozen:

- probability output normalization/calibration behavior
- timing and no-lookahead contract
- model-input feature contract
- config ownership contract
- validation profile
- review/audit route
