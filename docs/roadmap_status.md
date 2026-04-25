# 로드맵 상태

이 파일은 현재 작업 판단에 필요한 compact status만 유지한다. 완료 Step의 긴 구현/검증 이력은 `docs/roadmap_archive/` 아래 archive 문서를 확인한다.

## 현재 활성 단계

Step 18 = 밸류에이션 확장 준비, COMPLETE / candidate-only valuation-fundamental expansion implemented

- Recently completed: Step 18 = 밸류에이션 확장 준비, COMPLETE
- Recently completed before that: Step 17 = 보수적 백테스트, COMPLETE
- Carry-forward resolved for this Step: Step 18 now defines candidate-only financial metadata schema, availability-date validation, metric registry, and leakage guardrails.
- Current gate: Step 19 remains WAITING / not started. Step 18 candidate data is not activated in technical scoring, final ranking, or Step 17 backtest inputs.

## 병렬 Workspace 운영 메모

- Step 14 이후 병렬 구현, review, research ingestion, audit/scope watchdog, master integration 작업은 `docs/workspace_parallel_work_policy.md`를 따른다.
- Step 15부터는 Step implementation, Quant score/governance, research ingestion, chart runtime, review, audit/scope watchdog, master integration을 별도 branch/worktree로 분리하는 Step 15+ Branch Separation Process가 필수다.
- Step implementation은 major Step branch(`codex/stepXX-<scope>`)에서만 진행하고, Quant/research/review/audit/chart 작업은 minor/support branch(`quant/`, `research/`, `review/`, `audit/`, `chart/`)에서 분리한다.
- 모든 하위 에이전트는 파일 편집 전에 role branch/worktree를 만들거나 선택하고 루트 `WORKSPACE_MANIFEST.md`를 작성해야 한다.
- `C:\Users\jjaew\Project\master_mvp`는 integration / verification / status-control 전용 workspace로 유지한다.
- 모든 non-master worktree는 루트의 `WORKSPACE_MANIFEST.md`를 포함해야 한다.
- 이 운영 메모는 Step 상태를 변경하지 않는다.

## 전체 Step 판정

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
| Step 13 | COMPLETE |
| Step 14 | COMPLETE |
| Step 15 | COMPLETE |
| Step 16 | COMPLETE |
| Step 17 | COMPLETE |
| Step 18 | COMPLETE |
| Step 19 | WAITING / not started |
| Step 20 | WAITING / not started |

## Research ingestion 범위 확장 상태

- `reserch_mvp/config/research_queries.toml`에 technical, diagnostic, Korea/APAC/EM context, hybrid split query-set 확장 metadata를 추가했다.
- `reserch_mvp/config/research_classification.toml`에 required input boundary, forbidden valuation language, 명시적 classification rule name을 추가했다.
- `reserch_mvp/config/research_scholar_discovery.toml`에 user-provided DOI seed와 seed lifecycle을 문서화했다.
- `Quant_mvp/config/research_intake.toml`은 downstream EvidenceCard intake contract만 소유한다.
- `docs/research_ingestion_expansion.md`에 source 확장 후보와 정책 검토 조건을 문서화했다.
- EvidenceCard is not a score definition.
- EvidenceCard is not an adoption decision.
- Paper-reported backtest is diagnostic metadata only.
- Citation count is metadata only, not evidence strength.
- Scholar seeds are discovery inputs only.
- PDF fulltext download is disabled by default.
- Financial/fundamental data must not enter technical_composite_score or final_composite_score.
- ranking, latest ranking, composite score, backtest, valuation/fundamental scoring은 여전히 생성하지 않는다.

## 최근 완료 Step 요약

### Step 18 = Valuation / Fundamental Expansion

- Step 18 candidate-only valuation/fundamental contracts, metric registry, validation guardrails, candidate report, architecture boundary documentation, and tests are implemented.
- `src/valuation/` defines candidate records and report helpers only; it does not create a valuation score, fundamental score, valuation-aware composite, trading signal, or ranking output.
- `config/valuation_fundamental_metrics.toml` lists allowed candidate-only metric names and keeps `technical_composite_score`, `final_composite_score`, backtest integration, alpha validation, and external network calls disabled.
- `src/validation/step18_valuation_fundamental_guardrails.py` validates candidate records, availability-date usage, candidate report notices, production-output leakage, and backtest availability boundaries.
- `docs/architecture/step18_valuation_fundamental_boundary.md` documents the separation between technical scores, candidate valuation/fundamental data, final ranking scores, and Step 17 backtest inputs.
- Latest local validation: `python -m pytest -q` = 638 passed, 4 skipped, 25 subtests passed.
- Focused Step 18 validation: `tests/valuation`, `tests/validation/test_step18_valuation_fundamental_guardrails.py`, `tests/scanner/test_step18_valuation_boundary.py`, and `tests/backtest/test_step18_backtest_boundary.py` = 31 passed.
- Related technical scoring / normalization / Step 17 validation: 149 passed.
- `review_mvp` specialist static review found no high or medium findings on Step 18 production code; remaining low style findings are non-blocking.
- Cross-Step Conflict Checkpoint passed with no blocking roadmap/order, technical composite, final composite, Step 15 ranking, Step 17 backtest, generated-output, alpha-claim, or trading-signal issue found.

### Step 17 = Conservative Backtest

- Step 17 Worker A/B conservative backtest core and guardrail branches are integrated through `integration/step17-conservative-backtest-merge`.
- `src/backtest/` implements deterministic evaluation-only backtest contracts and runner logic using frozen Step 15/16-compatible technical ranking context as read-only input.
- Step 17 output permits realized/evaluation return fields only in Step 17 result/output context and rejects those fields as upstream inputs.
- `src/validation/step17_backtest_guardrails.py` rejects valuation/fundamental, future/forward/expected return, trading recommendation, forbidden report language, and return-feedback leakage.
- `reports/backtest/README.md`, `docs/step17_conservative_backtest_core.md`, `docs/step17_backtest_guardrails.md`, and `docs/architecture/step17_backtest_boundary.md` document the evaluation-only, generated-output, no-feedback, and Step 18 valuation boundary.
- Latest local validation: `python -m pytest -q` = 607 passed, 4 skipped, 25 subtests passed.
- Focused Step 17 validation: `tests/backtest` = 18 passed; `tests/validation/test_step17_backtest_guardrails.py` = 39 passed; `tests/reports` = 68 passed; `tests/scanner tests/reports tests/validation` = 188 passed.
- `review_mvp` specialist review found no high findings; the only Step 17 medium static warning was a false positive around guarded `start_positions[0]`; remaining Step 17 findings are non-blocking style/length warnings.
- Cross-Step Conflict Checkpoint: PASS, with no roadmap/order, Step 18 valuation/fundamental leakage, trading-signal leakage, Step 15 ranking rewrite, Step 16 report rewrite, generated-output boundary break, return-feedback loop, or dirty-worktree blocker found.

### Step 16 = Security Detail Report

- Step 16 Worker A/B implementation and guardrail branches are integrated into the master integration branch.
- `src/reports/security_detail_report.py` builds deterministic per-security technical-only detail reports from the Step 15 latest ranking snapshot as read-only context.
- Step 16 output displays ticker/date, source latest ranking date, read-only rank fields, technical-only composite score context, score/component breakdowns, source/adoption metadata, diagnostics, quality flags, explanations, and an explicit `technical-only detail report` boundary notice.
- `src/validation/step16_detail_report_guardrails.py` validates Step 16 report inputs and outputs, including recursive structured-output language checks after code-review fixes.
- Step 16 does not create a new ranking, re-rank securities, run backtests, compute future/forward/realized returns, create trading recommendations, or use valuation/fundamental scoring.
- `docs/step16_security_detail_report.md`, `docs/architecture/step16_report_backtest_boundary.md`, and `reports/security/README.md` document the generated-output and Step 15 read-only boundaries.
- Latest local validation: `python -m pytest -q` = 548 passed, 4 skipped, 25 subtests passed.
- Focused Step 16 validation: `tests/reports` = 66 passed; `tests/validation/test_step16_detail_report_guardrails.py` = 37 passed; `tests/scanner tests/reports tests/validation` = 147 passed.
- `review_mvp` specialist review found no high or medium findings after required Step 16 review fixes; remaining low style/length warnings are non-blocking.
- Cross-Step Conflict Checkpoint: PASS, with no roadmap/order, Step 17 backtest leakage, Step 18 valuation/fundamental leakage, trading-signal leakage, Step 15 read-only boundary, generated-output boundary, or dirty-worktree blocker found.

### Step 15 = Latest Ranking Output

- Step 15 Worker A/B implementation and validation branches are integrated into the master integration branch.
- `src/scanner/latest_ranking.py` builds a deterministic latest-date technical ranking snapshot from Step 14 adoption synthesis material and Step 10 normalized technical score inputs.
- Step 15 output keeps `technical_composite_score` and `final_composite_score` technical-only and rejects future/performance, trading, valuation, and financial/fundamental columns.
- `src/validation/step15_latest_ranking_guardrails.py` validates Step 15 output and input-plan guardrails, including blocked-row handling.
- `docs/architecture/research_backtest_boundary_design.md` documents the one-way Step 15/16 output -> Step 17 backtest input boundary without implementing backtests.
- `scripts/Start-RoleWorktree.ps1` and `docs/workspace_parallel_work_policy.md` add lightweight role-worktree setup support without weakening Step 15+ branch separation.
- Latest local validation: `python -m pytest -q` = 434 passed, 4 skipped, 25 subtests passed.
- Focused Step 15 validation: 44 passed.
- Research ingestion focused validation: 96 passed, 4 skipped.
- `review_mvp` specialist review found no high findings; remaining medium/low findings are pre-existing static-review items or non-blocking style/length warnings after required Step 15 guardrail fix.
- Cross-Step Conflict Checkpoint: PASS, with no roadmap/order, hard-stop, valuation, future-return, backtest, generated-output, or dirty-worktree blocking issue found.

### Step 14 = Adoption Synthesis

- Step 14 adoption synthesis docs, contracts, engine, report guardrails, and tests are complete.
- Step 14 output remains adoption synthesis material only and preserves Step 13 `review_status` as `source_review_status`.
- Step 14 does not generate ranking output, latest ranking output, `technical_composite_score`, `final_composite_score`, backtest, trading signals, or valuation/fundamental scoring.
- Latest recorded local validation: `python -m pytest` = 387 passed, 4 skipped.
- Focused Step 14 / research-ingestion validation: 180 passed, 4 skipped.
- `review_mvp` specialist review: no high or medium findings on changed production code; low style findings are non-blocking.
- Cross-Step Conflict Checkpoint: PASS, with no roadmap/order, hard-stop, composite, valuation, diagnostics, or generated-output blocking issue found.

### Step 13 = Technical Selection Reviewer

- Step 13 review contract, status vocabulary, validation guardrail, reviewer engine, report builder, and generated report path/language guardrails are implemented.
- Step 13 output remains technical review recommendation material for Step 14 only.
- `review_status` values are technical recommendations, not final adoption states.
- `diagnostic_only` and context roles remain constrained to diagnostic/context recommendation paths.
- Severe redundancy or blocked candidate diagnostics cannot auto-promote to adoption.
- Generated Step 13 reports are constrained to `reports/selection/` and must include `technical selection review material only`.
- Latest recorded validation: `$env:PYTHONPATH="src"; python -m pytest` = 277 passed, 4 skipped.

### Step 12 = Redundancy / Correlation Diagnostics

- Same-date cross-sectional Spearman redundancy/correlation diagnostics are implemented for review material.
- Normalized score columns are required; raw score fallback is not allowed.
- Diagnostics remain non-alpha, non-adoption, non-ranking, non-backtest, and non-valuation material.

## 상세 이력 위치

- Full archived Step history through Step 13: `docs/roadmap_archive/step_history_through_step13.md`
- Step-specific governing docs remain source of detail, including:
  - `docs/step13_technical_selection_reviewer.md`
  - `docs/step12_redundancy_correlation_diagnostics.md`
  - `docs/step11_composite_score_design.md`
  - `docs/step10_normalization_policy.md`
  - `docs/step9_research_tester_scores.md`
  - `docs/step8_testing_normalization_protocol.md`
  - `docs/step7_indicator_layer.md`
  - `docs/step2_financial_validation_summary.md`

## Step 17 진행 / 시작 기준

- Start Step 17 only after explicit user/root assignment and a new role branch/worktree with `WORKSPACE_MANIFEST.md`.
- Use Step 15 latest ranking output and Step 16 technical-only detail reports only as frozen input context.
- Do not alter Step 15 ranking generation or Step 16 report generation while implementing Step 17.
- Do not implement valuation/fundamental scoring before Step 18.
- Do not merge financial/fundamental data into `technical_composite_score` or `final_composite_score`.

## Step 간 충돌 체크포인트

Run a Cross-Step Conflict Checkpoint whenever an important in-Step stage ends and before each Step is closed.

Required trigger examples:

- design or output contract is locked
- implementation is ready for master-up
- cross-project handoff is about to be consumed downstream
- Step-end validation has passed and code review is about to begin
- required review fixes are complete and validation is about to be rerun

Use `docs/cross_step_conflict_check.md` and generate a compact review packet with:

```powershell
python scripts/build_review_packet.py --step "<current step>" --stage "<stage name>"
```

Completed Step artifacts are trusted by default. The checkpoint checks only whether the current stage conflicts with roadmap order, hard stops, cross-project handoffs, generated-output boundaries, or unresolved carry-forward risks.

## 밸류에이션 상태

- `valuation_status = candidate_only_not_activated`
- `financial_data_usage_now = candidate_schema_and_synthetic_fixtures_only`
- `point_in_time_status = availability_date_required_for_candidate_records`; live vendor PIT availability remains unverified until separately proven.
- `financial_data_in_technical_score = false`
- `financial_data_in_final_composite_score = false`
- Step 18 candidate data remains separate from technical scoring, final ranking, and Step 17 backtest inputs.

## 활성 Guardrails

- future data 금지
- lookahead 금지
- silent score redefinition 금지
- config-first implementation
- documented score definition 전 score implementation 금지
- documented composite design 전 composite score implementation 금지
- active Step이 명시적으로 허용하기 전에는 ranking generation 금지
- Step 17 전 backtest 금지
- valuation status가 candidate-only인 동안 active valuation/fundamental scoring 금지
- financial data를 `technical_composite_score`에 넣지 않는다
- financial data를 `final_composite_score`에 넣지 않는다
- price-only evidence에 valuation language 사용 금지
