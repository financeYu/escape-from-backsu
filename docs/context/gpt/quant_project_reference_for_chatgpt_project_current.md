# Quant Project Current Context

Generated at: 2026-04-27T13:22:56+09:00
Workspace: `repository root`
Project target: `current_quant_project`
Context key: `quant_project_current_context`

This file is the only local context snapshot kept by the master workspace.
Older local snapshots managed by this script are removed during refresh.
No paid API upload is performed by this local-only workflow.

## User-Requested Context Policy

- Refresh only when the user explicitly requests this ChatGPT reference update.
- Keep latest-only local retention and exclude secrets, caches, charts, and generated data.

## Authority Order

1. User's latest explicit instruction
2. Root `AGENTS.md`
3. `docs/root_hard_stops.md`
4. `docs/roadmap_status.md`
5. `docs/project_checklist.md` for targeted root authority lookup
6. Related source, tests, docs, and config

## Current Roadmap Position

Post-MVP `v0.2 predictive probability score route` Step is open for the
approved candidate-only implementation of `prob_up_1d_candidate` in a separate
role branch/worktree. Step 20 is complete, and the KOSPI200 technical MVP v0.1
baseline is frozen.
- Current baseline: MVP v0.1 frozen KOSPI200 technical-only scanner baseline.
- Current active Step: post-MVP `v0.2 predictive probability score route`.
- Current gate: this Step authorizes only the scoped implementation of
  `prob_up_1d_candidate` feature table, label-separated training/evaluation
  pipeline, candidate probability output, and validation tests in the approved
  role branch/worktree. It does not authorize production ranking activation,
  trading recommendations, `final_composite_score` replacement, report behavior
  changes, backtest metrics as model features, valuation/fundamental data, data
- omitted 1 additional lines for compact context

## Current Baseline

- MVP universe는 KOSPI200 only다.
- `technical_composite_score`는 technical-only이며 MVP v0.1에서 `final_composite_score`와 같다.
- Valuation/fundamental data는 candidate-only이며 technical/final composite에 들어가지 않는다.
- Backtest output은 evaluation-only이며 upstream scoring/ranking에 feedback하지 않는다.
- Generated reports, runtime outputs, chart images, local caches, raw market data는 default context가 아니다.
- MVP v0.1 frozen baseline 변경은 금지한다. 이후 변경은 `v0.2+` 또는 별도
- omitted 1 additional lines for compact context

## Cross-Step Conflict Checkpoint

- Run `docs/cross_step_conflict_check.md` when a gate-critical stage ends or a Step closes.
- Use `scripts/build_review_packet.py` for compact review input.

## Active Guardrails

- KOSDAQ150, futures, options, Nasdaq/overseas, or multi-universe activation.
- New market-data ingestion or live vendor assumptions.
- Runtime score formula, weight, adoption, normalization, ranking, report,
  backtest, or valuation semantic changes outside the approved
  `prob_up_1d_candidate` candidate-only implementation scope.

[Context truncated by `max_chars`; consult repository docs for full detail.]
