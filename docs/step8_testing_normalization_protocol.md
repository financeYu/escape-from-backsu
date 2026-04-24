# Step 8 Testing and Normalization Protocol

## 1. Purpose

Step 8의 목적은 Step 7 raw technical indicator output을 입력 계약으로 고정하고, Step 9/10에서 score와 normalization을 구현하기 전에 테스트 기준과 정규화 프로토콜을 문서로 잠그는 것이다.

이 문서는 protocol definition이다. `src/normalize/`, `src/scores/`, `src/composite/`의 production logic을 구현하지 않는다.

Step 8 산출물:

- Step 7 indicator output을 입력으로 보는 contract
- Step 9 Research Tester가 구현 전에 확인할 checklist
- Step 10 normalization implementation이 따라야 할 protocol
- diagnostics가 review material이라는 경계
- hard stop guardrail과 deviation log 정책

## 2. Non-Goals and Hard Stops

Step 8에서 금지되는 작업:

- score formula implementation
- production `raw_score` generation
- `normalized_score_time_series` 또는 `normalized_score_cross_sectional` production output
- `rank`, `ranking`, latest ranking output
- `technical_composite_score`
- `final_composite_score`
- family composite 또는 weighted composite
- backtest
- forward return 또는 future return 계산
- alpha signal claim
- score adoption decision
- valuation/fundamental scoring
- `PER`, `PBR`, `ROE` 등 valuation/fundamental data를 technical pipeline에 병합
- price-only evidence를 cheap, value, undervalued, bargain으로 표현

Diagnostics는 adoption evidence가 아니라 review material이다. Correlation, turnover proxy, stability diagnostics는 이후 Technical Selection Reviewer의 입력일 수 있지만, 그 자체로 score adoption decision이 아니다.

## 3. Upstream Input Contract

Step 8은 Step 7 output을 입력으로 본다. 현재 기본 경로는 다음 config key에 의해 결정된다.

```text
config/data.toml -> [indicators].output_path
```

현재 Step 7 기본 output path:

```text
data/processed/technical_indicators.csv
```

필수 입력 컬럼:

| column | source | requirement |
| --- | --- | --- |
| `ticker` | Step 6 | six-character string, leading zeros preserved |
| `date` | Step 6 | parseable date, no future date relative to execution `as_of_date` |
| `open` | Step 6 | validated numeric OHLCV field |
| `high` | Step 6 | validated numeric OHLCV field |
| `low` | Step 6 | validated numeric OHLCV field |
| `close` | Step 6 | validated numeric OHLCV field |
| `volume` | Step 6 | validated numeric OHLCV field |
| `history_count` | Step 7 | ticker별 현재 row까지 확보된 일봉 개수 |
| `minimum_history_required` | Step 7 | Step 7 active windows 기준 최소 history |
| `warmup_state` | Step 7 | `ready`, `warmup`, `insufficient_history` |

Step 7 raw indicator columns는 score가 아니다. 예시는 `return_5d`, `atr_14`, `realized_vol_20`, `rsi_14`, `bollinger_width_20`, `donchian_high_prior_20`, `cmf_20`, `efficiency_ratio_20` 등이다.

Upstream hard requirements:

- `ticker`/`date` pair는 unique해야 한다.
- `ticker`는 integer로 load되면 안 된다.
- date는 ticker별 time-series 계산 전에 deterministic하게 정렬되어야 한다.
- Step 7 output은 score, rank, ranking, composite, alpha, signal 컬럼을 포함하면 안 된다.
- financial/fundamental columns는 Step 8 technical input contract에 포함되지 않는다.

## 4. Downstream Handoff Contract

Step 9 Research Tester는 이 문서가 완료된 뒤에도 predefined candidate만 구현할 수 있다. Ambiguous formula는 `Quant_mvp/docs/score_definitions.md` 또는 versioned Score Architect update에서 먼저 잠겨야 한다.

Step 10 normalization implementation은 이 문서의 정규화 기준을 code/config로 옮긴다. Step 8은 구현을 하지 않는다.

Step 9/10으로 넘기는 필수 handoff:

- input validation requirements
- no-lookahead test requirements
- missing/warmup/coverage semantics
- normalization method semantics
- diagnostics output schema draft
- implementation deviation log policy
- real market data output restriction
- pre-implementation checklist

Downstream output naming guardrail:

- production score output은 Step 9가 열린 뒤에만 가능하다.
- normalized output은 Step 10이 열린 뒤에만 가능하다.
- ranking output은 Step 15 전까지 금지다.
- composite output은 documented composite design 전까지 금지다.
- backtest output은 Step 17 전까지 금지다.

## 5. Indicator Validation Protocol

Step 9/10 구현 전에 toy-data 또는 schema contract test로 확인할 기준:

| validation item | required behavior |
| --- | --- |
| required columns | `ticker`, `date`, OHLCV, Step 7 metadata columns must be present |
| ticker format | six-character string; leading zeros preserved |
| date parseability | invalid parse must fail or be explicitly reported |
| duplicate key | duplicate `ticker`/`date` rows must be rejected or blocked before downstream use |
| deterministic order | sort by `ticker`, `date` for time-series operations; sort by `date`, `ticker` for same-date diagnostics |
| forbidden columns | score/rank/ranking/composite/alpha/signal output columns must be absent in Step 8 |
| financial boundary | financial/fundamental fields must not enter technical validation or scoring |
| warmup metadata | `history_count`, `minimum_history_required`, `warmup_state` must be preserved |
| raw indicator NaN | warmup and insufficient-history NaN must remain observable, not silently filled |

Implementation note: Step 8 tests may validate protocol presence, schema compatibility, and guardrail naming. They must not calculate production normalized scores or rankings.

## 6. No-Lookahead and Time Alignment Tests

No-lookahead 기준:

- Time-series normalization은 ticker별 현재 date까지의 과거 관측치만 사용해야 한다.
- Cross-sectional normalization은 같은 `date`의 available universe만 사용해야 한다.
- Cross-sectional normalization은 future date 정보를 사용하면 안 된다.
- Rolling window가 current row를 포함하는 경우 current row의 raw value 자체가 current/prior input만으로 계산되었음을 먼저 확인해야 한다.
- Donchian-style breakout dependency는 Step 7처럼 prior-bar convention이 필요한 경우 same-date high/low를 쓰지 않는다.
- Forward return, future return, next-period label은 Step 8/9/10 test fixture에 포함하지 않는다.

Ticker/date alignment 기준:

- 모든 row key는 `ticker` + `date`다.
- Time-series 연산은 ticker boundary를 넘으면 안 된다.
- Same-date cross-section은 exact normalized `date` 기준으로 groupby한다.
- Missing dates는 calendar fill로 가정하지 않는다. 거래일 calendar 또는 market holiday 처리가 필요하면 별도 config/documentation이 필요하며, 현재 상태는 unknown이다.
- Tie 또는 output 정렬이 필요한 경우 sorting 기준은 `date`, value, `ticker` 순으로 명시해야 한다. Ranking output은 Step 15 전까지 생성하지 않는다.

Targeted tests:

- 같은 ticker의 future row 값을 바꿔도 과거 date의 normalized candidate value가 바뀌지 않아야 한다.
- 다른 ticker의 첫 row가 이전 ticker의 마지막 row를 참조하지 않아야 한다.
- 같은 date cross-section에 future date row를 추가해도 과거 date의 cross-sectional diagnostic result가 바뀌지 않아야 한다.

## 7. Missing, Warmup, and Coverage Policy

Missing value handling:

- Required OHLCV missing은 downstream normalization 후보에서 제외하거나 blocked로 표시한다.
- Raw indicator missing은 원인을 구분해야 한다: warmup, insufficient history, zero denominator, invalid input, unknown.
- Missing value를 optimistic score로 대체하지 않는다.
- Neutral fill은 production normalization에서 기본값이 아니다. 나중에 neutral shrinkage가 필요하면 Step 10/11에서 config와 문서로 별도 승인해야 한다.

Warmup / insufficient history handling:

- `warmup_state = ready`: 최소 history를 충족한 row다.
- `warmup_state = warmup`: ticker 전체 history는 충분하지만 현재 row까지의 누적 history가 부족하다.
- `warmup_state = insufficient_history`: ticker 전체 history가 최소 history보다 짧다.
- warmup rows는 production scoring candidate에서 제외되거나 explicit flag 처리되어야 한다.
- `insufficient_history`는 normalized output을 만들지 않는 것이 기본값이다.

Minimum observation policy:

- Time-series normalization의 기본 minimum non-null observations는 `Quant_mvp/config/thresholds.toml -> [quality].min_non_nan_observations`를 따른다.
- 현재 reference value는 `60`이다.
- Cross-sectional normalization의 기본 minimum same-date count는 `Quant_mvp/config/thresholds.toml -> [quality].min_cross_section_count`를 따른다.
- 현재 reference value는 `20`이다.
- Candidate-specific `minimum_history`가 더 크면 더 보수적인 값을 사용한다.
- Config key가 없거나 충돌하면 implementation은 중단하고 deviation log에 `blocked_by_missing_config`를 기록해야 한다.

Coverage status semantics:

| `coverage_status` | meaning |
| --- | --- |
| `adequate` | minimum observation/count와 coverage threshold를 충족 |
| `partial` | 사용할 수는 있으나 warning coverage threshold 미만 |
| `sparse` | minimum threshold 근처 또는 미달로 review warning 필요 |
| `blocked` | minimum observation/count 미달 또는 필수 dependency missing |
| `unknown` | 원인을 아직 분류하지 못함 |

Warmup status semantics:

| `warmup_status` | mapping / meaning |
| --- | --- |
| `ready` | Step 7 `warmup_state = ready` |
| `warmup` | Step 7 `warmup_state = warmup` |
| `insufficient_history` | Step 7 `warmup_state = insufficient_history` |
| `blocked_by_missing_dependency` | 필요한 raw indicator가 없거나 all-NaN |
| `unknown` | upstream status가 없거나 해석 불가 |

`warmup_status`는 downstream schema name으로 사용할 수 있다. Step 7의 기존 컬럼명 `warmup_state`는 input contract에서 그대로 보존한다.

## 8. Normalization Protocol

Normalization은 Step 10에서 구현한다. Step 8은 방법과 검증 기준만 고정한다.

공통 원칙:

- Normalization은 raw score formula가 잠긴 뒤에만 적용한다.
- `score_direction`은 candidate definition에 명시되어야 한다.
- Higher-is-better 변환은 candidate별로 문서화해야 한다.
- Missing value를 유리한 방향으로 채우지 않는다.
- `coverage_status`, `warmup_status`, `data_quality_flag`를 normalized value와 함께 보존한다.
- Time-series normalization과 cross-sectional normalization은 의미가 다르므로 별도 컬럼/파일/diagnostic으로 관리한다.
- 0-100 mapping은 Step 10 구현 대상이며, Step 8에서는 production output을 생성하지 않는다.

### 8.1 Time-Series Normalization

목적:

- ticker별 historical context를 제공한다.
- chart overlay 또는 per-stock history review에 사용할 수 있다.
- 같은 date의 다른 ticker와 직접 비교하는 의미로 해석하면 안 된다.

Protocol:

- group key는 `ticker`다.
- sort key는 `ticker`, `date`다.
- 각 row의 normalization context는 같은 `ticker`에서 `date <= current date`인 observations만 사용한다.
- Rolling context window는 config-first로 정한다. 현재 Step 8에서는 exact rolling normalization window가 unknown이다.
- Minimum non-null observations는 `[quality].min_non_nan_observations`와 candidate-specific `minimum_history` 중 더 보수적인 값을 사용한다.
- Observation count 미달이면 normalized value는 missing으로 두고 `coverage_status = blocked` 또는 `sparse`를 기록한다.
- Tie handling은 deterministic해야 하며, percentile 방식이면 tied values는 average percentile을 사용한다.

Allowed future methods:

- rolling percentile
- expanding percentile
- rolling robust z-score
- documented candidate-specific transform

Forbidden:

- future observations 포함
- whole-sample final distribution 사용
- ticker 간 섞인 rolling context
- warmup missing을 optimistic value로 대체

### 8.2 Cross-Sectional Normalization

목적:

- 같은 `date`의 available universe 안에서 relative standing을 계산한다.
- 향후 stock-selection review의 입력이 될 수 있지만 Step 8에서는 ranking을 생성하지 않는다.

Protocol:

- group key는 `date`다.
- universe는 해당 `date`에 실제로 available하고 validation을 통과한 ticker들이다.
- Future date의 ticker membership, future liquidity, future delisting/entry 정보를 사용하지 않는다.
- Minimum same-date count는 `[quality].min_cross_section_count`를 따른다.
- 현재 reference value는 `20`이다.
- 같은 date에서 raw value가 missing인 ticker는 denominator에 넣지 않는다.
- Cross-sectional percentile은 tied values에 average percentile을 부여한다.
- Output 정렬이 필요한 경우 `date`, normalized value descending, `ticker` ascending을 사용한다. 단, rank 컬럼은 Step 15 전까지 만들지 않는다.

Forbidden:

- 여러 date를 한 번에 섞은 cross-sectional scaling
- future date distribution으로 current date scaling
- missing ticker를 favorable neutral 값으로 denominator에 포함
- normalized output을 latest ranking처럼 저장

### 8.3 Robust Z-Score Policy

기본 robust z-score:

```text
robust_z = (value - median) / (1.4826 * MAD)
MAD = median(abs(value - median))
```

기준:

- Median과 MAD는 해당 normalization context 안에서만 계산한다.
- Time-series context는 ticker별 과거 observations만 사용한다.
- Cross-sectional context는 같은 date의 available observations만 사용한다.
- `MAD = 0`이거나 insufficient하면 fallback 또는 block을 명시해야 한다.

Documented fallback:

- `MAD = 0`이고 IQR이 positive이면 `IQR / 1.349` scale을 사용할 수 있다.
- IQR도 zero이면 normalized value를 missing으로 두고 `data_quality_flag`에 `zero_dispersion`을 기록한다.
- Fallback 사용 여부는 diagnostics와 implementation deviation log에 기록한다.

Hard stops:

- Zero dispersion에서 임의로 favorable score를 만들지 않는다.
- 전체 sample median/MAD를 current date 이전/이후 구분 없이 사용하지 않는다.

### 8.4 Winsorization and Clipping

Winsorization/clipping threshold는 config-first 원칙을 따른다.

현재 reference config:

```text
Quant_mvp/config/thresholds.toml -> [outliers].winsorize_lower_pct = 0.01
Quant_mvp/config/thresholds.toml -> [outliers].winsorize_upper_pct = 0.99
```

Policy:

- Raw value winsorization은 normalization context 안에서만 수행한다.
- Time-series winsorization은 ticker별 과거 context만 사용한다.
- Cross-sectional winsorization은 같은 date context만 사용한다.
- Robust z-score clipping threshold는 현재 config에서 unknown이다.
- Step 10에서 clipping threshold를 hardcode하면 deviation log에 threshold, rationale, scope, config 미사용 이유를 적어야 한다.
- Clipping은 diagnostics에 outlier sensitivity를 숨기면 안 된다. Pre-clipping distribution diagnostics를 별도로 보존해야 한다.

### 8.5 Tie Handling

Tie handling은 deterministic해야 한다.

기본 정책:

- Percentile transform은 tied raw values에 average percentile을 부여한다.
- Stable output order는 `date`, normalized value descending, `ticker` ascending이다.
- Time-series tie diagnostics는 `ticker`, `date` ascending을 유지한다.
- Ranking column은 Step 15 전까지 생성하지 않는다.
- If exact tie policy cannot be implemented by the chosen library, the implementation must document the library behavior as inference and add a deviation log entry.

## 9. Diagnostics Protocol

Diagnostics는 품질 관리와 review material이다. Diagnostics는 adoption evidence, alpha signal, ranking, valuation opinion이 아니다.

Diagnostics output schema draft:

| column | requirement |
| --- | --- |
| `diagnostic_name` | required; e.g. `coverage`, `stability`, `correlation`, `turnover_proxy` |
| `score_name` | conditional; predefined candidate or `unknown` |
| `score_family` | conditional; predefined family or `unknown` |
| `normalization_scope` | `time_series`, `cross_sectional`, `raw_indicator`, `unknown` |
| `date` | conditional; same-date diagnostics only |
| `start_date` | conditional; rolling diagnostics window start |
| `end_date` | conditional; rolling diagnostics window end |
| `ticker_count` | required where cross-sectional |
| `observation_count` | required where time-series |
| `missing_count` | required |
| `coverage_ratio` | required |
| `warmup_ready_count` | required where available |
| `zero_dispersion_count` | required where robust z-score used |
| `diagnostic_value` | optional numeric value |
| `diagnostic_status` | `pass`, `warn`, `blocked`, `info`, `unknown` |
| `coverage_status` | see section 7 |
| `warmup_status` | see section 7 |
| `data_quality_flag` | see section 10 |
| `implementation_deviation_id` | optional link to deviation log |
| `notes` | Korean summary; unknowns marked as `unknown` |

### 9.1 Coverage

Coverage diagnostics must report:

- non-null observation count
- missing count
- coverage ratio
- blocked candidate count
- warmup/insufficient-history count
- per-score and per-family coverage if score implementation later exists

Thresholds should use `Quant_mvp/config/thresholds.toml -> [coverage]`.

### 9.2 Stability

Stability diagnostics plan:

- Compare current normalized candidate values against prior available date values.
- Measure distribution drift using same method and same universe rules.
- Mark output as diagnostic-only review material.
- Do not call stability a proof of robustness or alpha.

Current exact stability formula is unknown until Step 9/10 implementation design.

### 9.3 Correlation

Correlation diagnostics plan:

- Use predefined score candidates only after Step 9 implementation.
- Cross-sectional correlation must be computed within the same date, then summarized across dates.
- Time-series correlation must be ticker-local or explicitly documented.
- Spearman thresholds should use `Quant_mvp/config/thresholds.toml -> [redundancy]`.
- Correlation is redundancy review input, not adoption decision.

### 9.4 Turnover Proxy

Turnover proxy diagnostics plan:

- Use changes in same-date relative ordering or percentile buckets after Step 10.
- Because ranking output is prohibited before Step 15, Step 9/10 may compute diagnostic-only movement metrics without exporting production ranks.
- Turnover proxy is review material and must not be framed as trading turnover or executable portfolio turnover.
- Exact formula remains unknown until Step 9/10 candidate output exists.

## 10. Data Quality Flags

`data_quality_flag` must make data limits visible. It must not hide missing or invalid rows.

Suggested semantics:

| flag | meaning |
| --- | --- |
| `valid` | no known data-quality issue for the row/context |
| `missing_required_input` | required OHLCV or indicator dependency missing |
| `invalid_ticker` | ticker is not six-character string-like |
| `leading_zero_lost` | ticker appears to have been loaded as integer or shortened |
| `invalid_date` | date parse failed |
| `future_date` | date exceeds allowed `as_of_date` |
| `duplicate_ticker_date` | duplicate row key detected |
| `invalid_numeric` | numeric conversion failed |
| `negative_volume` | volume is negative |
| `warmup` | current row is in warmup period |
| `insufficient_history` | ticker lacks minimum history |
| `insufficient_observations` | normalization context lacks minimum non-null observations |
| `insufficient_cross_section` | same-date universe count below threshold |
| `zero_dispersion` | MAD/IQR or equivalent dispersion is zero |
| `clipped_outlier` | value was clipped by documented policy |
| `blocked_by_missing_config` | required config key is missing |
| `implementation_deviation` | implementation differs from locked definition |
| `unknown` | issue exists but exact cause is unknown |

If multiple flags apply, store them in deterministic order. A single string field may use semicolon-separated values until a structured list schema is introduced. `valid` must not appear with any other flag.

## 11. Toy-Data Test Plan

Allowed Step 8 tests:

- protocol document exists and includes hard-stop guardrails
- required Step 7 input contract columns are named
- `ticker` leading-zero examples remain string-like
- duplicate `ticker`/`date` fixture is rejected or marked blocked in contract tests
- warmup and insufficient-history states are preserved in toy fixtures
- no-lookahead toy checks use artificial values only
- robust z-score zero-MAD handling is specified or blocked
- tie handling uses deterministic average percentile in toy-only helper checks if a helper is introduced later
- diagnostics schema columns are present in hand-built toy frames
- forbidden output tokens are absent from Step 8 toy artifacts

Forbidden Step 8 tests:

- production score formula correctness
- real market normalized score output
- cross-sectional ranking output
- latest ranking file generation
- composite score generation
- backtest metrics
- forward return / future return labels
- valuation/fundamental joins
- alpha claim validation

Test naming guidance:

- Prefer names such as `test_step8_protocol_guardrails`, `test_step8_toy_alignment_contract`, `test_step8_diagnostics_schema_contract`.
- Avoid names that imply production score/ranking/composite output.

## 12. Real Market Data Restrictions

Step 8 may inspect real Step 7 output only for schema presence and guardrail compatibility.

Step 8 must not generate:

- real market production `raw_score`
- real market normalized score output
- real market ranking output
- latest ranking
- composite score output
- score backtest report
- valuation/fundamental score table

If a test needs data, use toy fixtures. If real market output is accidentally created, mark it as generated output, do not use it as evidence, and remove or ignore it according to repository generated-output policy.

## 13. Implementation Deviation Log Policy

Step 9/10 implementation must create or update a deviation log when implementation differs from this protocol, `Quant_mvp/docs/score_definitions.md`, or config policy.

Suggested path:

```text
reports/diagnostics/implementation_deviation_log.csv
```

Suggested schema:

| column | requirement |
| --- | --- |
| `deviation_id` | stable identifier |
| `step` | e.g. `Step 9`, `Step 10` |
| `score_name` | candidate name or `unknown` |
| `affected_field` | formula, normalization, threshold, coverage, warmup, output schema |
| `expected_behavior` | protocol/config/document expectation |
| `actual_behavior` | implementation behavior |
| `reason` | why deviation was necessary |
| `risk` | conservative risk summary |
| `review_required` | `true` or `false` |
| `created_at_utc` | timestamp |

Hardcoded threshold deviation must state:

- threshold value
- why config was not used
- expected behavioral effect
- whether historical interpretation changes
- whether review_mvp or Technical Selection Reviewer should inspect it later

## 14. Step 9 Research Tester Checklist

Step 9 구현 전 checklist:

- [ ] Step 8 protocol 문서가 최신이다.
- [ ] Target score exists in `Quant_mvp/docs/score_definitions.md` or a versioned Score Architect update.
- [ ] Formula variant is locked; ambiguous formula is not guessed.
- [ ] Required Step 7 indicator columns are present or dependency gap is documented.
- [ ] `ticker` remains six-character string with leading zeros preserved.
- [ ] `ticker`/`date` uniqueness is validated.
- [ ] No future date or lookahead input is used.
- [ ] Time-series context uses only ticker-local current/prior observations.
- [ ] Cross-sectional context uses only same-date available universe.
- [ ] Missing values are not converted to optimistic values.
- [ ] Warmup and insufficient-history rows are excluded or explicitly flagged.
- [ ] Minimum observation policy is applied from config and candidate definition.
- [ ] Robust z-score fallback is documented before use.
- [ ] Winsorization/clipping thresholds come from config or deviation log.
- [ ] Tie handling is deterministic.
- [ ] `coverage_status`, `warmup_status`, and `data_quality_flag` semantics are preserved.
- [ ] Diagnostics are labeled review material, not alpha signals or adoption decisions.
- [ ] No real market normalized output is generated before Step 10.
- [ ] No ranking output is generated before Step 15.
- [ ] No composite score is generated before documented composite design.
- [ ] No backtest is run before Step 17.
- [ ] Financial/fundamental data remains outside the technical pipeline.

## 15. Completion Criteria

Step 8 is COMPLETE when:

- this protocol exists and covers no-lookahead, alignment, missingness, warmup, coverage, normalization, diagnostics, and deviation logging
- Step 7 upstream input contract is explicit
- Step 9/10 downstream handoff is explicit
- real market production score/ranking/composite/backtest output remains ungenerated
- docs checklist and roadmap status mark Step 8 complete and Step 9 waiting
- any Step 8 tests are protocol/guardrail tests only
- hard-stop self-check finds no score implementation, normalized production output, ranking, composite, backtest, or valuation/fundamental scoring

Step 9 remains WAITING until explicitly opened by a later user instruction or roadmap transition.
