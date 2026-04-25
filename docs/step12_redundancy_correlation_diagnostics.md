# Step 12 Redundancy / Correlation Diagnostics

## 1. Purpose

Step 12의 목적은 Step 10 normalized score 및 component score 사이의
redundancy/correlation을 진단하고, Step 13 Technical Selection Reviewer에게
넘길 review material을 만드는 것이다.

Step 12 산출물은 **diagnostic/review material only**다. 이 단계는 score
채택, ranking, composite score, backtest, valuation verdict를 만들지 않는다.

Worker split:

- Worker A: `src/diagnostics/score_redundancy.py`에서 core
  correlation/redundancy 계산 엔진과 contract-facing adapter 담당
- Worker B: output contract, report schema, guardrail,
  report writer, 문서 담당

Worker B는 Worker A 계산 파일을 직접 대규모 수정하지 않는다.

## 2. Upstream Inputs

Step 12 input은 아래 항목으로 제한한다.

| input | requirement |
| --- | --- |
| `ticker` | Step 6/9/10 정체성 key. six-character string, leading zeros preserved. |
| `date` | Step 6/9/10 정체성 key. parseable same-date grouping 기준. |
| Step 10 normalized score columns | 예: `{score_name}_cross_sectional_robust_z`, `{score_name}_ts_robust_zscore`. |
| Step 10 status/quality metadata | status, quality flag, valid count, observation count, coverage status. |
| Step 11 score metadata | score family, role, eligibility, branch metadata가 있으면 사용한다. |

Step 12는 Step 9 formula, Step 10 normalization formula, Step 11 composite
design을 재정의하지 않는다.

## 3. Output Contract

Step 12 output은 아래 네 종류로 고정한다. Worker A engine은 내부 검수용
`pair_summary`도 제공할 수 있다. 이 engine summary는 `score_a`, `score_b`,
`dates_evaluated`, `median_spearman`, `max_abs_spearman`,
`redundancy_status`, `redundancy_reason` 등을 포함하며, report-facing
`score_pair_diagnostics` contract로 변환되어 Worker B validator를 통과해야 한다.

### 3.1 Score Pair Diagnostics

Pair-level output은 score 대 score 관계를 요약한다. Row-level `ticker` 또는
`date` identity를 직접 내보내는 테이블이 아니다.

Required columns:

| column | meaning |
| --- | --- |
| `diagnostic_name` | `score_pair_correlation` 등 진단 이름 |
| `score_left` | 왼쪽 score name |
| `score_right` | 오른쪽 score name |
| `normalization_scope` | `cross_sectional`, `time_series`, `mixed`, `unknown` |
| `start_date` | 진단 대상 구간 시작일 |
| `end_date` | 진단 대상 구간 종료일 |
| `observation_count` | non-null pair observation 수 |
| `cross_section_count` | 사용된 same-date cross-section 수 |
| `spearman_correlation` | 이미 계산된 Spearman correlation 값 |
| `abs_spearman_correlation` | 절댓값 |
| `threshold_flag` | `none`, `spearman_warn`, `spearman_block`, `insufficient_input`, `insufficient_data`, `config_missing`, `undefined_correlation` |
| `diagnostic_status` | section 4 status semantics |
| `insufficient_data_reason` | 부족한 경우 명시적 이유 |
| `score_left_family` | Step 11 family metadata, unknown 가능 |
| `score_right_family` | Step 11 family metadata, unknown 가능 |
| `score_left_role` | Step 11 role metadata, unknown 가능 |
| `score_right_role` | Step 11 role metadata, unknown 가능 |
| `implementation_deviation_id` | deviation log link, 없으면 empty |
| `notes` | 보수적 review note, unknown은 unknown으로 표시 |

### 3.2 Coverage Summary

Coverage output은 score별로 Step 12 진단에 충분한 관측치가 있었는지 요약한다.

Required columns:

| column | meaning |
| --- | --- |
| `diagnostic_name` | `coverage_summary` |
| `score_name` | score name |
| `score_family` | Step 11 family metadata, unknown 가능 |
| `normalization_scope` | normalization context |
| `date` | same-date summary일 때 기준일, aggregate면 empty 가능 |
| `ticker_count` | 대상 ticker 수 |
| `observation_count` | 전체 관측 수 |
| `non_nan_observation_count` | finite/non-null 관측 수 |
| `coverage_ratio` | non-null ratio |
| `min_required_observations` | `[quality].min_non_nan_observations` |
| `min_cross_section_count` | `[quality].min_cross_section_count` |
| `diagnostic_status` | section 4 status semantics |
| `insufficient_data_reason` | 부족한 경우 명시적 이유 |
| `implementation_deviation_id` | deviation log link, 없으면 empty |
| `notes` | 보수적 review note |

### 3.3 Threshold Flags

Threshold flags are diagnostic flags only.

| flag | meaning |
| --- | --- |
| `none` | configured threshold breach 없음 |
| `spearman_warn` | absolute Spearman value가 warn threshold 이상 |
| `spearman_block` | absolute Spearman value가 block threshold 이상 |
| `insufficient_input` | required normalized/component score column 누락 |
| `insufficient_data` | configured minimum count 미달 |
| `config_missing` | 필수 threshold config 누락 |
| `undefined_correlation` | correlation 계산 불가 또는 non-finite |

`spearman_block` 또는 `block_candidate`는 Step 13 reviewer에게 넘길 강한
중복 후보 flag다. 이것은 adoption/rejection 판정이 아니다.

### 3.4 Implementation Deviation Log

Worker A 또는 integration wrapper가 Step 12 contract, Step 10/11 upstream
contract, config policy와 다르게 동작해야 할 경우 deviation log를 남긴다.

Required columns:

| column | meaning |
| --- | --- |
| `deviation_id` | stable identifier |
| `step` | `Step 12` |
| `affected_field` | schema, threshold, coverage, correlation, metadata 등 |
| `expected_behavior` | 문서/config 기대값 |
| `actual_behavior` | 실제 동작 |
| `reason` | 필요했던 이유 |
| `risk` | 보수적 risk summary |
| `review_required` | `true` / `false` |
| `created_at_utc` | UTC timestamp |

Suggested runtime path:

```text
reports/diagnostics/implementation_deviation_log.csv
```

Generated report/log files are runtime artifacts. They are not canonical
source-controlled project state.

## 4. Status Semantics

Allowed `diagnostic_status` values:

| status | meaning |
| --- | --- |
| `ok` | configured threshold breach 없음, minimum data 충족 |
| `warn` | 중복 위험 warning threshold 이상 |
| `block_candidate` | severe redundancy candidate; Step 13 검토 필요 |
| `severe_redundancy` | `block_candidate`의 호환 alias로만 허용 |
| `insufficient_input` | required normalized/component score column 누락 또는 upstream input 부재 |
| `insufficient_data` | minimum observation 또는 same-date count 미달 |
| `config_missing` | required threshold config key 누락 |
| `undefined_correlation` | finite correlation value를 정의할 수 없음 |

이 status들은 Step 13 Technical Selection Reviewer에게 넘기는 diagnostic flag다.
그 자체가 adoption/rejection decision이 아니며, 특정 score를 제거하거나 채택하지
않는다.

## 5. Threshold Policy

Step 12 threshold는 config-first로 로드해야 한다. 누락 시 silent hardcoding하지
않고 `config_missing` 또는 exception으로 처리한다.

Required config keys:

```text
Quant_mvp/config/thresholds.toml -> [redundancy].spearman_warn
Quant_mvp/config/thresholds.toml -> [redundancy].spearman_block
Quant_mvp/config/thresholds.toml -> [quality].min_cross_section_count
Quant_mvp/config/thresholds.toml -> [quality].min_non_nan_observations
```

Current reference values:

```text
[redundancy].spearman_warn = 0.80
[redundancy].spearman_block = 0.90
[quality].min_cross_section_count = 20
[quality].min_non_nan_observations = 60
```

`spearman_warn` must not exceed `spearman_block`.

## 6. Explicit Non-Outputs

Step 12 output must not include or imply:

- ranking
- latest ranking
- buy/sell signal
- alpha evidence
- adoption/rejection decision
- `technical_composite_score`
- `final_composite_score`
- backtest result
- forward/future return
- valuation/fundamental verdict
- `PER`, `PBR`, `ROE` 또는 point-in-time fundamental inference

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

`src/diagnostics/diagnostic_contracts.py` must reject these columns in Step 12
diagnostic output.

## 7. Report Contract

Generated Step 12 reports must:

- include the exact phrase `diagnostic/review material only`
- be written as runtime output, preferably under `reports/diagnostics/`
- not be treated as canonical source-controlled state
- avoid language that frames diagnostics as alpha, trading, ranking,
  backtest, valuation, or adoption output
- preserve threshold values and count summaries needed by Step 13

Source-controlled documentation belongs under `docs/`.
Generated report files do not belong under `docs/`.

`reports/diagnostics/README.md` is allowed as a source-controlled boundary note;
actual run outputs under that directory remain generated artifacts unless a
small fixture is explicitly added for tests with an explanation.

## 8. Integration Boundary

Worker B helper files:

```text
src/diagnostics/diagnostic_contracts.py
src/diagnostics/diagnostic_reports.py
tests/diagnostics/test_step12_diagnostic_contracts.py
tests/diagnostics/test_step12_report_guardrails.py
```

Worker A file boundary:

```text
src/diagnostics/score_redundancy.py
```

Worker A produces engine-level `pair_summary` / `pair_date_diagnostics` and
contract-facing `pair_diagnostics` / `coverage_summary`. The contract-facing
tables must pass Worker B validation helpers before report generation. Worker B
helpers do not depend on Worker A's calculation engine, so contract tests must
also pass independently.

## 9. Step 13 Handoff

Step 13 should receive:

- score pair diagnostics
- coverage summary
- threshold flags
- insufficient data reasons
- implementation deviation log, if present
- confirmation that Step 12 did not create ranking, composite score, backtest,
  forward/future return, or valuation/fundamental scoring output

Step 13 remains responsible for technical relevance, distinctiveness,
stability, complexity cost, regime fit, redundancy risk, and technical verdict.
Step 12 does not make that verdict.
