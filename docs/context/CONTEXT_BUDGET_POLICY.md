# Context Budget Policy

This policy is a routing aid, not an authority document. It keeps the post-Step20
baseline small enough for future work to start without re-reading completed Step
history.

## Default Prompt Context

Default prompt context after Step 20 consists of:

1. `docs/context/MVP_V0_1_BASELINE.md`
2. exactly one active packet, currently
   `docs/context/ACTIVE_PREFREEZE_OPTIMIZATION_PACKET.md`
3. optional routing index: `docs/context/CONTEXT_ROUTING_INDEX.md`

Authority files still govern through `AGENTS.md`, `docs/project_checklist.md`,
and `docs/roadmap_status.md`; default packets should link to them rather than
copying their bodies.

## Archive-Only Context

- Completed Step 1-20 history is archive-only.
- Full validation logs are archive-only.
- Score catalog dumps are not default context.
- Old generated packets, review packets, runtime reports, chart images, market
  caches, and scan outputs are not default context.

## Archive Lookup Gate

Archive lookup is allowed only for:

- conflict investigation
- regression investigation
- provenance check
- release/freeze verification

When archive lookup is needed, name the reason, read the narrowest file, and do
not paste archive bodies into active packets or ordinary planning answers.

## Planning Answer Budget

- Ordinary planning answers should repeat no more than 3 confirmed context facts.
- After those facts, move to current reasoning, tradeoffs, risks, or action.
- Completed Step outputs are trusted by default unless a named investigation
  requires targeted archive lookup.

## Active Packet Rule

- Future extension work must create a small active packet instead of expanding
  `MVP_V0_1_BASELINE.md`.
- The baseline should stay stable across tasks and should not absorb feature
  plans, validation logs, score catalogs, or Step history.
- At most one active packet should be treated as default context for a task.

## Packet Content Rules

- Packets should list file paths and short purpose notes.
- Packets must not embed large source files, generated outputs, caches, secrets,
  raw market data, or full release validation logs.
- If a file is missing, report the missing file instead of silently ignoring it.
