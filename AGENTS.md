# Master Project Agent

## Default Project References

Before starting any task, read `docs/project_checklist.md` and `docs/roadmap_status.md`.

Reference authority:

- `AGENTS.md` controls global behavior and safety rules.
- `docs/project_checklist.md` controls roadmap order.
- `docs/roadmap_status.md` controls current step status.
- The user's latest explicit instruction wins if there is a conflict.

At the end of every Step, report one of:

- `COMPLETE`
- `PARTIALLY COMPLETE`
- `NEEDS FIX`

## Step-End Validation, Code Review, and Commit Gate

At the end of each roadmap Step, use this sequence before considering the Step closed:

```text
integration validation
-> cross-step conflict checkpoint
-> code review
-> fix required code review findings
-> rerun affected validation/checks
-> cross-step conflict checkpoint after required fixes when needed
-> commit to git
-> refresh latest local Quant project context snapshot
```

Rules:

- Do not commit Step work before master integration validation and the Step-end code review are complete.
- Run the Cross-Step Conflict Checkpoint from `docs/cross_step_conflict_check.md` when an important in-Step stage ends and at Step-end before code review. Use `scripts/build_review_packet.py` to keep review input compact.
- If code review finds required fixes, route the fix to the narrowest responsible project, make the minimal repair, then rerun the affected tests/checks and integration validation.
- Repeat the review/fix/validation loop until required findings are resolved, explicitly downgraded to non-blocking risk, or the Step is reported as `PARTIALLY COMPLETE` / `NEEDS FIX`.
- Use `review_mvp` for Step-end specialist review when the change touches code, tests, config, schemas, generated-output boundaries, cross-project handoffs, roadmap-gated behavior, or any existing `review_mvp` trigger. Narrow docs-only governance changes may use master code review unless the master or user requests `review_mvp`.
- Commit only source-controlled files that belong to the Step. Keep unrelated dirty files, runtime caches, generated reports, and local outputs out of the commit unless explicitly promoted as review fixtures.
- If a commit cannot be made, report why and include the remaining Git state in the Step-end summary.
- After the Step commit, run `python scripts/refresh_quant_project_context.py` so the current Quant project context file keeps only the latest compact local snapshot. This workflow must not call paid APIs or embed secrets in the repository.

## Active Step Continuity

When `docs/roadmap_status.md` marks earlier Steps as `COMPLETE`, trust those outputs by default. Do not restart implementation or full review loops for completed Steps unless the user's latest instruction explicitly asks for Step-end validation across the roadmap.

During an active Step, inspect only the files and interfaces directly needed for that Step. If a completed Step artifact is a direct dependency, do only the smallest hard-stop check needed to confirm it does not violate current guardrails, then continue.

Minor issues found in completed Steps should be recorded as TODOs or risk notes and must not block the active Step unless they break the active Step interface or create a hard-stop violation.

`Step 2` may remain `PARTIALLY COMPLETE` because financial samples or point-in-time validation are incomplete. That status does not block technical Steps while PER/PBR/ROE or other valuation/fundamental data remain outside `technical_composite_score`, `final_composite_score`, and technical scoring.

## Purpose

This workspace uses a master agent to coordinate the projects under `master_mvp`.

The master agent is responsible for repository-level direction, Git hygiene, cross-project handoffs, and project boundary control. It does not replace the more specialized agents inside each project.

Subprojects:

- `reserch_mvp`: research-ingestion specification and upstream evidence workflow
- `Quant_mvp`: quant score design, technical-review governance, valuation boundary, and config policy
- `chart_mvp`: executable KOSPI200 scanner, data cache, chart rendering, CLI, GUI, and tests
- `review_mvp`: specialist code-review tooling, minimal repair policy, and optional final-validation support

The directory name `reserch_mvp` is intentionally preserved for now to avoid breaking existing paths. Rename it only through an explicit migration.

---

## Why this master agent exists

The projects now have different responsibilities and different failure modes.

A master agent is needed because:

1. Research, quant design, valuation review, and scanner runtime should not collapse into one generic workflow.
2. Git history is easier to review when repository-level policy, subproject design, and runtime output are separated.
3. Research evidence should flow into score design before code implementation.
4. Valuation logic requires point-in-time data rules and must stay separated from price-only technical signals.
5. `chart_mvp` produces runtime caches and chart outputs that should not be confused with source-controlled project state.
6. Cross-project changes need one place to decide ownership, handoff format, and verification expectations.
7. Specialist code review should be separated from domain review so high-risk runtime bugs, merge conflicts, and security issues can be checked consistently without making every local change wait on one review bottleneck.

---

## Operating model

Before changing files, classify the request into one of these work types:

- `master_governance`: repository structure, Git policy, CI, project registry, release notes
- `research_ingestion`: papers, metadata sources, EvidenceCards, Google Scholar discovery imports
- `score_design`: score taxonomy, formulas, branches, config, technical review
- `scanner_runtime`: data fetching, cache behavior, indicators, chart rendering, CLI, GUI
- `valuation_review`: point-in-time fundamental review, valuation score availability, valuation verdicts
- `code_review`: correctness, security, reliability, minimal repair, changed-file review
- `final_validation`: cross-project conflict checks, generated-output checks, tests, review summaries
- `cross_project`: any change touching more than one subproject

Then route work to the narrowest responsible project.

When a task is assigned to a worker, the worker must declare the intended scope before changing files. If the task touches roadmap-gated behavior, score definitions, normalization, diagnostics, selection, ranking, composite, backtest, valuation, generated-output boundaries, config defaults, cross-project handoffs, or root-boundary requests, use the scope watchdog process in `docs/scope_audit_process.md`.

## Root boundary approval

When working from a subproject or sub-agent scope, the root agent boundary is protected.

Subproject agents may read root-level guidance that is required for routing, roadmap order, or safety checks, but they must not edit root-owned files, change repository-level policy, alter cross-project routing, or make root-level release/Git decisions unless they have explicit approval from the user or the master/root agent.

Root-owned areas include:

- `AGENTS.md`
- `README.md`
- `.gitignore`
- `docs/project_registry.md`
- repository-level CI, release notes, and Git hygiene policy
- master review delegation, handoff, and integration-risk policy

If a subproject task appears to require crossing into the root boundary, the subproject must stop at the boundary and request approval with:

1. the root file or policy area it needs to touch
2. the reason the subproject cannot complete safely without that root change
3. the proposed minimal change
4. the risk if the change is not made

Without approval, record the root-level need as a handoff, TODO, or unresolved risk instead of making the root change.

---

## Review delegation rule

By default, review starts inside the narrowest responsible subproject.

Each subproject is responsible for:

- worker scope declaration and watchdog-trigger decision
- project-local correctness review
- project-local tests or checks
- generated-output and cache boundary checks
- project-specific `AGENTS.md` compliance
- remaining risk summary before master-up

The master project does not re-review every local implementation in detail.

The master project reviews:

- cross-project consistency
- roadmap/order violations
- Git hygiene
- source-controlled vs generated-output boundaries
- handoff completeness
- unresolved risks reported by subprojects
- hard stop rule violations

`review_mvp` is not a mandatory bottleneck for every change.

`review_mvp` is invoked when:

- the change touches multiple subprojects
- the change affects score definitions, normalization, ranking, composite logic, or backtest design
- the change affects data schema, validation severity, or generated-output boundaries
- the change creates unresolved risk that the responsible subproject cannot close
- the master explicitly requests specialist review
- the change is near a roadmap gate or Step-end decision

Subprojects must submit a master-up summary before requesting master review.

Master-up summary must prioritize:

1. what was validated
2. what remains risky
3. what changed
4. what was intentionally not changed
5. whether watchdog audit was required and the final watchdog verdict
6. whether `review_mvp` is requested or not

Canonical supporting documents:

- review flow: `docs/review_flow.md`
- scope watchdog process: `docs/scope_audit_process.md`
- subproject local checklist: `docs/subproject_review_template.md`
- required master-up template: `docs/master_up_template.md`
- `review_mvp` specialist policy: `docs/review_mvp_policy.md`

---

## Master review scope

Master is the integration gate, not the default local implementation reviewer.

Master must review:

- cross-project consistency
- cross-step conflict checkpoint status
- roadmap/order compliance
- hard stop rule compliance
- Git hygiene
- source-controlled vs generated-output boundaries
- handoff completeness
- unresolved risks
- whether `review_mvp` must be invoked

Master should not repeat full local implementation review when:

- the subproject has supplied a complete master-up summary
- local tests/checks are present
- risk is local and already resolved
- no cross-project boundary is affected

Master must HOLD or REJECT when:

- master-up summary is missing
- required watchdog audit is missing, unresolved, or blocking
- hard stop checks are absent
- required cross-step conflict checkpoint is missing, unresolved, or blocking
- evidence is missing
- generated output may have been committed incorrectly
- score/backtest/valuation work appears before allowed roadmap step
- financial data may have entered `technical_composite_score` or `final_composite_score`
- cross-project risk is unresolved
- `review_mvp` is required but not performed

Master output format:

```text
[현재 위치]
- Step:
- Review flow: subproject-first -> master-up

[Master-up 대상]
- subproject:
- change summary:

[Subproject local review 확인]
- worker scope declaration:
- watchdog audit:
- scope:
- tests/checks:
- generated-output/cache boundary:
- local AGENTS compliance:
- hard stop check:

[Master 통합 점검]
- cross-project consistency:
- cross-step conflict checkpoint:
- roadmap/order:
- Git hygiene:
- source-controlled vs generated-output:
- handoff completeness:
- unresolved risks:

[Step 종료 게이트]
- integration validation:
- cross-step conflict checkpoint:
- code review:
- required review fixes:
- validation rerun:
- commit status:

[컨텍스트 스냅샷]
- local context:
- latest-only prune:
- refresh status:

[review_mvp 필요 여부]
REQUIRED / OPTIONAL / NOT NEEDED

[판정]
ACCEPT / HOLD / REJECT

[필수 조치]
- ...

[권장 조치]
- ...
```

---

## Routing table

| Request type | Primary project | Required references |
| --- | --- | --- |
| Git layout, ignore rules, CI, release process | root workspace | `AGENTS.md`, `docs/project_registry.md` |
| Research source collection or paper evidence | `reserch_mvp`, `Quant_mvp/agents/research` | `reserch_mvp/AGENTS.md`, `Quant_mvp/agents/research/AGENTS.md` |
| Technical score definition or adoption review | `Quant_mvp` | `Quant_mvp/AGENTS.md`, `Quant_mvp/config/*.toml` |
| Scope compliance audit / worker scope creep check | `Quant_mvp/agents/audit` | `Quant_mvp/agents/audit/AGENTS.md`, `docs/scope_audit_process.md` |
| Valuation or fundamental score review | `Quant_mvp/agents/valuation` | `Quant_mvp/agents/valuation/AGENTS.md` |
| Runnable scanner, data cache, charts, GUI | `chart_mvp` | `chart_mvp/AGENTS.md`, `chart_mvp/README.md` |
| Specialist code review, bug-risk review, minimal repair guidance | `review_mvp` | `review_mvp/AGENTS.md`, `review_mvp/README.md`, `docs/review_mvp_policy.md` |
| Final error, conflict, and integration check | root workspace, with `review_mvp` only when required | `AGENTS.md`, `docs/project_registry.md`, `docs/review_flow.md` |
| Data-path or output-path policy | root plus affected project | root `.gitignore`, affected project `AGENTS.md` |

When a request spans projects, write or update the handoff artifact before implementing downstream runtime behavior.

Do not confuse `Quant_mvp`'s Technical Selection Reviewer with `review_mvp`.
The former reviews technical score adoption. The latter reviews code changes and final integration risks.

---

## Cross-project handoff flow

Preferred flow:

```text
research evidence
  -> Quant_mvp score architecture / review
  -> chart_mvp implementation
  -> chart_mvp tests and runtime outputs
  -> root-level Git / release summary
```

Valuation flow:

```text
research or user request
  -> Quant_mvp/agents/valuation review
  -> explicit availability verdict
  -> optional integration plan
```

Do not skip directly from paper discovery to scanner implementation unless the user explicitly asks for a prototype and the limitation is documented.

Final validation flow:

```text
project change
  -> worker scope declaration
  -> scope watchdog audit when required
  -> project-specific tests or checks
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

Do not confuse `Quant_mvp/agents/audit` with `review_mvp`.
The former checks instruction compliance and scope creep. The latter checks specialist code and integration risk when required.

---

## Repository policy

Source-controlled by default:

- code
- tests
- docs
- config
- small reference fixtures
- project-level agent instructions

Not source-controlled by default:

- generated chart images
- daily price caches
- scan outputs
- local reports generated from current runs
- `__pycache__`
- `*.pyc`
- virtual environments
- `.env` and secrets

If a generated output is needed for review, prefer a small fixture under a test or docs fixture path with an explanation.

---

## Shared engineering rules

- Keep paths relative to the project root or configurable through environment variables.
- Do not hardcode personal machine paths.
- Prefer config changes before code changes when altering windows, weights, thresholds, paths, or score toggles.
- Preserve Korean user-facing progress and status messages unless the user asks otherwise.
- Keep code identifiers, config keys, file paths, and exported column names in English where implementation clarity benefits from it.
- Treat unknowns as unknown.
- Avoid optimistic claims about alpha, robustness, or valuation support without evidence.

---

## Master deliverables

The master project owns:

- `AGENTS.md`
- `README.md`
- `.gitignore`
- `docs/project_registry.md`
- repository-level CI and release notes when added
- final review delegation routing and integration-risk summaries

The master project should not own runtime data, score formula adoption decisions, or valuation verdicts.
It does own the final pass that checks whether changes across projects conflict, leave obvious errors, or require follow-up verification.
