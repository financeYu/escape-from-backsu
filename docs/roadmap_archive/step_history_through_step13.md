# 로드맵 상태

> Archive-only notice:
> This document is historical material from pre-freeze planning.
> It is not an active roadmap, checklist, or implementation instruction.
> Use `docs/context/ARCHIVE_INDEX.md` to determine whether this file should be consulted.

## Historical Active Stage At Archive Time

Step 14 = Adoption Synthesis, NEXT / not started
Recently completed: Step 13 = Technical Selection Reviewer, COMPLETE
Recently completed before that: Step 12 = redundancy / correlation diagnostics, COMPLETE
Carry-forward: Step 2 PIT financial availability follow-up is assigned to Step 18, not Step 9/10/11 technical scoring.

## 현재 판정

- Step 1 verdict: COMPLETE or mostly complete
- Step 2 verdict: COMPLETE
- Step 3 verdict: COMPLETE
- Step 4 verdict: COMPLETE
- Step 5 verdict: COMPLETE
- Step 6 verdict: COMPLETE
- Step 7 verdict: COMPLETE
- Step 8 verdict: COMPLETE
- Step 9 status: COMPLETE
- Step 10 status: COMPLETE
- Step 11 status: COMPLETE
- Step 12 status: COMPLETE
- Step 13 status: COMPLETE
- Step 14 status: NEXT / not started
- Step 15 status: WAITING / not started
- Step 17 status: WAITING / not started
- Step 18 status: DEFERRED / waiting for valuation expansion

## Step 13 통합 완료 상태

완료:

- `docs/step13_technical_selection_reviewer.md` 작성 및 최종 output contract, `review_status` vocabulary, Step 14 경계, forbidden output/language, generated report boundary, 테스트 명령 문서화
- `src/selection/technical_selection_contracts.py`에 Step 13 review table schema, status vocabulary, forbidden column/language guardrail, all-eight-score bundle validation 추가
- `src/selection/technical_selection_reviewer.py`에 Step 11 metadata와 Step 12 coverage/redundancy diagnostics를 결합하는 보수적 technical review recommendation engine 추가
- `src/selection/technical_selection_reports.py`에 generated report renderer/writer 및 `reports/selection/` path guardrail 추가
- `reports/selection/README.md`에 generated runtime report boundary 명시
- `tests/selection/test_step13_technical_selection_contracts.py` 추가
- `tests/selection/test_step13_technical_selection_reviewer.py` 추가
- `tests/selection/test_step13_technical_selection_reports.py` 추가
- `eligibility == diagnostic_only` 또는 `role == diagnostic_context`는 `diagnostic_only` recommendation으로 제한
- insufficient input/data는 `blocked_by_data` 또는 `needs_manual_review` 성격으로 보수 처리
- Step 12 `block_candidate` / `severe_redundancy`는 자동 `adopt_candidate`가 되지 않도록 차단
- `confirmation` / `setup_context` role은 unconditional adoption이 아닌 conditional/context recommendation으로 제한
- `config_missing` / `undefined_correlation`은 optimistic하게 해석하지 않고 manual review 또는 data block 계열로 처리

유지되는 제한:

- Step 14 final adoption synthesis 없음
- ranking generation 없음
- latest ranking 없음
- `technical_composite_score` / `final_composite_score` 생성 없음
- family weighted composite 계산 없음
- backtest 없음
- forward/future return 계산 없음
- valuation/fundamental scoring 없음
- financial/fundamental data를 technical review decision에 사용하지 않음
- generated report는 `reports/selection/` runtime artifact boundary에 제한됨

검증:

- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests/selection`: 29 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests/test_step11_composite_schema.py tests/diagnostics tests/selection`: 61 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest`: 277 passed, 4 skipped

## Step 11 통합 상태

완료:

- `docs/step11_composite_score_design.md` 작성
- `src/composite/contracts.py`에 Step 11 composite input registry skeleton 추가
- `src/composite/schema.py`에 Step 11 schema/guardrail validation helper 추가
- `tests/test_step11_composite_schema.py` 추가
- Step 9 raw score와 Step 10 normalized score를 composite input 후보로만 분류
- eight MVP score를 `mean_reversion`, `trend_breakout`, `volatility_context`, `volume_flow` composite family로 매핑
- `candidate_signal`, `confirmation`, `setup_context`, `diagnostic_context` role semantics 명시
- `eligible`, `conditional`, `diagnostic_only`, `blocked` composite eligibility semantics 명시
- composite calculation readiness가 현재 `design_only`이며 Step 12/13 review 이전 계산 불가임을 명시
- `realized_vol_percentile`은 diagnostic/context-only, `bollinger_width_squeeze`는 setup/regime context, `cmf_confirmation`은 confirmation candidate로 제한
- mean reversion, trend/breakout, volatility context cluster 중복 위험 문서화
- normalized score 방향성, missing/warmup/coverage, Step 12/13/15/17/18 경계 문서화
- config-first `weights.toml` 설계안은 문서 예시로만 제시하고 production enable flag는 변경하지 않음

유지되는 제한:

- composite score implementation 없음
- `technical_composite_score` / `final_composite_score` 생성 없음
- ranking generation 없음
- latest ranking 없음
- backtest 없음
- forward/future return 계산 없음
- valuation/fundamental scoring 없음
- production runtime 연결 없음

검증:

- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests/test_step11_composite_schema.py`: 9 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests/test_step10_normalization_timeseries.py tests/test_step10_normalization_cross_sectional.py tests/test_step10_normalization_diagnostics.py`: 26 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest`: 225 passed, 4 skipped
- Step 11 통합 점검에서 A 설계 문서와 B schema registry의 family/role/eligibility 용어를 설계 문서 기준으로 정렬

## Step 12 통합 완료 상태

완료:

- `docs/step12_redundancy_correlation_diagnostics.md` 작성
- Step 12 목적을 normalized score/component score 간 redundancy/correlation 진단 및 Step 13 review material 생성으로 고정
- Step 12 input contract에 `ticker`, `date`, Step 10 normalized score columns, Step 11 score family/component metadata를 명시
- score pair diagnostics, coverage summary, threshold flags, insufficient data reasons, implementation deviation log output contract 명시
- `src/diagnostics/score_redundancy.py`에 same-date cross-sectional Spearman redundancy/correlation 계산 엔진 추가
- Worker A engine output을 Worker B contract-facing `pair_diagnostics` / `coverage_summary` schema로 변환하고 validator로 검증
- normalized score column이 없을 때 raw score로 조용히 대체하지 않고 `insufficient_input` / upstream missing reason을 명시
- pairwise NaN exclusion, insufficient cross-section, constant column, undefined correlation, config missing 처리를 구현
- `src/diagnostics/diagnostic_contracts.py`에 Step 12 schema/status/threshold/forbidden-column guardrail helper 추가
- `src/diagnostics/diagnostic_reports.py`에 generated markdown report writer와 report-language guardrail 추가
- `reports/diagnostics/README.md`에 generated runtime output boundary 명시
- `tests/diagnostics/test_step12_score_redundancy.py` 추가
- `tests/diagnostics/test_step12_diagnostic_contracts.py` 추가
- `tests/diagnostics/test_step12_report_guardrails.py` 추가

유지되는 제한:

- ranking generation 없음
- latest ranking 없음
- `technical_composite_score` / `final_composite_score` 생성 없음
- backtest 없음
- forward/future return 계산 없음
- valuation/fundamental scoring 없음
- diagnostics를 alpha signal, adoption decision, ranking, backtest, valuation verdict로 표현하지 않음

검증:

- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests/diagnostics/test_step12_score_redundancy.py`: 9 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests/diagnostics/test_step12_diagnostic_contracts.py`: 5 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests/diagnostics/test_step12_report_guardrails.py`: 5 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests/diagnostics`: 19 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests/test_step10_normalization_cross_sectional.py tests/test_step10_normalization_diagnostics.py tests/test_step10_normalization_timeseries.py tests/test_step11_composite_schema.py`: 37 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest`: 246 passed, 4 skipped

## Step 10 통합 상태

완료:

- `src/scores/normalization_timeseries.py`에 ticker-local time-series robust z-score normalization primitive 추가
- `src/scores/normalization_cross_sectional.py`에 same-date cross-sectional robust z-score primitive 추가
- `src/scores/normalization_diagnostics.py`에 Step 10B diagnostic summary helpers 추가
- `src/scores/__init__.py`에 Step 10 public API export 정리
- `src/scores/schema.py`에 forbidden output guardrail 키워드 보강
- `tests/test_step10_normalization_timeseries.py` 추가
- `tests/test_step10_normalization_cross_sectional.py` 추가
- `tests/test_step10_normalization_diagnostics.py` 추가
- `docs/step10_normalization_policy.md` 작성 및 Part A/B 통합 schema 반영

유지되는 제한:

- ranking generation 없음
- composite scoring 없음
- backtest 없음
- forward/future return 계산 없음
- valuation/fundamental scoring 없음
- production scanner/ranking 연결 없음

검증:

- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests/test_step10_normalization_timeseries.py tests/test_step10_normalization_cross_sectional.py tests/test_step10_normalization_diagnostics.py`: 26 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests/test_step9_scores_part_a.py tests/test_step9_scores_part_b.py tests/test_step9_scores_integration.py tests/data_validation/test_step8_protocol_guardrails.py tests/indicators/test_step7_indicators.py tests/preprocess/test_step6_preprocess.py`: 57 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest`: 216 passed, 4 skipped

## Step 9 Part A/B 통합 상태

완료:

- `src/scores/schema.py`에 Step 9 raw score output guardrail helper 추가
- `src/scores/score_contracts.py`에 Part A score contract 및 formula-locked implementation status 명시
- `src/scores/mean_reversion_scores.py`에 Part A raw score output 구현
- `src/scores/trend_vol_flow_scores.py`에 Part B raw score output 구현
- `src/scores/technical_scores.py`에 Part A/B thin integration entrypoint 추가
- `tests/test_step9_scores_part_a.py` 추가
- `tests/test_step9_scores_part_b.py` 추가
- `tests/test_step9_scores_integration.py` 추가
- `docs/step9_research_tester_scores_part_a.md` 작성
- `docs/step9_research_tester_scores_part_b.md` 작성
- `docs/step9_research_tester_scores.md` 작성

구현 상태:

- `realized_vol_percentile_raw`: implemented_for_research, diagnostic context only
- `donchian_breakout_distance_raw`: implemented_for_research
- `bollinger_width_squeeze_raw`: implemented_for_research, setup/regime context only
- `cmf_confirmation_raw`: implemented_for_research, confirmation candidate only
- `efficiency_ratio_trend_raw`: implemented_for_research
- `short_term_overreaction_raw`: implemented_for_research, MVP locked `-return_N` variant
- `atr_adjusted_oversold_distance_raw`: implemented_for_research, MVP locked Bollinger-mid/ATR variant
- `rsi_price_divergence_raw`: implemented_for_research, MVP locked deterministic RSI/price disagreement proxy

유지되는 제한:

- normalized score output 없음
- ranking generation 없음
- composite scoring 없음
- backtest 없음
- forward/future return 계산 없음
- valuation/fundamental scoring 없음
- production scanner/ranking 연결 없음

검증:

- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests\test_step9_scores_part_a.py`: 12 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests\test_step9_scores_part_b.py`: 11 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests\test_step9_scores_integration.py`: 6 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests\indicators\test_step7_indicators.py`: 10 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest`: 180 passed, 4 skipped

## Step 8 완료 상태

완료:

- `docs/step8_testing_normalization_protocol.md` 작성
- Step 7 raw technical indicator output을 Step 8 upstream input contract로 고정
- Step 9 Research Tester와 Step 10 normalization implementation으로 넘길 downstream handoff 기준 명시
- no-lookahead, ticker/date alignment, ticker leading-zero 보존, duplicate `ticker`/`date`, missing value, warmup, insufficient history, minimum observation 기준 문서화
- time-series normalization과 cross-sectional normalization의 분리 기준 문서화
- robust z-score, MAD zero fallback, winsorization/clipping, deterministic tie handling 기준 문서화
- `coverage_status`, `warmup_status`, `data_quality_flag` semantics 문서화
- diagnostics output schema 초안과 coverage/stability/correlation/turnover proxy 진단 계획 문서화
- implementation deviation log policy 문서화
- toy-data tests 허용 범위와 real market data normalized score/ranking output 금지 범위 문서화
- Step 9 Research Tester pre-implementation checklist 문서화

유지되는 제한:

- score implementation 없음
- normalized score output 없음
- ranking generation 없음
- composite scoring 없음
- backtest 없음
- valuation/fundamental scoring 없음
- Step 8 자체 산출물에는 score implementation 없음
- Step 9 raw score implementation 상태는 위 Step 9 section에 별도 기록
- Step 10 normalization implementation은 위 Step 10 통합 상태에 COMPLETE로 기록

검증:

- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest tests\data_validation\test_step8_protocol_guardrails.py`: 3 passed
- 2026-04-25 기준 `$env:PYTHONPATH="src"; python -m pytest`: 127 passed, 4 skipped

## Step 7 완료 상태

완료:

- `src/indicators/technical.py`에 config-first raw technical indicator 계산 레이어 추가
- `config/data.toml`의 `[indicators]` 경로를 사용해 Step 6 `data/processed/daily_ohlcv.csv`를 입력으로 사용
- `config/windows.toml`에 Step 7 raw indicator dependency window 활성화
- `data/processed/technical_indicators.csv` 생성 가능
- `reports/indicators/indicator_summary.md` 및 `reports/indicators/indicator_validation_summary.csv` 생성 가능
- indicator output metadata로 `history_count`, `minimum_history_required`, `warmup_state` 추가
- ticker별 group boundary를 유지해 return/rolling 계산이 종목 간 섞이지 않도록 테스트
- Donchian high/low는 prior-bar convention으로 same-date lookahead 방지
- rolling warmup 구간의 NaN을 보수적으로 유지하고 `warmup` / `insufficient_history` 상태 표시
- zero denominator 계산에서 infinite value가 나오지 않도록 NaN-aware safe division 테스트
- Step 7 입력의 as-of date 이후 future date를 reject
- score/rank/composite/alpha/signal 컬럼을 생성하지 않는 guardrail 테스트 추가
- focused unit tests 추가: `tests/indicators/test_step7_indicators.py`

유지되는 제한:

- score implementation 없음
- normalized score output 없음
- ranking generation 없음
- composite scoring 없음
- backtest 없음
- valuation/fundamental scoring 없음
- Step 8 normalization/testing protocol은 `docs/step8_testing_normalization_protocol.md`에 문서화 완료
- Step 9 raw score implementation 상태는 위 Step 9 section에 별도 기록

검증:

- 2026-04-25 기준 `python -m src.indicators.technical --project-root .`: rows=39390, indicator_columns=37, metadata_columns=3
- 2026-04-25 기준 root `python -m pytest`: 120 passed, 4 skipped

## Step 6 완료 상태

완료:

- `src/preprocess/daily_ohlcv.py`에 config-first 일봉 OHLCV 전처리 파이프라인 추가
- `config/data.toml`에 Step 6 입력/출력/리포트 경로 추가
- `src/preprocess/schema_validator.py`에 future date 및 non-negative volume 검증 추가
- ticker를 문자열로 보존하고 leading-zero 손실 후보를 명시적으로 reject/report
- date parseability, future date, 안전한 numeric conversion, duplicate ticker/date, missing required value, negative volume 검증
- 처리 결과는 canonical OHLCV 컬럼만 포함
- `reports/preprocess/preprocess_summary.md` 및 `reports/preprocess/preprocess_validation_summary.csv` 생성 경로 구성
- focused unit tests 추가: `tests/preprocess/test_step6_preprocess.py`

유지되는 제한:

- technical indicator 계산 없음
- score, ranking, composite, latest ranking 생성 없음
- backtest 없음
- financial/fundamental data 병합 없음
- financial_data_status는 `valuation_deferred` 유지

검증 / 후속:

- root `python -m pytest` 실행을 위한 `pytest.ini` 추가
- Step 6 preprocess policy가 허용되지 않은 값을 조용히 수용하지 않도록 fail-fast 검증 추가
- Step 7 raw indicator dependency layer 완료

## Step 5 완료 상태

완료:

- `Quant_mvp/docs/score_catalog.md` 작성
- `Quant_mvp/docs/score_definitions.md` 작성
- `Quant_mvp/docs/family_map.md` 작성
- `Quant_mvp/config/scores.toml`에 Step 5 정의 문서 경로 추가
- `realized_vol_percentile`을 direct technical alpha가 아닌 `diagnostic` branch 후보로 정정

유지되는 제한:

- score implementation 없음
- Research Tester implementation 없음
- ranking generation 없음
- composite scoring 없음
- backtest 없음
- valuation/fundamental scoring 없음

## Step 2 완료 상태

완료:

- `schema_validator.py` 강화
- dtype expectations 추가
- date parseability check 추가
- numeric conversion safety check 추가
- duplicate key validation 추가
- ticker leading-zero preservation check 명시
- legacy outputs 문서화 완료: `docs/legacy_output_inventory.md`
- `chart_mvp` Naver financial loader/cache 경로로 KOSPI200 200개 `data/<code>_financial_statements.csv` 로컬 캐시 생성
- financial statement cache validation 실행: 200 files, 26,208 rows, 200 unique codes
- `chart_mvp/src/stock_core/providers/naver_finance.py`가 중복 컬럼과 non-fiscal comparison table을 보수적으로 처리하도록 보완
- `chart_mvp/src/preprocess/financial_data_validator.py`가 `collected_at`만으로 point-in-time safety를 verified로 보지 않도록 보완
- `chart_mvp/reports/data_quality/financial_data_check.md` 현재 validation context로 재생성
- `chart_mvp/tests/test_financial_data_validator.py` 추가
- financial data는 `valuation_deferred` 상태 유지

유지되는 제한:

- 생성된 `chart_mvp/data/*_financial_statements.csv`와 `chart_mvp/reports/data_quality/*`는 runtime artifacts이며 source-controlled project state가 아님
- 현재 Naver financial statement rows에는 disclosure, filing, availability date가 없어 `point_in_time_status = unverified`
- financial data는 inventory-only 또는 GUI display-only이며 valuation/fundamental scoring에 사용하지 않음
- financial data는 `technical_composite_score`, `final_composite_score`, technical scoring에 들어가지 않음

검증:

- 2026-04-25 기준 `python -m unittest tests.test_naver_finance tests.test_financial_data_validator -v`: 9 passed
- 2026-04-25 기준 `python -m unittest discover -s tests -v`: 34 passed
- 2026-04-25 기준 root `python -m pytest`: 169 passed, 4 skipped

다음 Step 진행 메모:

- Step 9/10 technical workflow에서는 financial/fundamental data를 계속 입력에서 차단한다.
- Step 18 시작 시 `docs/step2_financial_validation_summary.md`를 확인하고 point-in-time financial metadata schema를 먼저 확정한다.
- Step 18 필수 항목: `filing_date`, `availability_date`, `disclosure_id` 또는 `source_report_id`, reporting lag policy, stale data policy.
- Step 18 전까지 valuation/fundamental score, valuation-aware composite, valuation verdict는 구현하지 않는다.

## 밸류에이션 상태

- `valuation_status = deferred`
- `financial_data_usage_now = inventory_only_or_gui_display_only`
- `point_in_time_status = unverified`, 단 disclosure 또는 availability date가 있으면 별도 검증 가능
- `financial_data_in_technical_score = false`
- `financial_data_in_final_composite_score = false`

## Step 4 경계 상태

- 기술 분석과 밸류에이션 경계는 `docs/technical_valuation_boundary.md`에 고정했다.
- score branch 분류는 `docs/score_branch_policy.md`에 고정했다.
- Step 5 진입 전 routing 기준은 `docs/selection_criteria.md`에 정리했다.
- price-only evidence를 valuation evidence로 표현하지 않는다.
- financial data는 technical scoring과 final composite scoring에서 제외한다.
- point-in-time-safe financial data가 확보되기 전까지 valuation review는 deferred 상태다.
- root `config/scores.toml`은 runtime score/composite를 비활성화한다.
- `Quant_mvp/config/scores.toml`의 `enabled = true`는 candidate registry visibility이며 `runtime_enabled = false`로 production scoring을 막는다.

## 활성 Guardrails

- future data 금지
- lookahead 금지
- silent score redefinition 금지
- config-first implementation
- documented score definition 전 score implementation 금지
- Step 17 전 backtest 금지
- price-only evidence에 valuation language 사용 금지
