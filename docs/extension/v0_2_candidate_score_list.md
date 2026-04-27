# v0.2 Candidate Score List

Status: frozen old-score feature inventory plus active predictive candidate
list for the post-MVP `v0.2 predictive probability score route` contract-freeze
Step. This document does not approve runtime model implementation, production
ranking activation, report changes, backtest feedback, valuation activation, or
data-ingestion changes.

## Version Boundary

The intended `v0.2` product goal is a candidate one-day probability score:
`prob_up_1d_candidate`.

The old technical and diagnostic score ideas below are frozen only as
`old_score_features` or diagnostics. They are not direct production score
candidates in this redesigned route.

MVP v0.1 remains the frozen historical baseline. A later approved `v0.2` line
may supersede v0.1 scoring semantics for v0.2 outputs, but it must do so through
versioned contracts and must not rewrite v0.1 release evidence.

- KOSPI200-only.
- Technical-only.
- Backtest output remains evaluation-only and must not feed scoring or ranking.
- Valuation or fundamental data must not enter `technical_composite_score`.
- Valuation or fundamental data must not enter `final_composite_score` in this
  draft. Any later valuation-aware final-composite route requires separate
  versioned approval, point-in-time availability proof, and updated contracts.

## Candidate Status Rules

Allowed states in this route:

- `active_predictive_candidate`: active candidate probability route, not
  approved for implementation.
- `old_score_feature`: may be used as a model feature only if available at or
  before `decision_time`.
- `diagnostic_old_score_feature`: may support diagnostics, not ranking
  adoption.
- `blocked_by_data`: not implementable with current approved data.

Explicit exclusions use `out_of_scope`, but they are not part of the frozen
v0.2 technical/diagnostic candidate set.

No candidate here is approved for runtime implementation, production ranking, or
trading use.

## Active Predictive Candidate

| candidate_id | branch | family | candidate purpose | label | initial state | main blocker |
| --- | --- | --- | --- | --- | --- | --- |
| `prob_up_1d_candidate` | `predictive_probability` | supervised one-day probability | Estimate candidate probability that `adjusted_close[t+1] > adjusted_close[t]`. | `up_1d_label` | `active_predictive_candidate` | Needs model, validation, generated-output, and review/audit contracts before implementation. |

## Frozen Old Score Feature Set

| candidate_id | branch | family | candidate purpose | raw input boundary | initial state | main blocker |
| --- | --- | --- | --- | --- | --- | --- |
| `trend_efficiency_candidate` | `old_score_feature` | trend efficiency | Separate orderly directional movement from noisy drift. | Daily OHLCV-derived returns, rolling range, rolling volatility. | `old_score_feature` | May feed model only with no-lookahead feature timing. |
| `breakout_follow_through_candidate` | `old_score_feature` | breakout | Test whether recent range expansion persists after a breakout condition. | Daily high, low, close, adjusted close, volume. | `old_score_feature` | Needs no-lookahead prior-channel timing. |
| `mean_reversion_exhaustion_candidate` | `old_score_feature` | mean reversion | Identify short-horizon extension where reversal risk may be technically relevant. | Daily adjusted close returns, rolling drawdown, oscillator-style technical inputs. | `old_score_feature` | Must avoid valuation or recommendation language. |
| `volatility_squeeze_expansion_candidate` | `old_score_feature` | squeeze / expansion | Capture transition from compressed volatility to expanding price movement. | Daily range, rolling volatility, adjusted close, volume. | `old_score_feature` | Needs warmup and invalid-row policy. |
| `price_volume_confirmation_candidate` | `old_score_feature` | price-volume / flow | Check whether price movement is confirmed or contradicted by volume behavior. | Daily close, adjusted close, volume, rolling volume statistics. | `old_score_feature` | Needs outlier handling for volume spikes. |
| `relative_strength_persistence_candidate` | `old_score_feature` | relative strength | Compare same-date stock strength within the eligible KOSPI200 universe. | Daily adjusted close returns and same-date eligible KOSPI200 population. | `old_score_feature` | Needs cross-sectional population timing contract. |
| `downside_resilience_candidate` | `old_score_feature` | risk / quality | Evaluate technical resilience after drawdowns without using fundamentals. | Daily adjusted close, drawdown path, downside volatility. | `old_score_feature` | Must not imply valuation quality. |
| `serial_dependency_candidate` | `old_score_feature` | serial dependency | Measure whether recent returns show persistence or reversal tendency. | Daily adjusted close returns, rolling autocorrelation-style statistics. | `old_score_feature` | Needs minimum history and stability criteria. |
| `correlation_regime_candidate` | `diagnostic_old_score_feature` | correlation structure | Describe whether a stock is moving with or away from the eligible universe. | Daily adjusted close returns, same-date KOSPI200 return population. | `diagnostic_old_score_feature` | Diagnostic only; no direct production ranking. |
| `liquidity_stability_candidate` | `diagnostic_old_score_feature` | data quality / liquidity | Track whether volume behavior is stable enough for score reliability review. | Daily volume and rolling volume coverage. | `diagnostic_old_score_feature` | Diagnostic only; no direct production ranking. |

## Frozen Candidate Specification Summaries

These summaries freeze the old-score feature-definition layer for the v0.2
predictive probability route. They are not runtime implementation instructions
and do not approve production adoption. Model design, probability calibration,
timing, config ownership, validation, and review gates remain separate
blockers.

### `trend_efficiency_candidate`

- `score_name`: `trend_efficiency_candidate`
- `score_family`: trend efficiency
- `score_branch`: `technical`
- `purpose`: Separate orderly directional movement from noisy drift.
- `market_regime_where_it_helps`: Trending single-name regimes where movement
  is persistent rather than choppy.
- `raw_input_features`: adjusted close, daily adjusted-close returns, rolling
  absolute return sum, rolling cumulative return, optional rolling range.
- `raw_formula_design`: Candidate efficiency ratio over configurable windows.
  Compute absolute cumulative adjusted-close return over `N` sessions divided
  by the sum of absolute daily adjusted-close returns over the same window.
  Keep direction as a separate signed component using the cumulative return
  sign, so trend orderliness and direction are reviewable separately.
- `normalization_candidates`: Cross-sectional robust percentile by same-date
  eligible KOSPI200 population; time-series rolling percentile per symbol;
  optional neutral shrinkage when window coverage is below threshold.
- `minimum_history_needed`: At least `max(N) + 20` trading sessions; initial
  review windows should include 20, 60, and 120 sessions, so practical minimum
  is 140 sessions before stable review.
- `expected_overlap_risk`: High overlap with momentum, relative strength, and
  breakout persistence; should be checked against those candidates before
  adoption.
- `failure_modes`: Low-volatility drift can look efficient without meaningful
  range; gaps can dominate the ratio; strongly overlaps with momentum and
  relative-strength candidates; signed interpretation may be unstable during
  sideways regimes.
- `data_requirements`: Daily adjusted close with split-adjustment policy,
  complete enough return history, KOSPI200 same-date eligibility for
  cross-sectional normalization.
- `notes_on_interpretability`: Interpretable as path orderliness, not as a
  standalone directional recommendation.

### `breakout_follow_through_candidate`

- `score_name`: `breakout_follow_through_candidate`
- `score_family`: breakout
- `score_branch`: `technical`
- `purpose`: Test whether range expansion persists after a prior-channel
  breakout condition.
- `market_regime_where_it_helps`: Expansion regimes where price moves beyond a
  prior range and maintains that move.
- `raw_input_features`: high, low, close, adjusted close, volume, prior rolling
  channel high, true range or ATR-style range scale.
- `raw_formula_design`: Use only information known at decision time. Compute
  prior rolling channel high excluding the current bar, then measure current
  adjusted close relative to that prior high using ATR or rolling range as the
  scale. Add a known-history persistence component that counts how often recent
  closes stayed above their own prior rolling channel after earlier breakouts.
- `normalization_candidates`: Same-date cross-sectional percentile of scaled
  breakout strength; per-symbol rolling percentile of breakout strength;
  separate diagnostic flag for insufficient channel history.
- `minimum_history_needed`: At least 80 trading sessions for a 60-session
  channel plus persistence and range warmup; longer 120-session review window
  should require at least 150 sessions.
- `expected_overlap_risk`: Medium to high overlap with trend efficiency,
  relative strength, and volatility expansion.
- `failure_modes`: False breakouts during high-volatility regimes; one-day gaps
  can dominate the score; split or adjustment issues can create artificial
  channel breaks; persistence component can become redundant with trend
  efficiency.
- `data_requirements`: Daily OHLCV, adjusted close, stable adjustment policy,
  configured channel windows, range or ATR-compatible derived fields.
- `notes_on_interpretability`: Breakout strength and follow-through should stay
  separate so failed-breakout diagnostics remain inspectable.

### `mean_reversion_exhaustion_candidate`

- `score_name`: `mean_reversion_exhaustion_candidate`
- `score_family`: mean reversion
- `score_branch`: `technical`
- `purpose`: Identify technical extension where reversal risk may be relevant
  without implying valuation support.
- `market_regime_where_it_helps`: Range-bound or overextended regimes where
  short-horizon movement deviates from recent behavior.
- `raw_input_features`: adjusted close, daily returns, rolling mean, rolling
  volatility, rolling drawdown, oscillator-style percentile position.
- `raw_formula_design`: Compute short-horizon technical extension using
  adjusted-close distance from a rolling mean scaled by rolling volatility,
  recent drawdown distance, and oscillator-style percentile position. Keep the
  output as an exhaustion intensity candidate, not as a directional instruction.
- `normalization_candidates`: Cross-sectional percentile of exhaustion
  intensity; per-symbol rolling percentile; optional cap/winsorization before
  normalization to reduce extreme gap sensitivity.
- `minimum_history_needed`: At least 80 trading sessions for 20/60-session
  extension windows, volatility scale, and oscillator percentile warmup.
- `expected_overlap_risk`: Medium overlap with downside resilience and serial
  dependency; inverse relationship with trend and breakout candidates must be
  reviewed explicitly.
- `failure_modes`: Can confuse technical oversoldness with valuation if wording
  drifts; strong trends can remain extended for long periods; mean-reversion
  interpretation may conflict with breakout and trend candidates; missing or
  adjusted price anomalies can exaggerate extension.
- `data_requirements`: Daily adjusted close, stable return computation, rolling
  mean and volatility windows, drawdown path.
- `notes_on_interpretability`: This is an extension/exhaustion measure only; it
  must not be described as cheapness, value, or a recommendation.

### `volatility_squeeze_expansion_candidate`

- `score_name`: `volatility_squeeze_expansion_candidate`
- `score_family`: squeeze / expansion
- `score_branch`: `technical`
- `purpose`: Capture transition from volatility compression to known-history
  range expansion.
- `market_regime_where_it_helps`: Volatility-regime transitions after quiet
  periods.
- `raw_input_features`: high, low, close, adjusted close, true range, rolling
  volatility, rolling band width or range percentile, volume as diagnostic only.
- `raw_formula_design`: Identify prior compression with rolling volatility or
  band-width percentile, then combine it with current known range expansion
  using true range divided by ATR or rolling median range. Keep compression and
  expansion subcomponents separately inspectable.
- `normalization_candidates`: Per-symbol rolling percentile for compression;
  cross-sectional percentile for expansion strength; combine only after each
  subcomponent passes coverage checks.
- `minimum_history_needed`: At least 260 trading sessions when using one-year
  rolling percentiles; a shorter 120-session draft variant may be reviewed but
  must be labeled less stable.
- `expected_overlap_risk`: Medium overlap with breakout follow-through and
  volatility regime diagnostics.
- `failure_modes`: Low-liquidity or stale prices can create false compression;
  volume or event gaps can create false expansion; signal can duplicate
  breakout behavior; long percentile windows may delay responsiveness.
- `data_requirements`: Daily OHLCV, reliable high/low fields, adjusted close,
  range-derived fields, warmup coverage for percentile windows.
- `notes_on_interpretability`: Compression and expansion should be reported as
  separate subcomponents to avoid hiding which side drives the candidate.

### `price_volume_confirmation_candidate`

- `score_name`: `price_volume_confirmation_candidate`
- `score_family`: price-volume / flow
- `score_branch`: `technical`
- `purpose`: Check whether known price movement is confirmed or contradicted by
  volume behavior.
- `market_regime_where_it_helps`: Movement regimes where participation quality
  matters for technical interpretation.
- `raw_input_features`: close, adjusted close, returns, volume, rolling volume
  mean/median, up-session and down-session flags, optional OBV-style series.
- `raw_formula_design`: Compare recent adjusted-close movement with volume
  participation. Candidate subcomponents may include signed return over `N`
  sessions multiplied by rolling volume surprise, up-session versus
  down-session volume balance, and OBV-style slope over a known-history window.
- `normalization_candidates`: Cross-sectional percentile of confirmation
  strength; per-symbol rolling z-score or percentile for volume surprise;
  separate outlier clipping for volume before combining with price movement.
- `minimum_history_needed`: At least 90 trading sessions for 20/60-session
  return and volume statistics; require enough non-missing volume observations
  for coverage review.
- `expected_overlap_risk`: Medium overlap with trend, breakout, and liquidity
  stability diagnostics.
- `failure_modes`: Volume spikes from events or index rebalancing can distort
  confirmation; price direction component can overlap with momentum; volume
  data quality varies by source; down-volume interpretation can become too
  noisy in low-turnover names.
- `data_requirements`: Daily adjusted close, close, volume, volume coverage
  checks, outlier policy for exceptional volume observations.
- `notes_on_interpretability`: Participation confirmation is contextual; it
  should not be treated as proof that movement will continue.

### `relative_strength_persistence_candidate`

- `score_name`: `relative_strength_persistence_candidate`
- `score_family`: relative strength
- `score_branch`: `technical`
- `purpose`: Compare a symbol's same-date technical strength against the
  eligible KOSPI200 population and track persistence.
- `market_regime_where_it_helps`: Cross-sectional dispersion regimes where
  stock selection depends on relative technical behavior.
- `raw_input_features`: adjusted close, 20/60-day returns, same-date eligible
  KOSPI200 population returns, population median or percentile.
- `raw_formula_design`: For each decision date, compare each symbol's 20/60-day
  adjusted-close return against the same-date eligible KOSPI200 population
  median or percentile. Add a persistence component based on the fraction of
  recent eligible dates where the symbol stayed above the population median.
- `normalization_candidates`: Direct same-date cross-sectional percentile;
  per-symbol rolling percentile of relative-strength percentile; neutral
  shrinkage when same-date eligible population is incomplete.
- `minimum_history_needed`: At least 90 trading sessions per symbol and a
  validated same-date eligible population for each cross-sectional date.
- `expected_overlap_risk`: High overlap with momentum, trend efficiency, and
  breakout candidates.
- `failure_modes`: Requires strict universe membership timing; can duplicate
  momentum and trend efficiency; sector clustering can dominate without sector
  controls; delayed or partial data can bias cross-sectional population.
- `data_requirements`: Daily adjusted close for eligible KOSPI200 symbols,
  same-date membership/eligibility rule, no future membership leakage.
- `notes_on_interpretability`: This is a relative technical comparison inside
  the eligible universe, not index timing or market-wide forecasting.

### `downside_resilience_candidate`

- `score_name`: `downside_resilience_candidate`
- `score_family`: risk / quality
- `score_branch`: `technical`
- `purpose`: Evaluate technical resilience after drawdowns without using
  fundamentals or business-quality claims.
- `market_regime_where_it_helps`: Corrective or choppy regimes where downside
  behavior and recovery quality matter.
- `raw_input_features`: adjusted close, rolling peak, drawdown depth, downside
  volatility, local trough, recovery ratio, rolling-low events.
- `raw_formula_design`: Measure technical resilience using drawdown depth,
  downside volatility, recovery ratio from recent local trough, and fraction of
  recent sessions avoiding new rolling lows. Do not use fundamentals or
  valuation wording.
- `normalization_candidates`: Cross-sectional percentile of resilience
  subcomponents after orienting them consistently; per-symbol rolling
  percentile; neutral shrinkage when drawdown window is incomplete.
- `minimum_history_needed`: At least 140 trading sessions for 60/120-session
  drawdown and downside-volatility windows.
- `expected_overlap_risk`: Medium overlap with mean reversion and volatility
  candidates; may partially invert momentum in some regimes.
- `failure_modes`: Low beta or low movement can look resilient without useful
  technical information; rebound component may overlap with mean reversion;
  drawdown windows can be regime-sensitive; wording can accidentally imply
  business quality or valuation quality.
- `data_requirements`: Daily adjusted close with enough history for peak and
  drawdown path, downside-volatility window, missing-data policy.
- `notes_on_interpretability`: Resilience means price-path behavior only; it is
  not financial quality or valuation support.

### `serial_dependency_candidate`

- `score_name`: `serial_dependency_candidate`
- `score_family`: serial dependency
- `score_branch`: `technical`
- `purpose`: Measure whether recent returns exhibit persistence or reversal
  tendency.
- `market_regime_where_it_helps`: Regimes where return autocorrelation is
  stable enough to describe recent technical behavior.
- `raw_input_features`: adjusted close, daily returns, lagged returns,
  same-sign run counts, rolling autocorrelation windows.
- `raw_formula_design`: Compute rolling lagged return autocorrelation and run
  persistence over adjusted-close returns. Keep separate subcomponents for
  lag-1 autocorrelation, lag-5 autocorrelation, and recent same-sign run
  behavior.
- `normalization_candidates`: Per-symbol rolling percentile for autocorrelation
  strength; cross-sectional percentile on same-date values; require stability
  flags before any adoption review.
- `minimum_history_needed`: At least 180 trading sessions for stable
  autocorrelation review; shorter windows should be diagnostic-only until
  stability is proven.
- `expected_overlap_risk`: Medium overlap with trend efficiency, mean
  reversion, and short-horizon momentum depending on sign orientation.
- `failure_modes`: Autocorrelation estimates are noisy; sign can flip across
  regimes; thin trading or stale prices can create artificial serial
  dependency; may overlap with trend or mean-reversion candidates depending on
  orientation.
- `data_requirements`: Daily adjusted close, stable return series, missing-date
  handling, minimum observation count per rolling window.
- `notes_on_interpretability`: Autocorrelation should be reported with sign and
  stability flags; raw estimates alone are fragile.

### `correlation_regime_candidate`

- `score_name`: `correlation_regime_candidate`
- `score_family`: correlation structure
- `score_branch`: `diagnostic`
- `purpose`: Describe whether a stock is moving with or away from the eligible
  universe.
- `market_regime_where_it_helps`: Broad-market stress or dispersion regimes
  where co-movement context is useful.
- `raw_input_features`: adjusted-close returns, same-date eligible KOSPI200
  population return proxy, rolling correlation windows, optional residual
  volatility.
- `raw_formula_design`: Diagnostic candidate that computes rolling correlation
  of each symbol's adjusted-close returns with the same-date eligible KOSPI200
  population return proxy, plus optional residual-volatility subcomponent.
- `normalization_candidates`: Diagnostic percentile within same-date eligible
  population; per-symbol rolling percentile; keep as diagnostic output unless
  later adoption review explicitly changes its status.
- `minimum_history_needed`: At least 140 trading sessions for 60/120-session
  rolling correlation windows and same-date population coverage.
- `expected_overlap_risk`: Medium overlap with volatility and relative-strength
  diagnostics; default status remains diagnostic.
- `failure_modes`: Population proxy can be biased by missing constituents;
  correlation can spike during market stress; diagnostic meaning can be
  mistaken for ranking attractiveness; overlaps with volatility-regime review.
- `data_requirements`: Same-date KOSPI200 return population, daily adjusted
  close, universe eligibility timing, missing constituent policy.
- `notes_on_interpretability`: This is context for co-movement, not a direct
  attractiveness score unless a later adoption review changes branch status.

### `liquidity_stability_candidate`

- `score_name`: `liquidity_stability_candidate`
- `score_family`: data quality / liquidity
- `score_branch`: `diagnostic`
- `purpose`: Track whether volume behavior is stable enough for score
  reliability review.
- `market_regime_where_it_helps`: Any regime where data quality and tradability
  context affect confidence in technical scores.
- `raw_input_features`: volume, close, adjusted close, zero-volume count,
  missing-volume count, rolling volume coefficient of variation, price-times-
  volume turnover proxy.
- `raw_formula_design`: Diagnostic candidate using rolling volume coverage,
  zero or missing volume counts, rolling volume coefficient of variation, and
  price-times-volume turnover proxy when price and volume are available.
- `normalization_candidates`: Diagnostic coverage flag; same-date
  cross-sectional percentile of stability; per-symbol rolling percentile of
  volume irregularity. Default output remains diagnostic, not ranking.
- `minimum_history_needed`: At least 90 trading sessions for 20/60-session
  volume stability windows.
- `expected_overlap_risk`: Medium overlap with price-volume confirmation and
  data-quality flags; should not be used as ranking input by default.
- `failure_modes`: Volume spikes from corporate events or rebalancing can
  reduce apparent stability; turnover proxy is not a fundamental liquidity
  model; missing volume can reflect source quality rather than traded reality;
  diagnostic may be overused as a score gate without review.
- `data_requirements`: Daily volume, close or adjusted close for turnover
  proxy, missing-volume policy, volume outlier policy.
- `notes_on_interpretability`: Useful as confidence and data-quality context;
  default branch is diagnostic.

## Explicitly Excluded Route Markers

These entries are not part of the old-score feature set. `prob_up_1d_candidate`
is governed by `docs/extension/v0_2_predictive_probability_route.md`.

### `valuation_overlay_score`

- `score_name`: `valuation_overlay_score`
- `score_family`: valuation
- `score_branch`: `out_of_scope`
- `purpose`: Fundamental valuation overlay, excluded from the current v0.2
  technical score revision.
- `market_regime_where_it_helps`: Unknown in this route; requires separate
  valuation review.
- `raw_input_features`: Not approved. Would require point-in-time fundamental
  data such as earnings, book value, market capitalization, and filing
  availability metadata.
- `raw_formula_design`: Not defined in this v0.2 technical score revision.
  Requires a separate valuation route, point-in-time fundamental availability
  proof, and explicit approval before any formula can be specified.
- `normalization_candidates`: Not applicable under current technical-only
  scope.
- `minimum_history_needed`: Not applicable under current technical-only scope.
- `expected_overlap_risk`: Not evaluated; valuation must not be mixed into
  `technical_composite_score`, and must not enter `final_composite_score` from
  this draft.
- `failure_modes`: Fundamental data can leak future filing information;
  valuation wording can contaminate technical-only outputs; activation would
  violate the technical-composite boundary and the current final-composite draft
  boundary.
- `data_requirements`: Separate point-in-time valuation data contract and
  availability proof; absent from current approved technical route.
- `notes_on_interpretability`: Kept in the list only as an explicit boundary
  marker, not a candidate for this technical score revision.

## Required Review Order

1. Score Architect freezes the predictive candidate and old-score feature
   contracts.
2. Scope watchdog checks label, model-input, ranking, report, backtest, and
   generated-output boundaries.
3. Research Tester implements only after model, validation, and review/audit
   contracts are frozen and implementation approval exists.
4. Technical Selection Reviewer evaluates adoption only after diagnostics and
   probability validation are available.
5. Master integration checks hard stops, generated-output boundaries, and
   cross-step conflicts.

## Timing And No-Lookahead Prerequisite

No candidate implementation request may proceed until the request defines:

- `decision_time`: decision timestamp or decision date.
- `source_data_availability_time`: when each source input is available.
- `feature_construction_time`: when features are built and which source rows
  they may include.
- `normalization_population_time`: same-date population timing for
  cross-sectional normalization and eligible past/current values for
  time-series normalization.
- `report_generation_time`: when reports are generated relative to decision
  time and data availability.
- `evaluation_label_time`: when evaluation labels become knowable, if
  evaluation is performed.

Information after `decision_time` must not be used as score input.
Cross-sectional normalization must use only the same-date eligible population
available at that time. Time-series normalization must use only past and
current eligible values. Evaluation labels must stay separate from scoring,
ranking, normalization, report-generation, and adoption inputs. Rows with
unclear timing or availability must be excluded or marked non-evaluable.

## Technical Selection Review Gate

Before any implemented candidate can be adopted, downgraded, or rejected, the
Technical Selection Reviewer must record:

- `technical_relevance`
- `technical_distinctiveness`
- `technical_stability`
- `technical_complexity_cost`
- `regime_fit`
- `redundancy_risk`
- `implementation_clarity`
- `data_sufficiency`
- `final_candidate_state`

Allowed `final_candidate_state` values:

- `core_adopted`
- `conditional_adopted`
- `technical_only`
- `regime_only`
- `diagnostic_only`
- `research_only`
- `rejected`
- `blocked_by_data`

No candidate in this draft has a final state. Final states require implementation
diagnostics, redundancy review, scope watchdog review, and master integration
checks in a later approved `v0.2` Step.

## Backtest And Evaluation Boundary

Any backtest or simulation for these candidates is evaluation-only. Evaluation
output must not feed scoring, ranking, adoption, or parameter optimization.

Any evaluation report for this candidate list must include:

- candidate-only status
- data window
- eligibility rules
- timing assumptions
- leakage checks
- limitations
- generated-output boundary
- statement that backtest or simulation results alone cannot approve adoption

## Current Blockers

- Post-MVP `v0.2 predictive probability score route` Step is open for contract
  freeze and approval preparation only.
- Active predictive candidate is `prob_up_1d_candidate`.
- Old technical/diagnostic score ideas are frozen as old-score features, not
  direct production score candidates.
- Candidate specification summaries are frozen for the Score Architect
  candidate-definition layer.
- Raw feature lineage contract is frozen in
  `docs/extension/v0_2_raw_feature_lineage_contract.md`.
- Probability output normalization/calibration contract is frozen in
  `docs/extension/v0_2_probability_output_contract.md`.
- Model-input and candidate probability handoff contract is frozen in
  `docs/extension/v0_2_model_input_handoff_contract.md`.
- Diagnostic output schema is frozen in
  `docs/extension/v0_2_diagnostic_output_schema.md`.
- Label timing and no-lookahead contract is frozen in
  `docs/extension/v0_2_prob_up_1d_label_contract.md`.
- Generated-output and source-control policy is frozen in
  `docs/extension/v0_2_generated_output_boundary.md`.
- Config ownership contract is frozen in
  `docs/extension/v0_2_config_ownership_contract.md`.
- Diagnostics plan is frozen in
  `docs/extension/v0_2_diagnostic_output_schema.md`.
- Validation profile is frozen in
  `docs/extension/v0_2_predictive_validation_profile.md`.
- Rollback and deactivation rule is frozen in
  `docs/extension/v0_2_rollback_deactivation_rule.md`.
- Review/audit route is frozen in
  `docs/extension/v0_2_review_audit_route.md`.
- No implementation approval exists.
