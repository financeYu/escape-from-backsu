# Quant Project Step 12 Reference For ChatGPT Upload

이 문서는 ChatGPT Project 또는 별도 GPT 세션에 업로드하기 위한 Step 12 현재 컨텍스트 파일이다.
기준 시점은 2026-04-25 Asia/Seoul이다.

최신 상태 판단은 항상 아래 순서를 따른다.

1. 사용자의 최신 명시 지시
2. 루트 `AGENTS.md`
3. `docs/project_checklist.md`
4. `docs/roadmap_status.md`
5. 관련 source, tests, docs, config

현재 루트 워크스페이스:

```text
C:\Users\jjaew\Project\master_mvp
```

## 1. Current Position

현재 활성 단계:

```text
Step 12 = redundancy / correlation diagnostics
roadmap verdict = COMPLETE
```

`docs/roadmap_status.md` 기준 Step 12는 통합 완료 상태다.
Worker A calculation engine과 Worker B output contract/report guardrail이 통합되었다.
다음 단계는 Step 13 Technical Selection Reviewer다.

## 2. Work Classification And Routing

Step 12 관련 작업 유형:

```text
score_design / final_validation
```

주 책임 영역:

- root workspace: roadmap status, generated-output boundary, integration decision
- `src/diagnostics`: Step 12 calculation, contracts, report guardrails
- `Quant_mvp/config/thresholds.toml`: config-first threshold source
- `src/composite/contracts.py`: Step 11 composite input metadata registry

`review_mvp`는 모든 변경의 필수 bottleneck은 아니다.
다만 Step 12 completion gate 또는 cross-project integration risk가 남으면 specialist review가 필요할 수 있다.

## 3. Roadmap State Summary

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
| Step 12 | COMPLETE |
| Step 13 | NEXT / not started |
| Step 15 | WAITING / not started |
| Step 17 | WAITING / not started |
| Step 18 | DEFERRED / waiting for valuation expansion |

Step 13 Technical Selection Reviewer는 Step 12 diagnostic output을 받은 뒤 진행한다.
Step 15 ranking, Step 17 backtest, Step 18 valuation expansion은 아직 허용되지 않는다.

## 4. Absolute Hard Stops

항상 금지:

- ranking 또는 latest ranking 생성
- `technical_composite_score` 생성
- `final_composite_score` 생성
- family weighted composite 계산
- buy/sell/trading signal 생성
- alpha evidence 표현
- forward/future return 계산 또는 label 생성
- backtest 실행 또는 backtest output 생성
- valuation/fundamental scoring
- financial/fundamental data를 technical scoring에 사용
- financial/fundamental data를 `technical_composite_score` 또는 `final_composite_score`에 사용
- price-only evidence를 cheap, value, undervalued, bargain 등 valuation language로 표현
- diagnostics를 adoption/rejection decision처럼 표현

Step 12 산출물은 반드시:

```text
diagnostic/review material only
```

이어야 한다.

## 5. Step 12 Purpose

Step 12의 목적은 Step 10 normalized score 및 Step 11 component candidate 사이의
redundancy/correlation을 진단하고, Step 13 Technical Selection Reviewer에게 넘길 review material을 만드는 것이다.

Step 12는 아래를 하지 않는다.

- score formula 재정의
- normalization formula 재정의
- composite score 계산
- score 채택 또는 탈락 판정
- ranking 생성
- backtest
- valuation verdict

## 6. Required Files To Read First In A Step 12 Session

다음 Step 12 세션을 시작하면 먼저 아래 파일을 확인한다.

```text
docs/project_checklist.md
docs/roadmap_status.md
docs/step12_redundancy_correlation_diagnostics.md
Quant_mvp/config/thresholds.toml
src/composite/contracts.py
src/diagnostics/diagnostic_contracts.py
src/diagnostics/diagnostic_reports.py
src/diagnostics/score_redundancy.py
tests/diagnostics/test_step12_diagnostic_contracts.py
tests/diagnostics/test_step12_report_guardrails.py
tests/diagnostics/test_step12_score_redundancy.py
```

If the task is only documentation or GPT context preparation, avoid full implementation review loops.
If the task is Step 12 completion, inspect the listed files and run the relevant focused tests.

## 7. Step 12 Worker Split

Worker A responsibility:

```text
src/diagnostics/score_redundancy.py
```

Expected responsibility:

- normalized/component score column input preparation
- same-date cross-sectional Spearman correlation diagnostics
- pair-level redundancy summary
- config-first threshold loading
- no raw-score fallback
- no ranking/composite/backtest/valuation output

Worker B responsibility:

```text
docs/step12_redundancy_correlation_diagnostics.md
src/diagnostics/diagnostic_contracts.py
src/diagnostics/diagnostic_reports.py
reports/diagnostics/README.md
```

Expected responsibility:

- Step 12 output schema contract
- status and threshold flag semantics
- forbidden-column guardrails
- report-language guardrails
- generated-output boundary
- integration-facing bundle validation

Worker B should not make large changes to Worker A's calculation engine unless explicitly assigned.

## 8. Current Worker A Implementation Candidate

`src/diagnostics/score_redundancy.py` currently exposes:

```text
RedundancyScoreInput
ScoreRedundancyConfig
ScoreRedundancyConfigError
load_score_redundancy_config
score_inputs_from_registry
score_inputs_from_columns
prepare_redundancy_input_frame
calculate_score_pair_correlations
summarize_score_redundancy
build_score_redundancy_diagnostics
```

Current Worker A output tables:

```text
pair_summary
pair_date_diagnostics
```

Current `pair_summary` columns:

```text
score_a
score_b
dates_evaluated
dates_insufficient
min_pair_observations
median_pair_observations
median_spearman
mean_spearman
max_abs_spearman
redundancy_status
redundancy_reason
```

Current `pair_date_diagnostics` columns:

```text
score_a
score_b
date
pair_observations
spearman
diagnostic_status
diagnostic_reason
```

Important integration note:

Worker A also produces contract-facing `pair_diagnostics` and `coverage_summary`.
Those tables map engine output into Worker B's `STEP12_PAIR_DIAGNOSTIC_COLUMNS` and
`STEP12_COVERAGE_SUMMARY_COLUMNS` and are validated before report generation.

## 9. Worker B Contract

`src/diagnostics/diagnostic_contracts.py` defines:

```text
STEP12_PAIR_DIAGNOSTIC_COLUMNS
STEP12_COVERAGE_SUMMARY_COLUMNS
STEP12_DEVIATION_LOG_COLUMNS
Step12DiagnosticStatus
Step12ThresholdPolicy
load_step12_threshold_policy
validate_step12_pair_diagnostics
validate_step12_coverage_summary
validate_step12_deviation_log
validate_step12_diagnostics_bundle
classify_spearman_diagnostic_status
threshold_flag_for_status
```

Allowed `diagnostic_status` values:

```text
ok
warn
block_candidate
severe_redundancy
insufficient_data
insufficient_input
config_missing
undefined_correlation
```

These are Step 13 review flags only.
They are not adoption/rejection decisions.

Forbidden output columns include:

```text
rank
ranking
latest_rank
technical_composite_score
final_composite_score
forward_return
future_return
backtest_return
alpha
signal
buy
sell
valuation_score
undervalued
cheap
bargain
```

`src/diagnostics/diagnostic_reports.py` writes generated Markdown reports and rejects forbidden report language.
Generated reports must not be written under `docs/`.

## 10. Config-First Thresholds

Required config source:

```text
Quant_mvp/config/thresholds.toml
```

Required keys:

```text
[redundancy].spearman_warn
[redundancy].spearman_block
[quality].min_cross_section_count
[quality].min_non_nan_observations
```

Current reference values:

```text
[redundancy].spearman_warn = 0.80
[redundancy].spearman_block = 0.90
[quality].min_cross_section_count = 20
[quality].min_non_nan_observations = 60
```

Do not silently hardcode fallback thresholds.
If required config is missing, report `config_missing` or raise a config error.
`spearman_warn` must not exceed `spearman_block`.

## 11. Upstream Contracts From Steps 9-11

Step 9 raw score implementation is complete for eight MVP candidates:

```text
short_term_overreaction_raw
atr_adjusted_oversold_distance_raw
donchian_breakout_distance_raw
bollinger_width_squeeze_raw
cmf_confirmation_raw
rsi_price_divergence_raw
realized_vol_percentile_raw
efficiency_ratio_trend_raw
```

Step 10 normalization is complete and provides normalized score columns such as:

```text
{score_name}_cross_sectional_robust_z
{score_name}_ts_robust_zscore
```

Step 11 composite structure design is complete but design-only.
It defines metadata and candidate inputs in:

```text
src/composite/contracts.py
```

Important Step 11 guardrail:

- Step 11 may classify composite inputs.
- Step 11 does not calculate composite scores.
- Step 12 may use Step 11 metadata for diagnostics.
- Step 12 must not activate composite scoring.

## 12. Step 11 Composite Input Registry

Default Step 11 registry maps eight score names to family, branch, role, and eligibility.

Families:

```text
mean_reversion
trend_breakout
volatility_context
volume_flow
```

Roles:

```text
candidate_signal
confirmation
setup_context
diagnostic_context
```

Eligibility:

```text
eligible
conditional
diagnostic_only
blocked
```

`realized_vol_percentile` is diagnostic/context-only.
`bollinger_width_squeeze` is setup/regime context.
`cmf_confirmation` is confirmation candidate.

## 13. Step 12 Completion Result

Step 12 completion work is done:

1. Worker A calculation behavior is implemented and tested.
2. Worker A output is aligned with Worker B contracts.
3. Coverage summary output exists and validates against `STEP12_COVERAGE_SUMMARY_COLUMNS`.
4. Pair diagnostics validate against `STEP12_PAIR_DIAGNOSTIC_COLUMNS`.
5. Config-first threshold loading is preserved from `Quant_mvp/config/thresholds.toml`.
6. Forbidden output columns/language are rejected by tests.
7. Focused Step 12 tests pass.
8. `docs/roadmap_status.md` and `docs/project_checklist.md` mark Step 12 COMPLETE.

Do not expand into Step 13 adoption review unless explicitly requested.

## 14. Relevant Focused Tests

Step 12 focused tests currently present:

```text
tests/diagnostics/test_step12_diagnostic_contracts.py
tests/diagnostics/test_step12_report_guardrails.py
tests/diagnostics/test_step12_score_redundancy.py
```

Useful focused test command:

```powershell
$env:PYTHONPATH="src"; python -m pytest tests/diagnostics --basetemp=tests/_tmp/pytest_step12_diagnostics
```

Broader tests may be run after focused tests if Step 12 completion touches shared schema/composite code:

```powershell
$env:PYTHONPATH="src"; python -m pytest tests/test_step11_composite_schema.py tests/diagnostics
```

Do not claim tests were rerun unless they were actually rerun in the current session.

## 15. Generated Output Boundary

Source-controlled by default:

- code
- tests
- docs
- config
- small reference fixtures
- project-level agent instructions
- `reports/diagnostics/README.md` as boundary documentation

Not source-controlled by default:

- generated diagnostic reports
- implementation deviation logs produced by current runs
- daily price caches
- financial statement caches
- scan outputs
- chart images
- local runtime reports
- `__pycache__`
- `*.pyc`
- virtual environments
- `.env` and secrets

Generated Step 12 reports should live under:

```text
reports/diagnostics/
```

Generated Step 12 reports must include:

```text
diagnostic/review material only
```

## 16. Valuation Boundary

Current valuation state:

```text
valuation_status = deferred
financial_data_usage_now = inventory_only_or_gui_display_only
point_in_time_status = unverified
financial_data_in_technical_score = false
financial_data_in_final_composite_score = false
```

Step 2 financial collector validation is complete, but point-in-time financial availability follow-up is assigned to Step 18.

PER/PBR/ROE or other financial/fundamental display values must not affect:

- technical scoring
- Step 12 diagnostics
- technical composite scoring
- final composite scoring
- ranking
- adoption decisions
- valuation verdicts

## 17. ChatGPT Behavior For This Project

When helping inside this project:

- Use Korean for progress, status, and final summaries unless the user asks otherwise.
- Keep code identifiers, config keys, file paths, column names, and function names in English.
- Treat unknowns as unknown.
- Label inference as inference.
- Do not make optimistic claims about alpha, robustness, valuation, or trading usefulness.
- Do not infer valuation from price-only technical evidence.
- Do not silently redefine score formulas after seeing outputs.
- Completed Steps 1-11 are trusted by default.
- For Step 12, inspect only direct dependencies unless the user requests full roadmap validation.
- If a Step-end report is requested, report exactly one of:

```text
COMPLETE
PARTIALLY COMPLETE
NEEDS FIX
```

## 18. Minimal Decision Rule

The safe default interpretation:

```text
Step 12 is COMPLETE.
Worker A calculation engine and Worker B contracts/report guardrails are integrated.
Step 13 is NEXT / not started.
Ranking remains blocked until Step 15.
Backtest remains blocked until Step 17.
Valuation/fundamental scoring remains blocked until Step 18 readiness and PIT validation.
Financial/fundamental data must stay out of technical scoring, Step 12 diagnostics, and final composite scoring.
```
