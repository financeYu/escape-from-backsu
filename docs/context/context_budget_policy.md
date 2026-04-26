# Context Budget Policy

Context packets should be small enough that future workers can act without reloading the full project history.

## Budget Rules

- Implementation worker packets should be compact and task-specific.
- Audit and review packets may be larger when they need boundary evidence, but they should still avoid full archive dumps.
- Archive files are not included by default.
- Generated data, caches, secrets, images, local runtime outputs, and large raw reports must never be embedded in packets.
- Current state summary and historical details must stay separated.
- Completed Step artifacts are trusted by default unless current changes touch their boundary.
- Packets should list required and optional files rather than copying large file contents.
- If a file is missing, the packet or handoff should report the missing file instead of silently ignoring it.

## Staleness Rules

A context packet is stale when it contradicts `docs/roadmap_status.md`, `docs/project_checklist.md`, the active `WORKSPACE_MANIFEST.md`, or the latest user instruction.

Prefer warning over hard failure for ambiguous staleness. Treat direct contradictions as blockers before implementation or Step-end closure.

## Forbidden Packet Content

Do not embed:

- `.env`, secrets, API keys, credentials, local tokens
- generated chart images or runtime scan outputs
- daily price caches or raw market data caches
- large research dumps or PDF full text
- old generated review packets unless explicitly requested for a narrow historical question
