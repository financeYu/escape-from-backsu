# Research / Backtest Boundary Design

## 2. Status

이 문서는 현재 Step 15 support branch의 boundary design 산출물이다. 같은 branch에는 명시적으로 배정된 research ingestion 최소 수리도 포함되어 있지만, 이 문서 자체는 Step 17 backtest 구현 승인이나 ranking/report 구현 변경이 아니다.

- boundary design
- research ingestion minimal repair included in this branch
- no backtest executed
- no ranking output generated
- no score formula changed
- no normalization formula changed
- no composite logic changed
- no valuation/fundamental scoring added

이 문서는 기존 technical research/scoring 산출물과 미래 Step 17 conservative backtest 산출물 사이의 경계를 정의한다. 이 문서 자체는 runtime pipeline, ranking output, report output, backtest engine, valuation/fundamental logic을 변경하지 않는다. 이 branch의 source 변경은 `reserch_mvp/src/research_ingestion/`의 header redaction, request-cache path portability, refresh new-only routing boundary 수리에 한정된다.

## 3. Purpose

이 문서의 목적은 이미 구현된 technical research/scoring pipeline과 미래 Step 17 conservative backtest domain을 분리하는 것이다.

현재 저장소는 KOSPI200 constituent-level daily OHLCV 기반 technical/statistical multi-score ranking engine을 보수적으로 구축하고 있다. Step 1~14는 technical score definition, raw score implementation, normalization, diagnostics, technical review, adoption synthesis를 완료한 상태다. Step 15는 latest ranking output 구현 단계이고, Step 16은 per-stock detail report, Step 17은 conservative backtest의 첫 허용 단계다.

따라서 Step 15/16 output은 Step 17 backtest input이 될 수 있지만, Step 17 output은 Step 5~16 score/ranking definition으로 자동 역류할 수 없다. Backtest 결과에서 떠오른 개선 아이디어는 별도의 명시적 research/review cycle에서 새 candidate 또는 변경 제안으로 기록되어야 한다.

## 4. Domain Separation Overview

### A. Quant Algorithm / Scoring / Ranking Domain

이 domain은 daily OHLCV 기반 technical scoring과 ranking-facing output contract를 소유한다.

Owned responsibilities:

- technical score definitions
- technical indicator calculation
- raw score generation
- time-series normalization
- cross-sectional normalization
- redundancy/correlation diagnostics
- technical review recommendation
- adoption synthesis
- composite design or future composite calculation when allowed
- Step 15 latest ranking output
- Step 16 per-stock detail report

이 domain은 아래 항목을 input 또는 formula decision material로 소비하면 안 된다.

- backtest performance metrics
- `forward_return`
- `future_return`
- `next_period_return`
- `realized_pnl`
- `CAGR`
- `Sharpe`
- `MDD`
- `win_rate`
- `hit_ratio`
- transaction-cost-adjusted return
- any future-dated label

Technical diagnostics는 review material일 수 있지만 stock-selection alpha signal이 아니다. Adoption synthesis는 Step 15 입력 material일 수 있지만 final trading decision이 아니다.

### B. Backtest Domain

이 domain은 미래 Step 17에서만 열린다. 현재 문서에서는 구현하지 않는다.

Owned responsibilities:

- fixed score/ranking/signal-like output을 input으로 수신
- 날짜별 historical portfolio construction 재구성
- no-lookahead rebalance schedule 적용
- separate config에서 transaction cost, slippage, turnover, holding period, execution assumption 적용
- performance 및 diagnostics 측정
- score definitions를 변경하지 않고 결과 보고

Backtest domain must not:

- redefine score formulas
- redefine normalization logic
- change adoption states
- modify Step 15 latest ranking logic
- modify Step 16 report logic
- feed performance results back into score definitions silently
- use valuation/fundamental data unless Step 18+ explicitly permits it

Backtest 결과는 downstream measurement output이다. Score formula, normalization, adoption state, ranking logic을 직접 mutate하는 control signal이 아니다.

## 5. Existing Artifact Inventory

아래 inventory는 파일 이동, rename, 구현 변경 없이 현재 저장소 artifact의 boundary role만 분류한다.

| category | path | current role | proposed domain | allowed downstream consumer | forbidden downstream consumer | risk if misused |
| --- | --- | --- | --- | --- | --- | --- |
| `quant_algorithm_scoring` | `src/indicators/technical.py` | Step 7 daily OHLCV technical indicator calculation layer | Quant algorithm / scoring | Step 9 raw score generation, Step 15 ranking preparation when contracted | Backtest engine mutating indicator windows from performance results | Indicator windows could be tuned after seeing performance, creating silent lookahead-style contamination. |
| `quant_algorithm_scoring` | `src/preprocess/daily_ohlcv.py`, `src/preprocess/schema_validator.py` | Step 6 preprocessing and schema validation | Quant algorithm / scoring | Indicator and score pipeline | Backtest-specific label generation inside preprocessing | Preprocessing could become mixed with future labels or simulation artifacts. |
| `quant_algorithm_scoring` | `src/scores/score_contracts.py` | Locked Step 9 score metadata and raw score contracts | Quant algorithm / scoring | Step 9 raw score code, Step 11 composite design, Step 13 review | Step 17 performance optimizer | Performance-driven edits here would silently redefine score candidates. |
| `quant_algorithm_scoring` | `src/scores/mean_reversion_scores.py` | Step 9 Part A raw technical/diagnostic score calculation | Quant algorithm / scoring | Step 10 normalization and Step 11+ review material | Backtest performance feedback loop | Formula edits after performance review would invalidate prior adoption synthesis. |
| `quant_algorithm_scoring` | `src/scores/trend_vol_flow_scores.py` | Step 9 Part B raw technical/context score calculation | Quant algorithm / scoring | Step 10 normalization and Step 11+ review material | Backtest performance feedback loop | Performance metrics could be mistaken for score design evidence. |
| `quant_algorithm_scoring` | `src/scores/technical_scores.py` | Integrated Step 9 raw score entrypoint for eight MVP candidates | Quant algorithm / scoring | Step 10 normalization | Step 17 engine changing formula parameters | Backtest could become an implicit score optimizer. |
| `quant_algorithm_scoring` | `src/scores/schema.py` | Score output hard-stop guardrails and valuation/future output rejection | Quant algorithm / scoring boundary guard | Scoring, normalization, diagnostics, selection validators | Backtest output schema | If weakened, forbidden future/performance columns could enter score outputs. |
| `quant_algorithm_scoring` | `src/scores/normalization_timeseries.py` | Step 10A ticker-local robust normalization | Quant algorithm / scoring | Step 11 composite design, Step 13 review, Step 15 display contract | Backtest parameter fitting loop | Normalization windows/clipping could be tuned from performance results. |
| `quant_algorithm_scoring` | `src/scores/normalization_cross_sectional.py` | Step 10B same-date cross-sectional robust normalization | Quant algorithm / scoring | Step 11 composite design, Step 13 review, Step 15 ranking input contract | Backtest performance optimizer | Same-date ranking inputs could be contaminated by future result labels. |
| `quant_algorithm_scoring` | `src/scores/normalization_diagnostics.py` | Normalization coverage and event-count diagnostics | Diagnostic-only support within scoring domain | Step 12/13 review material | Direct ranking alpha or backtest decision layer | Diagnostics could be mislabeled as selection evidence. |
| `quant_algorithm_scoring` | `src/composite/contracts.py`, `src/composite/schema.py` | Step 11 composite design/schema skeleton only | Quant algorithm / scoring | Step 13 review and future allowed composite implementation | Step 17 backtest-driven score selection | Composite design could be silently changed after seeing simulated outcomes. |
| `quant_algorithm_scoring` | `Quant_mvp/config/scores.toml`, `Quant_mvp/config/windows.toml`, `Quant_mvp/config/thresholds.toml`, `Quant_mvp/config/weights.toml` | Config-owned score, window, threshold, and design settings | Quant algorithm / scoring | Score/normalization/diagnostic/review pipeline | Backtest performance threshold storage | Backtest criteria in score config would blur design with measurement. |
| `quant_algorithm_scoring` | `Quant_mvp/docs/score_catalog.md`, `Quant_mvp/docs/score_definitions.md`, `Quant_mvp/docs/family_map.md` | Score taxonomy, definitions, and family map | Quant algorithm / scoring | Score implementation/review stages | Backtest-result narrative | Paper or simulation claims could be laundered into score definitions. |
| `diagnostic_only` | `src/diagnostics/score_redundancy.py` | Step 12 same-date redundancy/correlation diagnostic engine | Diagnostic-only review material | Step 13 Technical Selection Reviewer | Ranking, backtest, or direct score adoption | Correlation flags could be treated as alpha or automatic selection decisions. |
| `diagnostic_only` | `src/diagnostics/diagnostic_contracts.py`, `src/diagnostics/diagnostic_reports.py` | Step 12 output contract and report guardrails | Diagnostic-only review material | Step 13 review | Backtest output schema or ranking output | Diagnostic reports could become performance or ranking artifacts. |
| `diagnostic_only` | `docs/step12_redundancy_correlation_diagnostics.md` | Canonical Step 12 diagnostic boundary | Diagnostic-only governance | Step 13 review and future audit | Backtest implementation source | Methodology warnings could be misused as portfolio rules. |
| `diagnostic_only` | `reports/diagnostics/README.md` | Source-controlled boundary note for generated diagnostics reports | Diagnostic-only report boundary | Generated report path policy | Score/ranking/backtest evidence store | Generated diagnostics could be committed or interpreted as canonical output. |
| `ranking_or_report_interface` | `src/selection/technical_selection_contracts.py`, `src/selection/technical_selection_reviewer.py`, `src/selection/technical_selection_reports.py` | Step 13 technical review recommendation contract/engine/reporting | Technical review interface | Step 14 adoption synthesis | Ranking engine, backtest engine, final trading decision layer | Review recommendations could be mistaken for final adoption or simulated performance evidence. |
| `ranking_or_report_interface` | `src/selection/adoption_synthesis_contracts.py`, `src/selection/adoption_synthesis.py`, `src/selection/adoption_synthesis_reports.py` | Step 14 adoption synthesis material and guardrails | Ranking/report input interface | Step 15 latest ranking output implementation | Step 17 engine changing adoption states | Adoption states could be backfit after simulation results. |
| `ranking_or_report_interface` | `docs/step13_technical_selection_reviewer.md`, `docs/step14_adoption_synthesis.md` | Step 13/14 review-to-adoption contracts | Ranking/report input interface | Step 15 design/implementation | Backtest result justification | Step 15 could consume review material as if it were performance proof. |
| `ranking_or_report_interface` | `reports/selection/README.md` | Source-controlled boundary note for generated selection reports | Report boundary | Step 13/14 report generators | Backtest/ranking output store | Generated review reports could be confused with ranking snapshots. |
| `ranking_or_report_interface` | `chart_mvp/src/stock_core/ranking/base.py`, `chart_mvp/src/stock_core/ranking/placeholder.py`, `chart_mvp/src/stock_core/ranking/scorer.py`, `chart_mvp/src/stock_core/ranking/selector.py` | Legacy/chart runtime ranking placeholders and selector helpers | Ambiguous legacy ranking interface; not Step 15 canonical until reviewed | Chart runtime only after Step 15 ownership review | Quant score definition, Step 17 backtest input without freeze/contract | Legacy output could bypass Step 15 contract and contaminate backtest input. |
| `ranking_or_report_interface` | `chart_mvp/src/stock_core/pipeline/daily_scan.py` | Existing chart batch scan pipeline that writes top-N runtime output | Chart runtime / legacy ranking-like output | Chart runtime after Step 15 boundary review | Quant score definitions, Step 17 direct performance testing | Runtime top-N output could be mistaken for current Step 15 technical ranking output. |
| `future_backtest_boundary` | `docs/project_checklist.md`, `docs/roadmap_status.md` | Roadmap order and hard-stop authority | Cross-step boundary governance | All roadmap stages as guardrails | Any implementation that bypasses Step order | Step 17 behavior could appear before allowed stage. |
| `future_backtest_boundary` | `docs/cross_step_conflict_check.md` | Checkpoint procedure for roadmap/order/hard-stop conflicts | Cross-step boundary governance | Step-end and stage-end review | Runtime engine or scoring code | Conflict checks could be treated as implementation approval rather than a gate. |
| `future_backtest_boundary` | `docs/technical_valuation_boundary.md` | Technical/valuation separation policy | Boundary governance | Score/review/valuation agents | Price-only technical scoring or backtest output as valuation evidence | Valuation language or financial inputs could enter technical scoring too early. |
| `future_backtest_boundary` | `docs/legacy_output_inventory.md`, `reports/data_quality/legacy_output_inventory.md` | Inventory of legacy/background runtime outputs | Boundary evidence | Audit/review only | Step 15/17 current evidence | Legacy rankings could be reused as current ranking or backtest material. |
| `future_backtest_boundary` | `scripts/build_review_packet.py` | Compact review packet builder for conflict review | Validation support | Cross-step checkpoint | Backtest/report generation | Review packets could be mistaken for generated market outputs. |
| `research_ingestion` | `reserch_mvp/AGENTS.md` | Canonical Research Ingestion Agent policy | Research ingestion | EvidenceCard generation and upstream handoff | Score adoption, ranking, or backtest implementation | Research claims could be promoted directly into scores or performance claims. |
| `research_ingestion` | `reserch_mvp/src/research_ingestion/**` | Research source adapters, discovery, normalization, classification, EvidenceCard, reporting code | Research ingestion | Quant intake via EvidenceCards/handoff files | Direct Step 15 ranking or Step 17 backtest | Paper-reported results could be treated as verified project performance. |
| `research_ingestion` | `reserch_mvp/config/research_sources.toml`, `reserch_mvp/config/research_queries.toml`, `reserch_mvp/config/research_policy.toml`, `reserch_mvp/config/research_classification.toml`, `reserch_mvp/config/research_scholar_discovery.toml` | Source/query/policy/classification/discovery config | Research ingestion | Research ingestion runs and downstream EvidenceCard review | Score formula config or backtest config | Research query terms could be mistaken for implemented scores or tested strategies. |
| `research_ingestion` | `reserch_mvp/reports/research_ingestion/**` | Korean ingestion reports, handoff summaries, reject/source reports | Research ingestion reports | Quant research intake and manual review | Ranking/backtest evidence | Literature summaries could be overstated as alpha or performance validation. |
| `research_ingestion` | `Quant_mvp/config/research_intake.toml` | Downstream EvidenceCard intake contract | Quant intake boundary | Quant score/governance review | Source collection policy or direct score adoption | Intake could bypass canonical `reserch_mvp` ownership or adopt scores from EvidenceCards. |
| `research_ingestion` | `Quant_mvp/docs/research_ingestion_usage.md`, `Quant_mvp/agents/research/AGENTS.md` | Compatibility/intake notes for Quant consuming research outputs | Quant intake boundary | Quant governance | Canonical research source collection | Ownership confusion could weaken source policy and seed resolution rules. |
| `ambiguous_or_needs_review` | `chart_mvp/outputs/*`, `chart_mvp/data/scan_results/*`, `chart_mvp/outputs/charts/*` | Legacy generated runtime outputs recorded in inventory docs | Generated-output boundary | Audit/background inventory only | Step 15 current ranking or Step 17 historical backtest input | Generated legacy outputs may contain pre-roadmap assumptions and must not be treated as current evidence. |
| `ambiguous_or_needs_review` | `chart_mvp/TEMPORARY_TOP5_OVERRIDE.md` | Temporary Top-5 override note | Generated-output/legacy boundary | Audit/background inventory only | Step 15 canonical ranking | Temporary override could mask ranking logic or data quality issues. |
| `out_of_scope_for_now` | `Quant_mvp/agents/valuation/**`, `Quant_mvp/reports/valuation_review/**`, `Quant_mvp/docs/valuation_*.md` | Valuation/fundamental review examples and pretest material | Step 18+ valuation domain | Future Step 18 valuation process | Technical score/composite/ranking/backtest before Step 18 | Fundamental inputs could enter technical or final composite scoring too early. |
| `out_of_scope_for_now` | `review_mvp/**` | Specialist code-review tooling | Code review support | Review flow when required | Score/ranking/backtest implementation | Review tooling is not a scoring or backtest domain owner. |

## 6. Step 15 / Step 16 / Step 17 Interface Contract

### Step 15 Latest Ranking Output

Step 15 latest ranking output should be treated as a downstream-facing snapshot, not as a backtest engine.

Conceptual candidate columns may include the following if already supported or explicitly planned by Step 15 implementation. This document does not force these columns into implementation.

- `as_of_date`
- `ticker`
- `rank`
- `score_name`
- `score_value`
- `normalized_score`
- `technical_composite_score`
- `adoption_state`
- `eligibility_flag`
- `warmup_state`
- `coverage_status`
- `data_quality_flag`
- `source_run_id`
- `generated_at`

Boundary requirements:

- `as_of_date` must be the latest date whose data is allowed in the snapshot.
- Ranking output must not include future labels or performance outcomes.
- Ranking output must preserve enough traceability to identify score inputs, data quality, and adoption state.
- Ranking output must not call itself a trading decision.

### Step 16 Per-Stock Detail Report

Step 16 report should explain current ranking/score state only.

It must not include:

- future return
- backtest result
- realized performance
- PnL attribution
- buy/sell/trading signal wording
- valuation wording

Allowed narrative scope:

- score and normalized score explanation
- current technical context
- warmup/coverage/data quality state
- adoption synthesis traceability
- diagnostic limitations

### Step 17 Future Backtest Input

Step 17 should consume frozen historical snapshots or reproducible historical score outputs.

Requirements:

- Input must be fixed by date and reproducible from Step 15/16 contracts or historical score-output generation contracts.
- Backtest must not call score formula internals in a way that lets performance results alter score definitions.
- If historical score recomputation is required, it must use committed score/normalization/adoption configs from the simulated `as_of_date` context or an explicitly versioned frozen contract.
- Backtest output must be written to backtest-specific outputs only.

## 7. One-Way Dependency Rule

Allowed direction:

```text
OHLCV data
-> indicators
-> raw scores
-> normalization
-> diagnostics/review/adoption
-> Step 15 latest ranking output
-> Step 16 report
-> Step 17 backtest input
```

Forbidden reverse direction:

```text
Step 17 backtest metrics
-> score formula changes
-> normalization changes
-> adoption-state changes
-> ranking logic changes
```

Any future score change inspired by backtest findings must go through a separate explicit research/review process and must be logged as a new candidate or explicit design revision. It must not be silently patched into an existing score.

Minimum future process for a backtest-inspired idea:

1. Record the observation as `diagnostic_only` or research note.
2. Open a new explicit research/review cycle.
3. Define whether the change is a new candidate, a formula revision, or a rejection/risk note.
4. Re-run the appropriate upstream review and conflict checkpoint.
5. Preserve the original score definition lineage.

## 8. No-Lookahead / No-Future-Data Guardrails

Required guardrails:

- `as_of_date` must mean the latest date whose data is allowed for that snapshot.
- No field in Step 15/16 output may require data after `as_of_date`.
- Backtest must only consume information available at or before each rebalance decision date.
- Any future Step 17 rebalance logic must define whether the trade is assumed at next open, next close, or another conservative execution point.
- Future return labels must never appear in scoring/ranking files.
- Backtest performance columns must live in backtest-specific outputs only.
- Universe membership and missing-data policy must be explicit for each simulated decision date.
- Generated output path must identify whether it is ranking/report output or backtest output; mixed files are not allowed.

Backtest execution timing must be conservative. For example, a score snapshot with `as_of_date = D` cannot assume an execution price from date `D` unless the design explicitly proves the execution point is available after all required data for `D` is known. If not proven, use a later conservative execution point.

## 9. Configuration Separation

This section proposes separation only. It does not implement or edit config files.

### Quant Algorithm / Scoring Configs

Scoring configs may include:

- score definitions
- indicator windows
- normalization windows
- winsorization / clipping policy
- warmup policy
- redundancy thresholds
- adoption synthesis thresholds
- ranking display settings

Scoring configs must not contain:

- backtest performance thresholds
- portfolio performance targets
- performance-based parameter search state
- execution-cost assumptions used only for simulation
- future-return labels

### Backtest Configs

Future Step 17 configs may include only:

- rebalance frequency
- holding period
- portfolio size
- weighting rule
- transaction cost
- slippage
- turnover constraint
- execution timing assumption
- benchmark
- survivorship/universe handling policy
- missing data handling for historical simulation

Backtest config must not contain score formulas. Score config must not contain backtest performance thresholds.

Recommended future naming pattern:

- scoring/ranking config: existing `Quant_mvp/config/*.toml` or Step 15-owned ranking config if approved.
- future backtest config: a Step 17-owned config path such as `config/backtest.toml` or `src/backtest` adjacent config only after Step 17 begins.

## 10. Forbidden Column and Language Policy

### Forbidden Columns Before Step 17

The following columns are forbidden from quant algorithm / scoring / ranking outputs before Step 17:

- `forward_return`
- `future_return`
- `next_return`
- `next_period_return`
- `realized_return`
- `realized_pnl`
- `strategy_return`
- `portfolio_return`
- `benchmark_return`
- `excess_return`
- `alpha`
- `sharpe`
- `mdd`
- `drawdown`
- `win_rate`
- `hit_ratio`

Backtest-specific outputs may define performance columns only after Step 17 opens, and only inside backtest-owned output paths.

### Forbidden Language In Scoring / Ranking / Report Docs

The following language is forbidden in scoring/ranking/report docs except inside explicit forbidden-language policy lists:

- alpha proven
- backtest proves
- buy signal
- sell signal
- trading signal
- expected return
- profitable
- market-beating
- undervalued
- cheap
- bargain
- value stock
- target price
- 실전 매수 후보
- 수익률 보장

Step 15/16 Korean-facing text should use neutral technical-status language. It may describe `technical context`, `coverage_status`, `warmup_state`, `data_quality_flag`, `adoption_state`, and `diagnostic limitations`, but must not imply live trading advice or guaranteed performance.

## 11. Contamination Scenarios

| scenario | required response |
| --- | --- |
| If a backtest performs poorly and someone wants to adjust `score_formula` | Reject unless a new explicit research cycle is opened and the change is logged as a new candidate or explicit design revision. |
| If Step 15 ranking output contains `future_return` | Block as hard-stop violation. Remove the column before treating the output as ranking material. |
| If diagnostics are described as stock-selection alpha | Rewrite as diagnostic/review material only. |
| If price-only oversoldness is described as cheap or undervalued | Block valuation language and rewrite as technical condition only. |
| If Step 17 code imports internal score formula modules and mutates parameters based on results | Block and require frozen snapshot input or versioned historical score-output contract. |
| If a generated chart/runtime ranking from `chart_mvp/outputs/` is reused as Step 15 canonical output | Block until Step 15 contract verifies provenance, column policy, and as-of-date semantics. |
| If `Quant_mvp/config/weights.toml` is edited after reviewing backtest metrics | Block unless the edit is part of a separate approved research/review process. |
| If Step 16 report includes realized performance or PnL attribution | Block and move the material to Step 17 backtest-specific outputs after Step 17 opens. |
| If research EvidenceCards with paper-reported performance are treated as verified project performance | Rewrite as paper-claim-only diagnostic metadata; no score adoption or backtest validation is implied. |
| If valuation/fundamental fields are added to `technical_composite_score` or `final_composite_score` before Step 18 | Block as roadmap and valuation-boundary violation. |

## 12. Proposed Future Implementation Boundary

Do not implement this now. This is a logical boundary proposal based on actual repository paths observed in this branch.

| logical domain | actual current paths | future boundary note |
| --- | --- | --- |
| Indicator calculation | `src/indicators/technical.py` | Owns daily OHLCV-derived indicators only. No score, ranking, or backtest output. |
| Score calculation | `src/scores/technical_scores.py`, `src/scores/mean_reversion_scores.py`, `src/scores/trend_vol_flow_scores.py`, `src/scores/score_contracts.py`, `src/scores/schema.py` | Owns raw technical score calculation and score guardrails. No performance labels. |
| Normalization | `src/scores/normalization_timeseries.py`, `src/scores/normalization_cross_sectional.py`, `src/scores/normalization_diagnostics.py` | Owns robust normalization and coverage diagnostics. No rank or future labels. |
| Composite design/schema | `src/composite/contracts.py`, `src/composite/schema.py` | Currently design/schema only. Future composite calculation must remain technical-only until Step 18+ explicitly changes valuation policy. |
| Diagnostics | `src/diagnostics/score_redundancy.py`, `src/diagnostics/diagnostic_contracts.py`, `src/diagnostics/diagnostic_reports.py` | Owns redundancy/correlation diagnostics as review material only. |
| Selection/review/adoption | `src/selection/technical_selection_*`, `src/selection/adoption_synthesis*` | Owns Step 13 review and Step 14 adoption synthesis material. Not final trading output. |
| Future Step 15 ranking | Future `src/ranking/` or current equivalent selected by Step 15 owner | Should own latest ranking snapshot output only. It must consume fixed score/adoption inputs and avoid backtest metrics. |
| Future Step 16 reports | Future `src/reports/` or current equivalent selected by Step 16 owner | Should explain current ranking/score state only. It must not include future returns, backtest results, realized performance, PnL attribution, trading wording, or valuation wording. |
| Future Step 17 backtest | Future `src/backtest/` or Step 17-owned equivalent | Should own conservative historical simulation only. It consumes frozen snapshots or reproducible historical score outputs and writes backtest-specific outputs only. |
| Legacy/chart runtime | `chart_mvp/src/stock_core/ranking/**`, `chart_mvp/src/stock_core/pipeline/daily_scan.py`, `chart_mvp/outputs/**` | Must be reviewed before serving as Step 15 canonical ranking output or Step 17 input. Existing outputs are legacy/background material only. |
| Research ingestion | `reserch_mvp/src/research_ingestion/**`, `reserch_mvp/config/research_*.toml`, `reserch_mvp/reports/research_ingestion/**` | Owns paper discovery and EvidenceCards only. It does not adopt scores or run backtests. |
| Valuation/fundamental | `Quant_mvp/agents/valuation/**`, `Quant_mvp/reports/valuation_review/**` | Deferred to Step 18+. Must stay out of technical scoring and current ranking/backtest design. |

If Step 15 chooses existing `chart_mvp` paths as a runtime implementation target, it should first document the canonical Step 15 output contract and generated-output boundary. Legacy path names alone must not grant canonical status.

## 13. Required Acceptance Checklist

This design is acceptable only if:

- It does not implement backtesting.
- It does not generate ranking output.
- It does not change score definitions.
- It does not change normalization logic.
- It does not change composite logic.
- It does not use future returns.
- It does not use valuation/fundamental data.
- It separates Step 15/16 output from Step 17 backtest input.
- It defines one-way dependency from scoring/ranking to backtest.
- It blocks silent score redefinition after seeing backtest results.
- It keeps report language Korean while preserving file paths, config keys, function names, and column names in English.

Local confirmation for this branch:

- `WORKSPACE_MANIFEST.md` limits writes to this design doc, manifest, and explicitly assigned `reserch_mvp/src/research_ingestion/` repair files.
- No root `src/` scoring, normalization, ranking, report, composite, backtest, or valuation code is changed by this task.
- No runtime outputs under `reports/`, `data/`, `chart_mvp/outputs/`, or backtest-specific paths are generated by this task.
- `docs/roadmap_status.md` remains unchanged.

## 14. Cross-Step Conflict Checkpoint

This document should be reviewed with `docs/cross_step_conflict_check.md`, current roadmap status, and Step 15/16/17 boundaries.

Checkpoint scope for this design:

- trigger: design document and explicitly assigned research ingestion minimal repair created for Step 15 support branch
- roadmap/order: Step 15 remains waiting for implementation; Step 16 and Step 17 remain not started
- hard stops: no backtest, no ranking output generation, no future data, no valuation/fundamental scoring
- score/composite boundary: score formulas, normalization, and composite logic are unchanged
- valuation boundary: valuation/fundamental material remains Step 18+ only
- diagnostics boundary: diagnostics remain review material only
- handoff consistency: Step 15/16 output may feed Step 17 input one-way; Step 17 metrics may not flow backward
- generated-output boundary: no generated reports, caches, charts, rankings, or backtest outputs are created
- dirty worktree isolation: research support branch and manifest are separate from Step 15 implementation branches
- root-agent conflict stop: no stop trigger observed after isolating worktree and write scope

Expected verdict: `PASS`, unless later review finds that the design document itself is treated as implementation approval or used to bypass the Step 15/16/17 roadmap gates.
