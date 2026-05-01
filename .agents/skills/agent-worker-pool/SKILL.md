---
name: agent-worker-pool
description: Use as the worker-pool role in the coordinator -> planner -> plan-review -> supervisor -> worker architecture. Normalizes bounded coder, validator, reporter, and tracker packets without executing worker tasks.
---

# Agent Worker Pool

## Purpose

The worker pool is the fifth role in the redesigned agent architecture. It
consumes a `supervisor_packet` and normalizes the bounded worker packets for
`coder`, `validator`, `reporter`, and `tracker`.

This skill is contract-only. It does not implement code, run validators, write
final reports, persist tracker state, commit, fetch, pull, push, or replace
existing project gates by itself.

Existing project-local gates remain the authority during the transition. The
worker pool may preserve those gates as compatibility targets, but it must not
bypass them.

## Architecture Position

```text
user
  -> coordinator
  -> planner
  <-> plan-review
  -> supervisor/root-agent
  -> worker pool
       -> coder
       -> validator
       -> reporter
       -> tracker
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

- `coder`: may implement only inside assigned scope; returns changed scope and
  implementation summary only
- `validator`: may run assigned checks only; returns validation evidence only
- `reporter`: may write compact Korean reports only from approved summaries
- `tracker`: may record workflow status, blockers, dependencies, and one next
  request only

Workers are tools for the supervisor, not independent route owners.

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
  block_reason: "none | supervisor blocked | worker packet set incomplete | unsafe execution policy | unsafe worker contract"
  role_specs:
    - worker_role: "coder"
      ready: true
      purpose: "<role purpose>"
      allowed_scope:
        - "<from worker packet>"
      forbidden_scope:
        - "<from worker packet>"
      required_input: "supervisor worker packet only"
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

The worker pool is part of the replacement path, but it must not delete,
rename, or bypass existing Codex skills. Existing project-local gates remain
the authority until coordinator, planner, plan-review, supervisor, coder,
validator, reporter, and tracker roles are all documented, validated, and
accepted.

## Validation

For this skill, run:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/validate_agent_worker_pool.py --dry-run
.venv\Scripts\python.exe .agents/skills/agent-worker-pool/scripts/worker_pool.py --supervisor-packet-json "<json>" --format json
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
