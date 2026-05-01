# Agent Orchestration Architecture

This document defines the replacement architecture for project-local Codex
skills. The redesign starts with the coordinator and expands role by role before
any existing project-local skill is deleted, renamed, or bypassed.

The existing project gates remain authoritative during the transition.

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
       -> validator
       -> reporter
       -> tracker
```

## Design Goals

- Keep user intent separate from execution details.
- Keep planning separate from plan review.
- Keep supervisor orchestration separate from worker implementation.
- Prevent worker context from overflowing into parent roles.
- Preserve root hard stops and current route state while the architecture is
  replacing existing skills.
- Replace current Codex skills only after the new role chain is documented,
  validated, and accepted.

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
- preserve current route, selected gate, scope lock, validation plan, hard
  stops, and context firewall
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

- `coder`: implements only inside the assigned scope
- `validator`: runs assigned checks and returns validation evidence
- `reporter`: produces compact final reports from approved summaries
- `tracker`: records state, dependencies, blockers, and next action

Worker Pool responsibilities:

- consume only the supervisor packet
- verify the worker packet set contains `coder`, `validator`, `reporter`, and
  `tracker`
- verify supervisor execution policy keeps fetch, pull, push, commit, and
  stage disabled
- verify every worker has allowed scope, forbidden scope, validation commands,
  required output, and compact result contract
- normalize every worker packet into a role spec
- block worker execution when supervisor is blocked, worker packets are
  incomplete, execution policy is unsafe, or result contracts leak raw context

Worker Pool non-goals:

- no code implementation
- no validator execution
- no final report generation
- no persistent tracking store
- no raw worker-context ingestion
- no commits, fetches, pulls, or pushes

Workers must return compact summaries, not raw context.

## Phase 6: Skill Replacement

Existing Codex skills are compatibility targets until the full architecture is
available. Replacement can start only after these artifacts exist:

- coordinator skill and validator
- planner skill and validator
- plan-review skill and validator
- supervisor skill and validator
- worker role specs and validators
- architecture-level review gate
- migration map from existing skills to new roles

Replacement rules:

- replace one owner at a time
- keep old and new paths side by side until validation passes
- do not delete a gate until its authority is represented in the new role chain
- preserve hard stops, route ownership, validation evidence, and Korean report
  discipline
- never use replacement to expand universe, data ingestion, live trading,
  production activation, or valuation/fundamental activation

## Coordinator Planner Packet

```yaml
coordinator_packet:
  user_goal: "<normalized user goal>"
  task_class: "planning/read-only | narrow edit | Step/gate closure"
  current_route: "<active route or named exception>"
  selected_gate: "<project-local skill gate or none yet>"
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
packet prepares bounded worker packets for `coder`, `validator`, `reporter`,
and `tracker`; blocked plan-review or user-approval states produce blocked
worker packets.

## Worker Pool Code Surface

The first executable worker-pool surface is:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/worker_pool.py --supervisor-packet-json "<json>" --format yaml
.venv\Scripts\python.exe .agents/skills/agent-coordinator/scripts/coordinator.py --user-goal "<goal>" --format json | .venv\Scripts\python.exe .agents/skills/agent-planner/scripts/planner.py --coordinator-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-plan-review/scripts/plan_review.py --planner-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-supervisor/scripts/supervisor.py --plan-review-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/worker_pool.py --supervisor-packet-json - --format yaml
```

It emits a `worker_pool_packet` only. It does not edit files, execute worker
tasks, run validators, write final reports, persist tracker state, stage,
commit, fetch, pull, or push.

## Current Migration State

Current state: Phase 5 worker pool introduced.

Next component: skill replacement.

Existing skill replacement status: not started. Existing project-local gates
remain authoritative.
