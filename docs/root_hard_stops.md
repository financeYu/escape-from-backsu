# Root Hard Stops

This is the current project authority document. `AGENTS.md` is only the compact
router/constitution, and `docs/roadmap_status.md` is only the current route
state. Use `docs/project_checklist.md` only for named historical roadmap-order,
provenance, regression, hard-stop, or release-evidence questions not answered
here.

## Authority Order

1. User's latest explicit instruction.
2. `AGENTS.md` for the always-on router.
3. `docs/root_hard_stops.md` for active project authority and hard stops.
4. `docs/roadmap_status.md` for current route state.
5. A triggered Codex skill, affected subproject `AGENTS.md`, one active packet,
   one needed domain stub, and targeted files.

The user's prompt defines only this gate's concrete goal and requested
deliverables. Do not move reusable process, guardrail, or validation policy into
the prompt.

## Current Baseline

- Step 20 is complete; KOSPI200 technical MVP v0.1 is frozen.
- The active route is post-MVP `v0.2 predictive probability score route`.
- The only approved active candidate ML output is `prob_up_1d_candidate`.
- Use `.agents/skills/quant-candidate-ml-gate/SKILL.md` for candidate ML gate
  work and `.agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh`
  for repeatable contract checks.

## Authorized Active Scope

The active route authorizes only:

- scoped feature table work for `prob_up_1d_candidate`
- label-separated training/evaluation pipeline work
- candidate probability output
- validation tests and contract checks
- work in the approved separate role branch/worktree

## Forbidden Scope Without Explicit Approval

- KOSDAQ150, futures, options, Nasdaq/overseas, or multi-universe activation.
- New market-data ingestion or live vendor assumptions.
- Production ranking activation or ranking generation unless the active route
  explicitly authorizes it.
- Report behavior changes or runtime score semantic changes outside the active
  candidate ML gate.
- `final_composite_score` replacement or silent score redefinition.
- `final_composite_score` replacement remains prohibited except under
  `QG_APPROVED_FINAL_SCORE_PROB_UP_1D_V0_2` and only after all v0.2 final score
  gates pass.
- Financial/fundamental data in `technical_composite_score` or
  `final_composite_score`.
- Valuation/fundamental scoring activation.
- Backtest metrics as model features.
- Backtest feedback into scoring, ranking, or model feature construction.
- Trading recommendations, buy/sell/hold, proven-alpha, or expected-return
  wording.

## Context Boundary

Completed Step 1-20 outputs are trusted by default. Do not read archives, old
Step detail, validation logs, generated packets, raw data, caches, charts, or
runtime reports unless a named conflict, regression, provenance question, or
release/freeze verification requires it. Start such lookup from
`docs/context/ARCHIVE_INDEX.md` and read the narrowest file needed.

Default task context is:

1. this file
2. `docs/roadmap_status.md`
3. triggered skill from `.agents/skills`
4. affected subproject `AGENTS.md`
5. one active packet
6. one domain stub only when needed
7. targeted files

## Generated Output Boundary

Generated reports, runtime outputs, chart images, caches, raw market data,
`.env`, and secrets are not default context and are not source-controlled unless
explicitly promoted as small review fixtures.

GPT-facing references under `docs/context/gpt/` are not refreshed by default.
Refresh them only when the user explicitly requests a GPT or ChatGPT context
update.

## Gate-End Status

At the end of a Step or assigned gate, report exactly one of:

- `COMPLETE`
- `PARTIALLY COMPLETE`
- `NEEDS FIX`
