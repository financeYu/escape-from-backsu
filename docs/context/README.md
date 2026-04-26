# Context Operating Notes

`docs/context/` exists to keep future Codex workers from re-reading the full
repository history for every task.

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

- `current_context.md`: latest-only default-read context.
- `active_step20_packet.md`: Step 20 final-validation routing packet.
- `context_usage_policy.md`: answer and archive-read rules for fresh reasoning.
- `context_index.md`: compact map of context files and when to read them.
- `context_routing.md`: task-based routing matrix for Step 20+ review and planning work.
- `context_budget_policy.md`: budget rules for packets and review inputs.
- `decision_log.md`: changed context-routing decisions only, not full history.
- `domain/`: lightweight domain stubs that link to canonical docs instead of duplicating them.
- `archive/`: completed-Step summaries that are not default-read context.
- `generated/`: packet examples or future generated packet outputs. Do not treat generated packets as authority overrides.

## Tooling

- `scripts/context/build_context_packet.py`: builds a compact routed packet for a task.
- `scripts/context/check_context_staleness.py`: warns about obvious roadmap/checklist/context packet mismatches.
- `scripts/context/check_context_conflicts.py`: flags suspicious forbidden claims in context docs.

## Step20+ Boundary

Step 20 is complete and the KOSPI200 technical MVP v0.1 is freeze-ready. Future
work must treat Step 20 release evidence as completed provenance unless the user
explicitly asks for a regression, conflict, or post-MVP expansion review.

This context layer is routing/support only. It must not implement missing domain
behavior, change quant logic, scoring, ranking, reports, backtests, valuation
logic, or data ingestion outside a separately approved post-MVP Step.

Future workers should separate confirmed context facts from new reasoning and
avoid repeating completed Step summaries unless the user asks for historical detail.
