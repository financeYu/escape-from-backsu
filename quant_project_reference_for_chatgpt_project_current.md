# Quant Project Current Context

Generated at: 2026-04-27T00:01:55+09:00
Workspace: `repository root`
Project target: `current_quant_project`
Context key: `quant_project_current_context`

This file is the only local context snapshot kept by the master workspace.
Older local snapshots managed by this script are removed during refresh.
No paid API upload is performed by this local-only workflow.

## Authority Order

1. User's latest explicit instruction
2. Root `AGENTS.md`
3. `docs/root_hard_stops.md`
4. `docs/roadmap_status.md`
5. `docs/project_checklist.md` for targeted root authority lookup
6. Related source, tests, docs, and config

## Current Roadmap Position

No active roadmap Step is in progress. Step 20 is complete, and the KOSPI200
technical MVP v0.1 baseline is freeze-ready.
- Current baseline: Step 20 completed KOSPI200 MVP completeness hardening and final Done validation.
- Current gate: future expansion needs a separately approved post-MVP Step, routed context packet, correct role branch/worktree, and conflict checkpoint when required.

## Current Baseline

- MVP universe는 KOSPI200 only다.
- `technical_composite_score`는 technical-only이며 MVP v0.1에서 `final_composite_score`와 같다.
- Valuation/fundamental data는 candidate-only이며 technical/final composite에 들어가지 않는다.
- Backtest output은 evaluation-only이며 upstream scoring/ranking에 feedback하지 않는다.
- Generated reports, runtime outputs, chart images, local caches, raw market data는 default context가 아니다.

## Cross-Step Conflict Checkpoint

- Run `docs/cross_step_conflict_check.md` when a gate-critical stage ends or a Step closes.
- Use `scripts/build_review_packet.py` for compact review input.

## Active Guardrails

- KOSDAQ150, futures, options, Nasdaq/overseas, or multi-universe activation.
- New market-data ingestion or live vendor assumptions.
- Score formula, weight, adoption, normalization, ranking, report, backtest, or valuation semantic changes.
- Financial/fundamental data in `technical_composite_score` or
  `final_composite_score`.
- Backtest feedback into scoring/ranking.
- Trading recommendations, buy/sell/hold, proven-alpha, or expected-return wording.

## Step-End Context Policy

- Refresh after Step-end validation, review, required fixes, rerun, and commit.
- Keep latest-only local retention and exclude secrets, caches, charts, and generated data.

## Route-Only References

- Root compact hard stops: `docs/root_hard_stops.md`.
- Current roadmap status: `docs/roadmap_status.md`.
- MVP baseline: `docs/context/MVP_V0_1_BASELINE.md`.
- MVP contracts: `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml`.
- Quant agent scope: `Quant_mvp/AGENTS.md`.
- Score catalog: `Quant_mvp/docs/score_catalog.md` (on-demand only; not embedded).
- Family map: `Quant_mvp/docs/family_map.md` (on-demand only; not embedded).
- Archive lookup: `docs/context/ARCHIVE_INDEX.md`.
