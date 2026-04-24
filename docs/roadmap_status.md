# 로드맵 상태

## 현재 활성 단계

Step 10 = normalization policy implementation, NEXT / not started
Recently completed: Step 9 = Research Tester MVP raw score implementation, COMPLETE
Carry-forward: Step 2 PIT financial availability follow-up is assigned to Step 18, not Step 9/10 technical scoring.

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
- Step 10 status: NEXT / not started

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
- Step 10 normalization implementation은 아직 시작하지 않음

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
