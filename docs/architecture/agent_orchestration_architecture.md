# Agent Orchestration Architecture

This document defines the active replacement architecture for project-local
Codex skills. The redesign now uses the coordinator as the default root entry
point and expands role by role before any existing project-local skill is
deleted or renamed.

Existing project gates remain domain authorities, but they are compatibility
targets selected and bounded by the architecture chain rather than direct root
entry points for routine work.

## Replacement Activation State

Status: `active_compatibility_mode`.

Activation date: 2026-05-05.

Primary root process:

1. `agent-coordinator` normalizes the user goal and selects the domain gate.
2. `agent-planner` produces the ordered scope-locked plan.
3. `agent-plan-review` approves or blocks supervisor handoff.
4. `agent-supervisor` prepares bounded worker packets.
5. `agent-worker-pool` normalizes `coder`, `validator`, `tracker`, and
   `reporter` roles.
6. `agent-reporter` collects compact worker results for supervisor/user
   reporting.
7. `agent-replacement` governs migration of old skill/process entry points.

Existing gates such as `quant-work-cycle`, `quant-review-gate`, and v0.3
domain gates are still used, but only as selected domain gates inside the
architecture packet. This starts replacement without deleting existing gate
authority.

## Resource Usage Profile

Architecture packets carry this role-level resource profile. The stored values
use the runtime effort vocabulary: `low`, `medium`, `high`, and `xhigh`.

| Role | Resource usage |
| --- | --- |
| `coordinator` | `medium` |
| `planner` | `xhigh` |
| `plan_review` | `high` |
| `supervisor` | `xhigh` |
| `coder` | `medium` |
| `validator` | `medium` |
| `reporter` | `low` |
| `tracker` | `low` |

## Target Shape

```text
user
  -> coordinator
  -> planner
  <-> plan-review
  -> supervisor/root-agent when plan-review passes without approval triggers
  -> user only when review fixes or separate approvals are required
  -> worker pool
       -> coder
       -> tracker
       -> validator
       -> tracker
       -> reporter
  -> reporter result collection
  -> supervisor and user summary
```

## Design Goals

- Keep user intent separate from execution details.
- Keep planning separate from plan review.
- Keep supervisor orchestration separate from worker implementation.
- Keep reporter-owned worker result collection separate from raw worker output.
- Prevent worker context from overflowing into parent roles.
- Preserve root hard stops and current route state while the architecture is
  replacing existing skills.
- Replace current Codex skill entry points by routing them through the
  architecture chain while preserving domain gate authority.

## Context Firewall

Worker context must not flow upward as raw context. Parent roles receive only
status, changed_scope, evidence, and next_request.

Allowed upward fields:

- `status`: complete, partial, failed, or blocked
- `changed_scope`: files, directories, or artifacts touched
- `evidence`: validation commands and compact results
- `next_request`: one parent decision or approval request

Forbidden upward content:

- raw worker logs
- full exploratory notes
- failed attempts unless they affect the next decision
- long private reasoning
- generated output dumps
- archive or raw-data context

If a role receives excessive lower-level context, it must compress the input
into the allowed upward fields before passing it further upward.

## Phase 1: Coordinator

The coordinator is the user-intent entry point. It converts natural language
into a compact planner prompt and names the current project-local gate that
still owns execution authority.

Coordinator responsibilities:

- normalize the user goal
- classify the task as `planning/read-only`, `narrow edit`, or
  `Step/gate closure`
- preserve the active route and hard stops
- select the current compatibility gate, or state `none yet`
- define allowed and forbidden scope for planning
- define validation expectations for the planner
- attach the context firewall rules
- require Korean final reporting

Coordinator non-goals:

- no code implementation
- no plan approval
- no worker supervision
- no validation acceptance
- no commits, fetches, pulls, or pushes
- no raw worker-context ingestion

## Phase 2: Planner

The planner will consume only the coordinator packet and produce an ordered
work plan. The planner must not execute work. It must prepare a plan-review
handoff with scope, sequence, validation commands, risks, and required
approvals.

Planner responsibilities:

- consume only the coordinator packet
- preserve the selected compatibility gate
- produce a scope lock from coordinator allowed and forbidden scope
- produce ordered plan steps
- produce validation plan items
- produce a plan-review handoff
- block supervisor handoff when coordinator approval is still required

Planner non-goals:

- no code implementation
- no self-approval
- no worker supervision
- no validation acceptance
- no commits, fetches, pulls, or pushes

## Phase 3: Plan Review

Plan Review consumes only the planner packet and inspects it before
implementation. It checks direction, scope, hard stops, route alignment,
missing validation, context-firewall compliance, and whether the plan can be
safely handed to the supervisor.

Plan Review responsibilities:

- consume only the planner packet
- verify current route and selected gate are preserved
- verify scope lock allowed and forbidden boundaries are present
- verify hard stops remain forbidden unless separate approval is required
- verify ordered plan and validation plan are present
- verify planner did not pre-approve supervisor execution
- return exact planner fixes for failed review items
- approve supervisor handoff only when review passes and no approval trigger
  exists

Plan Review non-goals:

- no code implementation
- no plan mutation
- no worker supervision
- no final validation acceptance
- no commits, fetches, pulls, or pushes

Do not require user approval for every clean plan. Require user approval only
when a review item failed and the plan must be changed before execution, or
when the requested change crosses a boundary that already requires separate
approval.

## Phase 4: Supervisor

The supervisor/root-agent consumes only an approved `plan_review_packet` and
prepares bounded worker packets. It owns workflow order, retry decisions, fix
passes, and final acceptance routing, but it does not perform the worker tasks
itself.

Supervisor responsibilities:

- consume only the plan-review packet
- execute only when `review_status` is `approved_for_supervisor`
- execute only when `supervisor_handoff.ready` is `true`
- block when `user_approval.required` is `true`
- preserve current route, selected gate, scope lock, ordered plan, validation
  plan, hard stops, and context firewall
- pass approved planner steps to coder and validator as `assigned_plan_steps`
- create bounded worker packets for `coder`, `validator`, `reporter`, and
  `tracker`
- require compact worker results only: `status`, `changed_scope`, `evidence`,
  and `next_request`
- keep Git remote and finalize actions disabled

Supervisor non-goals:

- no code implementation
- no direct validation execution
- no final completion acceptance
- no raw worker-context ingestion
- no commits, fetches, pulls, or pushes

## Phase 5: Worker Pool

Workers are tools for the supervisor, not independent route owners.

- `coder`: implements only inside the assigned scope and approved
  `assigned_plan_steps`
- `validator`: runs assigned checks, compares coder output to project
  direction, hard stops, scope lock, assigned validation commands, and
  `assigned_plan_steps`, and returns validation evidence
- `reporter`: owns worker_result collection and produces compact final reports
  from approved summaries
- `tracker`: records state transitions, dependencies, blockers, and next action

Worker Pool responsibilities:

- consume only the supervisor packet
- verify the worker packet set contains `coder`, `validator`, `reporter`, and
  `tracker`
- verify supervisor execution policy keeps fetch, pull, push, commit, and
  stage disabled
- verify every worker has allowed scope, forbidden scope, validation commands,
  required output, and compact result contract
- verify a ready coder has non-empty `assigned_plan_steps`
- provide a coder tool that applies explicit supervisor-approved file
  operations only inside locked coder scope and approved plan steps
- provide a validator tool that blocks coder results that drift from active
  route direction, hard stops, locked scope, or approved plan steps
- provide a tracker tool that records coder completion, advances validation,
  records validator completion, and advances reporting
- normalize every worker packet into a role spec
- block worker execution when supervisor is blocked, worker packets are
  incomplete, execution policy is unsafe, or result contracts leak raw context

Worker Pool non-goals:

- no planner- or supervisor-level code implementation
- no validator execution
- no final report generation
- no persistent tracking store
- no raw worker-context ingestion
- no commits, fetches, pulls, or pushes

Workers must return compact summaries, not raw context. The reporter owns
worker_result collection before any worker output reaches the supervisor or
user.

## Phase 6: Reporter Result Collection

The reporter consumes only the `worker_pool_packet` and compact
`worker_result` summaries from coder, validator, and tracker. The reporter owns worker_result collection and
converts approved worker outputs into a supervisor/user report without exposing
raw worker context upward. The reporter emits its own reporter `worker_result`
after the report gate passes or blocks.

Reporter responsibilities:

- consume only ready role specs from the worker pool
- collect coder implementation summaries after coder work
- collect validator verification and quality evidence after validator work
- collect tracker status, blockers, dependencies, and next request
- require tracker evidence that the workflow reached `ready_for_reporter`
- validate the worker-pool context firewall
- block oversized compact fields before summary generation
- draft the compact Korean supervisor/user report
- block unknown worker roles, missing result fields, raw logs, raw context,
  generated output dumps, archive/raw-data context, and private reasoning

Reporter non-goals:

- no code implementation
- no validation execution
- no direct retry or final acceptance decision
- no raw worker-context forwarding
- no commits, fetches, pulls, or pushes

The required worker order is:

1. `coder` implements inside assigned scope and approved `assigned_plan_steps`.
2. `tracker` records coder completion and advances the workflow to validator.
3. `validator` verifies coder output, quality, project direction, hard-stop
   safety, locked scope, and assigned step coverage.
4. `tracker` records validator completion and advances the workflow to
   reporter.
5. `reporter` collects approved results and drafts reports.

## Phase 7: Skill Replacement

Existing Codex skills are compatibility targets inside the active architecture.
Replacement has started in compatibility mode because these artifacts exist:

- coordinator skill and validator
- planner skill and validator
- plan-review skill and validator
- supervisor skill and validator
- worker role specs and validators
- reporter result collection contract and validator
- architecture-level replacement gate
- migration map from existing process entry points to new roles

Replacement rules:

- replace one entry point or owner at a time
- keep old and new paths side by side until validation passes
- do not delete a gate until its authority is represented in the new role chain
- preserve hard stops, route ownership, validation evidence, and Korean report
  discipline
- never use replacement to expand universe, data ingestion, live trading,
  production activation, or valuation/fundamental activation

## Migration Map

| Existing entry point | New architecture owner | Compatibility target |
| --- | --- | --- |
| Root task intake | `agent-coordinator` | selected domain gate |
| Manual planning | `agent-planner` | selected domain gate validation plan |
| Ad hoc plan review | `agent-plan-review` | hard-stop and scope checks |
| Root orchestration | `agent-supervisor` | `quant-work-cycle` when implementation is required |
| Direct implementation | `agent-worker-pool` `coder` | supervisor-approved file operations only |
| Direct validation | `agent-worker-pool` `validator` | assigned validator commands |
| Informal status updates | `agent-worker-pool` `tracker` | compact workflow state |
| Final user summary | `agent-reporter` | Korean compact report |
| Process migration | `agent-replacement` | old gates kept as domain authorities |

Detailed one-by-one migration status is tracked in
`.agents/skills/agent-replacement/MIGRATION_STATUS.md`.

## Coordinator Planner Packet

```yaml
coordinator_packet:
  user_goal: "<normalized user goal>"
  task_class: "planning/read-only | narrow edit | Step/gate closure"
  current_route: "<active route or named exception>"
  selected_gate: "<project-local skill gate or none yet>"
  resource_usage_profile:
    coordinator: "medium"
    planner: "xhigh"
    plan_review: "high"
    supervisor: "xhigh"
    coder: "medium"
    validator: "medium"
    reporter: "low"
    tracker: "low"
  allowed_scope:
    - "<file, directory, or role boundary>"
  forbidden_scope:
    - "<hard stop or out-of-scope boundary>"
  planner_must_output:
    - "ordered plan"
    - "scope lock"
    - "validation plan"
    - "handoff packet for plan-review"
  validation_expectations:
    - "<required command or not_applicable reason>"
  context_firewall:
    upward_allowed:
      - "status"
      - "changed_scope"
      - "evidence"
      - "next_request"
    upward_forbidden:
      - "raw worker logs"
      - "full exploratory notes"
      - "generated output dumps"
  korean_final_report: true
  open_questions:
    - "<none or exact blocker>"
```

## Coordinator Code Surface

The first executable coordinator surface is:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-coordinator/scripts/coordinator.py --user-goal "<goal>" --format yaml
```

It emits a `coordinator_packet` only. It does not edit files, call workers,
approve plans, validate task outputs, stage, commit, fetch, pull, or push.

## Planner Code Surface

The first executable planner surface is:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-planner/scripts/planner.py --coordinator-packet-json "<json>" --format yaml
.venv\Scripts\python.exe .agents/skills/agent-coordinator/scripts/coordinator.py --user-goal "<goal>" --format json | .venv\Scripts\python.exe .agents/skills/agent-planner/scripts/planner.py --coordinator-packet-json - --format yaml
```

It emits a `planner_packet` only. It does not edit files, call workers, approve
its own plan, validate task outputs, stage, commit, fetch, pull, or push.

## Plan Review Code Surface

The first executable plan-review surface is:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-plan-review/scripts/plan_review.py --planner-packet-json "<json>" --format yaml
.venv\Scripts\python.exe .agents/skills/agent-coordinator/scripts/coordinator.py --user-goal "<goal>" --format json | .venv\Scripts\python.exe .agents/skills/agent-planner/scripts/planner.py --coordinator-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-plan-review/scripts/plan_review.py --planner-packet-json - --format yaml
```

It emits a `plan_review_packet` only. It does not edit files, call workers,
validate task outputs, stage, commit, fetch, pull, or push. A clean review may
set `supervisor_handoff.ready` to `true`; failed review items return to the
planner with exact fixes, and separate-approval boundaries stay blocked until
approved.

## Supervisor Code Surface

The first executable supervisor surface is:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-supervisor/scripts/supervisor.py --plan-review-packet-json "<json>" --format yaml
.venv\Scripts\python.exe .agents/skills/agent-coordinator/scripts/coordinator.py --user-goal "<goal>" --format json | .venv\Scripts\python.exe .agents/skills/agent-planner/scripts/planner.py --coordinator-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-plan-review/scripts/plan_review.py --planner-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-supervisor/scripts/supervisor.py --plan-review-packet-json - --format yaml
```

It emits a `supervisor_packet` only. It does not edit files, execute workers,
validate final outputs, stage, commit, fetch, pull, or push. A clean supervisor
packet preserves the approved planner `ordered_plan` and prepares bounded
worker packets for `coder`, `validator`, `reporter`, and `tracker`; blocked
plan-review or user-approval states produce blocked worker packets.

## Worker Pool Code Surface

The first executable worker-pool surface is:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/worker_pool.py --supervisor-packet-json "<json>" --format yaml
.venv\Scripts\python.exe .agents/skills/agent-coordinator/scripts/coordinator.py --user-goal "<goal>" --format json | .venv\Scripts\python.exe .agents/skills/agent-planner/scripts/planner.py --coordinator-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-plan-review/scripts/plan_review.py --planner-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-supervisor/scripts/supervisor.py --plan-review-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/worker_pool.py --supervisor-packet-json - --format yaml
```

It emits a `worker_pool_packet` only. It does not edit files, execute worker
tasks, run validators, write final reports, persist tracker state, stage,
commit, fetch, pull, or push.

The worker-pool coder tool surface is:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/coder.py --worker-pool-packet-json "<json>" --coder-task-json "<json>" --format yaml
```

It consumes a ready `worker_pool_packet` and a compact `coder_task` with
explicit `write_file` operations. It writes only inside coder `allowed_scope`
after confirming approved `assigned_plan_steps`, active route alignment, and
raw-context/hard-stop boundaries in task metadata. Ordinary file content may
contain guardrail wording, but the coder still emits only a compact
`coder_packet` with a compact `worker_result`; it does not choose scope,
approve its own work, run validators, stage, commit, fetch, pull, or push.

The worker-pool validator tool surface is:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/validator.py --worker-pool-packet-json "<json>" --coder-result-json "<json>" --format yaml
```

It emits a `validator_packet` only. It does not implement code, execute project
tests, approve final completion, stage, commit, fetch, pull, or push. It blocks
coder output that violates active route direction, hard stops, locked scope,
approved `assigned_plan_steps`, or the raw-context firewall.

The worker-pool tracker tool surface is:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/tracker.py --worker-pool-packet-json "<json>" --event coder_completed --worker-result-json "<json>" --format yaml
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/tracker.py --worker-pool-packet-json "<json>" --event validator_completed --worker-result-json "<json>" --tracker-state-json "<json>" --format yaml
```

It emits a `tracker_packet` only. It does not implement code, run project
validators, generate final reports, persist state outside the packet, stage,
commit, fetch, pull, or push. A clean tracker packet moves the worker sequence
from coder completion to validation, and from validator completion to reporter
collection; out-of-order validator completion is blocked.

## Reporter Result Collection Code Surface

The first executable reporter surface is:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-reporter/scripts/reporter.py --worker-pool-packet-json "<json>" --worker-results-json "<json>" --format yaml
```

It emits a `reporter_packet` only. It does not implement code, execute
validators, approve final completion, persist tracker state, stage, commit,
fetch, pull, or push. A clean reporter packet consumes only coder, validator,
and tracker results, confirms tracker reached `ready_for_reporter`, emits the
reporter worker_result itself, and contains only fields allowed by the context
firewall: `status`, `changed_scope`, `evidence`, and `next_request`.

## Current Migration State

Current state: Phase 7 skill replacement completed in active compatibility mode.

Next component: none; keep routine work on the active architecture chain and
use `agent-replacement` only for future process migration changes.

Existing skill replacement status: completed for the tracked entry points.
Existing project-local gates remain domain authorities as compatibility targets
selected and bounded by the active architecture chain.
