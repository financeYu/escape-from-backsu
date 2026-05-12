---
name: quant-review-gate
description: Use before accepting master_mvp or Quant_mvp task completion. Checks scoped changed files, forbidden boundaries, validation evidence, and worktree status. This is the minimal default review gate when no narrower Codex skill gate matches.
---

# Quant Review Gate

## Purpose

Provide the compact completion review gate for route-only, docs, config, tests,
and implementation handoffs in `master_mvp`.

This skill does not authorize new quant behavior. It verifies that the completed
task stayed inside the selected skill gate and project hard stops before root
accepts completion.

When `.agents/skills/cost-aware-review-refactor/SKILL.md` has already produced
a compact summary for the same changed scope, this gate consumes that utility
output as advisory triage evidence. Do not repeat utility-owned selection of
cheapest checks, local refactor opportunities, or duplicate-owner discovery
unless the utility summary is missing, stale, scope-mismatched, or conflicts
with project hard stops.

If that summary reports blocked cheap checks such as denied `rg`, unavailable
`bash`/WSL, Git Bash `Win32 error 5`, missing `pytest`, inaccessible
temp/cache directories, or Git `safe.directory` ownership errors, consume those
as environment blockers, not as validation evidence. Review any substitute
evidence separately, then route remaining required validator commands to the
selected gate, root, or subproject owner. Repeated bash/WSL/Git Bash validator
blockers must pass through `cost-aware-review-refactor` first and then
`.agents/skills/quant-validator-approval/SKILL.md` for an exact-command
approval path when escalation is required.

## When To Use

Use this skill:

- before accepting any sub-agent or worker task as complete
- after implementation, docs, config, script, or test edits
- when no narrower execution skill exists and root needs the minimal default
  review gate
- before `.agents/skills/quant-git-finalize/SKILL.md` may create a commit or
  consider a push

For candidate ML probability work, run the selected execution gate first:
`.agents/skills/quant-candidate-ml-gate/SKILL.md`.

For Quant subproject-wide audit or scope-watchdog work, run the selected audit
gate first:
`.agents/skills/quant-subproject-audit-gate/SKILL.md`.

For specialist review routing, use `.agents/skills/review_gate/SKILL.md`.
If that dispatcher selects technical, valuation, adoption, full, or
`review_mvp` review, this gate must wait for that downstream review result.

## Required Task Packet

Root must provide or reconstruct a compact task packet before review:

- current task
- allowed scope
- forbidden scope
- required output
- validation commands
- Korean final report format
- selected execution skill gate, or `quant-review-gate` as the minimal default
- optional `cost-aware-review-refactor` summary when it was run for the same
  scope
- optional `blocked_cheap_checks`, `substitute_evidence`, and
  `routed_validator_requests` from the same-scope utility summary
- optional `validator_approval_route` from the utility summary when a required
  validator hit bash/WSL or Git Bash `Win32 error 5`

The worker or sub-agent must not expand beyond the selected skill gate. If the
packet is missing a boundary needed to judge safety, return `NEEDS FIX`.

## Review Checks

Check only task-relevant files and summaries.

If a same-scope `cost-aware-review-refactor` summary is provided, treat these as
already checked by the utility and do not recreate them inside this gate:

- choosing the cheapest useful next checks
- identifying narrow in-scope refactor opportunities
- identifying duplicate process, validator, skill, or subproject owners
- collecting the changed-file list or cheap-check history, when those fields
  are fresh and scope-matched

If the utility reported blocked cheap checks, do not repeat the same blocked
command unless it is the required validator and a safer/approved execution path
is available. Record the blocker separately from validation status, and record
substitute evidence separately from required validator evidence.
For bash/WSL or Git Bash `Win32 error 5` validator blockers, require a
same-scope cost-aware summary before using `quant-validator-approval`; the
review gate should not jump straight from failure to escalation.

This de-duplication does not waive this gate's authority checks. The gate still
must verify scope, forbidden-boundary safety, validation evidence, skill
isolation, and worktree status.

Required checks:

- changed files are inside the allowed scope for the task
- forbidden scope was not touched by the task
- required validation commands were run, or an explicit blocker is reported
- blocked cheap checks from the utility, if any, are separated from validation
  status and either substituted narrowly or routed to the responsible owner
- bash/WSL or Git Bash `Win32 error 5` validator blockers, if any, went through
  `cost-aware-review-refactor` before `quant-validator-approval`
- project-local skill isolation was preserved: Quant gates did not become
  cross-project authority, and Quant work did not edit non-Quant skill lanes
- selected skill authority came only from this workspace's `.agents/skills`;
  external, global, user, or plugin skills were not used for project gates
- worktree status is reported, including unrelated pre-existing dirty files

Unrelated pre-existing dirty files do not automatically fail this gate, but
they must be separated from task changed files and reported as remaining risk.

## Allowed Local Commands

- `git status --short`
- `git diff --name-only`
- `git diff --check`
- targeted `git diff -U0 -- <task files>`
- targeted `rg`
- task-specific validation commands from the selected execution gate
- `powershell -ExecutionPolicy Bypass -File scripts\run_bash_validator.ps1 .agents\skills\quant-review-gate\scripts\validate_review_gate.sh`

When a same-scope cost-aware utility summary is present, skip commands used only
to rediscover its utility findings. Run only the commands still needed for this
gate's independent PASS rules.

Fresh same-scope evidence may satisfy changed-file and cheap-check discovery
for this gate, but it does not replace forbidden-boundary, validation-evidence,
skill-isolation, or worktree-status authority checks.

When `rg` is denied, targeted PowerShell `Select-String` over the same scoped
file list is an acceptable substitute for wording/search triage. It is not a
substitute for a required gate validator.

Do not run `git fetch`, `git pull`, or `git push` in this review gate.

## PASS Rules

Return `PASS` only when all are true:

- task changed files are within allowed scope
- forbidden scope was not touched by the task
- required validation passed or was correctly marked not applicable
- downstream specialist review is not required, or it already passed
- same-scope cost-aware utility findings, when provided, were consumed as
  advisory evidence and did not replace this gate's authority checks
- same-scope blocked cheap checks, when provided, were separated from
  validation evidence and remaining required validators were routed or run
- changed lines do not introduce unauthorized production activation
- changed lines do not let another project invade Quant gates or let Quant
  tasks modify another project skill lane without explicit approval
- worktree status is included

Otherwise return `NEEDS FIX`.

## Compact Output

Return this shape in Korean:

```yaml
gate_result: PASS | NEEDS FIX
changed_files:
  - "<task changed file>"
validation_evidence:
  - "<command: pass/fail/not_run with short evidence>"
blocked_cheap_checks:
  - "<command or none: short blocker>"
substitute_evidence:
  - "<substitute check or none>"
routed_validator_requests:
  - "<owner and command, or none>"
validator_approval_route:
  - "<quant-validator-approval exact command, or none>"
remaining_risk:
  - "<none or compact risk>"
worktree_status: "<clean | dirty with scoped/unrelated summary>"
```

Do not paste old Step 1-20 history. Confirm at most three context facts.
