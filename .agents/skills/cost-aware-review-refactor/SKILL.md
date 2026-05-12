---
name: cost-aware-review-refactor
description: Lightweight project-local utility for reducing review and refactor cost through diff-first, changed-files-first, cheapest-check-first triage. Not a gate, release approval, security audit, production activation path, or blocker process.
---

# Cost-Aware Review Refactor

## Purpose

Reduce repeat review and refactor cost by helping the root agent choose the
smallest useful inspection, validation, and cleanup path for a changed scope.
This skill is advisory and lightweight. It does not approve completion, block
release, replace gate skills, or expand project authority.

Root remains responsible for orchestration, scope control, delegation, and final
confirmation. This skill only helps summarize the cheapest next checks and
small refactor opportunities that are already inside the assigned scope.

## When To Use

Use this skill when the task asks for review cost reduction, lightweight
refactor triage, changed-file inspection, validation minimization, or repeated
review cleanup before a formal gate or specialist review.

Good fits:

- docs/config/test/code changes where a cheaper focused check may be enough
- identifying duplicate review work already owned by an existing gate or
  subproject process
- proposing narrow refactors within changed files
- preparing a compact handoff for the root agent or an owning subproject agent

## When Not To Use

Do not use this skill as:

- gate, release approval, blocker declaration, or approval packet
- security audit, full audit, production activation, or final acceptance review
- replacement for `.agents/skills/quant-review-gate/SKILL.md`,
  `.agents/skills/review_gate/SKILL.md`, validators, root policy, or affected
  subproject `AGENTS.md`
- authority for shared policy, global routing, schema/contract, score
  semantics, architecture boundary, or multiple-subproject changes

If a formal gate, validator, audit, or specialist review is required, stop using
this skill as the decision maker and route to the existing owner.

## Operating Rules

Apply these principles in order:

1. Diff first: start from `git diff --name-only`, `git status --short`, or the
   explicit changed-file list.
2. Changed files first: inspect changed files and nearby references before
   broad searches.
3. Cheapest check first: prefer targeted `rg`, `git diff --check`, local unit
   tests for touched files, or existing validators over broad suites.
4. Reuse owners: if an existing skill, validator, subproject workflow, or root
   policy already owns the rule, reference it instead of restating it.
5. Keep refactors local: propose or make only narrow cleanup inside allowed
   scope and changed ownership boundaries.

Avoid repeating long Codex process rules already present in `AGENTS.md`,
project docs, gate skills, validators, or subproject instructions.

## Same-Scope Evidence Reuse

When this utility is run for a scope, its compact output becomes the reusable
same-scope evidence packet for downstream routing, completion review, and Git
finalization. Downstream gates should consume it instead of rediscovering the
same changed files, cheapest checks, duplicate owners, or local refactor
opportunities.

The packet is reusable only while all of these stay true:

- the changed-file set is the same or a downstream gate explicitly narrows it
- the evidence is from the current task turn or a named fresh validation pass
- no blocked cheap check is being treated as validation evidence
- no gate needs an independent authority check that this utility does not own

If the packet is stale, scope-mismatched, or conflicts with a hard stop, discard
it and rerun the narrowest applicable check. Otherwise, pass the compact fields
forward and do not rerun `git status --short`, `git diff --name-only`,
`git diff --check`, or targeted `rg` solely to rediscover utility-owned facts.

## Blocked Cheap Check Protocol

When a cheap check is blocked by the environment, do not convert the blockage
into a gate failure by itself and do not keep retrying the same blocked path.
Record it separately from validation status, choose the cheapest safe
substitute when one exists, and route any remaining required validator request
to the responsible root, gate, or subproject owner.

Common blocked cheap checks:

- missing `pytest`
- unavailable `bash` or WSL
- Windows `bash.exe` WSL install/update messages
- Git Bash `Win32 error 5`, including `couldn't create signal pipe` or
  `CreateFileMapping` failures
- denied `rg`
- denied WindowsApps `rg` execution or missing project-local `rg`
- inaccessible temp/cache directories
- Git `safe.directory` ownership errors
- Git `.git/index.lock` or `.git` ACL permission errors during index-writing
  commands such as `git add`

Required handling:

1. Record the blocked command, short error, and affected scope under
   `blocked_cheap_checks`.
2. If a narrow substitute exists, use it and label it as substitute evidence.
   For example, when `rg` is denied on Windows, use targeted PowerShell
   `Select-String` over the same file list.
3. If the blocked check is a required validator, route it to the responsible
   gate/root agent instead of marking the utility result as complete
   validation. For Git Bash `Win32 error 5` cases, preserve the exact validator
   command and route through `.agents/skills/quant-validator-approval/SKILL.md`
   for the narrow approved execution path.
4. Keep findings, substitute evidence, and remaining validator requests as
   separate fields. The downstream gate decides whether the blocker is
   acceptable, needs escalation, or requires a different owner.

This protocol is advisory triage only. It does not approve completion and does
not waive required validation.

## Root Coordination Boundary

This skill must not directly perform or approve changes that affect:

- shared policy or global routing
- schema, contract, validator, or score semantics
- multiple subprojects or cross-project ownership
- architecture boundaries
- release, production activation, or final completion acceptance

When such a change appears necessary, report it as requiring root agent approval
and stop at a recommendation. The root agent may split the work, select the
proper gate, or delegate to a sub-agent or subproject owner.

## Subproject Delegation

For review or refactor checks that can be performed inside one subproject or
worktree, defer to that subproject agent and its local `AGENTS.md`. Provide only
a compact handoff:

- changed files
- cheapest useful checks
- suspected duplicate process or owner
- questions requiring root approval

Do not use this utility to bypass subproject workflows.

## Compact Output

Return a compact Korean summary:

```yaml
utility: cost-aware-review-refactor
scope: "<changed files or assigned scope>"
cheapest_next_checks:
  - "<targeted check>"
blocked_cheap_checks:
  - "<command or none: short blocker and affected scope>"
substitute_evidence:
  - "<substitute check or none>"
refactor_opportunities:
  - "<narrow in-scope opportunity or none>"
existing_owner_refs:
  - "<skill/process/subproject owner or none>"
routed_validator_requests:
  - "<responsible gate/root/subproject and command, or none>"
validator_approval_route:
  - "<quant-validator-approval with exact command, or none>"
root_approval_required:
  - "<condition or none>"
handoff_target: "<root | subproject/worktree | gate skill>"
```

Use `root_approval_required: ["none"]` only when the work stays within the
assigned local scope and does not overlap root-owned or gate-owned authority.
