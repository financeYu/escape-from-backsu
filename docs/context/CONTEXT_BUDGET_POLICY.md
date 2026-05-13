# Context Budget Policy

This policy is a routing aid, not an authority document. It keeps the post-Step20
baseline small enough for future work to start without re-reading completed Step
history.

## Default Prompt Context

Default prompt context after Step 20 consists of:

1. `docs/context/MVP_V0_1_BASELINE.md`
2. `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml`
3. `docs/context/EXTENSION_REGISTRY.toml`
4. `docs/context/CHANGE_IMPACT_MATRIX.yml`
5. exactly one active packet, task-specific, when a task needs one
6. optional routing index: `docs/context/CONTEXT_ROUTING_INDEX.md`

Authority files still govern through `AGENTS.md`, `docs/project_checklist.md`,
and `docs/roadmap_status.md`; default packets should link to them rather than
copying their bodies.

## Codex Task Start Context

Codex workers must not read the full repository history at task start. Default
local task context is limited to:

1. current state and hard stops from the root authority files
2. the affected subproject `AGENTS.md`
3. exactly one active context packet
4. one needed domain context stub
5. targeted source, test, config, or docs files in the change scope

Completed Step 1-20 outputs are trusted by default. Read archive or older Step
detail only for a named conflict, regression, provenance, or release-evidence
check, and then read the narrowest file needed.

## Archive-Only Context

- Completed Step 1-20 history is archive-only.
- Archive lookup starts from `docs/context/ARCHIVE_INDEX.md`.
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

## Handoff Context Limit

- Handoffs and ordinary answers may include at most 3 confirmed context facts.
- After confirmed facts, focus on current judgment, changes, validation, and
  remaining risks.
- Do not repeat completed Step history unless the user asks for historical
  detail or a permitted archive lookup requires it.

## GPT-Facing Context Budget

Default GPT input = one generated brief only: `docs/context/gpt/gpt_context_quant.md`.

The generated brief is assembled from compact baseline facts plus one active
request packet. This budget policy, `docs/context/GPT_CONTEXT_GENERATION_RULES.md`,
and `docs/context/CONTEXT_ROUTING_INDEX.md` are internal rules and routing aids.
Do not paste those internal files into GPT by default.
Generate GPT submission context directly at `docs/context/gpt/gpt_context_quant.md`.
Do not refresh GPT-folder outputs unless the user explicitly requests a GPT or
ChatGPT context update.
Use `.agents/skills/gpt-context-refresh/SKILL.md` for that explicit refresh
workflow. GPT-facing output must describe v0.3 research-to-strategy adoption
and post-v1.0 v1.x staged release development as active routes, with v1.1 as
the current net profitability evidence runner stage, while keeping v0.1 frozen
and v0.2 archived/supporting.

Rules:

- Default GPT context max 80 lines.
- Active task packet max 120 lines.
- Ordinary planning context may include at most 3 confirmed context facts.
- GPT receives the generated brief, not the internal rules files.
- No Step-by-Step roadmap table in GPT default context.
- No repeated Step completion summaries.
- No pasted old validation logs.
- No full score catalog.
- No long guardrail prose copied from older context.
- Route to file paths instead of embedding file bodies.
- Completed Step 1-20 history is archive-only.
- Full validation logs are archive-only.
- Full score catalog material is archive-only.

GPT briefs must include:

```text
Do not repeat completed Step history. Use the baseline as trusted context and focus on the current decision.
```
