# Review Flow

## Default flow

```text
worker scope declaration
-> scope watchdog audit when required
-> subproject local change
-> subproject local first review
-> pre-master-up scope watchdog audit when required
-> master-up summary
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
8. whether `review_mvp` is requested or not

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
- required watchdog audit is missing or unresolved
- required cross-step conflict checkpoint is missing or unresolved

REJECT:

- hard stop violation
- roadmap/order violation
- unresolved high-risk issue
- missing or misleading evidence
- watchdog found an unresolved `BLOCKING_ISSUE`
- cross-step conflict checkpoint found an unresolved `BLOCKING_ISSUE`
