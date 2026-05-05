---
name: agent-worker-pool
description: Use as the worker-pool role in the coordinator -> planner -> plan-review -> supervisor -> worker architecture. Normalizes bounded worker packets and exposes supervisor-owned coder, validator, tracker, and reporter handoff tools.
---

# Agent Worker Pool

## Purpose

The worker pool is the fifth role in the redesigned agent architecture. It
consumes a `supervisor_packet`, normalizes the bounded worker packets for
`coder`, `validator`, `reporter`, and `tracker`, and exposes supervisor-owned
worker tools under those role contracts.

The worker-pool normalizer is contract-only. The coder tool may write files
only from explicit supervisor-approved file operations inside coder
`allowed_scope` and approved `assigned_plan_steps`. This skill does not run
project validators, write final reports, persist tracker state, commit, fetch,
pull, push, or replace existing project gates by itself.

In active compatibility mode, existing project-local gates remain domain
authorities selected by the coordinator. The worker pool may preserve those
gates as compatibility targets, but it must not bypass the architecture chain.

## Architecture Position

```text
user
  -> coordinator
  -> planner
  <-> plan-review
  -> supervisor/root-agent
  -> worker pool
       -> coder
       -> tracker
       -> validator
       -> tracker
       -> reporter
```

## Required Input

The worker pool accepts only a compact `supervisor_packet` with:

- `user_goal`
- `task_class`
- `current_route`
- `selected_gate`
- `supervisor_status`
- `block_reason`
- `execution_policy`
- `worker_packets`
- `context_firewall`
- `korean_final_report`

Do not read archives, generated outputs, raw data, caches, charts, logs,
release evidence, subproject files, or implementation details while normalizing
worker packets unless the supervisor packet explicitly names that exception.

## Worker Role Contracts

The worker pool must preserve these role boundaries:

- `coder`: may apply explicit file operations only inside assigned scope and
  approved `assigned_plan_steps`; returns changed scope and implementation
  summary only
- `validator`: may run assigned checks only and compare coder output to
  project direction, hard stops, scope lock, assigned validation commands, and
  `assigned_plan_steps`; returns validation evidence only
- `reporter`: owns worker-result collection and may write compact Korean
  supervisor/user reports only from approved summaries
- `tracker`: may record coder completion, advance validation, record
  validator completion, and advance one next worker request only

Workers are tools for the supervisor, not independent route owners.
Coder returns implementation scope, validator returns verification and quality
evidence, reporter converts approved summaries into supervisor/user reporting,
and tracker records the current workflow state and next request. The tracker
is the only worker-pool tool that may move the sequence from coder to
validator, and from validator to reporter.

## Coder Tool Contract

The coder tool lives inside this worker-pool skill:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/coder.py --worker-pool-packet-json "<json>" --coder-task-json "<json>" --format json
```

It consumes only:

- the compact `worker_pool_packet`
- a compact `coder_task` with explicit `write_file` operations,
  `completed_plan_steps`, compact evidence, and one next request

It checks before writing:

- active v0.3 route alignment
- worker-pool and coder role readiness
- every file path stays inside coder `allowed_scope`
- every approved `assigned_plan_steps` id is covered
- coder task metadata contains no raw logs, raw context, generated dumps,
  archive/raw data context, private reasoning, or hard-stop activation markers
  outside ordinary file content

It writes files only after those checks pass, then emits a compact
`coder_packet` with a reporter-compatible `worker_result`. It does not choose
scope, approve its own work, run validators, stage, commit, fetch, pull, or
push.

## Validator Tool Contract

The validator tool lives inside this worker-pool skill:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/validator.py --worker-pool-packet-json "<json>" --coder-result-json "<json>" --format json
```

It consumes only:

- the compact `worker_pool_packet`
- the coder `worker_result`

It checks:

- active v0.3 route alignment
- coder and validator role readiness
- coder changed scope stays inside assigned scope
- coder output does not cross hard stops or archived-route markers
- coder evidence covers every approved `assigned_plan_steps` id
- coder result contains no raw logs, raw context, generated dumps, archive/raw
  data context, or private reasoning

It emits a compact `validator_packet` with a reporter-compatible
`worker_result`. It does not execute project tests, approve final completion,
commit, stage, fetch, pull, or push.

## Tracker Tool Contract

The tracker tool lives inside this worker-pool skill:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/tracker.py --worker-pool-packet-json "<json>" --event coder_completed --worker-result-json "<json>" --format json
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/tracker.py --worker-pool-packet-json "<json>" --event validator_completed --worker-result-json "<json>" --tracker-state-json "<json>" --format json
```

It consumes only:

- the compact `worker_pool_packet`
- one compact `worker_result`
- optional previous tracker `workflow_state`

It enforces this order:

1. `coder_completed`: require a complete coder result, record coder
   completion, and emit `validation_required` with `next_worker=validator`.
2. `validator_completed`: require previous tracked coder completion, require a
   complete validator result, and emit `ready_for_reporter` with
   `next_worker=reporter`.

It blocks validator completion before coder tracking, incomplete worker
results, unavailable worker roles, unsafe worker-pool packets, raw logs, raw
context, generated dumps, private reasoning, and hard-stop markers.

It emits a compact `tracker_packet` with a reporter-compatible
`worker_result`. It does not execute worker tasks, run validators, generate
final reports, persist state outside the packet, commit, stage, fetch, pull, or
push.

## Context Firewall

Every worker result must use only this compact result shape:

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

## Worker Pool Packet Contract

Return a worker-pool packet in this shape:

```yaml
worker_pool_packet:
  user_goal: "<from supervisor>"
  task_class: "<from supervisor>"
  current_route: "<from supervisor>"
  selected_gate: "<from supervisor>"
  worker_pool_status: "ready_for_worker_execution | blocked"
  block_reason: "none | supervisor blocked | worker packet set incomplete | unsafe execution policy | unsafe worker contract | unsafe context firewall"
  role_specs:
    - worker_role: "coder"
      ready: true
      purpose: "<role purpose>"
      allowed_scope:
        - "<from worker packet>"
      forbidden_scope:
        - "<from worker packet>"
      assigned_plan_steps:
        - id: "<from worker packet>"
          role: "<from worker packet>"
          action: "<from worker packet>"
          output: "<from worker packet>"
      required_input: "supervisor worker packet with approved assigned_plan_steps only"
      required_output: "<from worker packet>"
      validation_commands:
        - "<from worker packet>"
      result_contract:
        upward_allowed:
          - "status"
          - "changed_scope"
          - "evidence"
          - "next_request"
        upward_forbidden:
          - "<blocked context type>"
      execution_limits:
        fetch: false
        pull: false
        push: false
        commit: false
        stage: false
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

## Replacement Policy

The worker pool is part of the active replacement path, but it must not delete,
rename, or weaken existing Codex skills. Existing project-local gates remain
domain authorities as compatibility targets selected and bounded by the
architecture chain.

## Validation

For this skill, run:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/validate_agent_worker_pool.py --dry-run
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/worker_pool.py --supervisor-packet-json "<json>" --format json
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/coder.py --worker-pool-packet-json "<json>" --coder-task-json "<json>" --format json
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/validator.py --worker-pool-packet-json "<json>" --coder-result-json "<json>" --format json
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/tracker.py --worker-pool-packet-json "<json>" --event coder_completed --worker-result-json "<json>" --format json
.venv\Scripts\python.exe .agents/skills/agent-coordinator/scripts/coordinator.py --user-goal "<goal>" --format json | .venv\Scripts\python.exe .agents/skills/agent-planner/scripts/planner.py --coordinator-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-plan-review/scripts/plan_review.py --planner-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-supervisor/scripts/supervisor.py --plan-review-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/worker_pool.py --supervisor-packet-json - --format json
```

Also run `git diff --check` for documentation edits.

## Output

Answer in Korean with this compact shape:

```yaml
gate: agent_worker_pool
task_class: planning/read-only | narrow edit | Step/gate closure
worker_pool_status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
selected_gate: "<project-local skill gate or approval blocker>"
scope_lock:
  allowed:
    - "<scope>"
  forbidden:
    - "<scope>"
validation:
  - "<command: pass/fail/not_run>"
next_architecture_component: "skill-replacement | none"
remaining_risk:
  - "<none or compact risk>"
```
