# Quant Project Current Context

Generated at: 2026-04-25T21:09:01+09:00
Workspace: `repository root`
Project target: `current_quant_project`
Context key: `quant_project_current_context`

This file is the only local context snapshot kept by the master workspace.
Older local snapshots managed by this script are removed during refresh.
No paid API upload is performed by this local-only workflow.

## Authority Order

1. User's latest explicit instruction
2. Root `AGENTS.md`
3. `docs/project_checklist.md`
4. `docs/roadmap_status.md`
5. Related source, tests, docs, and config

## Current Roadmap Position

Step 18 = 밸류에이션 확장 준비, DEFERRED / waiting for valuation expansion
- Recently completed: Step 17 = 보수적 백테스트, COMPLETE
- Recently completed before that: Step 16 = 종목별 상세 리포트 구현, COMPLETE
- Carry-forward: Step 2 PIT financial availability follow-up is assigned to Step 18, not Step 9/10/11/12/13/14/15/16/17 technical or backtest work.
- Current gate: Step 18 valuation/fundamental expansion remains deferred and must not start without explicit user/root assignment and PIT financial-data boundary validation.
## 병렬 Workspace 운영 메모
- Step 14 이후 병렬 구현, review, research ingestion, audit/scope watchdog, master integration 작업은 `docs/workspace_parallel_work_policy.md`를 따른다.
- Step 15부터는 Step implementation, Quant score/governance, research ingestion, chart runtime, review, audit/scope watchdog, master integration을 별도 branch/worktree로 분리하는 Step 15+ Branch Separation Process가 필수다.
- Step implementation은 major Step branch(`codex/stepXX-<scope>`)에서만 진행하고, Quant/research/review/audit/chart 작업은 minor/support branch(`quant/`, `research/`, `review/`, `audit/`, `chart/`)에서 분리한다.
- 모든 하위 에이전트는 파일 편집 전에 role branch/worktree를 만들거나 선택하고 루트 `WORKSPACE_MANIFEST.md`를 작성해야 한다.
- `C:\Users\jjaew\Project\master_mvp`는 integration / verification / status-control 전용 workspace로 유지한다.
- 모든 non-master worktree는 루트의 `WORKSPACE_MANIFEST.md`를 포함해야 한다.
- omitted 1 additional lines for compact context

## Roadmap Verdicts

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
| Step 18 | DEFERRED / waiting for valuation expansion |
| Step 19 | WAITING / not started |
| Step 20 | WAITING / not started |
## Research ingestion 범위 확장 상태
- `reserch_mvp/config/research_queries.toml`에 technical, diagnostic, Korea/APAC/EM context, hybrid split query-set 확장 metadata를 추가했다.
- `reserch_mvp/config/research_classification.toml`에 required input boundary, forbidden valuation language, 명시적 classification rule name을 추가했다.
- `reserch_mvp/config/research_scholar_discovery.toml`에 user-provided DOI seed와 seed lifecycle을 문서화했다.
- `Quant_mvp/config/research_intake.toml`은 downstream EvidenceCard intake contract만 소유한다.
- `docs/research_ingestion_expansion.md`에 source 확장 후보와 정책 검토 조건을 문서화했다.
- omitted 8 additional lines for compact context

## Most Recent Completed Step

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
- omitted 21 additional lines for compact context

## Cross-Step Conflict Checkpoint

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

## Active Guardrails

- score definition 전에는 score implementation 금지.
- documented composite design 전에는 composite score implementation 금지.
- Step 17 전에는 backtest 금지.
- financial data를 `technical_composite_score`에 넣지 않는다.
- financial data를 `final_composite_score`에 넣지 않는다.
- price-only evidence에 valuation language를 쓰지 않는다.
- valuation status가 deferred인 동안 valuation/fundamental scoring을 하지 않는다.
- active Step이 명시적으로 허용하기 전에는 ranking generation을 하지 않는다.

## Git Snapshot

- branch: `integration/step16-detail-report-merge`
- commit: `f3fa3dc`
- status:
```text
clean
```

## Step-End Context Policy

- Refresh this file after Step-end validation, review, required fixes, rerun, and commit.
- Keep latest-only local retention: remove obsolete local context files listed in config.
- Do not include `.env`, API keys, local runtime caches, chart images, generated data caches, or secrets.

## Next Allowed Work

- Step 17 conservative backtest is the next roadmap step.
- Start Step 17 from a new role branch/worktree with `WORKSPACE_MANIFEST.md` before file edits.
- Step 18 valuation/fundamental scoring remains gated.

## Quant Agent Scope

This repository uses Codex as a **multi-agent conservative quant engineering system** for a **KOSPI200 constituent-level stock scanner**.
The main objective is to build an **explainable, modular, backtest-friendly technical multi-score engine** that ranks KOSPI200 constituent stocks using:
- daily OHLCV-derived technical/statistical signals
- explicit regime, diagnostic, and composite scoring logic
This is **not** a single-strategy repository.
This is **not** an "AI black box alpha" repository.
Valuation / fundamental review is handled by a separate agent, not by this main technical agent.
The goal is to:
1. define candidate scores clearly
2. implement and test them conservatively
3. compare them from a technical usefulness, stability, and redundancy perspective
4. adopt only the strongest and most defensible technical score set
Prioritize:
1. implementation realism
2. rule clarity
3. explainability
4. robustness over novelty
5. modularity and diagnostics
6. conservative rejection of weak or ambiguous ideas
When uncertain, do **not** resolve ambiguity optimistically.
Prefer explicit downgrades, deferrals, or narrower implementations.
---

## Quant Adoption Synthesis Policy

A candidate score or score family should be assigned one of the following final states:
- `core_adopted`
- `conditional_adopted`
- `technical_only`
- `regime_only`
- `diagnostic_only`
- `research_only`
- `rejected`
- `blocked_by_data`

## Score Catalog Snapshot

| `short_term_overreaction` | `mean_reversion` | `technical` | core candidate | define for MVP testing | Korea reversal evidence plus short-horizon reversal literature |
| `atr_adjusted_oversold_distance` | `mean_reversion` | `technical` | robustness variant | define for MVP testing with redundancy warning | volatility-scaled oversold proxy |
| `donchian_breakout_distance` | `breakout` | `technical` | core candidate | define for MVP testing | trading range breakout evidence |
| `bollinger_width_squeeze` | `squeeze_expansion` | `technical` | regime/conditional candidate | define for MVP testing as technical-only context | volatility compression and expansion setup |
| `cmf_confirmation` | `flow` | `technical` | confirmation candidate | define for MVP testing | price-volume participation evidence |
| `rsi_price_divergence` | `oscillator_divergence` | `technical` | cautious pattern proxy | define only as deterministic proxy | oscillator divergence, with pattern-mining warning |
| `realized_vol_percentile` | `volatility_regime` | `diagnostic` | regime diagnostic | keep out of direct alpha ranking until reviewed | risk/regime context and testing discipline |
| `efficiency_ratio_trend` | `trend_efficiency` | `technical` | distinctness candidate | define for MVP testing | smooth-trend versus noisy-trend proxy |
| `medium_term_relative_strength` | folded into trend/breakout review queue | Korea evidence is mixed and overlap with breakout, 52-week high, and trend return is high |
| `moving_average_trend_structure` | folded into `efficiency_ratio_trend` or later trend review | high overlap with breakout and relative strength |
| `price_near_52w_high` | folded into `donchian_breakout_distance` as longer-window alternative | concept is useful but redundant in first MVP set |
| `time_series_trend_return` | folded into `efficiency_ratio_trend` review | too close to relative strength unless separate use is proven later |
| `volume_participation_momentum_filter` | future conditional filter / diagnostic backlog | strict turnover may require shares outstanding; OHLCV proxy needs review |

[Context truncated by `max_chars`; consult repository docs for full detail.]
