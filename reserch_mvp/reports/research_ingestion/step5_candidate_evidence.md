# Step 5 Research-Support: MVP Technical Candidate Evidence Preparation

## 현재 위치

Step 5 research-support / candidate evidence preparation

Canonical agent:

```text
reserch_mvp/AGENTS.md
```

`reserch_mvp`가 canonical research-ingestion owner이다. 본 산출물은 `Quant_mvp` Score Architect를 지원하기 위한 upstream evidence report이며, score definition이나 adoption decision이 아니다.

## 작업 범위

- This is research evidence preparation only.
- No score implementation.
- No backtest.
- No adoption decision.
- No production ranking generation.
- No Google Scholar direct scraping.
- No valuation/fundamental scoring.

본 문서는 daily OHLCV 또는 그 파생 기술/통계 feature로 정의 가능한 후보만 Step 5 검토 대상으로 정리한다. 논문 claim은 검증된 alpha가 아니며, EvidenceCard와 CandidateScoreSpecDraft는 Score Architect 검토용 초안이다.

## Source Intake Summary

- sources_reviewed: 11
- sources_accepted: 9
- sources_rejected: 0 full-source rejection; 4 claim-level rejections are recorded below.
- manual_review_required: 5

### Source Intake Records

| source_id | title | authors | year | venue_or_source | source_type | url_or_reference | discovery_method | access_status | robots_or_terms_status | asset_universe | market_region | data_frequency | sample_period | evidence_limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SRC-BLL-1992 | Simple Technical Trading Rules and the Stochastic Properties of Stock Returns | William Brock, Josef Lakonishok, Blake LeBaron | 1992 | Journal of Finance | peer-reviewed article | [Brandeis ScholarWorks](https://scholarworks.brandeis.edu/esploro/outputs/journalArticle/Simple-Technical-Trading-Rules-and-the/9924036588601921) | approved web metadata search, not Google Scholar | public metadata/abstract; fulltext not downloaded | unknown; public metadata page viewed only | Dow Jones index | US | daily/inferred from index trading-rule tests | 1897-1986 | index-level evidence, not KOSPI200 constituents; transaction-cost and modern-market portability require review |
| SRC-JT-1993 | Returns to Buying Winners and Selling Losers | Narasimhan Jegadeesh, Sheridan Titman | 1993 | Journal of Finance | peer-reviewed article | [ResearchGate metadata](https://www.researchgate.net/publication/4992307_Returns_to_Buying_Winners_and_Selling_Losers_Implications_for_Stock_Market_Efficiency) / DOI 10.1111/j.1540-6261.1993.tb04702.x | approved web metadata search, not Google Scholar | public metadata/abstract; fulltext not downloaded | unknown; public metadata page viewed only | US stocks | US | monthly returns | 1965-1989, inferred from original paper context; exact sample not revalidated here | classic momentum evidence, but Korea-specific sources below weaken direct transfer |
| SRC-GH-2004 | The 52-Week High and Momentum Investing | Thomas J. George, Chuan-Yang Hwang | 2004 | Journal of Finance | peer-reviewed article | [HKUST repository](https://repository.hkust.edu.hk/ir/Record/1783.1-27926) | approved web metadata search, not Google Scholar | public metadata/abstract; fulltext not downloaded | unknown; public metadata page viewed only | stocks | US/inferred from Journal of Finance paper context | daily or monthly price-derived, exact frequency unknown in this intake | unknown | 52-week-high proximity is OHLCV-compatible, but direct KOSPI200 portability requires review |
| SRC-LEH-1990 | Fads, Martingales, and Market Efficiency | Bruce N. Lehmann | 1990 | Quarterly Journal of Economics / NBER WP | peer-reviewed article and working paper metadata | [NBER](https://www.nber.org/papers/w2533) | approved web metadata search, not Google Scholar | public metadata/abstract; fulltext not downloaded | unknown; public metadata page viewed only | equities | US | weekly returns | unknown in this intake | short-horizon reversal supports a candidate direction but turnover, spreads, and microstructure costs are material |
| SRC-EOM-PARK-2023 | Short-term Reversal and Short-term Momentum in the Korean Stock Markets | Cheoljun Eom, Jong Won Park | 2023 | Korean Journal of Financial Management / KCI | peer-reviewed article metadata | [KCI](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002987582) | approved web metadata search, not Google Scholar | public metadata/abstract; fulltext not downloaded | unknown; public metadata page viewed only | Korean stocks | Korea | monthly/inference from prior-month return wording | unknown in this intake | Korea-specific and useful, but KOSPI200 subset and daily implementation require separate definition |
| SRC-KRW-2025 | Momentum and reversal effects in the Korean stock market | Daeyun Kang, Doojin Ryu, Robert I. Webb | 2025 | Investment Analysts Journal / SKKU repository metadata | peer-reviewed article metadata | [Sungkyunkwan University PURE](https://pure.skku.edu/en/publications/momentum-and-reversal-effects-in-the-korean-stock-market/) | approved web metadata search, not Google Scholar | public metadata/abstract; fulltext not downloaded | unknown; public metadata page viewed only | Korean individual stocks and industry sectors | Korea | unknown | 1983-2023 | strongly relevant regionally, but abstract indicates reversal dominance, so medium-term momentum must be cautious |
| SRC-MOP-2012 | Time Series Momentum | Tobias J. Moskowitz, Yao Hua Ooi, Lasse Heje Pedersen | 2012 | SSRN / Journal of Financial Economics paper metadata | peer-reviewed article metadata / working-paper page | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2089463) | approved web metadata search, not Google Scholar | public metadata/abstract; fulltext not downloaded | unknown; public metadata page viewed only | futures across equity index, currency, commodity, bond | global multi-asset | monthly/inference from 1-12 month horizon | unknown in this intake | futures and asset-class universe differ from KOSPI200 stocks; use only as cautious trend concept |
| SRC-LS-2000 | Price Momentum and Trading Volume | Charles Lee, Bhaskaran Swaminathan | 2000 | Journal of Finance / EconPapers metadata | peer-reviewed article metadata | [EconPapers](https://econpapers.repec.org/article/blajfinan/v_3a55_3ay_3a2000_3ai_3a5_3ap_3a2017-2069.htm) | approved web metadata search, not Google Scholar | public metadata/abstract; fulltext not downloaded | unknown; public metadata page viewed only | stocks | US | turnover and returns; exact frequency unknown in this intake | unknown | paper also discusses value/glamour characteristics; only volume/momentum persistence evidence is usable for technical workflow |
| SRC-CSA-2001 | Trading Activity and Expected Stock Returns | Tarun Chordia, Avanidhar Subrahmanyam, V. Ravi Anshuman | 2001 | Journal of Financial Economics / SSRN metadata | peer-reviewed article metadata | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=205388) | approved web metadata search, not Google Scholar | public metadata/abstract; fulltext not downloaded | unknown; public metadata page viewed only | stocks | US | dollar volume and turnover variability; exact frequency unknown in this intake | unknown | controls include non-OHLCV variables; only OHLCV-computable activity variability is eligible for a technical draft |
| SRC-LOMW-2000 | Foundations of Technical Analysis | Andrew W. Lo, Harry Mamaysky, Jiang Wang | 2000 | NBER / Journal of Finance | peer-reviewed article and working-paper metadata | [NBER](https://www.nber.org/papers/w7613) | approved web metadata search, not Google Scholar | public metadata/abstract; fulltext not downloaded | unknown; public metadata page viewed only | US stocks | US | daily | 1962-1996 | supports systematic pattern recognition, but kernel-regression chart patterns are too complex for MVP score definition |
| SRC-PI-2007 | What do we know about the profitability of technical analysis? | Cheol-Ho Park, Scott H. Irwin | 2007 | Journal of Economic Surveys / Illinois Experts | review article | [Illinois Experts](https://experts.illinois.edu/en/publications/what-do-we-know-about-the-profitability-of-technical-analysis/) | approved web metadata search, not Google Scholar | public metadata/abstract; fulltext not downloaded | unknown; public metadata page viewed only | mixed speculative markets | global | mixed | literature review | diagnostic source; highlights data snooping, ex-post rule selection, risk estimation, and transaction-cost issues |

## EvidenceCards

### EvidenceCard EC-001

- evidence_id: EC-001
- source_id: SRC-BLL-1992
- claim_summary: 이동평균 및 trading range break 계열의 단순 기술 규칙은 OHLCV 기반 후보 정의로 전환 가능하다. 다만 원 논문은 Dow Jones index-level 테스트이므로 KOSPI200 constituent ranking으로 직접 확장하면 안 된다.
- exact_variable_or_indicator: moving average rule, trading range break
- formula_description: moving-average 구조 또는 N-day range breakout 조건을 이용한 추세/돌파 상태 측정
- required_inputs: daily high, low, close; optional volume 없음
- required_frequency: daily
- required_history_length: 20-200 trading days, exact window requires Score Architect definition before testing
- ranking_type: hybrid
- intended_effect: trend_following
- evidence_strength: strong
- implementation_readiness: ready_for_architect_review
- known_failure_modes: range-bound false breakout, index-to-constituent mismatch, transaction-cost sensitivity, window overfitting
- assumptions: KOSPI200 stock-level rule는 index rule보다 cross-sectional normalization이 필요하다는 것은 inference
- limitations: 원천은 US index이며 한국 개별주 universe 검증이 아니다.
- notes_for_score_architect: `donchian_breakout_distance`와 `moving_average_trend_structure`를 별도 후보로 정의하되 중복 검사를 전제로 둔다.
- recommended_route: technical_score_architect

### EvidenceCard EC-002

- evidence_id: EC-002
- source_id: SRC-JT-1993
- claim_summary: 과거 3-12개월 성과 기반 winner/loser 정렬은 medium-term relative strength 후보를 정의하는 근거가 될 수 있다.
- exact_variable_or_indicator: past 3-12 month stock return
- formula_description: 최근 중기 누적수익률을 cross-sectional rank로 변환
- required_inputs: daily close adjusted to return series
- required_frequency: daily data aggregated to medium-term return windows
- required_history_length: 60-252 trading days
- ranking_type: cross_sectional
- intended_effect: relative_strength
- evidence_strength: medium
- implementation_readiness: needs_manual_review
- known_failure_modes: long-run reversal, Korea-specific momentum weakness, crash/reversal regimes, overlap with trend and 52-week-high proximity
- assumptions: daily scanner에서는 monthly formation horizon을 trading-day windows로 근사해야 한다는 것은 inference
- limitations: US evidence이며 한국 개별주 연구는 단순 momentum에 더 보수적이다.
- notes_for_score_architect: 이 후보는 `medium_term_relative_strength`로 정의 가능하지만 Korean evidence를 반영해 강한 claim을 피해야 한다.
- recommended_route: technical_score_architect

### EvidenceCard EC-003

- evidence_id: EC-003
- source_id: SRC-LEH-1990
- claim_summary: 짧은 구간의 winner/loser는 다음 짧은 구간에서 reversal을 보일 수 있으며, 단기 과잉반응 후보의 정의 근거가 된다.
- exact_variable_or_indicator: recent short-horizon return
- formula_description: 최근 1-5일 또는 1개월 부진/급등을 역방향 score로 변환
- required_inputs: daily close, daily returns; optional realized volatility scaling
- required_frequency: daily
- required_history_length: 5-60 trading days
- ranking_type: cross_sectional
- intended_effect: mean_reversion
- evidence_strength: medium
- implementation_readiness: ready_for_architect_review
- known_failure_modes: falling-knife risk, persistent trend regimes, liquidity shocks, bid-ask spread and turnover cost
- assumptions: weekly reversal evidence를 daily scanner 후보로 축소 적용하는 것은 inference
- limitations: 원천은 US equity evidence이며 KOSPI200 거래비용과 유동성 제약은 별도 검토가 필요하다.
- notes_for_score_architect: `short_term_overreaction`은 단순한 baseline으로 정의하되 volatility scaling과 missing-data policy를 먼저 고정해야 한다.
- recommended_route: technical_score_architect

### EvidenceCard EC-004

- evidence_id: EC-004
- source_id: SRC-EOM-PARK-2023
- claim_summary: 한국 주식시장에서는 단기반전이 유의하게 관찰되지만 단기모멘텀은 확인되지 않았다는 요약이 제공된다.
- exact_variable_or_indicator: prior-month return, turnover grouping
- formula_description: 직전 수익률이 약했던 종목을 reversal candidate로 보는 구조; turnover는 caution/diagnostic feature로만 사용
- required_inputs: daily close, daily volume
- required_frequency: daily data aggregated to monthly or 20 trading-day windows
- required_history_length: 20-60 trading days
- ranking_type: cross_sectional
- intended_effect: mean_reversion
- evidence_strength: medium
- implementation_readiness: ready_for_architect_review
- known_failure_modes: 작은 규모/낮은 유동성 종목에서 효과가 강하다는 조건이 KOSPI200 대형주에는 약해질 수 있음
- assumptions: KOSPI200 large-cap subset에서는 원 논문보다 reversal 강도가 낮을 수 있다는 것은 inference
- limitations: daily formula는 논문 초록만으로 확정할 수 없다.
- notes_for_score_architect: 한국 맥락에서는 short-term reversal을 momentum보다 우선 검토하되, factor premium 크기가 작다는 한계를 명시한다.
- recommended_route: technical_score_architect

### EvidenceCard EC-005

- evidence_id: EC-005
- source_id: SRC-KRW-2025
- claim_summary: 1983-2023 한국 주식시장 장기 표본에서 개별주 momentum portfolio는 대체로 reversal effect를 보였고, 일부 하위기간만 momentum effect가 관찰되었다.
- exact_variable_or_indicator: individual stock momentum, industry momentum
- formula_description: 중기 momentum 후보에 Korea-specific regime caution을 부여
- required_inputs: daily close aggregated to return windows; optional industry labels are not available and should not be required for MVP
- required_frequency: daily input, monthly or medium-term return aggregation
- required_history_length: 60-252 trading days
- ranking_type: cross_sectional
- intended_effect: relative_strength
- evidence_strength: medium
- implementation_readiness: needs_manual_review
- known_failure_modes: Korea individual-stock reversal dominance, industry label unavailable, sub-period instability
- assumptions: KOSPI200 constituent ranking may differ from all-Korea stock universe; this is inference
- limitations: full formula and portfolio construction are not available from intake summary alone.
- notes_for_score_architect: `medium_term_relative_strength` should be framed as a hypothesis requiring review, not as a strong Korea-ready signal.
- recommended_route: technical_score_architect

### EvidenceCard EC-006

- evidence_id: EC-006
- source_id: SRC-GH-2004
- claim_summary: 현재가가 52-week high에 가까운 정도는 momentum 계열 정보를 담는 가격 기반 후보로 정의 가능하다.
- exact_variable_or_indicator: nearness to 52-week high
- formula_description: `close / rolling_252d_high` 또는 distance-to-52-week-high를 cross-sectional score로 변환
- required_inputs: daily high, daily close
- required_frequency: daily
- required_history_length: 252 trading days
- ranking_type: cross_sectional
- intended_effect: relative_strength
- evidence_strength: medium
- implementation_readiness: ready_for_architect_review
- known_failure_modes: extended trend exhaustion, overlap with medium-term momentum and Donchian breakout, 252-day history warmup
- assumptions: KOSPI200에서는 corporate action-adjusted price handling이 필요하다는 것은 inference
- limitations: direct Korea evidence is not established in this intake.
- notes_for_score_architect: `price_near_52w_high`는 `donchian_breakout_distance`와 중복될 수 있으므로 둘 중 하나를 단순화 후보로 둘 수 있다.
- recommended_route: technical_score_architect

### EvidenceCard EC-007

- evidence_id: EC-007
- source_id: SRC-MOP-2012
- claim_summary: 1-12개월 시계열 momentum은 다양한 futures 자산에서 문서화되었지만, KOSPI200 개별주 daily scanner에는 universe mismatch가 크다.
- exact_variable_or_indicator: own past 1-12 month return sign or cumulative return
- formula_description: 종목 자신의 과거 중기 수익률을 time-series trend score로 변환
- required_inputs: daily close
- required_frequency: daily input aggregated to 60-252 trading-day returns
- required_history_length: 60-252 trading days
- ranking_type: time_series
- intended_effect: trend_following
- evidence_strength: medium
- implementation_readiness: needs_manual_review
- known_failure_modes: futures-to-equity mismatch, overlap with cross-sectional momentum, reversal after long horizon
- assumptions: 개별주 시계열 trend를 cross-sectional scanner에 넣으려면 universe normalization이 필요하다는 것은 inference
- limitations: 원천은 futures 중심이며 KOSPI200 종목별 미시구조와 다르다.
- notes_for_score_architect: `time_series_trend_return`은 `medium_term_relative_strength`와 별도인지 먼저 정의해야 한다.
- recommended_route: technical_score_architect

### EvidenceCard EC-008

- evidence_id: EC-008
- source_id: SRC-LS-2000
- claim_summary: 과거 거래량은 price momentum의 크기와 지속성을 설명하는 보조 정보로 쓰일 수 있으나, 논문의 value/glamour 해석은 technical workflow에서 사용하지 않는다.
- exact_variable_or_indicator: past turnover, price momentum
- formula_description: momentum 또는 relative strength 후보에 volume participation state를 filter 또는 interaction으로 부여
- required_inputs: daily close, daily volume, shares outstanding if turnover is used; if shares unavailable, use traded value or volume percentile with caution
- required_frequency: daily
- required_history_length: 60-252 trading days
- ranking_type: hybrid
- intended_effect: liquidity_filter
- evidence_strength: medium
- implementation_readiness: needs_manual_review
- known_failure_modes: valuation language contamination, volume spikes, split/corporate action effects, turnover needs share-count data if strict
- assumptions: OHLCV-only MVP에서는 turnover 대신 volume percentile or traded-value proxy를 사용할 수 있다는 것은 inference
- limitations: strict turnover may require shares outstanding, which is not pure OHLCV.
- notes_for_score_architect: `cmf_confirmation`보다는 `volume_participation_momentum_filter`처럼 역할을 명확히 하는 이름이 안전하다.
- recommended_route: technical_score_architect

### EvidenceCard EC-009

- evidence_id: EC-009
- source_id: SRC-CSA-2001
- claim_summary: dollar volume 및 share turnover variability는 cross-sectional return과 관련된 trading-activity 변수로 보고되며, OHLCV 기반 liquidity/risk penalty 후보로 검토 가능하다.
- exact_variable_or_indicator: variability of dollar trading volume, share turnover
- formula_description: 거래대금 또는 volume의 변동성을 penalty 또는 caution flag로 변환
- required_inputs: daily close, daily volume; shares outstanding optional if turnover is strict
- required_frequency: daily
- required_history_length: 60-252 trading days
- ranking_type: cross_sectional
- intended_effect: liquidity_filter
- evidence_strength: weak
- implementation_readiness: needs_manual_review
- known_failure_modes: controls include size/book-to-market/momentum, share turnover requires non-OHLCV data, liquidity interpretation may overlap with risk control
- assumptions: traded-value variability can approximate dollar volume variability from OHLCV; this is inference
- limitations: 원천의 controls 중 non-OHLCV 요소가 있으므로 pure technical score claim은 약하다.
- notes_for_score_architect: `trading_activity_variability_penalty`는 core alpha가 아니라 risk-adjusted technical ranking 또는 diagnostic으로만 검토한다.
- recommended_route: technical_score_architect

### EvidenceCard EC-010

- evidence_id: EC-010
- source_id: SRC-LOMW-2000
- claim_summary: chart pattern을 systematic recognition으로 바꾸는 연구는 있으나, nonparametric kernel regression과 pattern geometry는 MVP의 simple/config-first 후보로는 복잡하다.
- exact_variable_or_indicator: head-and-shoulders, double-bottoms, technical pattern recognition
- formula_description: pattern-conditioned return distribution comparison; not a first-pass score formula
- required_inputs: daily price series
- required_frequency: daily
- required_history_length: unknown
- ranking_type: diagnostic_only
- intended_effect: regime_diagnostic
- evidence_strength: weak
- implementation_readiness: needs_manual_review
- known_failure_modes: subjective pattern labeling, high complexity, parameter mining, fragile swing-point detection
- assumptions: `rsi_price_divergence`류의 swing/pattern logic도 유사한 fragility를 가질 수 있다는 것은 inference
- limitations: abstract supports systematic technical analysis research, not a simple MVP score.
- notes_for_score_architect: `rsi_price_divergence` or geometric pattern scores should be deferred unless a simple deterministic proxy is specified before testing.
- recommended_route: diagnostic_backlog

### EvidenceCard EC-011

- evidence_id: EC-011
- source_id: SRC-PI-2007
- claim_summary: technical analysis literature에는 긍정/부정/혼합 결과가 공존하며, data snooping, ex-post rule selection, risk estimation, transaction cost 문제가 반복적으로 지적된다.
- exact_variable_or_indicator: not applicable
- formula_description: not applicable; testing discipline evidence
- required_inputs: not applicable
- required_frequency: not applicable
- required_history_length: not applicable
- ranking_type: diagnostic_only
- intended_effect: regime_diagnostic
- evidence_strength: strong
- implementation_readiness: ready_for_architect_review
- known_failure_modes: parameter search, data snooping, transaction-cost omission, risk mismeasurement
- assumptions: MVP 후보는 simple windows and config-first constraints로 제한해야 한다는 것은 inference
- limitations: review source는 candidate formula 자체를 제공하지 않는다.
- notes_for_score_architect: 모든 후보는 window 후보를 사전에 고정하고, Research Tester 단계에서 ex-post tuning을 금지해야 한다.
- recommended_route: diagnostic_backlog

## CandidateScoreSpecDrafts

### CandidateScoreSpecDraft CSD-001

- candidate_score_id: medium_term_relative_strength
- candidate_name: Medium-Term Relative Strength
- score_family: momentum
- hypothesis_type: technical_ranking
- required_columns: `date`, `symbol`, `close`
- derived_inputs: adjusted daily returns, 60d/120d/252d cumulative return candidates
- formula_outline_plain_language: 각 종목의 중기 누적수익률을 계산한 뒤 같은 날짜의 KOSPI200 universe 안에서 cross-sectional percentile로 변환한다.
- formula_outline_math_optional: `rank_pct(cum_return(close, N))`, where `N` is predefined.
- suggested_windows: 60, 120, 252 trading days; choose before testing
- minimum_history: 252 trading days if 252d variant is enabled; otherwise 120 trading days
- expected_direction: higher_is_better
- normalization_requirement: cross_sectional_percentile with optional winsorization
- missing_data_policy: insufficient history => neutral or missing; do not forward-fill prices across long gaps
- tie_handling_policy: average-rank percentile
- no_lookahead_notes: use only closes available up to decision date; rolling window must exclude future bars
- likely_failure_modes: Korea reversal dominance, momentum crash, overlap with 52-week high and time-series trend
- redundancy_risk: high
- complexity_level: low
- recommended_route: technical_score_architect

### CandidateScoreSpecDraft CSD-002

- candidate_score_id: short_term_overreaction
- candidate_name: Short-Term Overreaction
- score_family: mean_reversion
- hypothesis_type: technical_ranking
- required_columns: `date`, `symbol`, `close`
- derived_inputs: 5d/10d/20d return, optional realized-volatility scaled return
- formula_outline_plain_language: 최근 짧은 구간에서 상대적으로 크게 하락한 종목에 더 높은 reversal candidate 점수를 부여한다. 상승 과열을 반대로 벌점 처리할지는 Score Architect가 명시해야 한다.
- formula_outline_math_optional: `-rank_pct(return_N)` or `rank_pct(-return_N / realized_vol_M)`
- suggested_windows: return window 5, 10, 20 trading days; volatility scale 20 trading days optional
- minimum_history: 60 trading days
- expected_direction: lower_is_better for raw recent return; higher_is_better after reversal-score transform
- normalization_requirement: cross_sectional_percentile or rolling_percentile; choose one before testing
- missing_data_policy: missing close or insufficient window => neutral/missing, not imputed as zero return
- tie_handling_policy: average-rank percentile
- no_lookahead_notes: use trailing returns only; do not classify based on next-day rebound
- likely_failure_modes: persistent downtrends, earnings gaps, low-liquidity names, high turnover
- redundancy_risk: medium
- complexity_level: low
- recommended_route: technical_score_architect

### CandidateScoreSpecDraft CSD-003

- candidate_score_id: donchian_breakout_distance
- candidate_name: Donchian Breakout Distance
- score_family: breakout
- hypothesis_type: technical_ranking
- required_columns: `date`, `symbol`, `high`, `close`
- derived_inputs: N-day rolling high, optional ATR scale
- formula_outline_plain_language: 현재 종가가 최근 N일 최고가에 얼마나 가까운지 또는 얼마나 돌파했는지 측정한다.
- formula_outline_math_optional: `(close_t - rolling_max(high, N)_t) / ATR_M` or `close_t / rolling_max(high, N)_t - 1`
- suggested_windows: breakout window 20, 60; ATR scale 14 or 20 optional
- minimum_history: 60 trading days
- expected_direction: higher_is_better
- normalization_requirement: cross_sectional_percentile after clipping extreme values
- missing_data_policy: insufficient high history => missing; do not substitute close for high unless explicitly defined
- tie_handling_policy: average-rank percentile
- no_lookahead_notes: rolling high must be computed only from bars available at or before scoring date; if using previous breakout level, define whether current bar is included
- likely_failure_modes: false breakouts, crowding into extended names, overlap with relative strength
- redundancy_risk: high
- complexity_level: low
- recommended_route: technical_score_architect

### CandidateScoreSpecDraft CSD-004

- candidate_score_id: moving_average_trend_structure
- candidate_name: Moving Average Trend Structure
- score_family: trend
- hypothesis_type: technical_ranking
- required_columns: `date`, `symbol`, `close`
- derived_inputs: short and long moving averages, price-to-moving-average distance
- formula_outline_plain_language: 단기 이동평균이 장기 이동평균보다 높고 가격이 추세 구조를 유지하는 정도를 측정한다.
- formula_outline_math_optional: `rank_pct((MA_short / MA_long) - 1)` with optional price-above-MA condition
- suggested_windows: 20/60, 50/200 as predefined alternatives; do not test many grids
- minimum_history: 200 trading days if 50/200 is used; 60 trading days for 20/60
- expected_direction: higher_is_better
- normalization_requirement: cross_sectional_percentile or rolling_percentile; one must be selected before testing
- missing_data_policy: insufficient moving-average history => missing
- tie_handling_policy: average-rank percentile
- no_lookahead_notes: moving averages use trailing closes only
- likely_failure_modes: whipsaw, range-bound markets, redundancy with Donchian and momentum
- redundancy_risk: high
- complexity_level: low
- recommended_route: technical_score_architect

### CandidateScoreSpecDraft CSD-005

- candidate_score_id: price_near_52w_high
- candidate_name: Price Near 52-Week High
- score_family: relative_strength
- hypothesis_type: technical_ranking
- required_columns: `date`, `symbol`, `high`, `close`
- derived_inputs: 252d rolling high, close-to-high ratio
- formula_outline_plain_language: 현재 가격이 최근 52주 최고가에 가까울수록 relative strength 후보 점수를 높인다.
- formula_outline_math_optional: `rank_pct(close_t / rolling_max(high, 252)_t)`
- suggested_windows: 252 trading days
- minimum_history: 252 trading days
- expected_direction: higher_is_better
- normalization_requirement: cross_sectional_percentile
- missing_data_policy: fewer than 252 observations => missing or delayed eligibility
- tie_handling_policy: average-rank percentile
- no_lookahead_notes: rolling 52-week high must not include future highs; corporate-action adjustment policy must be explicit
- likely_failure_modes: overlap with medium-term momentum, extended names, insufficient history for new constituents
- redundancy_risk: high
- complexity_level: low
- recommended_route: technical_score_architect

### CandidateScoreSpecDraft CSD-006

- candidate_score_id: time_series_trend_return
- candidate_name: Time-Series Trend Return
- score_family: trend
- hypothesis_type: technical_ranking
- required_columns: `date`, `symbol`, `close`
- derived_inputs: own-stock trailing return, optional sign or volatility scale
- formula_outline_plain_language: 종목 자신의 중기 trailing return이 양호한지 측정한 뒤, cross-sectional scanner에 맞게 동일 날짜 universe 내에서 정규화한다.
- formula_outline_math_optional: `rank_pct(return_N)` or `rank_pct(return_N / realized_vol_M)`
- suggested_windows: 60, 120, 252 trading days
- minimum_history: 252 trading days if long horizon enabled
- expected_direction: higher_is_better
- normalization_requirement: cross_sectional_percentile after time-series feature calculation
- missing_data_policy: insufficient history => missing
- tie_handling_policy: average-rank percentile
- no_lookahead_notes: return window must end at the scoring date only
- likely_failure_modes: futures evidence mismatch, duplicate with relative strength, reversal regimes
- redundancy_risk: high
- complexity_level: low
- recommended_route: technical_score_architect

### CandidateScoreSpecDraft CSD-007

- candidate_score_id: volume_participation_momentum_filter
- candidate_name: Volume Participation Momentum Filter
- score_family: volume_liquidity
- hypothesis_type: risk_adjusted_technical_ranking
- required_columns: `date`, `symbol`, `close`, `volume`
- derived_inputs: rolling volume percentile, traded value proxy `close * volume`, momentum state
- formula_outline_plain_language: momentum 후보가 높은 종목 중 거래량 참여가 비정상적으로 낮거나 과열된 상태인지 보조적으로 표시한다. 독립 alpha가 아니라 filter 또는 interaction 후보로 둔다.
- formula_outline_math_optional: `momentum_score * volume_state_adjustment`, exact adjustment not specified at research stage
- suggested_windows: volume percentile 20, 60, 120; momentum window from linked momentum candidate
- minimum_history: 120 trading days
- expected_direction: conditional
- normalization_requirement: rolling_percentile for volume state, cross-sectional normalization only after formula is fixed
- missing_data_policy: missing volume => candidate unavailable for that date
- tie_handling_policy: average-rank percentile
- no_lookahead_notes: volume state uses trailing volume only; no future turnover data
- likely_failure_modes: volume spike noise, split/corporate-action artifacts, overlap with liquidity penalty
- redundancy_risk: medium
- complexity_level: medium
- recommended_route: technical_score_architect

### CandidateScoreSpecDraft CSD-008

- candidate_score_id: trading_activity_variability_penalty
- candidate_name: Trading Activity Variability Penalty
- score_family: liquidity_risk
- hypothesis_type: risk_adjusted_technical_ranking
- required_columns: `date`, `symbol`, `close`, `volume`
- derived_inputs: rolling variability of `close * volume`, rolling variability of volume, optional volume percentile
- formula_outline_plain_language: 거래활동 변동성이 지나치게 큰 종목에 risk penalty를 부여해 기술 점수의 불안정성을 낮추는 후보로 정의한다.
- formula_outline_math_optional: `-rank_pct(std(log(close * volume), N))`
- suggested_windows: 60, 120 trading days
- minimum_history: 120 trading days
- expected_direction: lower_is_better for raw variability; higher_is_better after penalty transform
- normalization_requirement: cross_sectional_percentile after robust clipping
- missing_data_policy: missing volume or close => missing; do not infer volume
- tie_handling_policy: average-rank percentile
- no_lookahead_notes: use trailing trading activity only
- likely_failure_modes: may penalize legitimate liquidity expansion, may overlap with volatility and volume filters
- redundancy_risk: medium
- complexity_level: medium
- recommended_route: technical_score_architect

### CandidateScoreSpecDraft CSD-009

- candidate_score_id: realized_vol_percentile
- candidate_name: Realized Volatility Percentile
- score_family: volatility_regime
- hypothesis_type: regime_condition
- required_columns: `date`, `symbol`, `close`
- derived_inputs: daily returns, rolling realized volatility, trailing percentile
- formula_outline_plain_language: 종목의 최근 변동성 상태를 direct alpha가 아니라 regime/risk context로 표시한다.
- formula_outline_math_optional: `percentile_trailing(std(daily_return, N), M)`
- suggested_windows: realized volatility 20; percentile history 120 or 252
- minimum_history: 120 trading days
- expected_direction: conditional
- normalization_requirement: rolling_percentile; optional cross-sectional diagnostic table only
- missing_data_policy: insufficient history => unknown regime
- tie_handling_policy: average percentile
- no_lookahead_notes: volatility uses trailing returns only
- likely_failure_modes: role confusion as ranking alpha, overlap with squeeze/ATR scaling
- redundancy_risk: medium
- complexity_level: low
- recommended_route: diagnostic_backlog

## Reject Log

### Reject Item RJ-001

- source_id: SRC-LOMW-2000
- rejected_claim: head-and-shoulders, double-bottoms, or kernel-regression chart patterns should become first-pass MVP scores.
- rejection_reason: too complex for MVP, subjective pattern boundaries, high parameter-mining risk, and not aligned with simple config-first score definitions.
- safer_route_if_any: diagnostic_backlog

### Reject Item RJ-002

- source_id: SRC-LS-2000
- rejected_claim: volume evidence can be described as value/glamour or valuation evidence inside the technical workflow.
- rejection_reason: value/glamour interpretation is not OHLCV-only technical evidence and would violate valuation boundary.
- safer_route_if_any: valuation_agent_handoff only if point-in-time fundamentals become available; otherwise omit valuation language.

### Reject Item RJ-003

- source_id: SRC-MOP-2012
- rejected_claim: futures time-series momentum performance can be directly ported into KOSPI200 constituent ranking.
- rejection_reason: asset universe, instrument structure, liquidity, and portfolio construction differ materially.
- safer_route_if_any: technical_score_architect as cautious `time_series_trend_return` definition draft.

### Reject Item RJ-004

- source_id: SRC-KRW-2025
- rejected_claim: Korean individual-stock medium-term momentum should be treated as a strong ready-to-use candidate.
- rejection_reason: source summary indicates reversal effects are dominant overall, with momentum appearing only in certain sub-periods.
- safer_route_if_any: technical_score_architect with manual review and explicit Korea-specific limitation.

## Manual Review Queue

### Manual Review MR-001

- source_id: SRC-KRW-2025, SRC-EOM-PARK-2023
- issue: Korean evidence is more supportive of reversal than plain momentum.
- needed_clarification: whether KOSPI200 large-cap subset behaves like broader Korean stocks; formation/holding window and industry controls.
- risk_if_used_directly: medium-term momentum may be over-prioritized despite Korea-specific reversal evidence.

### Manual Review MR-002

- source_id: SRC-LS-2000, SRC-CSA-2001
- issue: strict turnover requires shares outstanding, which may be outside OHLCV-only scope.
- needed_clarification: whether MVP allows traded value `close * volume` as a proxy, and how to handle corporate actions.
- risk_if_used_directly: volume filter may accidentally depend on non-OHLCV data or create unstable liquidity bias.

### Manual Review MR-003

- source_id: SRC-BLL-1992, SRC-GH-2004, SRC-MOP-2012
- issue: trend, breakout, 52-week high, and medium-term return candidates may be redundant.
- needed_clarification: Score Architect should define whether these are separate score families or one simplified trend/relative-strength family.
- risk_if_used_directly: multiple near-duplicate trend scores could dominate the composite without adding distinct information.

### Manual Review MR-004

- source_id: SRC-LOMW-2000
- issue: pattern-recognition evidence is systematic but complex.
- needed_clarification: whether any deterministic low-complexity proxy is desired, or whether this entire family should remain deferred.
- risk_if_used_directly: subjective or parameter-heavy pattern definitions may leak ex-post choices into the score design.

### Manual Review MR-005

- source_id: SRC-PI-2007
- issue: testing discipline risks apply to all technical candidates.
- needed_clarification: which windows are allowed before Research Tester work starts, and how many alternatives are permitted.
- risk_if_used_directly: window grid search or post-result parameter tuning could invalidate the conservative workflow.

## Downstream Handoff Summary

- to technical_score_architect: EC-001, EC-002, EC-003, EC-004, EC-005, EC-006, EC-007, EC-008, EC-009
- to diagnostic_backlog: EC-010, EC-011, CSD-009
- to hybrid_split_required: none
- to valuation_agent_handoff: none; only rejected valuation-language fragments from SRC-LS-2000 are noted
- to reject_log: RJ-001, RJ-002, RJ-003, RJ-004

CandidateScoreSpecDrafts ready for Score Architect review:

- CSD-001 `medium_term_relative_strength`
- CSD-002 `short_term_overreaction`
- CSD-003 `donchian_breakout_distance`
- CSD-004 `moving_average_trend_structure`
- CSD-005 `price_near_52w_high`
- CSD-006 `time_series_trend_return`
- CSD-007 `volume_participation_momentum_filter`
- CSD-008 `trading_activity_variability_penalty`

Diagnostic-only or regime-context draft:

- CSD-009 `realized_vol_percentile`

## Step 5 Readiness Note

이 evidence set은 Score Architect가 Step 5 후보 정의를 시작하기에 충분한 초안 수준이다.

단, Step 5가 완료된 것은 아니다. Score Architect가 최종 candidate score definitions를 작성하고, 중복/역할/창 길이/정규화 정책을 확정해야 Step 5 candidate definition 단계가 완료된다.

특히 다음 제한을 유지해야 한다:

- score 구현 없음
- backtest 없음
- adoption decision 없음
- alpha claim 없음
- valuation/fundamental evidence 사용 없음
- Google Scholar direct scraping 없음
