# Root Agent Conflict Stop Process

## Purpose

This process defines what a subproject worker or delegated agent must do when its work may conflict with the root/master agent, root-owned policy, or protected concurrent work.

The goal is to stop before a mixed ownership change becomes harder to review. A conflict stop is a normal safety outcome, not a failed task.

## When To Stop

Stop work and report before making more edits when any of these conditions appear:

- The task needs to edit a root-owned file without explicit root/master approval.
- The task needs to change repository-level routing, Git policy, review delegation, release policy, or CI ownership.
- `git status` shows dirty files in the same file, directory, or roadmap Step that the user or root agent said is active elsewhere.
- A subproject change would consume or override a root-level handoff before the root agent has accepted it.
- The current instruction conflicts with `AGENTS.md`, `docs/project_checklist.md`, `docs/roadmap_status.md`, or a direct latest user instruction.
- A generated output, runtime cache, or local report may be mixed into a source-controlled root change.
- The worker cannot separate its owned files from unrelated dirty files with confidence.

## Immediate Actions

When a stop condition is found:

1. Stop editing immediately.
2. Do not run formatting, cleanup, staging, commit, reset, checkout, or broad repair commands.
3. Preserve the working tree as-is unless the user or root/master explicitly approves a rollback or repair.
4. Collect only compact evidence needed to explain the conflict:
   - current scope declaration
   - `git status --short`
   - touched or intended files
   - conflicting instruction, file, Step, or ownership boundary
   - last safe action completed
5. Report using the template below.
6. Wait for the user or root/master decision before resuming.

Reads are allowed if needed to prepare the report. Writes are not allowed after the stop point unless the report requests and receives approval.

## Report Template

```text
[Root Agent Conflict Stop Report]
- status: NEEDS_ROOT_DECISION
- worker/subproject:
- requested task:
- declared scope:
- stop trigger:
- conflicting root area or protected work:
- files already touched:
- files intended but not touched:
- git status summary:
- last safe action:
- evidence checked:
- risk if continued:
- requested decision:
```

## Resume Rules

Work may resume only after one of these decisions is recorded:

- `RESUME_WITH_SCOPE`: continue inside a narrowed file list or behavior scope.
- `ROOT_TAKES_OVER`: root/master handles the conflicting area.
- `SPLIT_HANDOFF`: subproject records a handoff or TODO and does not edit root-owned files.
- `ABANDON_LOCAL_CHANGE`: stop the task; rollback only if explicitly approved.
- `NEEDS_USER_CLARIFICATION`: ask the user for a concrete ownership or priority decision.

After any resume decision, rerun `git status --short`, restate the active scope, and continue with the narrowest non-conflicting change.

## Master Handling

The master/root agent must treat a conflict stop as a HOLD until the ownership decision is clear.

Master review must check:

- whether the stop was triggered before additional edits were made
- whether unrelated dirty files stayed out of the proposed change
- whether the resume decision is documented
- whether the affected Step, handoff, or root policy still matches `docs/roadmap_status.md`
- whether `review_mvp` is required because the conflict touches code, config, schema, generated-output boundaries, cross-project handoffs, or roadmap-gated behavior

If the conflict remains unresolved, the Step or task is reported as `PARTIALLY COMPLETE` or `NEEDS FIX`, not `COMPLETE`.
