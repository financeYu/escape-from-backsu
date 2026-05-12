---
name: quant-work-cycle
description: Use when root receives an implementation task in master_mvp or Quant_mvp and must run the controlled implement-review-fix-verify loop before reporting commit-ready status. Routes scope locking, delegated implementation, mandatory diff review, automatic fix passes, focused validation, and no-commit/no-push reporting for Quant workflow work.
---

# Quant Work Cycle

## Purpose

Run a local-first implementation cycle that keeps root focused on
orchestration, scope control, and final review. The cycle prepares a
commit-ready report only after required review and validation pass; it never
commits, stages, fetches, pulls, or pushes.

This skill is workflow automation only. It does not authorize quant logic,
score semantics, ranking/report behavior, backtest behavior, data ingestion,
universe expansion, live trading, production activation, or valuation
activation changes.

## Required Root Packet

Before implementation begins, root must provide or reconstruct this compact
packet:

- current task
- classification: `planning/read-only`, `narrow edit`, or `Step/gate closure`
- selected project-local skill gate for the task
- allowed scope locked to explicit files, directories, or subproject/worktree
- forbidden scope
- required output
- validation commands
- Korean final report format
- Git policy: `fetch=false`, `pull=false`, `push=false`, `commit=false`,
  `stage=false`

If any boundary needed for a safe scope lock is missing, stop and return
`NEEDS FIX` with the missing boundary. Do not start implementation from a vague
or expanding scope.

## Scope Lock

Lock the task to the narrowest owner before edits:

- Use only this workspace's `.agents/skills` as project gate authority.
- For subproject work, read only the subproject `AGENTS.md`, one active packet,
  one needed domain stub, and targeted files.
- Do not read archives, generated outputs, raw data, caches, charts, logs, or
  release evidence unless the user names a conflict, regression, provenance, or
  release check.
- Keep v0.1/v0.2 material archive-only unless explicitly requested for a named
  compatibility or provenance check.
- Delegate implementation and validation inside the owning subproject/worktree
  when the task can be safely handled there.

The scope lock must be repeated in the final report as the basis for deciding
whether changed files are in scope.

## Cycle Procedure

### 1. Scope Confirmation

Confirm the task packet, selected gate, allowed scope, forbidden scope, and
validation commands. If the task touches a narrower existing gate such as
`quant-candidate-ml-gate`, `quant-strategy-adoption-gate`,
`score-runtime-semantics-gate`, or `quant-subproject-audit-gate`, route there
inside this cycle instead of inventing a new review path.

When the task is about reducing repeated review, validation, or refactor cost,
run or consume `.agents/skills/cost-aware-review-refactor/SKILL.md` before
formal routing. Treat its compact output as the same-scope evidence packet for
changed files, cheapest checks, duplicate owners, and narrow refactor
opportunities.

### 2. Implementation

Implement only inside the scope lock. If a sub-agent is used, root must give it:

- current task
- allowed scope
- forbidden scope
- required output
- validation commands
- Korean final report format
- selected skill gate

The implementer must not perform Git remote work, staging, or commits.

### 3. Diff Review

After implementation, review the actual diff before validation. Start from the
same-scope evidence packet when it is fresh and scope-matched:

- `git diff --name-only`
- `git diff --check`
- targeted `git diff -U0 -- <scoped files>`
- targeted search only when needed for forbidden language or boundary checks

Do not rerun commands solely to rediscover cost-aware-owned facts already in a
fresh same-scope packet. Still run any independent authority check required by
the selected gate, and rerun the narrowest check if the packet is stale,
scope-mismatched, or missing required evidence.

Review must check changed-file scope, forbidden-boundary safety, unintended
behavior changes, missing tests/validators, and commit-readiness blockers.

If diff review returns `FAIL`, do not proceed to commit-ready status. Run a fix
pass and then repeat diff review.

### 4. Fix Pass

Apply only fixes that address review findings or validation failures inside the
scope lock. If the fix requires expanding scope, stop and report
`separate approval required` or `NEEDS FIX` instead of editing outside scope.

After every fix pass, return to diff review.

### 5. Verify Pass

Run required focused checks after diff review passes. Minimum default checks:

- `git diff --check`
- changed file list check
- task-specific validator or focused test when applicable

Reuse same-scope evidence for the changed file list and cheap-check history;
the verify pass should add only missing required validation, freshness checks,
or selected-gate authority checks.

If a required validator is blocked by environment issues, route the blocker
through `.agents/skills/cost-aware-review-refactor/SKILL.md` first. Keep
blocked checks separate from validation status and route any remaining required
validator request to the responsible gate/root owner.
For project-local `.sh` validators, use
`powershell -ExecutionPolicy Bypass -File scripts\run_bash_validator.ps1 <validator>`
instead of bare `bash`; treat `BLOCKED_BASH_VALIDATOR` as an environment
blocker, not validation evidence.

If verification returns `FAIL`, do not proceed to commit-ready status. Run a
fix pass and repeat diff review and verify.

### 6. Commit-Ready Report

Only after diff review and all required verification pass, report commit-ready
status without committing or staging. Include:

- changed files
- validation results
- review result
- scope lock summary
- recommended commit message
- remaining risks or manual checks

If any review or validation failure remains, report `NEEDS FIX` with changed
files, failed items, and the next action. Do not call the result commit-ready.

## Commit-Ready Gate

Set `review_result: "PASS"` and `gate_result: COMPLETE` only when all are
true:

- changed files are inside the locked allowed scope
- forbidden scope was not touched
- mandatory diff review passed
- every required validation command passed or was explicitly marked not
  applicable by the owning gate
- no automatic staging, commit, fetch, pull, or push occurred
- final report gives the user enough information to commit manually

Set `review_result: "FAIL"` and `gate_result: NEEDS FIX` when any are true:

- review found a blocker that still needs code or doc changes
- validation failed
- required validation is blocked, not run, or only routed to another owner
- changed files escaped the scope lock
- forbidden scope was touched
- required validator status is missing or conflated with an environment blocker
- commit-ready language is used before review and verification pass

Routed blockers are useful evidence, but they are not validation PASS evidence.
Do not report commit-ready status until the responsible owner resolves the
blocker or marks the validation not applicable.

## Git and Network Policy

Default disabled commands:

- `git fetch`
- `git pull`
- `git push`
- `git add`
- `git commit`

This workflow never pushes. It also does not create commits; after `PASS`, the
user may commit manually or explicitly invoke a separate finalize workflow.

## Local Script

Use the bundled self-check to verify that this skill still contains the required
workflow controls:

```powershell
python .agents/skills/quant-work-cycle/scripts/validate_work_cycle.py --dry-run
```

The script validates the skill document only. It does not inspect project logic,
stage files, commit, fetch, pull, or push.

## Korean Final Report Shape

Use this compact shape:

```yaml
gate_result: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
scope_lock:
  allowed:
    - "<file or directory>"
  forbidden:
    - "<boundary>"
changed_files:
  - "<file>"
review_result: "PASS | FAIL with reason"
validation_evidence:
  - "<command: pass/fail/not_run with short evidence>"
commit_performed: "no"
push_performed: "no"
recommended_commit_message: "<message>"
remaining_risk:
  - "<none or compact risk/manual check>"
```
