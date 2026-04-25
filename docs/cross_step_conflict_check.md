# Cross-Step Conflict Checkpoint

## Purpose

This checkpoint keeps important in-Step milestones from drifting into later roadmap behavior before the project is ready.

It is a compact conflict check, not a full re-review of every completed Step. Completed Step outputs are trusted unless the current change touches them, consumes them downstream, or appears to violate a hard stop.

## When To Run

Run this checkpoint whenever an important in-Step stage ends, including:

- design or output contract lock
- implementation ready for master-up
- cross-project handoff ready to be consumed
- Step-end integration validation passed
- required review fixes completed before validation rerun
- user explicitly asks for all-Step conflict validation

## Inputs

- `docs/roadmap_status.md`
- `docs/project_checklist.md`
- current diff or changed-file manifest
- affected subproject `AGENTS.md`
- master-up summary or local review summary
- generated review packet from `scripts/build_review_packet.py`

## Checks

| Check | Question | Blocking examples |
| --- | --- | --- |
| Roadmap order | Does this stage implement behavior before its allowed Step? | Step 15 ranking before Step 15, Step 17 backtest before Step 17 |
| Hard stops | Does this stage violate active guardrails? | lookahead, future data, silent score redefinition |
| Score/composite boundary | Does this stage turn design/review material into production output too early? | `technical_composite_score` before allowed implementation |
| Valuation boundary | Does financial/fundamental data enter technical or final composite outputs? | PER/PBR/ROE used in technical score or final composite |
| Diagnostics boundary | Are diagnostics described as alpha, adoption evidence, ranking, or valuation verdicts? | Step 12/13 diagnostic output treated as signal |
| Handoff consistency | Does the downstream consumer match the upstream contract? | Step 14 consuming Step 13 statuses as final adoption states |
| Generated-output boundary | Are runtime reports, caches, charts, or scan outputs excluded unless promoted as fixtures? | committing generated reports outside documented fixture paths |
| Dirty worktree isolation | Are owned files separated from unrelated dirty files? | mixed unrelated edits in the planned commit |

## Output

Record the checkpoint in the review packet or master-up summary:

```text
[Cross-Step Conflict Checkpoint]
- trigger:
- roadmap/order:
- hard stops:
- score/composite boundary:
- valuation boundary:
- diagnostics boundary:
- handoff consistency:
- generated-output boundary:
- dirty worktree isolation:
- verdict: PASS / WARNING / BLOCKING_ISSUE / NEEDS_CLARIFICATION
- required follow-up:
```

`BLOCKING_ISSUE` must be fixed before the stage is treated as complete. `WARNING` may proceed only when copied into master-up or Step-end risk notes.
