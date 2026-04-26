# Context Operating Notes

`docs/context/` exists to keep future Codex workers from re-reading the full repository history for every task.

This directory separates:

- current-state routing notes
- domain context summaries
- contract and boundary references
- sample or generated context packets
- archive/history references that should not be loaded by default

This directory does not replace the authority chain:

1. user's latest explicit instruction
2. `AGENTS.md`
3. `docs/project_checklist.md`
4. `docs/roadmap_status.md`
5. affected project `AGENTS.md`, source, tests, docs, and config

Context docs are routing aids. They are not permission to bypass roadmap order, Step gates, root/worktree boundaries, valuation guardrails, generated-output policy, or Cross-Step Conflict Checkpoints.

## Directory Layout

- `context_index.md`: compact map of context files and when to read them.
- `context_routing.md`: task-based routing matrix for Step 19+ work.
- `context_budget_policy.md`: budget rules for packets and review inputs.
- `domain/`: lightweight domain stubs that link to canonical docs instead of duplicating them.
- `generated/`: packet examples or future generated packet outputs. Do not treat generated packets as authority overrides.

## Tooling

- `scripts/context/build_context_packet.py`: builds a compact routed packet for a task.
- `scripts/context/check_context_staleness.py`: warns about obvious roadmap/checklist/context packet mismatches.
- `scripts/context/check_context_conflicts.py`: flags suspicious forbidden claims in context docs.

## Pre-Step19 Boundary

This Pre-Step19 context-routing work is planning/support only. It must not start Step 19 implementation, automatic execution, new market-data ingestion, KOSDAQ150 expansion, futures/options work, ranking/scoring/backtest changes, valuation scoring, or report semantic changes.
