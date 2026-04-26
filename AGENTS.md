# Master Project Agent

## Default Project References

Before starting any task, read the compact root start set:

- `docs/root_hard_stops.md`
- `docs/roadmap_status.md`

Use `docs/project_checklist.md` as a root authority/reference file. Its long
Step roadmap/checklist body is historical pre-freeze planning after the MVP
v0.1 baseline, so read it only when a task needs roadmap-order, hard-stop,
provenance, regression, or release-evidence detail not covered by the compact
start set.

Reference authority:

- `AGENTS.md` controls global behavior and safety rules.
- `docs/project_checklist.md` controls roadmap order and root hard-stop policy,
  with historical Step detail targeted/on-demand after MVP v0.1.
- `docs/roadmap_status.md` controls current step status.
- The user's latest explicit instruction wins if there is a conflict.

## Context Optimization Directive

Do not read the full repository history at task start. Keep initial context to the smallest safe set:

1. current root authority status and hard stops from `docs/root_hard_stops.md` and `docs/roadmap_status.md`
2. the relevant subproject `AGENTS.md`
3. exactly one active context packet for the current task
4. one needed domain context stub, when a domain is involved
5. only the targeted source, test, or config files that may be changed or reviewed

Completed Step 1-20 outputs are trusted by default. Do not read archive files, old Step detail docs, generated packets, validation logs, runtime reports, raw market data, caches, or chart images unless there is a named conflict, regression, provenance question, or release-evidence check. When that exception applies, read the narrowest file needed and do not copy long bodies into active context.

Answers and handoffs must not repeat completed Step history. State at most three confirmed context facts, then focus on the current judgment, changed files, validation, and remaining risks.

Active packets must use file paths and short purpose notes. They must not embed long document bodies, validation logs, generated outputs, raw market data, caches, chart images, secrets, or archive content.

If the task touches scoring, ranking, reports, backtests, valuation, generated-output boundaries, roadmap verdicts, or root policy, follow the existing guardrails, root-boundary rules, and worktree/branch separation policy.

For `chart_mvp`-scoped work, do not expand beyond the `chart_mvp` ownership boundary without explicit root/master approval. If a task appears to require edits or implementation decisions in another subproject or root-owned policy area, stop at the boundary, report the needed crossing, and wait for root/master permission before proceeding.

For post-Step20 subproject delegation, use the compact packet in `docs/context/POST_MVP_AGENT_TASK_PACKET.md`. The packet is a sidecar routing aid for assigning current tasks while preserving the MVP v0.1 baseline; it does not authorize future extensions, scoring/ranking/report/backtest changes, valuation activation, or data-ingestion changes unless the user's concrete task explicitly assigns that scope.

MVP v0.1 pre-freeze readiness refactors are allowed only when root/master
assigns that concrete scope before freeze. These refactors may add policy
objects, schemas, validators, tests, and routing notes that make
KOSPI200/Naver/six-digit ticker assumptions explicit and injectable. They are
part of Step 20 closure/freeze preparation, not Step 21 entry. They must not
activate KOSDAQ, futures, options, NASDAQ/overseas ingestion, cross-universe
comparison outputs, derivative pricing, new score semantics, valuation scoring,
backtest feedback, or trading recommendations.

## Prompt Constraint Guard

Before acting on a user prompt, check whether the requested action conflicts with this repository's hard stops, roadmap order, root boundary rules, protected concurrent work, Git hygiene, generated-output policy, valuation/financial-data boundary, or safety/security constraints.

If the prompt violates those constraints, do not perform the violating work. Instead:

1. warn the user that the request is blocked or needs rerouting
2. name the specific rule or project boundary involved
3. explain the narrow safe alternative or prerequisite step
4. offer to perform only the allowed subset when one exists

Do not bypass this guard by reframing prohibited work as exploration, prototype work, cleanup, validation, or convenience automation. If the violation is ambiguous, pause long enough to clarify the safe route before editing files or running side-effecting commands.

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
```

Rules:

- Do not commit Step work before master integration validation and the Step-end code review are complete.
- Run the Cross-Step Conflict Checkpoint from `docs/cross_step_conflict_check.md` when an important in-Step stage ends and at Step-end before code review. Use `scripts/build_review_packet.py` to keep review input compact.
- If code review finds required fixes, route the fix to the narrowest responsible project, make the minimal repair, then rerun the affected tests/checks and integration validation.
- Repeat the review/fix/validation loop until required findings are resolved, explicitly downgraded to non-blocking risk, or the Step is reported as `PARTIALLY COMPLETE` / `NEEDS FIX`.
- Use `review_mvp` for Step-end specialist review when the change touches code, tests, config, schemas, generated-output boundaries, cross-project handoffs, roadmap-gated behavior, or any existing `review_mvp` trigger. Narrow docs-only governance changes may use master code review unless the master or user requests `review_mvp`.
- Commit only source-controlled files that belong to the Step. Keep unrelated dirty files, runtime caches, generated reports, and local outputs out of the commit unless explicitly promoted as review fixtures.
- If a commit cannot be made, report why and include the remaining Git state in the Step-end summary.
- Refresh `docs/context/gpt/quant_project_reference_for_chatgpt_project_current.md` only when the user explicitly requests that ChatGPT reference refresh. Use `python scripts/refresh_quant_project_context.py --user-requested`; the workflow must not call paid APIs or embed secrets in the repository.
- Refresh `docs/context/gpt/gpt_context_quant.md` only when the user explicitly requests a GPT brief refresh. Use `python scripts/context/build_context_packet.py --mode gpt-brief --user-requested --request "<current GPT task>"`; the workflow must not call paid APIs or embed secrets in the repository.

## Active Step Continuity

When `docs/roadmap_status.md` marks earlier Steps as `COMPLETE`, trust those outputs by default. Do not restart implementation or full review loops for completed Steps unless the user's latest instruction explicitly asks for Step-end validation across the roadmap.

During an active Step, inspect only the files and interfaces directly needed for that Step. If a completed Step artifact is a direct dependency, do only the smallest hard-stop check needed to confirm it does not violate current guardrails, then continue.

Minor issues found in completed Steps should be recorded as TODOs or risk notes and must not block the active Step unless they break the active Step interface or create a hard-stop violation.

`Step 2` may remain `PARTIALLY COMPLETE` because financial samples or point-in-time validation are incomplete. That status does not block technical Steps while PER/PBR/ROE or other valuation/fundamental data remain outside `technical_composite_score`, `final_composite_score`, and technical scoring.

## Concurrent Work Guard

When the user reports that another project area or roadmap Step is actively being worked on, treat that area as protected concurrent work. Inspect `git status` before editing, avoid touching those files unless the user's latest request explicitly requires it, and keep the change to the narrowest non-conflicting scope.

## Multi-Workspace Parallel Work Policy

Parallel Step implementation, review, research ingestion, audit/scope watchdog, and master integration work must use separate git worktrees and branches as defined in `docs/workspace_parallel_work_policy.md`.

Starting immediately before Step 15, every sub-agent or subproject worker must create or select the correct role branch and worktree before editing files. Do not begin work on an inherited, shared, or master workspace branch.

Read-only inspection, planning, status reporting, and policy recommendations do not require a new branch. If a compatible active role branch/worktree already exists, check or update its `WORKSPACE_MANIFEST.md` and reuse it instead of creating another branch. Create a new branch only when the role, write scope, or risk level no longer fits the active manifest.

Branch class rule for Step 15+:

- Roadmap Step implementation is the major Step branch: `codex/stepXX-<scope>` unless the master assigns a narrower pattern.
- Quant score/governance work, research ingestion, review, audit/scope watchdog, and chart runtime work are minor/support branches: `quant/stepXX-<scope>`, `research/stepXX-<scope>`, `review/stepXX-<scope>`, `audit/stepXX-<scope>`, or `chart/stepXX-<scope>`.
- Low-risk review, chart, research, and docs-only support patches may be collected on one Step-scoped minor branch, normally `minor/stepXX-<scope>`, only when the user or root/master explicitly assigns that bundled minor-patch scope and the manifest lists every allowed write path. If the patch touches runtime behavior, contracts, generated-output boundaries, roadmap verdicts, or any Level 3 risk, split it back into the narrowest role branch.
- Minor/support branches must not update roadmap status, final Step verdicts, or master integration policy unless the root/master explicitly assigns that task.
- Minor/support branches are disposable after integration: delete the local and remote branch after a successful merge unless root/master explicitly records a reason to keep it.
- Major Step branches are also disposable after their Step work is merged into the accepted integration target and no unresolved handoff depends on the branch tip. Keep only core branches: `main`, the active root/master integration branch, active unmerged role branches or worktrees, and branches with a root/master-recorded retention reason.

The master workspace is for integration, verification, and status-control only. Do not use it for experimental implementation, research exploration, review edits mixed with implementation, direct Step work, or generated report experiments.

Every non-master worktree must include a root-level `WORKSPACE_MANIFEST.md` before editing project files and must produce the required handoff output before master integration.

## Root Agent Conflict Stop

When a subproject worker or delegated agent detects a conflict with root-owned policy, root/master active work, protected concurrent work, or unrelated dirty files that cannot be safely separated, it must stop immediately and report instead of continuing.

Use `docs/root_agent_conflict_process.md` for stop triggers, the report template, and resume decisions. Do not stage, commit, reset, cleanup, or broaden the repair after a stop trigger unless the user or root/master explicitly approves the next action.

## Purpose

This workspace uses a master agent to coordinate the projects under `master_mvp`.

The master agent is responsible for repository-level direction, Git hygiene, cross-project handoffs, and project boundary control. It does not replace the more specialized agents inside each project.

Subprojects:

- `reserch_mvp`: research-ingestion specification and upstream evidence workflow
- `Quant_mvp`: quant score design, technical-review governance, valuation boundary, and config policy
- `Quant_mvp/backtest_mvp`: Quant-dependent evaluation-only conservative backtest module
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
- `backtest_mvp`: evaluation-only conservative backtest contracts, config, runner, and generated-output boundary under `Quant_mvp/backtest_mvp`
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
6. which context budget was used and whether archive/history reads were justified
7. whether `review_mvp` is requested or not

Canonical supporting documents:

- review flow: `docs/review_flow.md`
- parallel workspace policy: `docs/workspace_parallel_work_policy.md`
- root conflict stop process: `docs/root_agent_conflict_process.md`
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
- a root-agent conflict stop is unresolved or lacks a documented resume decision
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
- root-agent conflict stop:
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
- context budget:
- archive/history read:
- archive/history reason:

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
| Research source collection or paper evidence | `reserch_mvp` | `reserch_mvp/AGENTS.md`, `reserch_mvp/config/research_*.toml` |
| Research EvidenceCard intake for score governance | `Quant_mvp` | `Quant_mvp/AGENTS.md`, `Quant_mvp/config/research_intake.toml`, `Quant_mvp/agents/research/AGENTS.md` |
| Technical score definition or adoption review | `Quant_mvp` | `Quant_mvp/AGENTS.md`, `Quant_mvp/config/*.toml` |
| Evaluation-only conservative backtest module | `Quant_mvp/backtest_mvp` | `Quant_mvp/backtest_mvp/AGENTS.md`, `docs/context/domain/backtest_context.md`, `docs/step17_conservative_backtest_core.md` |
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
- User-facing thought summaries, decision rationale, progress notes, review notes, and final reports should be written in Korean by default. Do not expose private chain-of-thought; provide concise Korean reasoning summaries instead.
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
