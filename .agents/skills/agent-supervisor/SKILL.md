---
name: agent-supervisor
description: Use as the supervisor/root-agent role in the coordinator -> planner -> plan-review -> supervisor -> worker architecture. Converts approved plan-review packets into bounded worker packets without executing worker tasks directly.
---

# Agent Supervisor

## Purpose

The supervisor is the fourth role in the redesigned agent architecture. It
consumes an approved `plan_review_packet` and prepares bounded work packets for
the worker pool.

This skill is orchestration-only. It does not implement code, validate final
outputs, write final reports, track long-running state outside the packet,
commit, fetch, pull, push, or replace existing project gates by itself.

In active compatibility mode, existing project-local Codex skills remain
domain authorities selected by the coordinator. The supervisor may name those
gates as compatibility targets, but it must not bypass the architecture chain.

## Architecture Position

```text
user
  -> coordinator
  -> planner
  <-> plan-review
  -> supervisor/root-agent
  -> workers: coder, validator, reporter, tracker
```

## Required Input

The supervisor accepts only a compact `plan_review_packet` with:

- `user_goal`
- `task_class`
- `current_route`
- `selected_gate`
- `scope_lock`
- `ordered_plan`
- `validation_plan`
- `review_status`
- `user_approval`
- `supervisor_handoff`
- `planner_feedback`
- `context_firewall`
- `korean_final_report`

Do not read archives, generated outputs, raw data, caches, charts, logs,
release evidence, subproject files, or worker logs while building worker
packets unless the plan-review packet explicitly names that exception.

## Supervisor Responsibilities

The supervisor must:

- execute only when `review_status` is `approved_for_supervisor`
- execute only when `supervisor_handoff.ready` is `true`
- block when `user_approval.required` is `true`
- preserve current route, selected gate, scope lock, validation plan, hard
  stops, and context firewall
- preserve the approved planner `ordered_plan` as worker `assigned_plan_steps`
- create worker packets for `coder`, `validator`, `reporter`, and `tracker`
- route worker-result collection and final report drafting to the `reporter`
  worker only
- keep every worker packet bounded by the same allowed and forbidden scope
- for subproject delegation, assign work to the owning lane/worktree with one
  writer per path and compact result contracts only
- require compact worker outputs only: `status`, `changed_scope`, `evidence`,
  and `next_request`
- keep Git remote and finalize actions disabled

## Supervisor Non-Goals

- no code implementation
- no direct validation execution
- no final completion acceptance
- no raw worker-context ingestion
- no commits, fetches, pulls, or pushes
- no replacement of existing project-local gates

## Worker Context Firewall

Workers must not return raw context to the supervisor. Every worker packet must
require this compact result shape:

```yaml
worker_result:
  status: "complete | partial | failed | blocked"
  changed_scope:
    - "<file, directory, or artifact>"
  evidence:
    - "<command/result or compact proof>"
  next_request: "<none or one supervisor decision>"
```

Forbidden worker output:

- raw logs
- full exploratory notes
- generated output dumps
- archive or raw-data context
- long private reasoning

## Supervisor Packet Contract

Return a supervisor packet in this shape:

```yaml
supervisor_packet:
  user_goal: "<from plan-review>"
  task_class: "<from plan-review>"
  current_route: "<from plan-review>"
  selected_gate: "<from plan-review>"
  resource_usage_profile: "<from plan-review>"
  supervisor_status: "ready_for_workers | blocked"
  block_reason: "none | plan-review not approved | user approval required | supervisor handoff not ready"
  execution_policy:
    fetch: false
    pull: false
    push: false
    commit: false
    stage: false
  worker_packets:
    - worker_role: "coder"
      resource_usage: "<from resource_usage_profile>"
      ready: true
      allowed_scope:
        - "<from scope lock>"
      forbidden_scope:
        - "<from scope lock>"
      assigned_plan_steps:
        - id: "<from ordered_plan>"
          role: "<from ordered_plan>"
          action: "<from ordered_plan>"
          output: "<from ordered_plan>"
      required_output: "<bounded worker output>"
      validation_commands:
        - "<command or not_applicable>"
      result_contract:
        upward_allowed:
          - "status"
          - "changed_scope"
          - "evidence"
          - "next_request"
        upward_forbidden:
          - "<blocked context type>"
  context_firewall:
    upward_allowed:
      - "status"
      - "changed_scope"
      - "evidence"
      - "next_request"
    upward_forbidden:
      - "<blocked context type>"
  korean_final_report: true
```

Worker order:

1. `coder` performs scoped implementation by following `assigned_plan_steps`
   and returns changed scope plus a compact implementation summary.
2. `tracker` records coder completion and advances the workflow to validator.
3. `validator` checks coder output against project direction, hard stops,
   scope lock, assigned validation commands, and `assigned_plan_steps`; then
   returns validation or quality evidence.
4. `tracker` records validator completion and advances the workflow to
   reporter.
5. `reporter` collects approved `worker_result` summaries and drafts the
   supervisor/user report.

## Replacement Policy

The supervisor is part of the active replacement path, but it must not delete,
rename, or weaken existing Codex skills. Existing project-local gates remain
domain authorities as compatibility targets selected and bounded by the
architecture chain.

## Validation

For this skill, run:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-supervisor/scripts/validate_agent_supervisor.py --dry-run
.venv\Scripts\python.exe .agents/skills/agent-supervisor/scripts/supervisor.py --plan-review-packet-json "<json>" --format json
.venv\Scripts\python.exe .agents/skills/agent-coordinator/scripts/coordinator.py --user-goal "<goal>" --format json | .venv\Scripts\python.exe .agents/skills/agent-planner/scripts/planner.py --coordinator-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-plan-review/scripts/plan_review.py --planner-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-supervisor/scripts/supervisor.py --plan-review-packet-json - --format json
```

Also run `git diff --check` for documentation edits.

## Output

Answer in Korean with this compact shape:

```yaml
gate: agent_supervisor
task_class: planning/read-only | narrow edit | Step/gate closure
supervisor_status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
selected_gate: "<project-local skill gate or approval blocker>"
scope_lock:
  allowed:
    - "<scope>"
  forbidden:
    - "<scope>"
validation:
  - "<command: pass/fail/not_run>"
next_architecture_component: "worker-pool | skill-replacement | none"
remaining_risk:
  - "<none or compact risk>"
```
