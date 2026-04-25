# Quant Project Current Context

Generated at: 2026-04-25T15:37:03+09:00
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

Step 14 = Adoption Synthesis, NEXT / not started
- Recently completed: Step 13 = Technical Selection Reviewer, COMPLETE
- Recently completed before that: Step 12 = redundancy / correlation diagnostics, COMPLETE
- Carry-forward: Step 2 PIT financial availability follow-up is assigned to Step 18, not Step 9/10/11/12/13/14 technical work.

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
| Step 14 | NEXT / not started |
| Step 15 | WAITING / not started |
| Step 16 | WAITING / not started |
| Step 17 | WAITING / not started |
| Step 18 | DEFERRED / waiting for valuation expansion |
| Step 19 | WAITING / not started |
| Step 20 | WAITING / not started |
## Research ingestion 범위 확장 상태
- `Quant_mvp/config/research_queries.toml`에 technical, diagnostic, Korea/APAC/EM context, hybrid split query-set 확장 metadata를 추가했다.
- `Quant_mvp/config/research_classification.toml`에 required input boundary, forbidden valuation language, 명시적 classification rule name을 추가했다.
- `Quant_mvp/config/research_scholar_discovery.toml`에 user-provided DOI seed와 seed lifecycle을 문서화했다.
- `docs/research_ingestion_expansion.md`에 source 확장 후보와 정책 검토 조건을 문서화했다.
- EvidenceCard is not a score definition.
- omitted 7 additional lines for compact context

## Most Recent Completed Step

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

- branch: `step12-diagnostics`
- commit: `d3752c9`
- status:
```text
clean
```

## Step-End Context Policy

- Refresh this file after Step-end validation, review, required fixes, rerun, and commit.
- Keep latest-only local retention: remove obsolete local context files listed in config.
- Do not include `.env`, API keys, local runtime caches, chart images, generated data caches, or secrets.

## Next Allowed Work

- Step 14 Adoption Synthesis is the next active roadmap step.
- Step 15 ranking, Step 17 backtest, and Step 18 valuation/fundamental scoring remain gated.
