# Quant Project Reference For ChatGPT Project

이 문서는 ChatGPT Project의 "프로젝트 참조 컨텍스트"에 넣기 위한 요약본이다.
기준 시점은 2026-04-25 Asia/Seoul이며, 현재 저장소 상태는 `docs/project_checklist.md`와
`docs/roadmap_status.md`를 기준으로 정리했다.

## 1. 최상위 기준

참조 우선순위:

1. 사용자의 최신 명시 지시
2. 루트 `AGENTS.md`
3. `docs/project_checklist.md`
4. `docs/roadmap_status.md`
5. 세부 프로젝트의 `AGENTS.md` 및 관련 docs/config

루트 워크스페이스는 `master_mvp`이고, Quant 관련 설계 책임은 `Quant_mvp`가 맡는다.
단, 현재 실행 파이프라인과 표준 schema/config/docs 일부는 루트에도 존재한다.

## 2. 프로젝트 목적

이 프로젝트의 목표는 KOSPI200 구성 종목을 대상으로 하는 일봉 OHLCV 기반
기술적/통계적 멀티 스코어 랭킹 엔진을 만드는 것이다.

핵심 성격:

- 설명 가능해야 한다.
- 모듈화되어야 한다.
- 백테스트 가능성을 고려해 설계한다.
- conservative quant engineering을 우선한다.
- config-first 원칙을 따른다.
- future data와 lookahead를 막는다.
- 결과를 본 뒤 score definition을 조용히 바꾸지 않는다.

이 저장소는 단일 매매 전략 저장소가 아니다.
이 저장소는 AI black-box alpha 저장소가 아니다.
valuation/fundamental analysis는 기술 스캐너가 완성된 뒤로 미룬다.

## 3. 현재 로드맵 상태

`docs/roadmap_status.md` 기준 현재 활성 단계:

```text
Step 8 = 테스트 / 정규화 프로토콜 작성
```

현재 판정:

| Step | 상태 |
| --- | --- |
| Step 1 | COMPLETE or mostly complete |
| Step 2 | COMPLETE |
| Step 3 | COMPLETE |
| Step 4 | COMPLETE |
| Step 5 | COMPLETE |
| Step 6 | COMPLETE |
| Step 7 | COMPLETE |
| Step 8 | Next, not implemented yet |

중요: Step 2 financial collector validation은 `COMPLETE`다. `chart_mvp` loader/cache 경로로
KOSPI200 200개 financial statement cache를 생성하고 validation을 실행했다. 단, 현재 Naver financial rows에는
disclosure/filing/availability date가 없어 `point_in_time_status = unverified`이며 valuation/fundamental data는
계속 `technical_composite_score`, `final_composite_score`, technical scoring에 들어가지 않는다.

## 4. 현재 절대 금지 사항

- score definition 전 score implementation 금지
- documented composite design 전 composite score implementation 금지
- Step 9 전 Research Tester score implementation 금지
- Step 15 전 latest ranking output 생성 금지
- Step 17 전 backtest 금지
- financial/fundamental data를 `technical_composite_score`에 넣기 금지
- financial/fundamental data를 `final_composite_score`에 넣기 금지
- price-only evidence를 cheap, value, undervalued, bargain 등 valuation language로 표현 금지
- diagnostics를 alpha signal 또는 stock-selection score처럼 표현 금지
- future data, lookahead, silent score redefinition 금지

## 5. Step 2 상태

Step 2의 목적은 네이버 financial/data collector와 관련 validation을 확인하는 것이다.

완료 또는 이후 guardrail에 반영된 항목:

- `src/preprocess/schema_validator.py` 강화
- dtype expectations 추가
- date parseability check 추가
- numeric conversion safety check 추가
- duplicate `ticker`/`date` validation 추가
- ticker leading-zero preservation check 명시
- legacy output inventory 문서화: `docs/legacy_output_inventory.md`
- financial data는 `valuation_deferred` 상태 유지

완료된 follow-up:

- `chart_mvp` loader/cache 경로로 `chart_mvp/data/*_financial_statements.csv` 200개 로컬 런타임 캐시 생성
- financial validation 실행: 200 files, 26,208 rows, 200 unique codes
- `chart_mvp/reports/data_quality/financial_data_check.md`를 current validation context로 재생성
- `collected_at`은 historical point-in-time safety 근거가 아니라 observation timestamp로만 취급

유지되는 제한:

- financial data는 technical scoring, final composite scoring, valuation verdict에 사용되지 않는다.
- 생성된 financial cache와 `chart_mvp/reports/data_quality/*`는 runtime artifact이며 source-controlled project state가 아니다.

## 6. Step 3-7 산출물 요약

Step 3:

- 루트 config/docs/source 구조 정리
- canonical OHLCV schema 문서화: `docs/data_schema.md`
- config-first 경로/상태 정리: `config/*.toml`
- financial data boundary는 `valuation_deferred`

Step 4:

- 기술 분석과 밸류에이션 경계 고정: `docs/technical_valuation_boundary.md`
- branch 정책 고정: `docs/score_branch_policy.md`
- Step 5 진입 기준 정리: `docs/selection_criteria.md`
- valuation/fundamental data는 technical score와 final composite에서 제외

Step 5:

- Score Architect candidate definition 완료
- 주요 산출물:
  - `Quant_mvp/docs/score_catalog.md`
  - `Quant_mvp/docs/score_definitions.md`
  - `Quant_mvp/docs/family_map.md`
  - `Quant_mvp/config/scores.toml`
- `enabled = true`는 candidate registry visibility만 의미한다.
- `runtime_enabled = false`가 runtime scoring 금지를 유지한다.

Step 6:

- canonical daily OHLCV preprocessing 구현
- 주요 코드:
  - `src/preprocess/daily_ohlcv.py`
  - `src/preprocess/schema_validator.py`
- 입력: `chart_mvp/data/*_daily_prices.csv`
- 출력: `data/processed/daily_ohlcv.csv`
- report:
  - `reports/preprocess/preprocess_summary.md`
  - `reports/preprocess/preprocess_validation_summary.csv`
  - `reports/preprocess/preprocess_invalid_rows.csv`
- focused tests: `tests/preprocess/test_step6_preprocess.py`

Step 7:

- raw technical indicator dependency layer 구현
- 주요 코드: `src/indicators/technical.py`
- 입력: `data/processed/daily_ohlcv.csv`
- 출력: `data/processed/technical_indicators.csv`
- report:
  - `reports/indicators/indicator_summary.md`
  - `reports/indicators/indicator_validation_summary.csv`
- metadata:
  - `history_count`
  - `minimum_history_required`
  - `warmup_state`
- focused tests: `tests/indicators/test_step7_indicators.py`
- score, normalized score, rank, composite, backtest, valuation/fundamental score는 생성하지 않는다.

주의: `docs/research_tester_readiness.md`에는 Step 7이 미완료라고 적힌 오래된 상태 설명이 포함될 수 있다.
최신 상태 판단은 `docs/roadmap_status.md`와 `docs/step7_indicator_layer.md`를 우선한다.

## 7. Canonical Data Contract

canonical OHLCV required columns:

- `ticker`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`

ticker 정책:

- string으로 보존
- six-character code
- leading zero 보존 필수
- integer ticker loading 금지

date 정책:

- parseable date 필요
- future date는 reject/report

numeric 정책:

- `open`, `high`, `low`, `close`, `volume`은 안전하게 numeric-convertible이어야 한다.
- `volume`은 non-negative이어야 한다.
- duplicate key는 `ticker + date`다.

## 8. Valuation Boundary

현재 valuation 상태:

```text
valuation_status = deferred
financial_data_usage_now = inventory_only_or_gui_display_only
point_in_time_status = unverified
financial_data_in_technical_score = false
financial_data_in_final_composite_score = false
```

valuation scoring 전에 필요한 것:

- fundamental field definition
- filing date, disclosure date, effective date, 또는 availability date
- reporting lag policy
- stale data policy
- 필요 시 market capitalization 또는 share-count logic
- sector-relative valuation이면 sector/industry metadata

위 조건 없이는 valuation opinion을 만들지 않는다. PER/PBR/ROE display 값은 technical score, final composite,
ranking에 영향을 주면 안 된다.

valuation-aware work 요청이 들어오면 `Quant_mvp/agents/valuation/AGENTS.md`로 라우팅한다.

## 9. Step 5 Candidate Scores

현재 MVP candidate registry는 아래 8개다. 모두 implementation/adoption/ranking이 아니라 definition/visibility 상태다.

| score_name | family | branch | role |
| --- | --- | --- | --- |
| `short_term_overreaction` | `mean_reversion` | `technical` | core candidate |
| `atr_adjusted_oversold_distance` | `mean_reversion` | `technical` | robustness variant |
| `donchian_breakout_distance` | `breakout` | `technical` | core candidate |
| `bollinger_width_squeeze` | `squeeze_expansion` | `technical` | regime/conditional candidate |
| `cmf_confirmation` | `flow` | `technical` | confirmation candidate |
| `rsi_price_divergence` | `oscillator_divergence` | `technical` | cautious deterministic proxy |
| `realized_vol_percentile` | `volatility_regime` | `diagnostic` | regime diagnostic |
| `efficiency_ratio_trend` | `trend_efficiency` | `technical` | distinctness candidate |

중복 위험:

- mean reversion cluster: `short_term_overreaction`, `atr_adjusted_oversold_distance`, `rsi_price_divergence`
- trend/breakout cluster: `donchian_breakout_distance`, `efficiency_ratio_trend`, folded relative-strength ideas
- volatility context cluster: `bollinger_width_squeeze`, `realized_vol_percentile`, ATR scaling
- volume/activity cluster: `cmf_confirmation`, folded volume participation ideas

## 10. Step 8에서 해야 할 일

현재 다음 단계는 Step 8 테스트 / 정규화 프로토콜 작성이다.

Step 8에서 정의해야 할 것:

- time-series normalization protocol
- cross-sectional normalization protocol
- robust z-score / winsorization / clipping policy
- tie handling
- minimum observation and warmup policy
- `warmup_state`, `coverage_status`, `data_quality_flag` semantics
- toy-data tests 범위
- real market data score output 금지 범위
- implementation deviation log policy
- diagnostics output schema

Step 8에서 하면 안 되는 것:

- real score formula implementation
- normalized production score output
- latest ranking generation
- composite score generation
- backtest
- valuation/fundamental scoring

## 11. 현재 구현 상태

현재 구현된 것:

- Step 6 preprocessing pipeline
- Step 7 raw technical indicator dependency layer
- schema validation and focused tests
- config-first path references

현재 구현되지 않은 것:

- production score formulas
- normalized score outputs
- `technical_composite_score`
- `final_composite_score`
- latest ranking
- backtest
- valuation/fundamental scoring

최근 검증 기록:

- 2026-04-25 기준 `python -m src.indicators.technical --project-root .`: rows=39390, indicator_columns=37, metadata_columns=3
- 2026-04-25 기준 root `python -m pytest`: 107 passed, 4 skipped

## 12. Generated Output Policy

source-controlled by default:

- code
- tests
- docs
- config
- small reference fixtures
- project-level agent instructions

not source-controlled by default:

- generated chart images
- daily price caches
- scan outputs
- local reports generated from current runs
- `__pycache__`
- `*.pyc`
- virtual environments
- `.env` and secrets

Generated output은 downstream evidence로 쓰기 전에 current validation context에서 다시 확인한다.

## 13. ChatGPT 응답 규칙

ChatGPT가 이 프로젝트를 도울 때:

- 한국어로 진행/상태/요약을 말한다.
- code identifiers, config keys, file paths, exported column names는 English를 유지한다.
- unknown은 unknown으로 둔다.
- inference는 inference라고 표시한다.
- optimistic alpha, robustness, valuation claim을 하지 않는다.
- price-only evidence를 valuation으로 표현하지 않는다.
- ambiguous score formula는 추측해서 구현하지 말고 Score Architect update 대상으로 돌린다.
- completed Step은 기본적으로 신뢰하고, 현재 Step의 직접 의존성만 hard-stop 수준으로 확인한다.
- Step 종료 보고가 필요하면 `COMPLETE`, `PARTIALLY COMPLETE`, `NEEDS FIX` 중 하나를 명시한다.

## 14. Routing

- repository/Git/CI/release policy: root `master_mvp`
- score taxonomy/formula/config/review: `Quant_mvp`
- research source/evidence ingestion: `reserch_mvp` 또는 `Quant_mvp/agents/research`
- valuation/fundamental review: `Quant_mvp/agents/valuation`
- runnable scanner, charts, GUI, caches: `chart_mvp`
- specialist code review/minimal repair: `review_mvp`
- cross-project or final validation: root master review, 필요 시 `review_mvp`

`Quant_mvp`의 Technical Selection Reviewer와 `review_mvp`를 혼동하지 않는다.
전자는 technical score adoption reviewer이고, 후자는 code/integration risk reviewer다.

## 15. Minimal Decision Rule

현재 상태에서 가장 안전한 기본 판단:

```text
Step 8 work is allowed.
Step 9 score implementation is not allowed yet.
Step 15 ranking is not allowed yet.
Step 17 backtest is not allowed yet.
Valuation remains deferred.
Financial/fundamental data must stay out of technical and final composite scoring.
```
