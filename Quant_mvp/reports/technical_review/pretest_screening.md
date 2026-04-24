# Technical Pre-Screening Report

## Scope and limitations

This report is a conservative candidate-stage technical pre-screen based on the current registry in `config/scores.toml`.

Weakness first:
- formal score definitions are not present yet
- this screening therefore relies partly on inference from score names, family tags, and window config
- any item marked `keep` is only "worth implementing and first-pass testing", not adopted
- role confusion is treated conservatively: non-directional ideas are downgraded toward `regime` or `diagnostic`

Current data scope used for screening:
- daily OHLCV is available
- point-in-time fundamentals are unavailable
- technical branch is enabled
- valuation review is separated from the current technical config

## Screening summary

| score_name | score_family | role_type | recommendation | testing_priority | main concern |
| --- | --- | --- | --- | --- | --- |
| `short_term_overreaction` | `mean_reversion` | `core` | `keep` | `high` | overlaps with other oversold / reversal candidates |
| `atr_adjusted_oversold_distance` | `mean_reversion` | `core` | `simplify` | `medium` | anchor definition is unclear and appears redundant |
| `donchian_breakout_distance` | `breakout` | `core` | `keep` | `high` | breakout crowding and false breakouts |
| `bollinger_width_squeeze` | `squeeze_expansion` | `regime` | `simplify` | `medium` | non-directional in its raw form |
| `cmf_confirmation` | `flow` | `core` | `simplify` | `medium` | "confirmation" role is unclear as a standalone score |
| `rsi_price_divergence` | `oscillator_divergence` | `core` | `defer` | `low` | implementation path is unclear and likely fragile |
| `realized_vol_percentile` | `volatility_regime` | `regime` | `keep` | `medium` | useful as regime context, not as direct ranking alpha |
| `efficiency_ratio_trend` | `trend_efficiency` | `core` | `keep` | `high` | partly overlaps with breakout / trend persistence |

## Candidate records

### 1. Short-Term Overreaction

- score_name: `short_term_overreaction`
- score_family: `mean_reversion`
- score_branch: `technical`
- role_type: `core`
- purpose: Capture short-horizon price overreaction that may mean revert at the constituent level.
- why_it_might_work: If recent downside or upside moves are temporarily excessive relative to normal daily movement, a simple reversal score may identify snapback candidates.
- why_it_might_fail: This appears redundant with other oversold or reversal ideas. It will also fail in persistent trend regimes, can catch falling knives, and can be swamped by earnings-gap style continuation.
- raw_input_features: daily close, daily returns, rolling return window, optional rolling volatility or ATR for scaling
- minimum_viable_formula: Negative 5-day return, winsorized, optionally divided by 20-day realized volatility; lower recent returns imply higher reversal score.
- likely_overlap_with: `atr_adjusted_oversold_distance`, `rsi_price_divergence`, short-horizon RSI-style oversold signals
- implementation_risk: `low`
- technical_distinctiveness: `medium`
- testing_priority: `high`
- recommendation: `keep`
- pretest_comment: Worth implementing and testing as the simplest mean-reversion baseline, but the family should not carry multiple near-duplicate oversold variants in round one.

### 2. ATR-Adjusted Oversold Distance

- score_name: `atr_adjusted_oversold_distance`
- score_family: `mean_reversion`
- score_branch: `technical`
- role_type: `core`
- purpose: Measure how far price has moved into an oversold state after scaling by recent trading range.
- why_it_might_work: ATR scaling can reduce raw price-level comparability problems and may separate routine pullbacks from more extreme dislocations.
- why_it_might_fail: Implementation path is unclear because the anchor is unspecified. This appears redundant with `short_term_overreaction` unless the oversold anchor is made explicit. It can also misfire in strong trends where large ATR-normalized drawdowns keep extending.
- raw_input_features: daily close, ATR(14), explicit anchor series such as EMA(20) or rolling mean
- minimum_viable_formula: `(close - EMA20) / ATR14`, signed so larger negative distance maps to more oversold conditions.
- likely_overlap_with: `short_term_overreaction`, `rsi_price_divergence`, z-scored distance-to-moving-average variants
- implementation_risk: `medium`
- technical_distinctiveness: `low`
- testing_priority: `medium`
- recommendation: `simplify`
- pretest_comment: This should first be simplified into one explicit anchor-based distance score. Without that, it is too vague and probably redundant.

### 3. Donchian Breakout Distance

- score_name: `donchian_breakout_distance`
- score_family: `breakout`
- score_branch: `technical`
- role_type: `core`
- purpose: Measure proximity to, or penetration of, an N-day price breakout level.
- why_it_might_work: A simple breakout score can capture persistence, trend continuation, and relative leadership without relying on opaque transformations.
- why_it_might_fail: False breakouts are common in range-bound markets. The score can also crowd into already-extended names and may partially overlap with trend persistence or efficiency measures.
- raw_input_features: daily high, daily close, rolling N-day high, optional ATR for scaling
- minimum_viable_formula: `(close - rolling_max(high, 20)) / ATR14`, clipped and normalized so names nearest to or above breakout levels score highest.
- likely_overlap_with: `efficiency_ratio_trend`, generic 20-day momentum or price-channel breakout scores
- implementation_risk: `low`
- technical_distinctiveness: `high`
- testing_priority: `high`
- recommendation: `keep`
- pretest_comment: Clear enough and implementable enough for first-pass testing. It is one of the cleaner core technical candidates in the current slate.

### 4. Bollinger Width Squeeze

- score_name: `bollinger_width_squeeze`
- score_family: `squeeze_expansion`
- score_branch: `technical`
- role_type: `regime`
- purpose: Identify volatility compression states that may precede expansion.
- why_it_might_work: Low realized band width can flag compressed market states where breakout or expansion-style signals become more relevant.
- why_it_might_fail: In its raw form this is non-directional, so it is being misused if treated as a direct constituent-ranking alpha. Low-volatility compression can also persist for long periods without producing a useful move.
- raw_input_features: daily close, Bollinger band width over 20 days, rolling percentile window
- minimum_viable_formula: Rolling percentile rank of 20-day Bollinger bandwidth; lower percentile means stronger squeeze state.
- likely_overlap_with: `realized_vol_percentile`, other low-volatility compression measures
- implementation_risk: `low`
- technical_distinctiveness: `medium`
- testing_priority: `medium`
- recommendation: `simplify`
- pretest_comment: This is better treated as a regime filter, not a standalone constituent-ranking score. It should first be simplified into a directional-neutral squeeze state variable.

### 5. CMF Confirmation

- score_name: `cmf_confirmation`
- score_family: `flow`
- score_branch: `technical`
- role_type: `core`
- purpose: Measure whether price action is being supported by accumulation or distribution pressure through volume-weighted flow.
- why_it_might_work: Chaikin Money Flow can add a simple price-volume confirmation layer that is different from pure price trend measures.
- why_it_might_fail: The word "confirmation" creates role confusion. This appears better as either a standalone accumulation score or a secondary filter on trend / breakout ideas. It may also be noisy when high-low ranges are unstable or when volume spikes dominate.
- raw_input_features: daily high, low, close, volume, CMF lookback window
- minimum_viable_formula: Raw `CMF(20)` standardized by a rolling robust z-score, interpreted as positive accumulation versus negative distribution.
- likely_overlap_with: ADL-based flow measures, OBV slope, price-volume confirmation filters
- implementation_risk: `low`
- technical_distinctiveness: `medium`
- testing_priority: `medium`
- recommendation: `simplify`
- pretest_comment: Possibly useful, but the current naming and role are unclear. It should first be simplified into a plain flow score or explicitly redefined as a filter.

### 6. RSI Price Divergence

- score_name: `rsi_price_divergence`
- score_family: `oscillator_divergence`
- score_branch: `technical`
- role_type: `core`
- purpose: Detect disagreement between price direction and RSI behavior that could indicate weakening continuation or reversal pressure.
- why_it_might_work: If price makes a fresh push while RSI fails to confirm, divergence may sometimes flag exhaustion.
- why_it_might_fail: Implementation path is unclear. Swing-high and swing-low detection can become subjective, parameter-heavy, and unstable. This also appears partly redundant with simpler reversal scores and may add decorative complexity without enough incremental information.
- raw_input_features: daily close, RSI(14), explicit swing-point or slope comparison rules
- minimum_viable_formula: Unknown robust first-pass formula. A simplified proxy could compare 20-day price change with 20-day RSI change, but that would only be an approximation.
- likely_overlap_with: `short_term_overreaction`, `atr_adjusted_oversold_distance`, generic oscillator oversold / exhaustion measures
- implementation_risk: `high`
- technical_distinctiveness: `medium`
- testing_priority: `low`
- recommendation: `defer`
- pretest_comment: Evidence is not established yet, and implementation realism is weak at this stage. Worth revisiting only after simpler mean-reversion baselines are in place.

### 7. Realized Volatility Percentile

- score_name: `realized_vol_percentile`
- score_family: `volatility_regime`
- score_branch: `technical`
- role_type: `regime`
- purpose: Describe whether the market or a stock is currently operating in a low-, normal-, or high-volatility state.
- why_it_might_work: Volatility regime information can help decide when other technical scores are less reliable, more unstable, or should be shrunk toward neutral.
- why_it_might_fail: This is not a direct directional stock-selection signal. Used incorrectly, it can create role confusion. High or low volatility by itself does not imply better ranking unless linked to another score family.
- raw_input_features: daily returns, 20-day realized volatility, rolling percentile history
- minimum_viable_formula: Percentile rank of 20-day realized volatility over a 252-day trailing window.
- likely_overlap_with: `bollinger_width_squeeze`, other volatility-compression or expansion diagnostics
- implementation_risk: `low`
- technical_distinctiveness: `medium`
- testing_priority: `medium`
- recommendation: `keep`
- pretest_comment: Worth implementing and testing as a regime variable. This should remain technical-only and should not be marketed as direct constituent alpha.

### 8. Efficiency Ratio Trend

- score_name: `efficiency_ratio_trend`
- score_family: `trend_efficiency`
- score_branch: `technical`
- role_type: `core`
- purpose: Measure how directional recent price movement has been relative to total path noise.
- why_it_might_work: A simple efficiency ratio can distinguish cleaner trend persistence from noisy movement and may complement breakout distance.
- why_it_might_fail: This appears partly redundant with breakout or medium-horizon momentum concepts. It can also score steady but exhausted trends highly and may be unstable after abrupt gaps.
- raw_input_features: daily close, efficiency ratio window, optional smoothing window
- minimum_viable_formula: Kaufman-style efficiency ratio over 20 days: absolute net change divided by sum of absolute daily changes over the same window.
- likely_overlap_with: `donchian_breakout_distance`, medium-horizon momentum, trend persistence measures
- implementation_risk: `low`
- technical_distinctiveness: `medium`
- testing_priority: `high`
- recommendation: `keep`
- pretest_comment: Worth implementing and testing as a simpler trend-quality measure, provided redundancy is checked directly against breakout-style candidates.

## Recommended first-pass technical testing slate

Keep first:
- `short_term_overreaction`
- `donchian_breakout_distance`
- `realized_vol_percentile` as `regime`
- `efficiency_ratio_trend`

Simplify before implementation:
- `atr_adjusted_oversold_distance`
- `bollinger_width_squeeze`
- `cmf_confirmation`

Defer for later round:
- `rsi_price_divergence`

## Conservative pretest notes

- The mean-reversion family is already at risk of internal overlap. Round one should not carry multiple loosely defined oversold variants without explicit differentiation.
- The current slate benefits from cleaner role separation: breakout and trend-efficiency as `core`, realized volatility and squeeze as `regime`, and any overlap or confirmation analysis as `diagnostic`.
- If formal score definitions later differ materially from the inferred intent here, this pre-screen should be versioned and updated rather than silently reinterpreted.
