# Review Flow

## Default flow

```text
worker scope declaration
-> root-agent conflict stop check
-> scope watchdog audit when required
-> subproject local change
-> subproject local first review
-> pre-master-up scope watchdog audit when required
-> master-up summary
-> master-up preflight
-> master integration review
-> cross-step conflict checkpoint at important stage boundaries
-> Step-end code review
-> required code review fixes
-> affected validation/check rerun
-> cross-step conflict checkpoint after required fixes when needed
-> review_mvp specialist review when required
-> final master decision
-> git commit
```

See `docs/scope_audit_process.md` for watchdog triggers, verdict handling, and worker handoff requirements.
See `docs/cross_step_conflict_check.md` for the all-Step conflict checkpoint used at important in-Step milestones and Step-end.
See `docs/root_agent_conflict_process.md` for stop/report handling when worker scope conflicts with root-owned policy, root/master active work, protected concurrent work, or dirty worktree ownership.

## Step-end gate

After integration validation for each Step, the default closure sequence is:

```text
integration validation
-> cross-step conflict checkpoint
-> code review
-> fix required code review findings
-> rerun affected validation/checks
-> cross-step conflict checkpoint after required fixes when needed
-> commit to git
```

Do not commit Step work before this gate is complete. If required review findings remain unresolved, the Step must be reported as `PARTIALLY COMPLETE` or `NEEDS FIX` instead of being committed as complete.

Use `scripts/build_review_packet.py` before checkpoint review so the reviewer reads the compact packet plus the diff, not the full archived roadmap history.

`review_mvp` is required at Step-end when the change touches code, tests, config, schemas, generated-output boundaries, cross-project handoffs, roadmap-gated behavior, or any other `review_mvp` trigger. Narrow docs-only governance changes may use master code review unless `review_mvp` is explicitly requested.

## Master-up preflight

Run a fast master-up preflight before master spends time on detailed integration review:

```powershell
python scripts/check_master_up_preflight.py --summary <path-to-master-up-summary.md>
```

The preflight is a completeness gate, not a substitute for master review. It checks that the master-up summary has enough evidence for review: owned files, unrelated dirty files, branch integration queue state, validation layer, required fix routing, generated-output exclusion, local validation, watchdog status, Cross-Step Conflict Checkpoint status, `review_mvp` request status, Step-end readiness, and requested master decision.

If the preflight fails, master returns `HOLD` without doing full review. The responsible worker fixes the summary or missing evidence first. This keeps master from rebuilding evidence during active master-up and avoids mixing unrelated dirty files into the integration decision.

The preflight may pass with warnings only when the warning is explicitly copied into the master-up risk notes. A required watchdog audit or required Cross-Step Conflict Checkpoint with `not run`, `pending`, `NEEDS_CLARIFICATION`, or `BLOCKING_ISSUE` remains blocking.

## Review output budget

Default reviews should stay findings-first and compact:

- use `quick` mode for narrow local changes and report at most 3 findings
- use `normal` mode for ordinary master/subproject review and report at most 5 findings
- use `step-end` mode only for Step closure or required Cross-Step Conflict Checkpoint records
- use `specialist` mode only when `review_mvp` is explicitly triggered or high-risk findings remain unresolved

Passed guardrails should not be restated in detail. Record `PASS` with a short reason when a gate record is required, and otherwise omit checks with no issue.

## Cross-Step Conflict Checkpoint

This checkpoint runs when an important in-Step stage ends, including contract lock, implementation ready for master-up, cross-project handoff consumption, Step-end validation, or post-fix validation rerun.

The checkpoint checks current changes against all roadmap Steps without reopening completed Steps for full review. Completed Step outputs are trusted unless the current diff touches them, consumes them downstream, or appears to violate a hard stop.

Required output is:

```text
[Cross-Step Conflict Checkpoint]
- trigger:
- roadmap/order:
- hard stops:
- score/composite boundary:
- valuation boundary:
- diagnostics boundary:
- handoff consistency:
- generated-output boundary:
- dirty worktree isolation:
- verdict: PASS / WARNING / BLOCKING_ISSUE / NEEDS_CLARIFICATION
- required follow-up:
```

## Root-Agent Conflict Stop

Before editing, a worker checks whether its scope overlaps root-owned policy, root/master active work, protected concurrent work, or unrelated dirty files that cannot be separated.

If a stop trigger exists, the worker must stop, avoid cleanup/staging/commit/reset actions, and report with `docs/root_agent_conflict_process.md`.

Accepted resume decisions are:

- `RESUME_WITH_SCOPE`
- `ROOT_TAKES_OVER`
- `SPLIT_HANDOFF`
- `ABANDON_LOCAL_CHANGE`
- `NEEDS_USER_CLARIFICATION`

Master treats an unresolved conflict stop as HOLD.

## Non-default flow

`review_mvp` can be called before master only when:

- the subproject already knows the change is high-risk
- the change crosses subproject boundaries
- the change touches roadmap-gated areas
- the subproject cannot resolve a risk locally

## Required master-up summary

Use `docs/master_up_template.md`.

The summary must make clear:

1. what was validated
2. what remains risky
3. what changed
4. what was intentionally not changed
5. which files are owned by this change and which dirty files are unrelated
6. whether watchdog audit was required and the final watchdog verdict
7. whether Cross-Step Conflict Checkpoint was required and the final verdict
8. whether Root-Agent Conflict Stop was triggered and the final resume decision
9. whether `review_mvp` is requested or not
10. which risk-based operating level applies: Level 1, Level 2, or Level 3
11. which branch integration queue state applies
12. whether branch integration validation was focused and Step-end validation is deferred until all queued branches are integrated
13. where required review/audit fixes must be routed
14. whether the master-up preflight passed or returned a missing-evidence error

The operating level comes from `docs/workspace_parallel_work_policy.md`. Master treats a Level 3 master-up as gate-critical: Scope watchdog audit and Cross-Step Conflict Checkpoint must be marked `required`, and `review_mvp` must not be marked `not needed`.

Master integration review handles one branch at a time. The expected queue states are `handoff-ready`, `preflight passed`, `merged`, `focused validation passed`, `checkpoint passed`, and `queued for step-end`. Branch integration validation should run only the focused checks for that branch unless a conflict, shared contract change, or blocking finding requires escalation. Full Step-end validation runs after the queued branches for the Step are integrated.

Required review or audit fixes are routed back to the narrowest responsible worktree or branch. Master should not make direct fixes during integration unless the user or root/master explicitly approves that repair scope.

## Scope watchdog audit

The scope watchdog is `Quant_mvp/agents/audit/AGENTS.md`.

It checks whether workers stayed inside the latest request, active roadmap Step, project boundary, and hard-stop guardrails.

Watchdog audit is required for changes affecting:

- score definitions, normalization, diagnostics, selection, adoption, ranking, composite, backtest, valuation, or future-return semantics
- data schema, validation severity, generated-output/cache boundaries, or config defaults
- cross-project handoffs or root-boundary requests
- any worker change that expands beyond the declared file list or behavior

Watchdog audit is optional only for narrow documentation-only or typo-only changes with no roadmap, implementation, config, schema, generated-output, or root-policy effect.

Accepted watchdog verdicts are `PASS`, `WARNING`, `BLOCKING_ISSUE`, and `NEEDS_CLARIFICATION`.

Master must hold when a required watchdog audit is missing, unresolved, or blocking.

## Decision meanings

ACCEPT:

- local review complete
- required cross-step conflict checkpoint passed or has only accepted warnings
- evidence sufficient
- no hard stop violation
- no unresolved cross-project risk

HOLD:

- direction is acceptable but evidence, handoff, docs, or local check is incomplete
- master-up preflight failed or was not run for a detailed master review request
- required watchdog audit is missing or unresolved
- required cross-step conflict checkpoint is missing or unresolved
- root-agent conflict stop is unresolved or lacks a resume decision

REJECT:

- hard stop violation
- roadmap/order violation
- unresolved high-risk issue
- missing or misleading evidence
- watchdog found an unresolved `BLOCKING_ISSUE`
- cross-step conflict checkpoint found an unresolved `BLOCKING_ISSUE`
