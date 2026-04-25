# Quant Project Reference For ChatGPT Project - Current Version

이 문서는 ChatGPT Project의 프로젝트 참조 컨텍스트에 넣기 위한 현재 버전 요약본이다.
기준 시점은 2026-04-25 Asia/Seoul이며, `docs/project_checklist.md`와
`docs/roadmap_status.md`를 최우선 현재 상태 문서로 본다.

이 파일은 이전 `quant_project_reference_for_chatgpt_project.md`보다 최신 상태를 반영한다.

## 1. Source Of Truth

참조 우선순위:

1. 사용자의 최신 명시 지시
2. 루트 `AGENTS.md`
3. `docs/project_checklist.md`
4. `docs/roadmap_status.md`
5. 세부 프로젝트의 `AGENTS.md`, docs, config

현재 루트 워크스페이스:

```text
C:\Users\jjaew\Project\master_mvp
```

주요 subproject:

- `Quant_mvp`: score design, score governance, technical review, valuation boundary
- `chart_mvp`: runnable scanner, local caches, chart/GUI/runtime provider code
- `reserch_mvp`: research ingestion upstream workflow. Directory name typo is intentionally preserved.
- `review_mvp`: specialist code/integration review, not the Quant technical selection reviewer

## 2. Project Goal

목표는 KOSPI200 구성 종목을 대상으로 하는 일봉 OHLCV 기반 기술적/통계적 멀티 스코어 랭킹 엔진이다.

기본 원칙:

- conservative quant engineering
- config-first implementation
- explainable and modular scoring
- no future data
- no lookahead
- no silent score redefinition after seeing results
- diagnostics are not alpha signals
- price-only evidence is not valuation evidence
- valuation/fundamental analysis remains separated until the explicit later roadmap step

이 저장소는 단일 매매 전략 저장소가 아니며, AI black-box alpha 저장소도 아니다.

## 3. Current Roadmap State

`docs/roadmap_status.md` 기준:

```text
Current active step: Step 11 = Composite Score structure design, COMPLETE
Next gated stage: Step 12 = redundancy / correlation diagnostics, WAITING / not started
Recently completed: Step 11 = Composite Score structure design, COMPLETE
Carry-forward: Step 2 PIT financial availability follow-up is assigned to Step 18, not Step 9/10/11 technical scoring.
```

현재 판정:

| Step | Status |
| --- | --- |
| Step 1 | COMPLETE or mostly complete |
| Step 2 | COMPLETE |
| Step 3 | COMPLETE |
| Step 4 | COMPLETE |
| Step 5 | COMPLETE |
| Step 6 | COMPLETE |
| Step 7 | COMPLETE |
| Step 8 | COMPLETE |
| Step 9 | COMPLETE |
| Step 10 | COMPLETE |
| Step 11 | COMPLETE |
| Step 12 | WAITING / not started |
| Step 13 | WAITING / not started |
| Step 15 | WAITING / not started |
| Step 17 | WAITING / not started |
| Step 18 | DEFERRED / waiting for valuation expansion |

Step 12 redundancy/correlation diagnostics가 다음 gated stage다. Step 15 ranking,
Step 17 backtest, Step 18 valuation 확장은 아직 허용되지 않는다.

## 4. Hard Stops

항상 금지:

- documented composite design 전 `technical_composite_score` 또는 `final_composite_score` 구현 금지
- Step 15 전 ranking 또는 latest ranking output 생성 금지
- Step 17 전 backtest 금지
- forward return, future return, next-period label을 Step 10 technical normalization에 섞기 금지
- financial/fundamental data를 technical scoring에 사용 금지
- financial/fundamental data를 `technical_composite_score`에 사용 금지
- financial/fundamental data를 `final_composite_score`에 사용 금지
- price-only evidence를 cheap, value, undervalued, bargain 등 valuation language로 표현 금지
- diagnostics를 alpha signal, stock-selection score, adoption decision처럼 표현 금지

현재 허용:

- Step 9에서 구현된 raw research score layer 유지 및 테스트
- Step 10 normalization layer 유지 및 테스트
- Step 11 composite input registry / schema guardrail skeleton 유지 및 테스트
- Step 12 redundancy/correlation diagnostics 준비
- normalization-related toy tests, guardrail tests, schema tests
- normalized score columns는 Step 10 범위 안에서만 유지하고 ranking/composite/backtest로 연결하면 안 됨

## 5. Step 2 Current Status

Step 2 financial collector validation은 COMPLETE다.

완료 항목:

- `schema_validator.py` 강화
- dtype expectations 추가
- date parseability check 추가
- numeric conversion safety check 추가
- duplicate key validation 추가
- ticker leading-zero preservation check 명시
- legacy outputs 문서화: `docs/legacy_output_inventory.md`
- `chart_mvp` Naver financial loader/cache 경로로 KOSPI200 200개 financial statement cache 생성
- financial statement cache validation 실행: 200 files, 26,208 rows, 200 unique codes
- `chart_mvp/src/stock_core/providers/naver_finance.py` 보완
- `chart_mvp/src/preprocess/financial_data_validator.py` 보완
- `chart_mvp/reports/data_quality/financial_data_check.md` 재생성
- `chart_mvp/tests/test_financial_data_validator.py` 추가
- summary: `docs/step2_financial_validation_summary.md`

유지되는 제한:

- generated financial caches and data-quality reports are runtime artifacts, not source-controlled project state
- Naver financial rows currently lack disclosure, filing, or availability date
- `point_in_time_status = unverified`
- financial data is inventory-only or GUI-display-only
- financial data must not enter technical scoring, final composite scoring, valuation verdicts, or ranking

Step 18 시작 시 처리할 carry-forward:

- PIT financial metadata schema 확정
- `filing_date`, `availability_date`, `disclosure_id` 또는 `source_report_id` 확보 가능성 검토
- reporting lag policy 문서화
- stale data policy 문서화
- row-level PIT 검증 없이는 valuation/fundamental scoring 금지

## 6. Completed Technical Pipeline

Step 6 preprocessing:

- code:
  - `src/preprocess/daily_ohlcv.py`
  - `src/preprocess/schema_validator.py`
- input:
  - `chart_mvp/data/*_daily_prices.csv`
- output:
  - `data/processed/daily_ohlcv.csv`
- reports:
  - `reports/preprocess/preprocess_summary.md`
  - `reports/preprocess/preprocess_validation_summary.csv`
- tests:
  - `tests/preprocess/test_step6_preprocess.py`

Step 7 raw technical indicator layer:

- code:
  - `src/indicators/technical.py`
- input:
  - `data/processed/daily_ohlcv.csv`
- output:
  - `data/processed/technical_indicators.csv`
- reports:
  - `reports/indicators/indicator_summary.md`
  - `reports/indicators/indicator_validation_summary.csv`
- metadata:
  - `history_count`
  - `minimum_history_required`
  - `warmup_state`
- tests:
  - `tests/indicators/test_step7_indicators.py`

Step 8 testing and normalization protocol:

- document:
  - `docs/step8_testing_normalization_protocol.md`
- defines:
  - no-lookahead and ticker/date alignment rules
  - time-series normalization semantics
  - cross-sectional normalization semantics
  - robust z-score / MAD fallback
  - winsorization and clipping policy
  - tie handling
  - `coverage_status`, `warmup_status`, `data_quality_flag`
  - diagnostics output schema draft
  - implementation deviation log policy
  - Step 9/10 handoff
- tests:
  - `tests/data_validation/test_step8_protocol_guardrails.py`

## 7. Step 9 Raw Score Implementation

Step 9 is COMPLETE. It implements Research Tester raw score output for eight MVP candidates.

Primary entrypoint:

```text
src/scores/technical_scores.py -> calculate_all_raw_scores(df: pd.DataFrame) -> pd.DataFrame
```

Supporting modules:

- `src/scores/schema.py`
- `src/scores/score_contracts.py`
- `src/scores/mean_reversion_scores.py`
- `src/scores/trend_vol_flow_scores.py`
- `src/scores/technical_scores.py`

Step 9 docs:

- `docs/step9_research_tester_scores_part_a.md`
- `docs/step9_research_tester_scores_part_b.md`
- `docs/step9_research_tester_scores.md`

Step 9 tests:

- `tests/test_step9_scores_part_a.py`
- `tests/test_step9_scores_part_b.py`
- `tests/test_step9_scores_integration.py`

Raw score columns:

| score_name | raw column | status |
| --- | --- | --- |
| `short_term_overreaction` | `short_term_overreaction_raw` | implemented_for_research |
| `atr_adjusted_oversold_distance` | `atr_adjusted_oversold_distance_raw` | implemented_for_research |
| `rsi_price_divergence` | `rsi_price_divergence_raw` | implemented_for_research |
| `realized_vol_percentile` | `realized_vol_percentile_raw` | implemented_for_research, diagnostic context only |
| `donchian_breakout_distance` | `donchian_breakout_distance_raw` | implemented_for_research |
| `bollinger_width_squeeze` | `bollinger_width_squeeze_raw` | implemented_for_research, setup/regime context only |
| `cmf_confirmation` | `cmf_confirmation_raw` | implemented_for_research, confirmation candidate only |
| `efficiency_ratio_trend` | `efficiency_ratio_trend_raw` | implemented_for_research |

Step 9 formula locks:

- `short_term_overreaction_raw`: `-return_N`, where `N = Quant_mvp/config/windows.toml [returns].short`
- `atr_adjusted_oversold_distance_raw`: `(bollinger_mid_N - close) / ATR_M`
- `rsi_price_divergence_raw`: `max(0, -return_N) * max(0, RSI_t - RSI_{t-N})`
- `realized_vol_percentile_raw`: ticker-local current/prior `realized_vol_20` trailing percentile; diagnostic only
- `donchian_breakout_distance_raw`: `(close_t / donchian_high_prior_N_t) - 1`
- `bollinger_width_squeeze_raw`: `-bollinger_width_N_t`
- `cmf_confirmation_raw`: `cmf_N_t`
- `efficiency_ratio_trend_raw`: `sign(return_Nd_t) * efficiency_ratio_N_t`

Step 9 output includes identity, raw scores, missing reasons, and metadata. It does not include:

- rank, ranking, latest rank
- normalized score, `*_normalized`
- `technical_composite_score`
- `final_composite_score`
- forward return, future return, backtest return
- alpha, signal, buy, sell
- valuation score

## 8. Current Config Meaning

Root `config/scores.toml` remains production runtime guardrail:

- production scoring disabled
- ranking disabled
- composite scoring disabled
- valuation/fundamental scoring disabled

`Quant_mvp/config/scores.toml` is the candidate registry and Step 9 raw testing contract:

- `enabled = true` means candidate visibility and Step 9 raw testing eligibility
- `runtime_enabled = false` means no production scanner/ranking/composite runtime connection
- `research_tester_implementation_enabled = true`
- `raw_score_research_testing_enabled = true`
- `ranking_generation_enabled = false`
- `composite_scoring_enabled = false`
- `backtest_enabled = false`
- `valuation_branch_enabled = false`

Important window/config references:

- root `config/data.toml`: data paths and financial boundary
- root `config/windows.toml`: Step 7 active indicator windows, score windows inactive for production
- `Quant_mvp/config/windows.toml`: score candidate formula windows
- `Quant_mvp/config/thresholds.toml`: normalization and diagnostics thresholds

Key threshold references:

- `[quality].min_non_nan_observations = 60`
- `[quality].min_cross_section_count = 20`
- `[outliers].winsorize_lower_pct = 0.01`
- `[outliers].winsorize_upper_pct = 0.99`
- `[redundancy].spearman_warn = 0.80`
- `[redundancy].spearman_block = 0.90`

## 9. Canonical Data Contract

Canonical OHLCV required columns:

- `ticker`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`

Ticker policy:

- preserve as string
- six-character code
- leading zero preservation required
- integer ticker loading is invalid

Date policy:

- parseable date required
- future date must be rejected or reported

Duplicate key:

```text
ticker + date
```

Step 7/9 technical input must preserve:

- `history_count`
- `minimum_history_required`
- `warmup_state`

## 10. Valuation Boundary

Current valuation state:

```text
valuation_status = deferred
financial_data_usage_now = inventory_only_or_gui_display_only
point_in_time_status = unverified
financial_data_in_technical_score = false
financial_data_in_final_composite_score = false
```

Valuation scoring requires PIT-safe fundamental data with:

- fundamental field definition
- filing date, disclosure date, effective date, or availability date
- reporting lag policy
- stale data policy
- market capitalization or share-count logic where required
- sector/industry metadata if sector-relative valuation is proposed

PER/PBR/ROE display values must not affect technical score, technical composite, final composite, ranking, or adoption decision.

Valuation-aware requests route to:

```text
Quant_mvp/agents/valuation/AGENTS.md
```

## 11. Step 10/11 Current Scope

Completed Step 10:

```text
Step 10 = normalization policy implementation, COMPLETE
```

Step 10 implemented the Step 8 normalization protocol for Step 9 raw scores.

- time-series normalization implementation
- cross-sectional normalization implementation
- robust z-score / winsorization / clipping implementation
- deterministic tie handling
- `coverage_status`, `warmup_status`, `data_quality_flag` propagation
- normalized score schema tests
- no-lookahead toy tests
- diagnostics helper outputs if clearly labeled as review material
- implementation deviation log if code differs from protocol/config/docs

Completed Step 11:

```text
Step 11 = Composite Score structure design, COMPLETE
```

Step 11 defined composite family structure and schema guardrail skeletons only.

- `docs/step11_composite_score_design.md`
- `src/composite/contracts.py`
- `src/composite/schema.py`
- `tests/test_step11_composite_schema.py`

Step 11 classifies Step 9 raw score and Step 10 normalized score candidates as
composite inputs only. It does not calculate `technical_composite_score`,
`final_composite_score`, rankings, backtests, or valuation-aware outputs.

Step 10/11 must not:

- create ranking or latest ranking output
- create composite scores
- create family weighted composites
- run backtests
- compute forward/future returns
- connect to production scanner ranking
- use valuation/fundamental data
- call diagnostics alpha evidence or adoption decision

Next gated stage:

```text
Step 12 = redundancy / correlation diagnostics, WAITING / not started
```

Step 12 should remain diagnostic and review-support oriented until the relevant
roadmap gate explicitly permits downstream ranking or composite calculation.

## 12. Test Snapshot

Current validation snapshot from `docs/roadmap_status.md`:

- Step 11 composite schema: `9 passed`
- Step 10 normalization focused tests: `26 passed`
- Step 9/8/7/6 focused integration set: `57 passed`
- root `pytest`: `225 passed, 4 skipped`

Do not claim tests were rerun unless they were actually rerun in the current turn.

## 13. Generated Output Policy

Source-controlled by default:

- code
- tests
- docs
- config
- small reference fixtures
- project-level agent instructions

Not source-controlled by default:

- generated chart images
- daily price caches
- financial statement runtime caches
- scan outputs
- local reports generated from current runs
- `__pycache__`
- `*.pyc`
- virtual environments
- `.env` and secrets

Generated runtime output may be used only after current validation context confirms it.

## 14. ChatGPT Behavior For This Project

When helping inside this project:

- Reply in Korean for progress/status/summary unless the user asks otherwise.
- Keep code identifiers, config keys, file paths, column names, and function names in English.
- Treat unknowns as unknown.
- Label inference as inference.
- Do not exaggerate alpha, robustness, or valuation support.
- Do not convert price-only technical evidence into valuation language.
- Do not silently redefine formulas after seeing outputs.
- Completed Steps are trusted by default. Do only minimal hard-stop checks for direct dependencies.
- If current work touches multiple subprojects, prepare handoff/master-up evidence and consider whether `review_mvp` is required.

Step-end report verdict must be one of:

```text
COMPLETE
PARTIALLY COMPLETE
NEEDS FIX
```

## 15. Minimal Current Decision Rule

The safest default interpretation of the current project state:

```text
Step 12 redundancy/correlation diagnostics is the next gated stage.
Step 11 composite structure design is complete but calculation is not implemented.
Step 10 normalization implementation is complete.
Step 9 raw score implementation is complete.
Ranking is not allowed before Step 15.
Composite scoring remains blocked until the roadmap permits calculation after review gates.
Backtest is not allowed before Step 17.
Valuation/fundamental scoring is not allowed before Step 18 readiness and PIT validation.
Financial/fundamental data must stay out of technical scoring and final composite scoring.
```
