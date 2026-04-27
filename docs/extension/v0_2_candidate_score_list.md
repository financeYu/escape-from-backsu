# v0.2 Candidate Score List

Status: draft candidate list only. This document does not approve
implementation, score adoption, ranking changes, report changes, backtest
feedback, valuation activation, or data-ingestion changes.

## Baseline Boundary

The intended `v0.2` product goal is score-set or score-semantics revision after
approval. Until that approval exists, every item below is candidate-only.

MVP v0.1 remains unchanged:

- KOSPI200-only.
- Technical-only.
- Existing `technical_composite_score` and `final_composite_score` semantics
  remain unchanged.
- Backtest output remains evaluation-only and must not feed scoring or ranking.
- Valuation or fundamental data must not enter technical or final composite
  scoring.

## Candidate Status Rules

Allowed candidate states in this list:

- `draft_candidate`: eligible for Score Architect review only.
- `diagnostic_candidate`: may support diagnostics, not ranking adoption.
- `blocked_by_data`: not implementable with current approved data.
- `out_of_scope`: excluded unless a later approval changes scope.

No candidate here is adopted. No candidate here is approved for implementation.

## Candidate Scores

| candidate_id | branch | family | candidate purpose | raw input boundary | initial state | main blocker |
| --- | --- | --- | --- | --- | --- | --- |
| `trend_efficiency_candidate` | `technical` | trend efficiency | Separate orderly directional movement from noisy drift. | Daily OHLCV-derived returns, rolling range, rolling volatility. | `draft_candidate` | Needs formula and normalization freeze. |
| `breakout_follow_through_candidate` | `technical` | breakout | Test whether recent range expansion persists after a breakout condition. | Daily high, low, close, adjusted close, volume. | `draft_candidate` | Needs timing rule for breakout confirmation. |
| `mean_reversion_exhaustion_candidate` | `technical` | mean reversion | Identify short-horizon extension where reversal risk may be technically relevant. | Daily adjusted close returns, rolling drawdown, oscillator-style technical inputs. | `draft_candidate` | Must avoid valuation or recommendation language. |
| `volatility_squeeze_expansion_candidate` | `technical` | squeeze / expansion | Capture transition from compressed volatility to expanding price movement. | Daily range, rolling volatility, adjusted close, volume. | `draft_candidate` | Needs warmup and invalid-row policy. |
| `price_volume_confirmation_candidate` | `technical` | price-volume / flow | Check whether price movement is confirmed or contradicted by volume behavior. | Daily close, adjusted close, volume, rolling volume statistics. | `draft_candidate` | Needs outlier handling for volume spikes. |
| `relative_strength_persistence_candidate` | `technical` | relative strength | Compare same-date stock strength within the eligible KOSPI200 universe. | Daily adjusted close returns and same-date eligible KOSPI200 population. | `draft_candidate` | Needs cross-sectional population timing contract. |
| `downside_resilience_candidate` | `technical` | risk / quality | Evaluate technical resilience after drawdowns without using fundamentals. | Daily adjusted close, drawdown path, downside volatility. | `draft_candidate` | Must not imply valuation quality. |
| `serial_dependency_candidate` | `technical` | serial dependency | Measure whether recent returns show persistence or reversal tendency. | Daily adjusted close returns, rolling autocorrelation-style statistics. | `draft_candidate` | Needs minimum history and stability criteria. |
| `correlation_regime_candidate` | `diagnostic` | correlation structure | Describe whether a stock is moving with or away from the eligible universe. | Daily adjusted close returns, same-date KOSPI200 return population. | `diagnostic_candidate` | Diagnostic only unless later adopted through review. |
| `liquidity_stability_candidate` | `diagnostic` | data quality / liquidity | Track whether volume behavior is stable enough for score reliability review. | Daily volume and rolling volume coverage. | `diagnostic_candidate` | Diagnostic only; not a ranking signal by default. |
| `valuation_overlay_score` | `out_of_scope` | valuation | Fundamental valuation overlay. | Requires point-in-time fundamental data. | `out_of_scope` | Valuation route and PIT proof required. |
| `ml_prob_up_1d_candidate` | `out_of_scope` | candidate ML | One-day up probability candidate from the v0.1n approval-prep line. | Requires separate candidate ML contract. | `out_of_scope` | Not part of v0.2 technical score revision unless separately approved. |

## Candidate Specification Drafts

These drafts fill the first Score Architect fields for review. They are not
implementation instructions and do not approve any production adoption.

### `trend_efficiency_candidate`

- `raw_formula_design`: Candidate efficiency ratio over configurable windows.
  Compute absolute cumulative adjusted-close return over `N` sessions divided
  by the sum of absolute daily adjusted-close returns over the same window.
  Keep direction as a separate signed component using the cumulative return
  sign, so trend orderliness and direction are reviewable separately.
- `minimum_history_needed`: At least `max(N) + 20` trading sessions; initial
  review windows should include 20, 60, and 120 sessions, so practical minimum
  is 140 sessions before stable review.
- `normalization_candidates`: Cross-sectional robust percentile by same-date
  eligible KOSPI200 population; time-series rolling percentile per symbol;
  optional neutral shrinkage when window coverage is below threshold.
- `failure_modes`: Low-volatility drift can look efficient without meaningful
  range; gaps can dominate the ratio; strongly overlaps with momentum and
  relative-strength candidates; signed interpretation may be unstable during
  sideways regimes.

### `breakout_follow_through_candidate`

- `raw_formula_design`: Use only information known at decision time. Compute
  prior rolling channel high excluding the current bar, then measure current
  adjusted close relative to that prior high using ATR or rolling range as the
  scale. Add a known-history persistence component that counts how often recent
  closes stayed above their own prior rolling channel after earlier breakouts.
- `minimum_history_needed`: At least 80 trading sessions for a 60-session
  channel plus persistence and range warmup; longer 120-session review window
  should require at least 150 sessions.
- `normalization_candidates`: Same-date cross-sectional percentile of scaled
  breakout strength; per-symbol rolling percentile of breakout strength;
  separate diagnostic flag for insufficient channel history.
- `failure_modes`: False breakouts during high-volatility regimes; one-day gaps
  can dominate the score; split or adjustment issues can create artificial
  channel breaks; persistence component can become redundant with trend
  efficiency.

### `mean_reversion_exhaustion_candidate`

- `raw_formula_design`: Compute short-horizon technical extension using
  adjusted-close distance from a rolling mean scaled by rolling volatility,
  recent drawdown distance, and oscillator-style percentile position. Keep the
  output as an exhaustion intensity candidate, not as a directional instruction.
- `minimum_history_needed`: At least 80 trading sessions for 20/60-session
  extension windows, volatility scale, and oscillator percentile warmup.
- `normalization_candidates`: Cross-sectional percentile of exhaustion
  intensity; per-symbol rolling percentile; optional cap/winsorization before
  normalization to reduce extreme gap sensitivity.
- `failure_modes`: Can confuse technical oversoldness with valuation if wording
  drifts; strong trends can remain extended for long periods; mean-reversion
  interpretation may conflict with breakout and trend candidates; missing or
  adjusted price anomalies can exaggerate extension.

### `volatility_squeeze_expansion_candidate`

- `raw_formula_design`: Identify prior compression with rolling volatility or
  band-width percentile, then combine it with current known range expansion
  using true range divided by ATR or rolling median range. Keep compression and
  expansion subcomponents separately inspectable.
- `minimum_history_needed`: At least 260 trading sessions when using one-year
  rolling percentiles; a shorter 120-session draft variant may be reviewed but
  must be labeled less stable.
- `normalization_candidates`: Per-symbol rolling percentile for compression;
  cross-sectional percentile for expansion strength; combine only after each
  subcomponent passes coverage checks.
- `failure_modes`: Low-liquidity or stale prices can create false compression;
  volume or event gaps can create false expansion; signal can duplicate
  breakout behavior; long percentile windows may delay responsiveness.

### `price_volume_confirmation_candidate`

- `raw_formula_design`: Compare recent adjusted-close movement with volume
  participation. Candidate subcomponents may include signed return over `N`
  sessions multiplied by rolling volume surprise, up-session versus
  down-session volume balance, and OBV-style slope over a known-history window.
- `minimum_history_needed`: At least 90 trading sessions for 20/60-session
  return and volume statistics; require enough non-missing volume observations
  for coverage review.
- `normalization_candidates`: Cross-sectional percentile of confirmation
  strength; per-symbol rolling z-score or percentile for volume surprise;
  separate outlier clipping for volume before combining with price movement.
- `failure_modes`: Volume spikes from events or index rebalancing can distort
  confirmation; price direction component can overlap with momentum; volume
  data quality varies by source; down-volume interpretation can become too
  noisy in low-turnover names.

### `relative_strength_persistence_candidate`

- `raw_formula_design`: For each decision date, compare each symbol's 20/60-day
  adjusted-close return against the same-date eligible KOSPI200 population
  median or percentile. Add a persistence component based on the fraction of
  recent eligible dates where the symbol stayed above the population median.
- `minimum_history_needed`: At least 90 trading sessions per symbol and a
  validated same-date eligible population for each cross-sectional date.
- `normalization_candidates`: Direct same-date cross-sectional percentile;
  per-symbol rolling percentile of relative-strength percentile; neutral
  shrinkage when same-date eligible population is incomplete.
- `failure_modes`: Requires strict universe membership timing; can duplicate
  momentum and trend efficiency; sector clustering can dominate without sector
  controls; delayed or partial data can bias cross-sectional population.

### `downside_resilience_candidate`

- `raw_formula_design`: Measure technical resilience using drawdown depth,
  downside volatility, recovery ratio from recent local trough, and fraction of
  recent sessions avoiding new rolling lows. Do not use fundamentals or
  valuation wording.
- `minimum_history_needed`: At least 140 trading sessions for 60/120-session
  drawdown and downside-volatility windows.
- `normalization_candidates`: Cross-sectional percentile of resilience
  subcomponents after orienting them consistently; per-symbol rolling
  percentile; neutral shrinkage when drawdown window is incomplete.
- `failure_modes`: Low beta or low movement can look resilient without useful
  technical information; rebound component may overlap with mean reversion;
  drawdown windows can be regime-sensitive; wording can accidentally imply
  business quality or valuation quality.

### `serial_dependency_candidate`

- `raw_formula_design`: Compute rolling lagged return autocorrelation and run
  persistence over adjusted-close returns. Keep separate subcomponents for
  lag-1 autocorrelation, lag-5 autocorrelation, and recent same-sign run
  behavior.
- `minimum_history_needed`: At least 180 trading sessions for stable
  autocorrelation review; shorter windows should be diagnostic-only until
  stability is proven.
- `normalization_candidates`: Per-symbol rolling percentile for autocorrelation
  strength; cross-sectional percentile on same-date values; require stability
  flags before any adoption review.
- `failure_modes`: Autocorrelation estimates are noisy; sign can flip across
  regimes; thin trading or stale prices can create artificial serial
  dependency; may overlap with trend or mean-reversion candidates depending on
  orientation.

### `correlation_regime_candidate`

- `raw_formula_design`: Diagnostic candidate that computes rolling correlation
  of each symbol's adjusted-close returns with the same-date eligible KOSPI200
  population return proxy, plus optional residual-volatility subcomponent.
- `minimum_history_needed`: At least 140 trading sessions for 60/120-session
  rolling correlation windows and same-date population coverage.
- `normalization_candidates`: Diagnostic percentile within same-date eligible
  population; per-symbol rolling percentile; keep as diagnostic output unless
  later adoption review explicitly changes its status.
- `failure_modes`: Population proxy can be biased by missing constituents;
  correlation can spike during market stress; diagnostic meaning can be
  mistaken for ranking attractiveness; overlaps with volatility-regime review.

### `liquidity_stability_candidate`

- `raw_formula_design`: Diagnostic candidate using rolling volume coverage,
  zero or missing volume counts, rolling volume coefficient of variation, and
  price-times-volume turnover proxy when price and volume are available.
- `minimum_history_needed`: At least 90 trading sessions for 20/60-session
  volume stability windows.
- `normalization_candidates`: Diagnostic coverage flag; same-date
  cross-sectional percentile of stability; per-symbol rolling percentile of
  volume irregularity. Default output remains diagnostic, not ranking.
- `failure_modes`: Volume spikes from corporate events or rebalancing can
  reduce apparent stability; turnover proxy is not a fundamental liquidity
  model; missing volume can reflect source quality rather than traded reality;
  diagnostic may be overused as a score gate without review.

### `valuation_overlay_score`

- `raw_formula_design`: Not defined in this v0.2 technical score revision.
  Requires a separate valuation route, point-in-time fundamental availability
  proof, and explicit approval before any formula can be specified.
- `minimum_history_needed`: Not applicable under current technical-only scope.
- `normalization_candidates`: Not applicable under current technical-only
  scope.
- `failure_modes`: Fundamental data can leak future filing information;
  valuation wording can contaminate technical-only outputs; activation would
  violate current composite boundaries without a separate approved route.

### `ml_prob_up_1d_candidate`

- `raw_formula_design`: Not defined in this v0.2 technical score revision. The
  only allowed candidate ML output remains routed through the v0.1n approval
  prep contract as `prob_up_1d_candidate`, with label
  `adjusted_close[t+1] > adjusted_close[t]`.
- `minimum_history_needed`: Not applicable in this v0.2 technical score list
  until a separate ML candidate implementation Step is approved.
- `normalization_candidates`: Not applicable; ML output must not enter
  production scoring or ranking through this list.
- `failure_modes`: Label leakage, training/evaluation split leakage, model
  artifact lineage ambiguity, and accidental production adoption remain
  blockers under the separate v0.1n route.

## Required Review Order

1. Score Architect freezes the candidate specification.
2. Scope watchdog checks score, normalization, ranking, report, backtest, and
   generated-output boundaries.
3. Research Tester implements only candidates approved for implementation in a
   later Step.
4. Technical Selection Reviewer assigns an adoption outcome only after
   diagnostics are available.
5. Master integration checks hard stops, generated-output boundaries, and
   cross-step conflicts.

## Current Blockers

- No approved post-MVP `v0.2` score revision Step exists.
- No candidate specification is frozen.
- No normalization or composite handoff contract is frozen.
- No timing and no-lookahead contract is frozen for these candidates.
- No diagnostics and redundancy plan is approved.
- No validation profile is approved.
- No implementation approval exists.
