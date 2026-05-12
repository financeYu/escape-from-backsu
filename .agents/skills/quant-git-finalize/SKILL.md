---
name: quant-git-finalize
description: Use only after quant-review-gate PASS to perform local-first Git finalization: inspect scoped changes, rerun required validation, create a local commit, and push only at the explicit remote-finalization stage.
---

# Quant Git Finalize

## Purpose

Provide the dedicated local-first Git finalization path for `master_mvp`.

This skill handles commit and optional final push process only. It does not
perform implementation review, authorize forbidden scope, or replace
`.agents/skills/quant-review-gate/SKILL.md`.

## When To Use

Use this skill only after implementation is complete and the review gate output
is `PASS`.

Do not use this skill:

- before review gate `PASS`
- when validation failed
- when forbidden scope was changed
- when the task still has `NEEDS FIX`
- to fetch, pull, or push repeatedly during ordinary work
- to push without explicit root remote-finalization approval

## Required Inputs

- review gate output showing `PASS`
- scoped changed files to include in the commit
- required validation commands and latest results
- same-scope cost-aware or review-gate evidence, when available
- current branch and worktree status
- commit message
- explicit remote-finalization approval before any push

## Local-First Procedure

1. Inspect changed files with local Git.
2. Confirm review gate `PASS` and no forbidden-scope changes.
3. Rerun required validation for the scoped task.
4. Stage only scoped task files, leaving unrelated dirty files unstaged.
5. Create a local commit and record the commit hash.
6. Push remote only at the final stage when root explicitly confirms remote
   finalization.
7. Report changed files, validation evidence, commit hash, and push result.

If remote sync is required before push, explain why, keep it minimal, and do not
repeat fetch/pull/push cycles.

When a fresh same-scope cost-aware or review-gate packet is available, use it
for scoped changed-file and cheap-check history instead of repeating discovery
triage. Git finalization still reruns required validation and performs its own
scoped staging and commit checks.

## Push Block Conditions

Do not push if:

- review gate is `NEEDS FIX`
- review gate `PASS` is missing
- forbidden scope was changed
- validation failed
- scoped commit was not created
- root has not explicitly confirmed that this task is ready for remote
  finalization

## Allowed Local Commands

- `git status --short`
- `git diff --name-only`
- `git diff --check`
- task-specific validation commands
- `git add -- <scoped files>`
- `git commit -m "<message>"`
- `git rev-parse --short HEAD`
- `powershell -ExecutionPolicy Bypass -File scripts\run_bash_validator.ps1 .agents\skills\quant-git-finalize\scripts\validate_git_finalize.sh`
- `powershell -ExecutionPolicy Bypass -File scripts\run_bash_validator.ps1 .agents\skills\quant-git-finalize\scripts\validate_git_finalize.sh --self-check`

Remote commands are allowed only in the finalization stage after explicit root
approval and must be reported as the push result.

## Compact Output

Return this shape in Korean:

```yaml
gate_result: PASS | NEEDS FIX
changed_files:
  - "<committed file>"
validation_evidence:
  - "<command: pass/fail>"
commit_hash: "<hash | not_created>"
push_result: "<not_requested | blocked | pushed | failed>"
remaining_risk:
  - "<none or compact risk>"
```
