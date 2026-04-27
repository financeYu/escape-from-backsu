---
name: quant-subproject-audit-gate
description: Use for master_mvp-managed Quant_mvp subproject-wide audit gates. Separates audit verdicts from validation evidence, checks Quant_mvp boundary compliance, and routes completion acceptance through quant-review-gate. Do not use for implementation, score/ranking/report/backtest semantic changes, valuation activation, data-ingestion expansion, or trading advice.
---

# Quant Subproject Audit Gate

## Purpose

Provide the root/master-managed Codex skill gate for auditing `Quant_mvp` as a
subproject. `Quant_mvp/AGENTS.md` owns the local process for detecting when a
check is needed and connecting the worker to this Codex skill gate.

This skill owns the master gate boundary:

- root selects this gate before a subproject audit executes
- audit verdict and validation evidence are separate parts
- audit can cover the whole `Quant_mvp` subproject by path and diff scope
- content reads remain targeted and do not become a full-repository scan

This gate does not authorize new quant behavior. It checks whether work stayed
inside the selected task, active route, and project hard stops.

## When To Use

Use this skill when root/master needs any of these:

- `Quant_mvp` scope watchdog or compliance audit
- subproject-wide audit before master-up
- audit of cross-project handoff files that include `Quant_mvp`
- pre-work, mid-work, or pre-master-up boundary check for Quant changes
- validation profile review where validation evidence must stay separate from
  the policy/scope audit verdict

For candidate probability work, use
`.agents/skills/quant-candidate-ml-gate/SKILL.md` as the execution gate first.
Then use this audit gate if the packet requires subproject-wide scope audit.

For completion acceptance, run
`.agents/skills/quant-review-gate/SKILL.md` after this gate reports a safe
result.

## When Not To Use

Do not use this skill to:

- implement features
- repair code or tests
- perform technical usefulness review
- perform valuation/fundamental review
- replace `review_mvp` specialist code or final-validation review when policy
  requires it
- approve production ranking, report behavior, runtime score semantic changes,
  backtest behavior changes, valuation activation, or data ingestion expansion
- read archives, generated outputs, raw data, caches, charts, logs, or release
  evidence without a named conflict, regression, provenance, or release check

## Required Root Packet

Root/master must provide or reconstruct this compact packet before execution:

- current task
- allowed scope
- forbidden scope
- required output
- validation commands
- Korean final report format
- selected execution skill gate, or this audit gate when audit is the task
- audit coverage: `pre_work`, `mid_work`, `pre_master_up`, or `subproject_full`

If a sub-agent is used, root must name this skill gate and pass the packet
before the sub-agent executes.

## Default Context

Read only:

1. `docs/root_hard_stops.md`
2. `docs/roadmap_status.md`
3. this skill
4. `Quant_mvp/AGENTS.md`
5. one active task packet
6. targeted changed files or diffs

Do not read all `Quant_mvp` files. A subproject-wide audit means path and
boundary coverage across `Quant_mvp/**`, not full content ingestion.

## Part 1: Audit

The audit part decides whether the work obeyed the latest instruction, selected
skill gate, active route, subproject boundary, terminology rules, and hard
stops.

Required checks:

- changed paths are inside the packet's allowed scope
- changed paths do not cross forbidden subproject or root-owned boundaries
- the worker used the Quant-side process in `Quant_mvp/AGENTS.md` when a
  check was required
- `Quant_mvp` changes do not alter score formulas, score semantics,
  normalization behavior, ranking/report/backtest behavior, valuation
  activation, data ingestion, or generated-output policy unless explicitly
  authorized
- `technical_composite_score` and `final_composite_score` are not redefined,
  replaced, or fed by unauthorized inputs
- validation failures are not relabeled as success
- validation artifacts are not treated as audit verdicts
- forbidden investment, trading, proven-alpha, expected-return, profitability,
  or valuation claims are not introduced
- unknowns remain unknown and inferences are labeled
- generated outputs, raw data, caches, charts, logs, and release evidence are
  not read or promoted unless the packet names the exception

Audit verdicts:

- `PASS`
- `WARNING`
- `BLOCKING_ISSUE`
- `NEEDS_CLARIFICATION`

Use this skill's required output for the gate result. Do not route through a
separate Quant-local audit `AGENTS.md` document.

## Part 2: Validation

The validation part records command evidence separately from the audit verdict.

Validation can include:

- task-specific validation commands from the selected execution skill gate
- targeted docs/config/schema checks for changed files
- `bash .agents/skills/quant-subproject-audit-gate/scripts/validate_subproject_audit_gate.sh`
- `git diff --check`
- focused `rg` checks for forbidden wording and gate vocabulary

Validation cannot:

- replace the audit verdict
- approve scope expansion
- prove alpha, trading usefulness, expected return, profitability, valuation, or
  adoption readiness
- hide failed or skipped checks

Validation result literals:

- `PASS`
- `FAIL`
- `NOT_RUN`

## Allowed Local Commands

- `git status --short`
- `git diff --name-only`
- `git diff --check`
- targeted `git diff -U0 -- <task files>`
- targeted `rg`
- task-specific validation commands from the selected execution gate
- `bash .agents/skills/quant-subproject-audit-gate/scripts/validate_subproject_audit_gate.sh`

Do not run `git fetch`, `git pull`, or `git push` in this gate.

## Extensibility Notes

Intentional contract literals:

- audit verdicts: `PASS`, `WARNING`, `BLOCKING_ISSUE`, `NEEDS_CLARIFICATION`
- validation result literals: `PASS`, `FAIL`, `NOT_RUN`
- protected score fields: `technical_composite_score`, `final_composite_score`
- required root authority files: `docs/root_hard_stops.md`,
  `docs/roadmap_status.md`

Extension points:

- Add new audit trigger paths in `docs/context/CODEX_REVIEW_GATE_POLICY.md`,
  not by broadening this gate into a full repository scan.
- Add new validation commands through the selected execution gate packet, then
  record them in the validation part.
- Add new forbidden claim families here only when they are root policy, not
  task-local wording preferences.

## Required Output

Return this compact Korean shape:

```text
[게이트]
- selected_skill_gate: .agents/skills/quant-subproject-audit-gate/SKILL.md
- work_type:
- active_step:
- audit_coverage:

[감사 파트]
- files_reviewed:
- changed_files:
- forbidden_scope_touched:
- hard_stop_check:
- audit_verdict: PASS | WARNING | BLOCKING_ISSUE | NEEDS_CLARIFICATION
- audit_notes:

[밸리데이션 파트]
- validation_commands:
- validation_result: PASS | FAIL | NOT_RUN
- validation_notes:

[남은 리스크]
- ...

[Step 판정]
COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
```

Use `COMPLETE` only when the audit verdict is `PASS` or an explicitly accepted
`WARNING`, validation evidence is `PASS` or correctly `NOT_RUN`, and completion
acceptance through `.agents/skills/quant-review-gate/SKILL.md` is not blocked.
