# Quant Project Current Context

Generated at: 2026-04-26T20:11:43+09:00
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

Step 20 = KOSPI200 MVP Completeness Hardening & Final Done Validation, COMPLETE / KOSPI200 technical MVP v0.1 freeze-ready
- Active: no in-progress roadmap Step.
- Current baseline: Step 20 completed KOSPI200 MVP completeness hardening and final Done validation.
- Current gate: future expansion needs a separately approved post-MVP Step, routed context packet, correct role branch/worktree, and conflict checkpoint when required.
## 컨텍스트 운영 상태
- 기본 시작점: `docs/context/current_context.md`, `docs/context/MVP_V0_1_BASELINE.md`, active packet 1개.
- Targeted lookup: `docs/context/CONTEXT_ROUTING_INDEX.md`와 필요한 domain stub만 사용한다.
- Archive lookup: conflict, regression, provenance, release-evidence 확인이 있을 때만 가장 좁은 파일을 읽는다.
- 답변과 handoff는 confirmed context fact를 최대 3개만 반복하고 현재 판단, 변경, 검증, 남은 리스크를 중심으로 작성한다.
- 완료 Step 1-20 산출물은 기본적으로 신뢰한다.
## 병렬 Workspace 운영 메모
- Step 14 이후 병렬 구현, review, research ingestion, audit/scope watchdog, master integration 작업은 `docs/workspace_parallel_work_policy.md`를 따른다.
- omitted 4 additional lines for compact context

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
| Step 18 | COMPLETE |
| Step 19 | COMPLETE |
| Step 20 | COMPLETE / KOSPI200 MVP Completeness Hardening & Final Done Validation |
## 현재 Baseline 핵심
- MVP universe는 KOSPI200 only다.
- `technical_composite_score`는 technical-only이며 MVP v0.1에서 `final_composite_score`와 같다.
- Valuation/fundamental data는 candidate-only이며 technical/final composite에 들어가지 않는다.
- Backtest output은 evaluation-only이며 upstream scoring/ranking에 feedback하지 않는다.
- Generated reports, runtime outputs, chart images, local caches, raw market data는 default context가 아니다.
- omitted 41 additional lines for compact context

## Most Recent Completed Step

- unavailable

## Cross-Step Conflict Checkpoint

Run a Cross-Step Conflict Checkpoint whenever an important in-Step stage ends and before each Step is closed.
Use `docs/cross_step_conflict_check.md` and generate a compact review packet with:
```powershell
python scripts/build_review_packet.py --step "<current step>" --stage "<stage name>"
```
Completed Step artifacts are trusted by default. The checkpoint checks only whether the current stage conflicts with roadmap order, hard stops, cross-project handoffs, generated-output boundaries, context-routing boundaries, or unresolved carry-forward risks.

## Active Guardrails

- score definition 전에는 score implementation 금지.
- documented composite design 전에는 composite score implementation 금지.
- Step 17 전에는 backtest 금지.
- financial data를 `technical_composite_score`에 넣지 않는다.
- financial data를 `final_composite_score`에 넣지 않는다.
- price-only evidence에 valuation language를 쓰지 않는다.
- valuation status가 candidate-only인 동안 active valuation/fundamental scoring을 하지 않는다.
- active Step이 명시적으로 허용하기 전에는 ranking generation을 하지 않는다.

## Git Snapshot

- branch: `codex/master-up-post20-pending`
- commit: `c7d1b59`
- status:
```text
clean
```

## Step-End Context Policy

- Refresh this file after Step-end validation, review, required fixes, rerun, and commit.
- Keep latest-only local retention: remove obsolete local context files listed in config.
- Do not include `.env`, API keys, local runtime caches, chart images, generated data caches, or secrets.

## Next Allowed Work

- Follow `docs/roadmap_status.md` and `docs/project_checklist.md` before starting the next Step.

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
