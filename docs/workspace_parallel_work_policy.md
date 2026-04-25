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

Use the lightest operating path that still preserves the branch/worktree boundary.
The isolation rule is mandatory; duplicating every review, audit, and full
validation step for low-risk support work is not. Apply the risk-based operating
levels below before creating extra role worktrees.

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

## Scripted Branch Start Gate

Use `scripts/Start-RoleWorktree.ps1` to remove the repeated setup cost for new
role worktrees. The script creates the role branch, worktree directory, and
initial `WORKSPACE_MANIFEST.md` from one command.

Example Level 1 docs/support setup:

```powershell
.\scripts\Start-RoleWorktree.ps1 `
  -Role docs `
  -Step 15 `
  -Scope worktree-speed `
  -Lightweight `
  -AllowedWritePaths @("docs/workspace_parallel_work_policy.md", "scripts/Start-RoleWorktree.ps1") `
  -ExpectedOutput @("policy update", "worktree bootstrap helper", "branch-local commit") `
  -RequiredValidation @("PowerShell parser check", "git status/diff review")
```

Example Level 2 implementation setup:

```powershell
.\scripts\Start-RoleWorktree.ps1 `
  -Role codex `
  -Step 15 `
  -Scope ranking-core `
  -AllowedWritePaths @("src/scanner/", "tests/scanner/") `
  -ExpectedOutput @("Step 15 ranking core implementation", "branch-local commit", "worker handoff summary") `
  -RequiredValidation @("focused pytest for changed scanner tests", "forbidden-scope search")
```

Manual `git worktree add` remains allowed when the script does not fit the task,
but new worktrees should still follow the same branch naming and manifest shape.
The script refuses to start from a base ref that already tracks the shared root
`WORKSPACE_MANIFEST.md` unless `-AllowTrackedManifest` is passed, because that
case is likely to create a manifest merge conflict.


## Context Routing Before Large Tasks

For Step 19+ or other large tasks, workers should use `docs/context/context_index.md` and `docs/context/context_routing.md` before broad file reads.

Worker prompts should name `required_context` and `forbidden_context` when a routed packet is available. The worker may still use targeted search when a direct contract, status, or boundary conflict is missing or unclear.

Context routing reduces default context load; it does not weaken worktree separation, manifest scope, hard stops, generated-output boundaries, or the full Cross-Step Conflict Checkpoint required before closing major Steps.

## Branch-Local Commit Default

After a role branch finishes its assigned work, commit the branch-local
source-controlled changes by default. This commit is not a Step-end acceptance
decision; it is a checkpoint that preserves the worktree state and makes master
integration faster.

Before a branch-local commit, run only the checks needed for that branch:

- confirm the diff stays inside the manifest's allowed write paths
- run the focused validation listed in the manifest
- run a forbidden-scope search when the branch touches roadmap-gated behavior
- exclude local `WORKSPACE_MANIFEST.md`, runtime caches, generated reports, and
  unrelated dirty files unless the master explicitly promotes them

Do not require full review, audit/scope watchdog, broad validation, or Cross-Step
Conflict Checkpoint before every branch-local commit. Those heavier gates run
when the Step is about to move forward, when master integration consumes a risky
handoff, or when the operating level explicitly requires them.

Commit messages should name the Step, role, and bounded scope, for example:

```text
Step 15 docs: streamline worktree branch workflow
Step 15 scanner: add latest ranking core
Step 15 validation: add latest ranking guardrails
```

## Risk-Based Operating Levels

Worktree separation prevents conflicts, but the amount of process around each
worktree should match the change risk.

### Level 1: Lightweight support

Use this for docs-only governance support, small process automation, narrow
handoff templates, or tests/check helpers that do not touch runtime behavior,
ranking/composite/backtest/valuation logic, generated-output paths, schemas, or
cross-project handoff contracts.

Requirements:

- separate minor/support branch and worktree
- compact `WORKSPACE_MANIFEST.md`
- allowed write paths limited to the named docs/scripts/test helper files
- focused validation for changed files only
- git status/diff review before handoff
- branch-local commit after focused validation passes

When the user or root/master explicitly assigns a bundled minor-patch scope,
low-risk review, chart, research, and docs-only support patches for the same
Step may share one `minor/stepXX-<scope>` branch and worktree. The manifest must
list every allowed write path, and the work must split back into role-specific
branches if it touches runtime behavior, contracts, generated-output
boundaries, roadmap verdicts, or any Level 3 risk.

Do not pre-create review or audit worktrees for Level 1 work unless the master
explicitly assigns them or the change reveals a boundary risk.

### Level 2: Standard implementation support

Use this for normal Step implementation slices, chart runtime changes,
validation helpers that enforce roadmap-gated behavior, and support branches
that may be consumed by implementation.

Requirements:

- separate role branch and worktree
- full manifest with forbidden actions and handoff notes
- focused tests plus forbidden-scope search
- master-up summary before integration
- branch-local commit after focused validation and scope checks pass
- review or audit worktree only when required by the change risk, Step gate, or
  master instruction

### Level 3: Gate-critical or cross-project work

Use this for changes touching ranking output contracts, composite behavior,
score definitions, normalization, diagnostics, data schemas, generated-output
boundaries, backtest preparation, valuation/fundamental boundaries, or multiple
subprojects.

Requirements:

- separate implementation, review, and audit/scope watchdog worktrees as needed
- complete manifest and handoff template
- Cross-Step Conflict Checkpoint at important stage boundaries
- affected validation reruns after required fixes
- Step-end gate sequence before final integrated Step commit
- branch-local commits may still be made before Step-end, but they do not replace
  Step-end validation, review, audit, or master acceptance

If a Level 1 or Level 2 task expands into Level 3 territory, stop and either
update the manifest with master approval or create a new correctly scoped
worktree.

## Step 15+ Branch Separation Process

Step 15 is the first roadmap stage allowed to produce latest ranking output.
Because Step 15 and later stages can mix upstream evidence, runnable chart
runtime code, review findings, and integration status updates, every Step 15+
task must start by assigning one role per branch before file edits begin.

Branch classes:

- Major Step branch: the roadmap Step implementation branch that carries the bounded Step deliverable, normally `codex/stepXX-<scope>`.
- Minor/support branch: a role-specific branch for Quant score/governance, research ingestion, chart runtime, review, audit/scope watchdog, or docs-only support. Minor/support branches feed master integration but do not own final Step status.
- Unified minor patch branch: a Step-scoped minor/support branch, normally `minor/stepXX-<scope>`, for explicitly assigned low-risk review, chart, research, or docs-only support patches that are small enough to share one manifest and one handoff.
- Core branch: a branch retained after integration because it is `main`, the active root/master integration branch, an active unmerged role branch/worktree, or a branch with a root/master-recorded audit or reproduction retention reason.

Required role separation:

| Role | Branch class | Worktree purpose | Branch pattern | Primary write area |
| --- | --- | --- | --- | --- |
| Step implementation | Major | one bounded roadmap Step or implementation slice | `codex/stepXX-<scope>` | Step-owned docs, source, tests |
| Quant score/governance | Minor/support | Quant score design, adoption synthesis, technical review governance, or config-policy support not owned by the major Step branch | `quant/stepXX-<scope>` | `Quant_mvp/`, Step-owned Quant docs/config/tests |
| Research ingestion | Minor/support | upstream evidence or EvidenceCard material only | `research/stepXX-<scope>` | `reserch_mvp/`, research handoff docs |
| Chart runtime | Minor/support | scanner, cache, ranking, chart, CLI, GUI implementation | `chart/stepXX-<scope>` | `chart_mvp/` runtime code/tests/config |
| Review | Minor/support | code review findings or explicitly assigned minimal repair | `review/stepXX-<scope>` | `review_mvp/` or review notes |
| Audit / scope watchdog | Minor/support | scope, roadmap, terminology, and boundary checks | `audit/stepXX-<scope>` | audit reports or compact packets |
| Minor patch bundle | Minor/support | explicitly assigned low-risk review, chart, research, or docs-only support patches for one Step | `minor/stepXX-<scope>` | manifest-listed support paths only |
| Master integration | Integration only | merge/validation/status-control only | existing master workspace or `docs/stepXX-integration` when a docs-only branch is assigned | root governance/status docs |

Process:

1. Read `docs/project_checklist.md`, `docs/roadmap_status.md`, and this policy.
2. Classify the task as major Step implementation or minor/support work: Quant score/governance, research, chart runtime, review, audit, bundled minor patch, or master integration.
3. Create or select a worktree whose branch matches exactly one role.
4. Add a root-level `WORKSPACE_MANIFEST.md` before editing project files.
5. Keep each worktree's writes inside its manifest and role boundary.
6. Produce the role-specific handoff before master integration consumes the branch.
7. Merge into the master workspace one branch at a time, with focused validation and a Cross-Step Conflict Checkpoint between branches.

Use `scripts/Start-RoleWorktree.ps1` from the master workspace when practical to
create the branch, worktree, and initial manifest in one command. Manual setup is
still allowed, but the branch name and manifest must match this policy.

Do not reuse a Step implementation branch for chart runtime fixes unless the
manifest already declares chart runtime ownership for that exact Step slice. Do
not reuse quant, chart, research, review, audit, or unified minor patch branches
for roadmap status updates.
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

Create review and audit worktrees when their work is ready to start, not as idle
placeholders. A Step may list expected review/audit branches up front, but those
branches should be materialized only when there is a specific diff, packet, or
handoff to inspect.

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

For Level 1 lightweight support work, keep the manifest compact and refer back
to this policy for common hard stops instead of duplicating every global rule.
The manifest must still include the branch, task type, active Step, allowed
write paths, forbidden actions, expected output, and required validation.

By default, the root `WORKSPACE_MANIFEST.md` is local workspace contract
metadata. Do not stage or commit it unless the master explicitly asks for a
source-controlled manifest artifact. If a durable handoff record is needed,
prefer a branch-specific note or integration report under an assigned docs path.
Committing the shared root manifest from multiple role branches creates
predictable merge conflicts.

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
- `research/stepXX-...`
- `chart/stepXX-...`
- `audit/stepXX-...`
- `docs/...`
- `minor/stepXX-...`
- `hotfix/...`

Good examples:

- `codex/step15-ranking-core`
- `chart/step15-ranking-runtime`
- `quant/step15-governance`
- `review/step15-ranking`
- `research/step15-handoff`
- `audit/step15-scope`
- `docs/step15-worktree-speed`
- `minor/step16-support-patches`
- `hotfix/step13-report-guardrail`

Bad examples to avoid:

- `codex/test`
- `codex/fix`
- `new-work`
- `review`
- `temp`

Branches should name the role and the bounded task. A branch name that cannot explain its purpose is not ready for parallel work.

Existing non-conforming branch names may be finished if renaming would disrupt
active work, but new Step 15+ branches should use the role/step/scope pattern.

## Integration Order

1. Worker branch completes local task.
2. Worker runs branch-local focused validation and scope checks.
3. Worker commits source-controlled branch changes by default, excluding local manifests and generated/runtime outputs unless explicitly promoted.
4. Worker reports changed files, tests run, risks, handoff notes, and commit SHA.
5. Master workspace accepts one branch into the integration queue.
6. Master runs master-up preflight before detailed review.
7. Master merges one branch at a time.
8. Master runs focused integration checks for the merged branch.
9. Master records the Cross-Step Conflict Checkpoint result before accepting the next branch.
10. Review workspace checks diff and guardrails when required by the operating level, Step gate, or master instruction.
11. Audit / scope watchdog checks for roadmap bypass, scope creep, forbidden outputs, and terminology laundering when required by the operating level, Step gate, or master instruction.
12. Required fixes go back to the narrowest responsible implementation, chart, review, or support worktree unless master/root explicitly approves a direct integration repair.
13. Before moving to the next roadmap Step, master runs the Step-end review/check sequence: integration validation, Cross-Step Conflict Checkpoint, required review/audit, required fixes, affected reruns, final Step verdict, and context refresh.
14. Master commits final integrated Step state after the Step-end gate passes.
15. After a major Step branch or minor/support branch is successfully merged and
    no unresolved handoff depends on the branch tip, delete the merged local and
    remote branch unless it is a core branch or root/master records a specific
    retention reason.

Do not merge a second worker branch until the current branch's integration risk and conflicts are understood.

After integration is complete, the repository should retain only core branches.
Merged `codex/stepXX-<scope>` major branches, role-specific minor/support
branches, and unified `minor/stepXX-<scope>` branches are cleanup targets once
their accepted target contains the work and their handoff, audit, or
reproduction value no longer depends on the branch tip.

## Master Integration Queue

Master tracks each branch through a short queue state so bottlenecks are visible:

```text
handoff-ready
-> preflight passed
-> merged
-> focused validation passed
-> checkpoint passed
-> queued for step-end
```

Each branch should move through this queue independently. If a branch stops, record the exact state and blocking reason in the master-up summary or integration notes before taking another branch.

Use two validation layers:

- Branch integration validation: focused tests/checks for the branch just merged, plus any forbidden-scope search or generated-output check triggered by that branch.
- Step-end validation: broad Step validation after all queued branches for the Step are integrated and required fixes have been rerun.

Do not repeat full Step-end validation after every small branch by default. Escalate a branch to broader validation only when it changes a shared contract, creates a merge conflict, touches gate-critical behavior, or reveals a blocking review/audit finding.

Master stays in the integration role. Required review/audit findings should be sent back to the narrowest responsible worktree or branch for repair. Master may apply a direct fix only when the user or root/master explicitly approves that minimal repair scope and the change remains isolated from unrelated dirty files.

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
