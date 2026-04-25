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
- 병렬 Step 구현, review, research ingestion, audit/scope watchdog, master integration 작업은 `docs/workspace_parallel_work_policy.md`의 worktree/branch 분리 정책을 따른다.

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

Parallel workspace rule:

- master workspace는 integration / verification / status-control 전용으로 유지한다.
- 모든 non-master worktree는 루트의 `WORKSPACE_MANIFEST.md`로 작업 범위, 허용 write path, 금지 actions, handoff output을 선언한 뒤 작업한다.
- implementation, review, research ingestion, audit/scope watchdog 작업은 서로 다른 branch와 worktree에서 수행한다.
- Step 15부터는 Step implementation, Quant score/governance, research ingestion, chart runtime, review, audit/scope watchdog, master integration 역할을 `docs/workspace_parallel_work_policy.md`의 Step 15+ Branch Separation Process에 따라 각각 별도 branch/worktree로 분리한다.

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

## 4.5 Step 15 이후 Branch / Worktree 분리 기준

Step 15 이후에는 최신 랭킹, 차트 런타임, 리뷰 수정, 리서치 handoff, audit, master integration이 한 워크트리에서 섞이지 않도록 아래 기준을 적용한다.

- Step implementation은 major Step branch인 `codex/stepXX-<scope>` branch와 전용 worktree에서만 진행한다.
- Quant score/governance/config-policy 지원 작업은 minor/support branch인 `quant/stepXX-<scope>` branch와 전용 worktree에서만 진행한다.
- Research ingestion 또는 EvidenceCard/handoff 작업은 minor/support branch인 `research/stepXX-<scope>` branch와 전용 worktree에서만 진행한다.
- Chart runtime, scanner, ranking, chart, CLI, GUI 변경은 minor/support branch인 `chart/stepXX-<scope>` branch와 전용 worktree에서만 진행한다.
- Review는 minor/support branch인 `review/stepXX-<scope>` branch와 전용 worktree에서 수행하고, 명시적으로 배정된 최소 수리 외에는 구현 branch를 수정하지 않는다.
- Audit/scope watchdog은 minor/support branch인 `audit/stepXX-<scope>` branch와 전용 worktree에서 수행한다.
- Master workspace는 merge, validation, Cross-Step Conflict Checkpoint, status-control, context refresh에만 사용한다.
- 모든 하위 에이전트와 non-master worktree는 편집 전 role branch를 먼저 만들거나 선택하고, 루트 `WORKSPACE_MANIFEST.md`를 작성한 뒤 작업한다.
- Minor/support branch는 final Step status, roadmap verdict, master integration policy를 수정하지 않는다. 필요한 변경은 handoff/TODO/risk note로 master에 올린다.

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
- Step 13 = COMPLETE
  - Worker A review contract, status vocabulary, validation guardrail, and documentation are implemented.
  - Worker B review engine, report builder, generated report path guardrail, and report language guardrail are implemented.
  - Step 13 output is a technical review recommendation table for Step 14 material only.
  - `review_status` values remain technical recommendations, not final adoption states.
  - Generated Step 13 reports are constrained to `reports/selection/` and must include `technical selection review material only`.
  - Step 15 ranking, Step 17 backtest, and Step 18 valuation/fundamental scoring remain not implemented.
- Step 14 = COMPLETE
  - Adoption synthesis docs, contracts, engine, report guardrails, and tests are complete.
  - Step 14 output remains adoption synthesis material only and preserves Step 13 `review_status` separately as `source_review_status`.
  - Step 14 does not generate ranking output, latest ranking output, `technical_composite_score`, `final_composite_score`, backtest, trading signals, or valuation/fundamental scoring.
  - Latest recorded local validation: `python -m pytest` = 387 passed, 4 skipped.
  - Focused Step 14 / research-ingestion validation: 180 passed, 4 skipped.
  - `review_mvp` specialist review found no high or medium findings on changed production code; low style findings are non-blocking.
  - Cross-Step Conflict Checkpoint passed with no blocking issue.
- Step 15 = WAITING / branch setup required
- Step 17 = WAITING / not started
- Step 18 valuation/fundamental expansion = DEFERRED
- Research ingestion scope expansion note:
  - `docs/research_ingestion_expansion.md` documents expanded paper query-set coverage, source expansion candidates, seed lifecycle, new-only run artifacts, and the separated `reserch_mvp` ownership boundary.
  - EvidenceCard is not a score definition.
  - EvidenceCard is not an adoption decision.
  - Paper-reported backtest is diagnostic metadata only.
  - Citation count is metadata only, not evidence strength.
  - Scholar seeds are discovery inputs only.
  - PDF fulltext download is disabled by default.
  - Financial/fundamental data must not enter technical_composite_score or final_composite_score.

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

[Step 종료 게이트]
- 통합 검증:
- 코드리뷰:
- 코드리뷰 필수 수정:
- 재검증:
- git commit:

[컨텍스트 스냅샷]
- local context:
- latest-only prune:
- refresh status:

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
