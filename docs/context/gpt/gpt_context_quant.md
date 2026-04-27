# Quant Project Current Context

Status: routing aid, not an authority document.
Generated only after an explicit user request with a non-empty request string.

This file is the only local context snapshot kept by the master workspace.
Older local snapshots managed by this script are removed during refresh.
No paid API upload is performed by this local-only workflow.

- Step 20 is complete; KOSPI200 technical MVP v0.1 is frozen.
- MVP v0.1 is KOSPI200-only and technical-only.
- Valuation/fundamental scoring, KOSDAQ150, futures/options, Nasdaq, and trading recommendation work remain outside the baseline unless a later routed task opens them.

1. User's latest explicit instruction
2. Root `AGENTS.md`
3. `docs/root_hard_stops.md`
4. `docs/roadmap_status.md`
5. `docs/project_checklist.md` for targeted root authority lookup
6. Related source, tests, docs, and config

- Task: gpt 폴더에 있는 두 GPT-facing context 파일을 모두 갱신하고, 명시 요청이 있을 때만 갱신되도록 생성 guard를 점검/수정
- Decision needed: focus on the current request, not old roadmap narration.

No active roadmap Step is in progress. Step 20 is complete, and the KOSPI200
technical MVP v0.1 baseline is freeze-ready.
- Current baseline: Step 20 completed KOSPI200 MVP completeness hardening and final Done validation.
- Current gate: future expansion needs a separately approved post-MVP Step, routed context packet, correct role branch/worktree, and conflict checkpoint when required.

## Current Baseline

## Boundaries

- No quant logic, score formula, ranking behavior, report behavior, backtest behavior, valuation/fundamental activation, data ingestion, or trading language changes unless explicitly requested and allowed.
- Do not implement KOSDAQ150, futures/options, or Nasdaq from this brief.
- Completed Step 1-20 history is archive-only. Full validation logs are archive-only. Full score catalog is not default context.
- Internal generation rules, budget policy, and routing index are not GPT prompt inputs.

## Route-Only References

- `docs/context/MVP_V0_1_BASELINE.md` - FOUND
- add task-specific file paths only when needed

## Missing Referenced Files

- none
