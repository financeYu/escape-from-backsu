# Quant Project Current Context

Generated at: 2026-04-25T17:53:28+09:00
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

Step 16 = 종목별 상세 리포트 구현, WAITING / branch setup required
- Recently completed: Step 15 = 최신 랭킹 출력 구현, COMPLETE
- Recently completed before that: Step 14 = Adoption Synthesis, COMPLETE
- Carry-forward: Step 2 PIT financial availability follow-up is assigned to Step 18, not Step 9/10/11/12/13/14/15/16 technical work.
- Current gate: Step 16 must start from a new role branch/worktree with `WORKSPACE_MANIFEST.md` before file edits.
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
| Step 16 | WAITING / branch setup required |
| Step 17 | WAITING / not started |
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
python scripts/build_review_packet.py --step "Step 14" --stage "<stage name>"
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
| `trading_activity_variability_penalty` | diagnostic backlog | risk/liquidity context, not first-pass ranking alpha |

## Family Map Snapshot

| `mean_reversion` | `short_term_overreaction`, `atr_adjusted_oversold_distance` | `technical` | reversal candidates | high within family | implement both only if diagnostics compare distinctness |
| `breakout` | `donchian_breakout_distance` | `technical` | continuation candidate | high with trend ideas | keep one simple breakout definition first |
| `squeeze_expansion` | `bollinger_width_squeeze` | `technical` | setup/regime candidate | medium with volatility diagnostics | report as conditional context unless review supports ranking use |
| `flow` | `cmf_confirmation` | `technical` | volume confirmation | medium with liquidity diagnostics | define whether standalone or interaction before coding |
| `oscillator_divergence` | `rsi_price_divergence` | `technical` | cautious reversal proxy | medium-high with mean reversion | use deterministic proxy only |
| `volatility_regime` | `realized_vol_percentile` | `diagnostic` | risk/regime context | medium with squeeze and ATR scores | keep out of direct alpha ranking until reviewed |
| `trend_efficiency` | `efficiency_ratio_trend` | `technical` | cleaner trend candidate | medium with breakout | signed versus unsigned role must be fixed |
| Short-term reversal cluster | `short_term_overreaction`, `atr_adjusted_oversold_distance`, `rsi_price_divergence` | compare correlation, rank overlap, warmup coverage, and trigger sparsity; downgrade duplicates |
| Trend and breakout cluster | `donchian_breakout_distance`, `efficiency_ratio_trend`, folded relative-strength ideas | do not add 52-week high, moving-average trend, and medium-term return variants until distinctness is shown |
| Volatility context cluster | `bollinger_width_squeeze`, `realized_vol_percentile`, ATR scaling | keep setup/regime diagnostics separate from direct ranking signals |
| Volume and activity cluster | `cmf_confirmation`, folded volume participation ideas, folded trading activity variability | avoid strict turnover unless shares outstanding becomes point-in-time safe and explicitly allowed |

## Git Snapshot

- branch: `integration/step15-a-b-merge`
- commit: `0a2e054`
- status:
```text
clean
```

[Context truncated by `max_chars`; consult repository docs for full detail.]
