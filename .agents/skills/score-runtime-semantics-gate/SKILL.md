---
name: score-runtime-semantics-gate
description: "Use for master_mvp score_runtime_semantics_gate work governing score, ranking, report runtime meaning: score meaning dictionaries, allowed or forbidden report language, evidence card mapping, candidate interpretation notes, ML label and feature availability semantics, no-lookahead validation ownership, evaluation-only calibration metrics, sidecar schema meaning, ranking activation permission, final_composite_score replacement approval, runtime semantic change approval, report behavior approval, and cross-step conflict checkpoints."
---

# Score Runtime Semantics Gate

Local gate alias: `score_runtime_semantics_gate`.

## Purpose

Separate score, ranking, report, candidate ML, and governance semantics so a
task can change documentation or candidate-only interpretation without silently
authorizing production behavior.

This gate does not activate ranking, replace `final_composite_score`, change
runtime report behavior, or redefine score formulas. It routes those requests to
the owning lane and requires explicit approval before any runtime behavior
change.

## Loading Process

Read in order:

1. `docs/root_hard_stops.md`
2. `docs/roadmap_status.md`
3. this `SKILL.md`
4. affected subproject `AGENTS.md` only when the task enters a subproject
5. one active packet only when required by the route
6. one needed domain stub only when required
7. targeted files only

Do not read archives, generated outputs, raw data, caches, charts, logs, or
release evidence unless a named conflict, regression, provenance, or release
check requires it.

## Ownership Structure

### Research-Owned

Research owns interpretation surfaces that explain what evidence or candidates
mean without changing runtime scoring behavior:

- score meaning dictionary
- allowed / forbidden report language
- evidence card mapping
- candidate interpretation notes

### Backtest/ML-Owned

Backtest/ML owns candidate probability, label, feature, leakage, and evaluation
surfaces. These outputs remain evaluation-only or candidate-only unless Quant
governance explicitly approves activation:

- label definition
- feature availability
- no-lookahead validation
- calibration / evaluation-only metrics
- sidecar output schema

### Quant Governance-Owned

Quant governance owns approval boundaries for runtime behavior, ranking, final
score semantics, and cross-step conflicts:

- ranking activation permission
- `final_composite_score` replacement prohibition/approval
- runtime semantic change approval
- report behavior change approval
- cross-step conflict checkpoint

## Routing Rules

Classify each task as `planning/read-only`, `narrow edit`, or
`Step/gate closure`.

Use the narrowest owner lane:

- Use Research-owned review for wording, interpretation, evidence mapping, and
  candidate explanation changes that do not alter runtime behavior.
- Use Backtest/ML-owned review for candidate label, feature availability,
  no-lookahead, calibration, evaluation-only metric, and sidecar schema changes.
- Use Quant governance-owned review for ranking activation, final score
  replacement, runtime score semantics, report behavior, or cross-step conflict
  approval.
- Use mixed routing only when the task touches more than one owner lane.

For `prob_up_1d_candidate` implementation, feature table, label-separated
training/evaluation, leakage, or sidecar output work, route through
`.agents/skills/quant-candidate-ml-gate/SKILL.md` and run its contract
validator when applicable.

Before any sub-agent executes, root must name this matching skill gate and
provide:

- current task
- allowed scope
- forbidden scope
- required output
- validation commands
- Korean final report format

## Hard Blocks

Block or return `NEEDS FIX` for:

- production ranking activation without Quant governance approval
- ranking generation unless the active route explicitly authorizes it
- `final_composite_score` replacement or silent redefinition without approval
- runtime score semantic changes without approval
- report behavior changes without approval
- valuation/fundamental scoring activation
- financial/fundamental data in `technical_composite_score` or
  `final_composite_score`
- backtest metrics as model features
- backtest feedback into scoring, ranking, or model feature construction
- new market-data ingestion or universe expansion
- trading recommendations, buy/sell/hold, proven-alpha, expected-return, or
  profitability claim wording

## Validation

Use validation proportional to the touched lane:

- Documentation-only semantics changes: `git diff --check` and targeted
  `rg` checks for forbidden wording.
- Candidate ML semantics changes: run
  `powershell -ExecutionPolicy Bypass -File scripts\run_bash_validator.ps1 .agents\skills\quant-candidate-ml-gate\scripts\validate_gate_contract.sh`
  when applicable.
- Completion acceptance: run `.agents/skills/quant-review-gate/SKILL.md` before
  reporting `COMPLETE`.

Always report validation that was not run and why.

## Output

Answer in Korean with this compact shape:

```yaml
gate: score_runtime_semantics
task_class: planning/read-only | narrow edit | Step/gate closure
owner_lane: research | backtest_ml | quant_governance | mixed
allowed_scope:
  - "<이번 작업에서 허용된 범위>"
forbidden_scope:
  - "<이번 작업에서 금지된 범위>"
approval_state: not_required | required | approved | blocked
validation:
  - "<command: pass/fail/not_run - short evidence>"
remaining_risks:
  - "<none or compact risk>"
status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
```
