# Step 11 Composite Score Design

## 1. Purpose

Step 11의 목적은 Step 9 raw score와 Step 10 normalized score를 이후
technical composite 설계의 입력 후보로 정리하는 것이다.

이 문서는 composite score 구조와 정책을 정의한다. 실제
`technical_composite_score` 또는 `final_composite_score` 계산은 구현하지
않는다.

Step 11 산출물:

- eight MVP score의 composite 입력 후보 분류
- score family 구조와 role 정의
- diagnostic/context-only score 처리 정책
- 중복 위험과 normalized direction 확인 정책
- missing, warmup, insufficient coverage 처리 정책
- Step 12/13/15/17/18 경계 명시
- config-first composite 설계안

## 2. Non-Goals and Hard Stops

Step 11에서 하지 않는 작업:

- `technical_composite_score` 계산 구현
- `final_composite_score` 계산 구현
- family score, weighted score, rank, latest ranking 생성
- production runtime 연결 또는 scanner 연결
- backtest, forward return, future return 계산
- valuation/fundamental data 병합
- `PER`, `PBR`, `ROE` 또는 financial statement field 사용
- price-only evidence를 `cheap`, `value`, `undervalued`, `bargain` 또는
  valuation evidence로 표현
- Step 9 formula 또는 Step 10 normalization formula 재정의
- diagnostic output을 alpha signal, adoption decision, selection score처럼 표현

Production enable flag는 계속 꺼져 있어야 한다.

```text
ranking_generation_enabled = false
composite_scoring_enabled = false
backtest_enabled = false
valuation_branch_enabled = false
runtime_enabled = false
```

## 3. Upstream Inputs

### 3.1 Step 9 Raw Score

Step 9 raw score는 formula-locked research output이다. Raw score는 composite
계산에 직접 넣는 기본 입력이 아니라 다음 용도로 사용한다.

- normalized score의 traceability 확인
- missing reason, warmup, coverage status 확인
- Step 12 redundancy/correlation diagnostics의 원천 값
- Step 13 Technical Selection Reviewer의 review material

Step 11 대상은 아래 eight MVP score뿐이다. 새 score를 추가하지 않는다.

```text
short_term_overreaction
atr_adjusted_oversold_distance
donchian_breakout_distance
bollinger_width_squeeze
cmf_confirmation
rsi_price_divergence
realized_vol_percentile
efficiency_ratio_trend
```

### 3.2 Step 10 Normalized Score

Step 10 normalized score는 composite input 후보일 뿐이다. Normalized column이
존재해도 자동 채택 또는 adoption을 의미하지 않는다.

Step 10 output namespace:

- time-series context: `{score_name}_ts_robust_zscore`
- cross-sectional context: `{score_name}_cross_sectional_robust_z`
- status/quality metadata:
  - `{score_name}_ts_status`
  - `{score_name}_ts_coverage_status`
  - `{score_name}_ts_data_quality_flag`
  - `{score_name}_cross_sectional_status`
  - `{score_name}_cross_sectional_quality_flag`
  - `{score_name}_cross_sectional_valid_count`

Composite 설계상 같은 날짜 종목 간 비교가 필요한 candidate signal은
cross-sectional normalized column을 우선 후보로 본다. Time-series normalized
column은 chart/context/review material로 우선 취급한다.

## 4. Composite Family Structure

Step 11 composite 설계는 기존 Step 5 family를 아래 composite family로 묶어
다룬다. 이것은 score adoption이 아니라 구조 설계다.

| composite family | source Step 5 families | intended use |
| --- | --- | --- |
| `mean_reversion` | `mean_reversion`, `oscillator_divergence` | reversal candidate cluster |
| `trend_breakout` | `breakout`, `trend_efficiency` | continuation and clean-trend candidate cluster |
| `volatility_context` | `squeeze_expansion`, `volatility_regime` | setup, regime, risk, shrinkage, diagnostics context |
| `volume_flow` | `flow` | confirmation and participation context |

Family aggregation must not be a blind average. Later implementation should be
config-first and should aggregate within family before any technical composite is
considered. Diagnostic/context-only inputs must remain visibly separate from
candidate signals.

## 5. Role Semantics

Allowed Step 11 roles:

| role | meaning |
| --- | --- |
| `candidate_signal` | May become a direct technical composite input only after Step 12 diagnostics and Step 13 review. |
| `confirmation` | May confirm or condition another technical family; must not be treated as standalone selection evidence by default. |
| `setup_context` | Describes regime/setup conditions; must not be treated as standalone alpha evidence. |
| `diagnostic_context` | Review, risk, coverage, shrinkage, or regime diagnostic only; no direct alpha contribution. |

## 6. Composite Eligibility Status

Eligibility status is a design-stage label, not adoption.

| status | meaning |
| --- | --- |
| `eligible` | Schema and role allow later composite consideration, pending Step 12/13. |
| `conditional` | May enter only as confirmation, setup, gating, shrinkage, or secondary input after explicit review. |
| `diagnostic_only` | Must stay outside direct technical composite contribution. May inform diagnostics or conservative shrinkage policy. |
| `blocked` | Must not enter composite until a hard dependency, data, or policy issue is resolved. |

## 7. Composite Calculation Readiness Status

Step 11 defines readiness labels for later stages. It does not calculate them in
runtime output.

| readiness status | meaning |
| --- | --- |
| `design_only` | Policy exists, but no composite calculation is implemented. This is the Step 11 state. |
| `input_contract_ready` | Raw and normalized input column names are known and can be reviewed. |
| `pending_step12_diagnostics` | Redundancy, correlation, coverage, and overlap diagnostics are required before inclusion. |
| `pending_step13_review` | Technical Selection Reviewer has not yet adopted, downgraded, or rejected the score. |
| `blocked_by_boundary` | Ranking, backtest, valuation, or production-runtime boundary prevents use. |

Current Step 11 verdict: all eight MVP scores are `input_contract_ready` at the
schema level, but actual composite calculation remains `design_only` and
`pending_step12_diagnostics` / `pending_step13_review`.

## 8. Score-Level Composite Design Table

| score_name | raw column | normalized column or Step 10 output column | proposed family | role | composite eligibility | primary risk | required review before inclusion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `short_term_overreaction` | `short_term_overreaction_raw` | primary: `short_term_overreaction_cross_sectional_robust_z`; context: `short_term_overreaction_ts_robust_zscore` | `mean_reversion` | `candidate_signal` | `eligible` | High overlap with other reversal scores; can reward persistent downtrends. | Step 12 correlation/rank-overlap diagnostics; Step 13 technical usefulness and failure-mode review. |
| `atr_adjusted_oversold_distance` | `atr_adjusted_oversold_distance_raw` | primary: `atr_adjusted_oversold_distance_cross_sectional_robust_z`; context: `atr_adjusted_oversold_distance_ts_robust_zscore` | `mean_reversion` | `candidate_signal` | `conditional` | Very high redundancy risk with `short_term_overreaction`; ATR spikes can distort distance. | Step 12 mean-reversion cluster redundancy; Step 13 decision whether it replaces, complements, or downgrades the simpler reversal score. |
| `donchian_breakout_distance` | `donchian_breakout_distance_raw` | primary: `donchian_breakout_distance_cross_sectional_robust_z`; context: `donchian_breakout_distance_ts_robust_zscore` | `trend_breakout` | `candidate_signal` | `eligible` | False breakouts and overlap with trend/relative-strength style information. | Step 12 trend/breakout correlation diagnostics; Step 13 continuation plausibility review. |
| `bollinger_width_squeeze` | `bollinger_width_squeeze_raw` | context candidate: `bollinger_width_squeeze_ts_robust_zscore`; optional diagnostic same-date view: `bollinger_width_squeeze_cross_sectional_robust_z` | `volatility_context` | `setup_context` | `conditional` | Squeeze can resolve in either direction; should not be standalone alpha. | Step 12 overlap with volatility diagnostics; Step 13 role review for gating/setup-only use. |
| `cmf_confirmation` | `cmf_confirmation_raw` | confirmation candidate: `cmf_confirmation_cross_sectional_robust_z`; context: `cmf_confirmation_ts_robust_zscore` | `volume_flow` | `confirmation` | `conditional` | Volume/high-low artifacts and overstatement as standalone selection score. | Step 12 relationship with trend/breakout candidates; Step 13 confirmation-only versus direct-input decision. |
| `rsi_price_divergence` | `rsi_price_divergence_raw` | primary candidate if coverage is adequate: `rsi_price_divergence_cross_sectional_robust_z`; context: `rsi_price_divergence_ts_robust_zscore` | `mean_reversion` | `candidate_signal` | `conditional` | Sparse deterministic proxy; overlaps with reversal cluster and can become pattern-mining if expanded. | Step 12 sparsity and overlap diagnostics; Step 13 review before any direct composite role. |
| `realized_vol_percentile` | `realized_vol_percentile_raw` | diagnostic context: `realized_vol_percentile_ts_robust_zscore`; optional same-date diagnostic: `realized_vol_percentile_cross_sectional_robust_z` | `volatility_context` | `diagnostic_context` | `diagnostic_only` | Direct-alpha role confusion and high-volatility chasing. | Step 12 diagnostic distribution/coverage review; Step 13 may only confirm diagnostic, gating, or shrinkage role unless reclassified later. |
| `efficiency_ratio_trend` | `efficiency_ratio_trend_raw` | primary: `efficiency_ratio_trend_cross_sectional_robust_z`; context: `efficiency_ratio_trend_ts_robust_zscore` | `trend_breakout` | `candidate_signal` | `eligible` | Signed trend interpretation can overlap with breakout and can penalize noisy reversals too strongly. | Step 12 trend/breakout cluster redundancy; Step 13 signed trend-efficiency review. |

## 9. Diagnostic and Context-Only Policy

`realized_vol_percentile` is diagnostic/regime context. It must not be described
as direct alpha or standalone selection evidence.

`bollinger_width_squeeze` is setup/regime context. It may describe compression
before expansion, but direction is unresolved by the squeeze alone.

`cmf_confirmation` is confirmation context. It may support another technical
family after review, but it must not be presented as a standalone final
selection score by default.

Context inputs may later support conservative mechanisms such as:

- requiring an explicit confirmation state before a candidate signal contributes
- shrinking uncertain family scores toward neutral when context is weak
- flagging high-risk regimes for review

Those mechanisms must be config-owned and reviewed later. Step 11 does not
implement them.

## 10. Redundancy and Overlap Risk

### 10.1 Mean Reversion Cluster

Affected scores:

- `short_term_overreaction`
- `atr_adjusted_oversold_distance`
- `rsi_price_divergence`

Risk:

- All can identify recent weakness or reversal-like setups.
- `atr_adjusted_oversold_distance` may be a volatility-scaled variant of the
  simpler recent-return reversal score.
- `rsi_price_divergence` may become sparse and still overlap with recent
  selloff measures.

Policy:

- Do not sum all reversal scores as independent evidence.
- Step 12 must compare correlation, rank overlap, trigger sparsity, coverage,
  and family-level concentration.
- Step 13 must decide whether one score is core, one is conditional, or one is
  downgraded to research/diagnostic context.

### 10.2 Trend / Breakout Cluster

Affected scores:

- `donchian_breakout_distance`
- `efficiency_ratio_trend`

Risk:

- Both may reward directional price strength.
- A later moving-average, relative-strength, or 52-week-high variant would be
  highly overlapping and is outside Step 11.

Policy:

- Treat this as one trend/breakout family until distinctness is shown.
- Step 12 must test whether efficiency ratio adds path-quality information
  beyond breakout distance.
- Step 13 must decide whether both can coexist or one should dominate the family.

### 10.3 Volatility Context Cluster

Affected scores:

- `bollinger_width_squeeze`
- `realized_vol_percentile`
- ATR-scaled interpretation inside `atr_adjusted_oversold_distance`

Risk:

- Volatility compression, volatility regime, and ATR scaling can double-count
  volatility information.
- High volatility and low volatility contexts have different meanings and must
  not be collapsed into "stronger is better" without review.

Policy:

- Keep volatility context separate from direct candidate signals.
- `realized_vol_percentile` remains `diagnostic_only`.
- `bollinger_width_squeeze` remains `conditional` setup context.
- Step 12 must diagnose overlap before any context-based gating or shrinkage is
  implemented.

## 11. Normalized Direction Check

Before any later composite implementation, every normalized input must have a
documented higher-is-better interpretation or be excluded from direct scoring.

Direction policy:

- The Step 9 raw formula direction is the source of truth.
- Step 10 robust z-score preserves raw direction: higher raw maps to higher
  normalized value within the active context.
- Any inversion must be explicitly documented before implementation.
- Context-only and diagnostic-only fields do not become "better" simply because
  their normalized value is higher.

Direction notes:

| score_name | direction check |
| --- | --- |
| `short_term_overreaction` | Higher raw means stronger technical oversold reversal setup. |
| `atr_adjusted_oversold_distance` | Higher raw means deeper ATR-scaled technical oversold distance. |
| `donchian_breakout_distance` | Higher raw means closer to or above prior Donchian high. |
| `bollinger_width_squeeze` | Higher raw means stronger compression context because Step 9 uses `-bollinger_width`; not standalone directional evidence. |
| `cmf_confirmation` | Higher raw means stronger positive price-volume confirmation context. |
| `rsi_price_divergence` | Higher raw means stronger deterministic bullish divergence proxy, subject to sparsity review. |
| `realized_vol_percentile` | Higher raw means higher realized volatility regime; not better or worse by itself. |
| `efficiency_ratio_trend` | Higher raw means cleaner positive signed trend under the Step 9 signed variant. |

## 12. Missing, Warmup, and Coverage Policy

Composite design must preserve Step 8/9/10 missingness semantics.

Rules:

- Missing raw score must not be filled with a favorable value.
- `score_warmup_state != ready` blocks direct composite use for that row.
- `score_coverage_status = blocked` blocks direct composite use for that row.
- Time-series status other than `ok` blocks direct use of the time-series
  normalized value.
- Cross-sectional status other than `adequate` blocks direct use of the
  cross-sectional normalized value.
- `insufficient_cross_section`, `zero_dispersion`, `invalid_numeric`,
  `missing_required_input`, `future_date`, `invalid_ticker`,
  `leading_zero_lost`, and duplicate key flags must remain visible.
- Family score coverage must be tracked separately from row-level score coverage.
- A later neutral shrinkage rule must be config-owned. For z-score space,
  neutral means `0.0`; for future 0-100 mappings, neutral means the configured
  neutral floor such as `Quant_mvp/config/thresholds.toml ->
  [quality].neutral_shrinkage_floor`.

Step 11 does not implement shrinkage.

## 13. Score Adoption Versus Composite Design

Composite design answers:

- Which families exist?
- Which normalized columns could be considered?
- Which roles and eligibility statuses are allowed?
- Which risks must be reviewed before inclusion?

Score adoption answers:

- Which score is adopted, conditional, downgraded, rejected, or diagnostic-only?
- Which family weights or contribution rules are approved?
- Which redundant scores are removed or demoted?

Step 11 does not adopt scores. Adoption belongs to later review and synthesis
steps.

## 14. Downstream Step Boundaries

### Step 12 Redundancy / Correlation Diagnostics

Step 12 may implement diagnostics such as correlation, rank overlap proxy,
coverage summaries, and family overlap summaries. Step 11 only states required
diagnostics and risk areas.

Step 11 does not compute correlations.

### Step 13 Technical Selection Reviewer

Step 13 decides technical relevance, distinctiveness, stability, complexity
cost, regime fit, redundancy risk, and technical verdict.

Step 11 does not make adoption decisions.

### Step 15 Ranking

Step 15 is the earliest stage for latest ranking output. Step 11 must not create
rank columns, latest ranking files, or selection output.

### Step 17 Backtest

Step 17 is the earliest stage for conservative backtesting. Step 11 must not
calculate forward returns, future returns, labels, performance metrics, or
portfolio turnover.

### Step 18 Valuation / Fundamental Expansion

Step 18 prepares valuation expansion only after point-in-time fundamental
availability is verified. Until then:

- financial/fundamental data stays out of `technical_composite_score`
- financial/fundamental data stays out of `final_composite_score`
- `PER`, `PBR`, `ROE` do not affect technical scoring
- no valuation-aware composite or valuation verdict is implemented

## 15. Config-First Composite Design Sketch

If a later step adds `Quant_mvp/config/weights.toml` or an equivalent config,
it should be documentation-first and disabled until the proper implementation
stage.

Illustrative design only:

```toml
[status]
design_stage = "step_11_design_only"
composite_scoring_enabled = false
ranking_generation_enabled = false
backtest_enabled = false
valuation_branch_enabled = false
runtime_enabled = false

[technical_composite]
enabled = false
input_scope = "cross_sectional_robust_z"
family_aggregation = "within_family_then_composite"
missing_policy = "block_or_shrink_neutral_after_review"
diagnostics_are_alpha = false

[families.mean_reversion]
enabled = false
role = "candidate_signal_cluster"
redundancy_review_required = true

[families.trend_breakout]
enabled = false
role = "candidate_signal_cluster"
redundancy_review_required = true

[families.volatility_context]
enabled = false
role = "setup_and_diagnostic_context"
direct_alpha_allowed = false

[families.volume_flow]
enabled = false
role = "confirmation_context"
standalone_selection_allowed = false
```

No config file is created by Step 11 unless explicitly requested in a later
implementation step. If created later, all production enable flags must remain
false until the roadmap opens composite implementation.

## 16. Schema / Contract Alignment

Step 11 schema and guardrail source must treat this design document as the
policy source of truth.

Required schema alignment:

- `src/composite/contracts.py` must contain only the eight MVP scores.
- Registry family values must use the Step 11 composite families:
  `mean_reversion`, `trend_breakout`, `volatility_context`, `volume_flow`.
- Registry role values must use:
  `candidate_signal`, `confirmation`, `setup_context`, `diagnostic_context`.
- Registry eligibility values must use:
  `eligible`, `conditional`, `diagnostic_only`, `blocked`.
- `realized_vol_percentile` must remain `diagnostic_context` /
  `diagnostic_only`.
- `bollinger_width_squeeze` must remain `setup_context` / `conditional`.
- `cmf_confirmation` must remain `confirmation` / `conditional`.
- Schema validation may require raw columns for traceability, but raw scores are
  not direct composite input candidates.
- Schema validation must not emit or accept production composite, ranking,
  future-return, backtest, valuation, or signal columns.

## 17. Step 11 Completion Criteria

Step 11 is complete when:

- the eight MVP scores are mapped to composite families, roles, and eligibility
  statuses
- diagnostic/context-only policies are explicit
- mean-reversion, trend/breakout, and volatility context overlap risks are
  documented
- normalized direction checks are documented
- missing/warmup/coverage treatment is documented
- Step 12/13/15/17/18 boundaries are explicit
- no composite score, ranking, backtest, future-return, or valuation/fundamental
  scoring output is implemented
