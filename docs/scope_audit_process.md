# Scope Audit Process

## Purpose

This process makes the scope watchdog a normal checkpoint for worker tasks.

The goal is to catch scope creep while work is still small:

- workers stay inside the assigned task and allowed roadmap Step
- roadmap-gated work is not pulled forward accidentally
- scoring, ranking, backtest, valuation, composite, and generated-output boundaries remain explicit
- master-up summaries include a clear audit verdict when the change needs one

The current root-managed watchdog gate is:

```text
.agents/skills/quant-subproject-audit-gate/SKILL.md
```

The watchdog audits instructions and scope. Validation is a separate evidence
part of the same gate. Neither part implements features, repairs code by
default, or changes roadmap state.

Audit and validation must stay separate: audit returns the policy/scope verdict,
and validation records command evidence.

## Roles

Worker:

- owns the assigned implementation, documentation, test, or config change
- declares the allowed scope before changing files
- pauses when the work needs to cross the declared boundary
- supplies evidence for local review and master-up

Scope watchdog:

- checks whether the worker stayed within the latest user request, active roadmap Step, and project boundary
- checks hard-stop categories, terminology, evidence strength, forbidden output columns, generated-output boundaries, and config integrity
- covers the whole `Quant_mvp` subproject by changed-path and boundary checks without reading all subproject content
- returns exactly one audit verdict: `PASS`, `WARNING`, `BLOCKING_ISSUE`, or `NEEDS_CLARIFICATION`
- records actual violations, risks, style suggestions, unknowns, and inferences separately

Validation part:

- records required commands, commands run, commands skipped, and short evidence
- reports `PASS`, `FAIL`, or `NOT_RUN` separately from the audit verdict
- does not approve scope expansion, score adoption, ranking, valuation, backtest, or trading claims

Master:

- decides whether the watchdog was required
- holds integration review when a required watchdog audit is missing
- keeps `review_mvp` separate from watchdog audit
- runs `.agents/skills/quant-review-gate/SKILL.md` before accepting completion

## When Watchdog Audit Is Required

Watchdog audit is required before master-up when a worker change touches any of these areas:

- score definitions, formula semantics, score families, score branches, or score adoption
- normalization, diagnostics, redundancy/correlation review, or Technical Selection Reviewer outputs
- data schema, validation severity, data-quality flags, or generated-output/cache boundaries
- config keys, default windows, thresholds, weights, score toggles, or runtime paths
- ranking, latest ranking, `top_n`, scanner selection behavior, or stock-ordering output
- `technical_composite_score`, `final_composite_score`, composite readiness, or composite activation
- backtest design, future returns, forward labels, performance claims, or trading claims
- valuation/fundamental data, point-in-time financial availability, valuation verdicts, or valuation language
- cross-project handoff artifacts or any change touching more than one subproject
- root-boundary handoffs requested by a subproject
- any task where the worker had to expand the originally declared file list or behavior

If the root-boundary handoff is also an active root/master conflict or protected concurrent-work conflict, stop first using `docs/root_agent_conflict_process.md`. Watchdog audit can resume only after the root/master resume decision is documented.

Watchdog audit is optional for narrow documentation-only or typo-only changes when all of the following are true:

- no roadmap-gated behavior is changed
- no implementation, tests, config, generated output, schema, or root policy is changed
- the worker records `watchdog audit: not needed` with a reason in local review

## Worker Scope Declaration

Before changing files, the worker records this minimum scope declaration in its notes or handoff:

```text
[Worker scope declaration]
- latest user request:
- work type:
- responsible project:
- active roadmap Step:
- allowed files / directories:
- explicitly forbidden work:
- expected outputs:
- generated artifacts expected:
- watchdog audit required: yes / no / unknown
- reason:
```

If `watchdog audit required` is `unknown`, the worker asks the watchdog for a pre-work scope check before implementation.

## Checkpoints

### 1. Pre-work scope check

Use this when the worker is unsure whether the request is allowed.

The worker gives the watchdog:

- latest user request
- active roadmap Step
- intended responsible project
- intended file list
- planned outputs
- known forbidden work

The watchdog returns a verdict and any blocking limits before implementation starts.

### 2. Mid-work boundary check

The worker must pause and request watchdog review if any of these happens:

- a new file or directory outside the declared scope appears necessary
- implementation changes become broader than the original request
- a config default, score formula, threshold, or runtime path needs to change
- generated outputs are created or promoted to source-controlled fixtures
- ranking, composite, valuation, backtest, future-return, or trading language becomes tempting
- a completed Step artifact seems to need more than a hard-stop dependency check

### 3. Pre-master-up audit

Before master-up, a required watchdog audit must inspect the actual changed files and the worker evidence.

The worker supplies:

```text
[Watchdog audit request]
- changed files:
- owned change files:
- unrelated dirty files:
- generated outputs changed or excluded:
- summary of what changed:
- what intentionally did not change:
- tests/checks run:
- hard-stop check:
- unresolved risks:
```

The watchdog responds using `.agents/skills/quant-subproject-audit-gate/SKILL.md`.

## Verdict Handling

`PASS`:

- worker may proceed to master-up
- include the watchdog verdict in `docs/master_up_template.md`

`WARNING`:

- worker may proceed only if non-blocking risks are copied into master-up
- master decides whether the warning needs follow-up before acceptance

`NEEDS_CLARIFICATION`:

- worker stops scope expansion
- clarify missing evidence, file ownership, intended behavior, or project-boundary authority
- do not proceed to master-up as complete

`BLOCKING_ISSUE`:

- worker stops the change
- remove or revise the violating work within the allowed scope
- request root/master approval only when the block is a root-boundary or cross-project policy issue

## Relationship To review_mvp

The watchdog, validation evidence, and `review_mvp` are different gates.

The watchdog checks whether the worker is allowed to do the work and whether the work stayed inside policy, roadmap, terminology, evidence, and boundary rules.

Validation evidence records whether the required commands passed, failed, or
were not run. It does not replace the watchdog verdict.

`review_mvp` checks specialist code-level and integration risks when repository policy requires it.

A watchdog `PASS` does not replace required `review_mvp`.
A watchdog `BLOCKING_ISSUE` must be resolved before `review_mvp` is used for ordinary code review.

## Master Hold Rules

Master must return `HOLD` or `REJECT` when:

- watchdog audit was required but missing
- watchdog verdict is `NEEDS_CLARIFICATION` and the clarification is unresolved
- watchdog verdict is `BLOCKING_ISSUE`
- the master-up summary omits watchdog status for a change that touches required-trigger areas
- a worker claims `watchdog audit: not needed` but changed roadmap-gated behavior, config, schema, generated outputs, scoring, ranking, composite, backtest, valuation, or cross-project handoff files
