# 퀀트 프로젝트 체크리스트

## 1. 프로젝트 목표

KOSPI200 구성 종목을 대상으로 하는 일봉 OHLCV 기반 기술적/통계적 멀티 스코어 랭킹 엔진을 만든다.

이 프로젝트는 다음 성격을 유지한다.

- 설명 가능해야 한다.
- 모듈화되어야 한다.
- 백테스트가 가능하도록 설계해야 한다.
- 보수적인 quant engineering을 우선한다.
- config-first 원칙을 따른다.
- future data와 lookahead를 막아야 한다.

이 저장소는 단일 매매 전략 저장소가 아니다.
이 저장소는 AI black-box alpha 저장소가 아니다.
valuation/fundamental analysis는 기술 스캐너가 완성된 뒤로 미룬다.

## 2. 전역 규칙

- conservative quant engineering을 기본값으로 둔다.
- config-first implementation을 우선한다.
- future data를 사용하지 않는다.
- lookahead를 허용하지 않는다.
- 결과를 본 뒤 score definition을 조용히 바꾸지 않는다.
- score definition을 문서화하기 전에는 score implementation을 하지 않는다.
- diagnostics를 alpha signal처럼 표현하지 않는다.
- price-only evidence에서 valuation을 추론하지 않는다.
- technical oversold 상태를 cheap 또는 value라고 부르지 않는다.
- unknown은 unknown으로 남긴다.
- inference는 inference라고 표시한다.
- paths, config keys, column names, function names는 English를 유지한다.
- 사용자에게 보여주는 요약과 상태 보고는 한국어를 기본으로 한다.

## 3. 에이전트 워크플로우

Stage 1: Score Architect

- 후보 점수의 목적, family, branch, raw inputs, formula path, normalization candidates, minimum history, overlap risk, failure modes를 정의한다.
- score 구현, backtest, optimization, adoption을 하지 않는다.

Stage 2: Research Tester

- 문서화되고 승인된 MVP technical score 후보만 구현한다.
- 재현 가능한 tests, diagnostics, normalized outputs를 만든다.
- 결과를 본 뒤 score를 조용히 재정의하지 않는다.

Stage 3: Technical Selection Reviewer

- 테스트된 technical score를 usefulness, stability, redundancy, market-structure plausibility 기준으로 비교한다.
- 기술 점수를 보수적으로 adopt, defer, downgrade, reject한다.
- valuation review를 수행하지 않는다.

Stage 4: Adoption Synthesis

- Technical Selection Reviewer의 결정을 명시적인 adoption plan으로 변환한다.
- composite design은 투명하고 문서화되어야 한다.
- financial data를 technical 또는 final composite scoring에 병합하지 않는다.

## 4. 전체 로드맵

| Step | 이름 |
| --- | --- |
| Step 1 | 에이전트 / 운영 규칙 수립 |
| Step 2 | 네이버 파이낸셜 데이터 수집기 검증 |
| Step 3 | 디렉터리 / config / 표준 스키마 정리 |
| Step 4 | 기술 분석과 밸류에이션 경계 고정 |
| Step 5 | Score Architect: MVP 기술 점수 후보 정의 |
| Step 6 | 데이터 전처리 파이프라인 구현 |
| Step 7 | 기술 지표 계산 레이어 구현 |
| Step 8 | 테스트 / 정규화 프로토콜 작성 |
| Step 9 | Research Tester: MVP 점수 구현 |
| Step 10 | 정규화 정책 구현 |
| Step 11 | Composite Score 구조 설계 |
| Step 12 | 중복성 / 상관성 진단 구현 |
| Step 13 | Technical Selection Reviewer |
| Step 14 | Adoption Synthesis |
| Step 15 | 최신 랭킹 출력 구현 |
| Step 16 | 종목별 상세 리포트 구현 |
| Step 17 | 보수적 백테스트 |
| Step 18 | 밸류에이션 확장 준비 |
| Step 19 | 자동 실행 파이프라인 구성 |
| Step 20 | 최종 Done 검증 |

## 4.1 Step 4 완료 기준

Step 4는 아래 기준이 모두 문서와 config에 반영되면 완료로 본다.

- `technical`, `valuation`, `diagnostic`, `hybrid`, `out_of_scope` branch가 분리되어 있다.
- daily OHLCV 기반 technical score와 point-in-time fundamental 기반 valuation score의 역할이 분리되어 있다.
- `valuation_status`가 현재 `valuation_deferred` 또는 `unavailable`로 유지된다.
- price-only evidence를 cheap, value, undervalued, bargain 같은 valuation language로 표현하지 않는다.
- financial data가 `technical_composite_score` 또는 `final_composite_score`에 들어가지 않는다는 정책이 명시되어 있다.
- `PER`, `PBR`, `ROE` display 값은 technical scoring이나 final composite에 영향을 주지 않는다.
- diagnostics는 alpha signal이나 stock-selection score로 표현하지 않는다.
- Step 5 전 production score implementation, Step 9 전 Research Tester implementation, Step 17 전 backtest를 금지한다.
- legacy ranking-like outputs는 current Step evidence로 사용하지 않는다.

## 4.2 Step 5 완료 기준

Step 5는 아래 기준이 모두 문서와 config에 반영되면 완료로 본다.

- MVP technical 또는 diagnostic 후보의 `score_name`, `score_family`, `score_branch`, purpose, regime fit, raw inputs, formula design path, normalization candidates, minimum history, overlap risk, failure modes, data requirements, interpretability notes가 명시되어 있다.
- `Quant_mvp/docs/score_catalog.md`, `Quant_mvp/docs/score_definitions.md`, `Quant_mvp/docs/family_map.md`가 작성되어 있다.
- 중복 위험이 큰 trend, breakout, relative strength, mean-reversion 후보가 family map에서 watchlist로 분리되어 있다.
- direct alpha가 아닌 regime 또는 diagnostic 후보는 `diagnostic` 또는 conditional context로 표시되어 있다.
- Step 5 결과가 score implementation, ranking generation, composite scoring, adoption decision, backtest를 활성화하지 않는다.
- valuation/fundamental data는 계속 deferred 상태이며 technical 또는 final composite에 들어가지 않는다.

## 4.3 Step 8 완료 기준

Step 8은 아래 기준이 모두 문서와 체크리스트에 반영되면 완료로 본다.

- `docs/step8_testing_normalization_protocol.md`가 작성되어 있다.
- Step 7 raw indicator output을 입력 contract로 명시한다.
- Step 9 Research Tester와 Step 10 normalization implementation으로 넘길 downstream contract를 명시한다.
- no lookahead, ticker/date alignment, ticker leading-zero 보존, duplicate `ticker`/`date`, missing value, warmup, insufficient history, minimum observation policy를 테스트 기준으로 고정한다.
- time-series normalization과 cross-sectional normalization의 의미와 분리 기준을 명시한다.
- robust z-score, winsorization/clipping, tie handling, `coverage_status`, `warmup_status`, `data_quality_flag` semantics를 명시한다.
- diagnostics는 coverage, stability, correlation, turnover proxy를 review material로만 정의하고 adoption evidence나 alpha signal로 표현하지 않는다.
- implementation deviation log policy와 diagnostics output schema 초안을 포함한다.
- toy-data tests의 허용 범위와 real market data score/ranking/normalized production output 금지 범위를 명시한다.
- Step 9 Research Tester pre-implementation checklist를 포함한다.
- production score, normalized score output, ranking, composite score, backtest, valuation/fundamental scoring을 구현하지 않는다.

## 4.4 Step 18 준비 기준

Step 18은 밸류에이션 확장 준비 단계다. Step 2에서 남겨둔 point-in-time financial availability 미검증 항목은 이 단계에서 먼저 처리해야 한다.

Step 18 시작 시 필수로 진행할 항목:

- `docs/step2_financial_validation_summary.md`를 확인한다.
- financial metadata schema를 확정한다: `ticker`, `period`, `metric`, `value`, `filing_date`, `availability_date`, `disclosure_id` 또는 `source_report_id`, `source_vendor`, `collected_at`.
- `collected_at`만으로 point-in-time safety를 verified로 보지 않는다.
- disclosure, filing, availability date가 없거나 parse 불가능한 row는 valuation 후보 입력에서 제외한다.
- reporting lag policy와 stale data policy를 문서화한다.
- financial/fundamental data가 `technical_composite_score`, `final_composite_score`, technical scoring에 들어가지 않는다는 guardrail을 재확인한다.
- Step 18 전에는 valuation/fundamental score, valuation-aware composite, valuation verdict를 구현하지 않는다.

## 5. 현재 상태

- Step 1 = COMPLETE or mostly complete
- Step 2 = COMPLETE
- Step 3 = COMPLETE
- Step 4 = COMPLETE
- Step 5 = COMPLETE
- Step 6 = COMPLETE
- Step 7 = COMPLETE
- Step 8 = COMPLETE
- Step 2 financial collector validation is complete; point-in-time financial availability follow-up is explicitly assigned to Step 18.
- Step 9 = COMPLETE
  - Part A/B raw score integration exists for the eight MVP candidates.
  - `short_term_overreaction`, `atr_adjusted_oversold_distance`, and `rsi_price_divergence` now use explicit Step 9 MVP locked formula variants.
  - Step 15 ranking, Step 17 backtest, and valuation/fundamental scoring remain WAITING / deferred.
- Step 10 = COMPLETE
  - Step 10A ticker-local time-series normalization is implemented and tested.
  - Step 10B cross-sectional normalization, diagnostics, and policy documentation are implemented and tested.
  - Step 10 integration review found no ranking, composite, backtest, or valuation/fundamental boundary violation.
- Step 11 = COMPLETE
  - `docs/step11_composite_score_design.md` defines technical composite family structure and policy.
  - `src/composite/contracts.py`, `src/composite/schema.py`, and `tests/test_step11_composite_schema.py` define and test schema/guardrail skeletons only.
  - Step 11 is design-only; no `technical_composite_score`, `final_composite_score`, ranking, backtest, or valuation/fundamental scoring is implemented.
- Step 12 = COMPLETE
  - Worker A core redundancy/correlation calculation engine is implemented in `src/diagnostics/score_redundancy.py`.
  - Worker B output contract, docs, report schema, guardrail, and report writer are implemented.
  - `docs/step12_redundancy_correlation_diagnostics.md` fixes Step 12 input/output/status/threshold semantics.
  - Worker A engine output now exposes both engine-level pair summaries and contract-facing pair diagnostics / coverage summaries validated by Worker B helpers.
  - Step 12 computes same-date cross-sectional Spearman diagnostics only; ranking, composite scoring, backtest, forward/future return, and valuation/fundamental scoring remain absent.
- Step 13 = NEXT / not started
- Step 15 = WAITING / not started
- Step 17 = WAITING / not started
- Step 18 valuation/fundamental expansion = DEFERRED

## 6. Step 종료 보고 형식

모든 Step 종료 시 아래 형식으로 보고한다.

```text
[현재 위치]
Step N: ...

[Step 판정]
COMPLETE / PARTIALLY COMPLETE / NEEDS FIX

[완료 항목]
- ...

[미완료 / 약한 항목]
- ...

[리스크]
- ...

[다음 Step 진입 가능 여부]
Yes / Yes, with minor follow-up / No

[로드맵 진행 상태]
Step 1: ...
Step 2: ...
Step 3: ...
Step 4: ...
Step 5: ...
Step 6: ...
Step 7: ...
Step 8: ...
Step 9: ...
Step 10: ...
Step 11: ...
Step 12: ...
Step 13: ...
Step 14: ...
Step 15: ...
Step 16: ...
Step 17: ...
Step 18: ...
Step 19: ...
Step 20: ...
```

## 6.1 활성 Step 진행 원칙

- `COMPLETE`로 판정된 Step은 기본적으로 신뢰하고, 현재 Step 진행 중에는 재구현하거나 전체 재검토 루프로 되돌리지 않는다.
- 현재 Step의 직접 의존성이 되는 completed Step 산출물은 hard stop 위반 여부만 최소 확인한다.
- completed Step에서 발견한 사소한 개선점은 TODO 또는 risk note로 기록하고 현재 Step을 막지 않는다.
- 단, 현재 Step 인터페이스를 깨거나 hard stop 위반을 만들면 `Step N dependency fix`로 표시하고 최소 수정한다.
- 모든 Step을 다시 점검하는 전체 검증은 Step 종료 검증 또는 사용자의 명시 요청이 있을 때만 수행한다.
- Step 2의 financial sample 또는 point-in-time 검증 부족은 valuation/fundamental data가 technical scoring, `technical_composite_score`, `final_composite_score`에 섞이지 않는 한 기술 Step 진행을 막지 않는다.

## 7. Hard Stop Rules

- score definition 전에는 score implementation 금지.
- documented composite design 전에는 composite score implementation 금지.
- Step 17 전에는 backtest 금지.
- financial data를 `technical_composite_score`에 넣지 않는다.
- financial data를 `final_composite_score`에 넣지 않는다.
- price-only evidence에 valuation language를 쓰지 않는다.
- valuation status가 deferred인 동안 valuation/fundamental scoring을 하지 않는다.
- active Step이 명시적으로 허용하기 전에는 ranking generation을 하지 않는다.
