# Multi-Workspace Parallel Work Policy

This policy prevents Step implementation, review, research ingestion, audit, and master integration work from being mixed in one workspace.

It applies whenever more than one agent, worker, or task stream may run in parallel, and whenever a task can affect roadmap-gated behavior.

## Core Rule

Use one git worktree and one branch per parallel task.

Before a sub-agent or subproject worker edits files, it must pass the Branch Start Gate:

1. Identify whether the task is a major Step task or a minor/support task.
2. Create or select the matching branch and worktree.
3. Add or update the worktree's root `WORKSPACE_MANIFEST.md`.
4. Confirm the write scope matches the branch role.

Do not switch a workspace from one role to another after work has started. If implementation work becomes review work, create a review worktree. If review finds a fix that is not explicitly assigned to the reviewer, hand it back to the implementation workspace or create a separate fix workspace.

The master workspace is integration, verification, and status-control only.

## Master Workspace Role

The master workspace is `C:\Users\jjaew\Project\master_mvp`.

Use the master workspace for:

- checking roadmap and checklist state
- reviewing branch readiness
- merging completed worker branches
- running final focused or full validation
- running the Cross-Step Conflict Checkpoint
- refreshing current project context after Step-end validation
- committing final integrated changes

Do not use the master workspace for:

- experimental implementation
- research exploration
- review edits mixed with implementation
- direct Step work
- generated report experiments

If the master workspace contains unrelated dirty files, do not broaden the task to clean them up. Separate the requested policy, validation, or integration work from existing dirty state and report any conflict that cannot be isolated.

## Worktree Isolation Rule

Each parallel task must use a separate git worktree and branch.

Starting with Step 15, this is required even when the task streams are
sequentially coordinated by the same master agent. Research ingestion, chart
runtime work, Step implementation, review, audit/scope watchdog, and master
integration must not share a writable worktree or branch.

Recommended structure:

```text
C:\Users\jjaew\Project\
  master_mvp\
  worktrees\
    step14_adoption_impl_a\
    step14_adoption_impl_b\
    review_step14\
    research_ingestion\
    audit_scope_watchdog\
```

Example commands:

```powershell
cd C:\Users\jjaew\Project\master_mvp

mkdir ..\worktrees

git worktree add ..\worktrees\step14_adoption_impl_a -b codex/step14-adoption-impl-a
git worktree add ..\worktrees\step14_adoption_impl_b -b codex/step14-adoption-impl-b
git worktree add ..\worktrees\review_step14 -b review/step14
git worktree add ..\worktrees\research_ingestion -b research/ingestion-followup
git worktree add ..\worktrees\audit_scope_watchdog -b audit/scope-watchdog
```

## Step 15+ Branch Separation Process

Step 15 is the first roadmap stage allowed to produce latest ranking output.
Because Step 15 and later stages can mix upstream evidence, runnable chart
runtime code, review findings, and integration status updates, every Step 15+
task must start by assigning one role per branch before file edits begin.

Branch classes:

- Major Step branch: the roadmap Step implementation branch that carries the bounded Step deliverable, normally `codex/stepXX-<scope>`.
- Minor/support branch: a role-specific branch for Quant score/governance, research ingestion, chart runtime, review, audit/scope watchdog, or docs-only support. Minor/support branches feed master integration but do not own final Step status.

Required role separation:

| Role | Branch class | Worktree purpose | Branch pattern | Primary write area |
| --- | --- | --- | --- | --- |
| Step implementation | Major | one bounded roadmap Step or implementation slice | `codex/stepXX-<scope>` | Step-owned docs, source, tests |
| Quant score/governance | Minor/support | Quant score design, adoption synthesis, technical review governance, or config-policy support not owned by the major Step branch | `quant/stepXX-<scope>` | `Quant_mvp/`, Step-owned Quant docs/config/tests |
| Research ingestion | Minor/support | upstream evidence or EvidenceCard material only | `research/stepXX-<scope>` | `reserch_mvp/`, research handoff docs |
| Chart runtime | Minor/support | scanner, cache, ranking, chart, CLI, GUI implementation | `chart/stepXX-<scope>` | `chart_mvp/` runtime code/tests/config |
| Review | Minor/support | code review findings or explicitly assigned minimal repair | `review/stepXX-<scope>` | `review_mvp/` or review notes |
| Audit / scope watchdog | Minor/support | scope, roadmap, terminology, and boundary checks | `audit/stepXX-<scope>` | audit reports or compact packets |
| Master integration | Integration only | merge/validation/status-control only | existing master workspace or `docs/stepXX-integration` when a docs-only branch is assigned | root governance/status docs |

Process:

1. Read `docs/project_checklist.md`, `docs/roadmap_status.md`, and this policy.
2. Classify the task as major Step implementation or minor/support work: Quant score/governance, research, chart runtime, review, audit, or master integration.
3. Create or select a worktree whose branch matches exactly one role.
4. Add a root-level `WORKSPACE_MANIFEST.md` before editing project files.
5. Keep each worktree's writes inside its manifest and role boundary.
6. Produce the role-specific handoff before master integration consumes the branch.
7. Merge into the master workspace one branch at a time, with focused validation and a Cross-Step Conflict Checkpoint between branches.

Do not reuse a Step implementation branch for chart runtime fixes unless the
manifest already declares chart runtime ownership for that exact Step slice. Do
not reuse quant, chart, research, review, or audit branches for roadmap status updates.
If review finds a required fix, route the fix back to the narrowest responsible
implementation or chart worktree, or create a new `codex/stepXX-fix-...` /
`chart/stepXX-fix-...` branch with its own manifest.

Suggested Step 15 worktree set:

```powershell
cd C:\Users\jjaew\Project\master_mvp

git worktree add ..\worktrees\step15_ranking_impl -b codex/step15-ranking-impl
git worktree add ..\worktrees\step15_quant_governance -b quant/step15-governance
git worktree add ..\worktrees\step15_chart_runtime -b chart/step15-ranking-runtime
git worktree add ..\worktrees\step15_research_handoff -b research/step15-handoff
git worktree add ..\worktrees\step15_review -b review/step15-ranking
git worktree add ..\worktrees\step15_audit -b audit/step15-scope
```

## Workspace Types

### Master Integration Workspace

Purpose:

- verify roadmap order, branch readiness, integration safety, and final repository state
- merge completed worker branches one at a time
- run final validation and commit the integrated result

Allowed write paths:

- root governance docs only when explicitly assigned
- roadmap/checklist/status docs only for approved status-control or process-control updates
- context snapshot files only after required validation
- source-controlled integration notes or review packets when required

Read-only paths:

- worker implementation files before their branch is selected for merge
- research, review, and audit branch artifacts before handoff acceptance
- generated outputs unless explicitly promoted as source-controlled fixtures

Forbidden actions:

- direct Step implementation
- experimental score, ranking, backtest, valuation, or report generation work
- research exploration
- review edits mixed into implementation branches
- merging more than one worker branch before the current branch has passed focused validation and conflict checks

Expected handoff output:

- master integration decision
- validation summary
- Cross-Step Conflict Checkpoint result
- commit SHA when a final integrated commit is made
- context refresh status after Step-end validation

### Step Implementation Workspace

Purpose:

- implement one assigned Step task or one narrow slice of that Step
- keep implementation changes separate from review, research, audit, and master status-control work

Allowed write paths:

- paths listed in that workspace's `WORKSPACE_MANIFEST.md`
- Step-specific docs, source files, and tests explicitly assigned to the worker
- small source-controlled fixtures only when the Step contract allows them

Read-only paths:

- `AGENTS.md`, `docs/project_checklist.md`, and `docs/roadmap_status.md`, unless the worker has explicit root/master approval
- completed Step artifacts except for the smallest hard-stop dependency check
- review, audit, and research handoff outputs unless consuming them is explicitly assigned
- unrelated subprojects

Forbidden actions:

- roadmap status changes unless explicitly assigned
- ranking output before Step 15
- latest ranking output before Step 15
- backtest before Step 17
- valuation or fundamental scoring before Step 18
- financial/fundamental data entering `technical_composite_score` or `final_composite_score`
- buy, sell, or trading signal generation unless a later approved Step explicitly allows it
- alpha evidence claims from diagnostics, review material, or paper-reported backtests

Expected handoff output:

- completed worker handoff template
- changed files
- tests/checks run and not run
- forbidden-scope check result
- known risks and integration notes

### Review Workspace

Purpose:

- review a completed worker branch or diff for correctness, guardrail compliance, and merge readiness
- keep review findings separate from implementation work

Allowed write paths:

- review reports, review notes, or branch-local comments assigned to the review task
- minimal fix files only when the reviewer is explicitly assigned a narrow repair

Read-only paths:

- implementation source and tests unless a narrow repair is explicitly assigned
- roadmap status files unless the review task explicitly includes status-control review
- research and audit outputs unless they are supplied as review evidence

Forbidden actions:

- broad implementation fixes without assignment
- silent score redefinition
- ranking, latest ranking, backtest, valuation, or signal generation
- mixing implementation and review history in one branch
- changing roadmap status or Step completion verdicts

Expected handoff output:

- files reviewed
- violations found
- required fixes
- optional improvements
- merge readiness verdict

### Research Ingestion Workspace

Purpose:

- collect, classify, and document upstream research evidence
- produce EvidenceCard material and ingestion artifacts that can be reviewed before adoption work

Allowed write paths:

- research query config
- research classification config
- EvidenceCard-related docs
- ingestion reports
- reject logs

Read-only paths:

- Step adoption logic
- ranking logic
- composite scoring logic
- backtest logic
- valuation or fundamental scoring logic
- roadmap status files unless a master/root task explicitly assigns status documentation

Forbidden actions:

- directly modifying Step adoption logic
- directly modifying ranking logic
- directly modifying `technical_composite_score` or `final_composite_score` logic
- directly modifying backtest logic
- directly modifying valuation or fundamental scoring
- converting EvidenceCards into final Step decisions without the Step adoption workflow

Expected handoff output:

- EvidenceCard or ingestion report summary
- source/reject-log summary
- explicit note that research evidence is upstream material only
- unresolved source-quality risks

### Audit / Scope Watchdog Workspace

Purpose:

- check roadmap bypass, scope creep, forbidden outputs, terminology laundering, generated-output boundaries, and root-boundary violations
- keep audit findings separate from implementation and review edits

Allowed write paths:

- audit reports
- scope watchdog verdicts
- compact review packets or notes produced by the assigned audit task

Read-only paths:

- implementation files unless the audit task explicitly assigns a narrow policy repair
- review findings unless audit is checking their completeness
- research outputs unless audit is checking evidence boundaries
- roadmap status files unless master/root explicitly assigns status-control work

Forbidden actions:

- implementing Step logic
- broad review fixes
- ranking, latest ranking, backtest, valuation, or signal generation
- silently rewriting worker scope after work has begun
- laundering terms such as diagnostic, review material, research evidence, or context into adoption, ranking, signal, alpha, cheap, value, or undervalued claims

Expected handoff output:

- watchdog verdict
- files and branches checked
- hard-stop or scope findings
- required fixes or stop recommendation
- remaining non-blocking risks

## WORKSPACE_MANIFEST.md Rule

Every non-master worktree must include a root-level `WORKSPACE_MANIFEST.md` before editing project files.

The manifest is the branch-local scope contract for that workspace. It must be updated when the assigned scope changes. If a worker needs to write outside the manifest, it must stop and request root/master approval or create a new workspace with the correct scope.

Minimum manifest schema:

```markdown
# WORKSPACE_MANIFEST

workspace_id:
branch:
task_type:
active_step:
owner_or_worker:
created_from_commit:

## Purpose

## Allowed write paths

## Read-only paths

## Forbidden actions

## Expected output

## Required validation

## Handoff notes
```

Concrete Step 14 implementation example:

```markdown
# WORKSPACE_MANIFEST

workspace_id: step14_adoption_impl_a
branch: codex/step14-adoption-impl-a
task_type: step_implementation
active_step: Step 14 Adoption Synthesis
owner_or_worker:
created_from_commit:

## Purpose

Implement one assigned Step 14 Adoption Synthesis slice without creating ranking, scoring, backtest, valuation, or signal outputs.

## Allowed write paths

- docs/step14_adoption_synthesis.md
- src/selection/adoption_synthesis_contracts.py
- src/selection/adoption_synthesis.py
- tests/selection/test_step14_adoption_synthesis_contracts.py
- tests/selection/test_step14_adoption_synthesis.py

## Read-only paths

- AGENTS.md
- docs/project_checklist.md
- docs/roadmap_status.md
- Step 13 output artifacts, except as Step 14 input material
- ranking, backtest, valuation, and research-ingestion implementation paths

## Forbidden actions

- ranking output
- latest ranking
- technical_composite_score
- final_composite_score
- backtest
- valuation / fundamental scoring
- buy / sell / trading signal
- alpha evidence
- roadmap status changes unless explicitly assigned

## Expected output

- Step 14 adoption synthesis implementation slice
- focused tests for the assigned contract
- worker handoff summary

## Required validation

- focused tests for changed Step 14 files
- forbidden-scope check
- Cross-Step Conflict Checkpoint before master-up when the implementation is ready

## Handoff notes
```

## Branch Naming Policy

Recommended branch prefixes:

- `codex/stepXX-...`
- `quant/stepXX-...`
- `review/stepXX-...`
- `research/...`
- `audit/...`
- `docs/...`
- `hotfix/...`

Good examples:

- `codex/step14-adoption-impl-a`
- `quant/step15-governance`
- `review/step14`
- `research/ingestion-followup`
- `audit/scope-watchdog`
- `docs/parallel-workspace-policy`
- `hotfix/step13-report-guardrail`

Bad examples to avoid:

- `codex/test`
- `codex/fix`
- `new-work`
- `review`
- `temp`

Branches should name the role and the bounded task. A branch name that cannot explain its purpose is not ready for parallel work.

## Integration Order

1. Worker branch completes local task.
2. Worker reports changed files, tests run, risks, and handoff notes.
3. Review workspace checks diff and guardrails.
4. Audit / scope watchdog checks for roadmap bypass, scope creep, forbidden outputs, and terminology laundering.
5. Master workspace merges one branch at a time.
6. Master runs focused tests.
7. Master runs Cross-Step Conflict Checkpoint.
8. Master updates context only after validation.
9. Master commits final integrated state.

Do not merge a second worker branch until the current branch's integration risk and conflicts are understood.

## Cross-Step Conflict Checkpoint

The Cross-Step Conflict Checkpoint must run:

- before consuming downstream handoff
- before closing a Step
- after major review fixes
- before roadmap status updates
- before context refresh

Command template:

```powershell
python scripts/build_review_packet.py --step "Step 14" --stage "<stage name>"
```

Use `docs/cross_step_conflict_check.md` to interpret the packet and record whether the current work conflicts with roadmap order, hard stops, cross-project handoffs, generated-output boundaries, or unresolved carry-forward risks.

## Research Separation Rule

Research ingestion work is upstream only.

Research work may modify:

- research query config
- research classification config
- EvidenceCard-related docs
- ingestion reports
- reject logs

Research work must not directly modify:

- Step adoption logic
- ranking logic
- composite scoring
- backtest
- valuation scoring
- final Step decisions

EvidenceCards are research material, not score definitions, adoption decisions, ranking inputs, alpha evidence, or valuation verdicts.

## Review Separation Rule

Review workspaces should not directly implement broad fixes unless explicitly assigned.

Review output should include:

- files reviewed
- violations found
- required fixes
- optional improvements
- merge readiness verdict

Required fixes should go back to the narrowest responsible implementation workspace unless the reviewer has an explicit repair assignment.

## Worker Handoff Template

```markdown
## Worker Handoff

workspace_id:
branch:
task_type:
base_commit:
changed_files:
tests_run:
tests_not_run:
forbidden_scope_check:
known_risks:
integration_notes:
ready_for_review: yes/no
```

The handoff must make forbidden-scope status explicit. For Step 14, it must state that the worker did not create ranking output, latest ranking output, `technical_composite_score`, `final_composite_score`, backtest, valuation/fundamental scoring, trading signals, alpha evidence, or roadmap status changes unless explicitly assigned.
