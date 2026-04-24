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

## 5. 현재 상태

- Step 1 = COMPLETE or mostly complete
- Step 2 = PARTIALLY COMPLETE
- Step 3 = COMPLETE
- Step 4 = COMPLETE
- Step 5 = COMPLETE
- Step 6 = COMPLETE
- Step 7 = NEXT

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

## 7. Hard Stop Rules

- score definition 전에는 score implementation 금지.
- documented composite design 전에는 composite score implementation 금지.
- Step 17 전에는 backtest 금지.
- financial data를 `technical_composite_score`에 넣지 않는다.
- financial data를 `final_composite_score`에 넣지 않는다.
- price-only evidence에 valuation language를 쓰지 않는다.
- valuation status가 deferred인 동안 valuation/fundamental scoring을 하지 않는다.
- active Step이 명시적으로 허용하기 전에는 ranking generation을 하지 않는다.
