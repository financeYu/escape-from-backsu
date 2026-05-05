---
name: gpt-context-refresh
description: Use when the user explicitly requests GPT or ChatGPT context refreshes for master_mvp. Keeps GPT-facing context local-only, latest-only, v0.3-aligned, and separated from authority docs, archives, generated data, raw data, caches, charts, and secrets.
---

# GPT Context Refresh

## Purpose

Refresh GPT-facing local context artifacts only after an explicit user request.
This skill governs context refresh workflow only. It does not authorize quant
logic, score semantics, ranking or report behavior, backtest behavior, data
ingestion, universe expansion, live trading, production activation, valuation
activation, Git remote work, staging, or commits.

The current active route is post-MVP v0.3 research-to-strategy adoption. GPT
context must treat v0.1 as a frozen KOSPI200 technical baseline and v0.2
`prob_up_1d_candidate` as archived/supporting compatibility only.

## Required Root Packet

Before refreshing GPT-facing context, root must provide or reconstruct:

- current user request text
- classification: `narrow edit` for refresh output changes
- selected architecture gate: `agent-replacement` when skill/context ownership
  is being updated, otherwise the active architecture chain
- selected domain compatibility gate: `gpt-context-refresh`
- allowed scope:
  - `.agents/skills/gpt-context-refresh/SKILL.md`
  - `docs/context/gpt/`
  - `docs/context/GPT_CONTEXT_GENERATION_RULES.md`
  - `docs/context/CONTEXT_BUDGET_POLICY.md`
  - `scripts/context/build_context_packet.py`
  - `scripts/context/refresh_gpt_references.py`
  - `scripts/refresh_quant_project_context.py`
  - `tests/context/`
- forbidden scope:
  - archives, generated output dumps, raw data, caches, charts, logs, `.env`,
    and secrets
  - v0.1/v0.2 archive body reads unless a named provenance, regression,
    compatibility, or release/freeze check requires them
  - quant logic, scoring, ranking, reporting, backtest, ingestion, trading, or
    production activation behavior
- validation commands
- Korean final report format
- Git policy: `fetch=false`, `pull=false`, `push=false`, `commit=false`,
  `stage=false`

## Workflow

1. Read only `docs/root_hard_stops.md`, `docs/roadmap_status.md`, this skill,
   and targeted context refresh files.
2. Verify that the user explicitly requested a GPT or ChatGPT context update.
3. Update generator rules before manually editing generated GPT-facing output.
4. Refresh both GPT-facing files together with:

```powershell
.venv\Scripts\python.exe scripts\context\refresh_gpt_references.py --user-requested --request "<active request>"
```

5. Keep the generated brief under 80 lines with at most 3 confirmed context
   facts.
6. Ensure GPT-facing output routes to file paths instead of embedding source
   bodies, archive history, validation logs, full score catalog content, raw
   data, charts, or secrets.
7. Run focused context tests and `git diff --check`.
8. Finish through `quant-review-gate` before accepting completion.

## Output Requirements

GPT-facing context must state:

- it is a routing aid, not an authority document
- v0.3 research-to-strategy adoption is the active route
- v0.1 is frozen baseline and v0.2 is archived/supporting compatibility only
- the current request and decision needed now
- hard stops and forbidden activation boundaries
- route-only references for deeper lookup

It must not state that v0.2 is the active route unless the user explicitly asks
for an archived/supporting probability compatibility check.

## Validation

Run the narrowest useful checks:

```powershell
.venv\Scripts\python.exe .agents/skills/gpt-context-refresh/scripts/validate_gpt_context_refresh.py --dry-run
.venv\Scripts\python.exe -m pytest tests/context/test_build_context_packet.py tests/context/test_gpt_context_generation_rules.py tests/context/test_refresh_gpt_references.py
git diff --check
```

## Compact Output

Answer in Korean with this shape:

```yaml
gate: gpt_context_refresh
gate_result: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
scope_lock:
  allowed:
    - "<file or directory>"
  forbidden:
    - "<boundary>"
changed_files:
  - "<file>"
validation_evidence:
  - "<command: pass/fail/not_run with short evidence>"
blocked_cheap_checks:
  - "<command or none>"
remaining_risk:
  - "<none or compact risk>"
```
