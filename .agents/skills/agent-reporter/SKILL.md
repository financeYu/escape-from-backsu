---
name: agent-reporter
description: Use as the reporter tool under the supervisor in the coordinator -> planner -> plan-review -> supervisor -> worker architecture. Collects worker_result packets, blocks raw context overflow, and prepares compact Korean reports for supervisor and user.
---

# Agent Reporter

## Purpose

The reporter is the supervisor-owned worker-result collection tool in the
redesigned agent architecture. It consumes a compact `worker_pool_packet` plus
bounded `worker_result` summaries from coder, validator, and tracker. It emits
the reporter `worker_result` itself after report-gate checks pass or fail.

This skill is collection-and-reporting-only. It does not implement code, run
validators, approve final completion, persist tracker state, commit, fetch,
pull, push, or replace existing project gates by itself.

In active compatibility mode, existing project-local gates remain domain
authorities selected by the coordinator. The reporter may summarize those
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
       -> validator
       -> reporter
       -> tracker
  -> reporter result collection
  -> supervisor and user summary
```

## Required Input

The reporter accepts only:

- a compact `worker_pool_packet`
- `worker_result` summaries from approved input worker roles: `coder`,
  `validator`, and `tracker`

The reporter must reject raw logs, full exploratory notes, generated output
dumps, archive or raw-data context, long private reasoning, and unapproved
worker fields before anything is summarized for the supervisor or user.

## Worker Result Collection Contract

Each worker result must use exactly this compact shape:

```yaml
worker_result:
  worker_role: "coder | validator | tracker"
  status: "complete | partial | failed | blocked"
  changed_scope:
    - "<file, directory, or artifact>"
  evidence:
    - "<command/result or compact proof>"
  next_request: "<none or one supervisor decision>"
```

Allowed upward fields:

- `status`
- `changed_scope`
- `evidence`
- `next_request`

Forbidden worker result fields:

- `raw_logs`
- `raw_context`
- `full_exploratory_notes`
- `private_reasoning`
- `generated_output_dump`
- `archive_context`
- any equivalent raw worker logs or generated output dumps

## Reporter Responsibilities

The reporter must:

- consume only ready role specs from the `worker_pool_packet`
- collect coder implementation summaries after coder work
- collect validator verification and quality evidence after validator work
- collect tracker status, blockers, dependencies, and next request
- require tracker evidence that the workflow reached `ready_for_reporter`
- validate the worker-pool `context_firewall` before summarizing
- block oversized compact fields before they can overflow upward
- produce a compact Korean report for the supervisor and user
- preserve only `status`, `changed_scope`, `evidence`, and `next_request`
- fail closed when a worker result has missing fields, unknown roles, raw
  context, or unapproved output

## Reporter Non-Goals

- no code implementation
- no validation execution
- no quality approval beyond checking result-contract shape
- no direct worker retry decision
- no raw context forwarding to supervisor
- no commits, fetches, pulls, pushes, or staging

## Reporter Packet Contract

Return a reporter packet in this shape:

```yaml
reporter_packet:
  user_goal: "<from worker pool>"
  task_class: "<from worker pool>"
  current_route: "<from worker pool>"
  selected_gate: "<from worker pool>"
  reporter_status: "ready_for_supervisor_summary | blocked | needs_worker_fix"
  block_reason: "none | worker pool blocked | worker result contract violation | unauthorized worker context"
  worker_summaries:
    - worker_role: "coder"
      status: "complete | partial | failed | blocked"
      changed_scope:
        - "<compact scope>"
      evidence:
        - "<compact evidence>"
      next_request: "<none or one supervisor decision>"
  supervisor_summary:
    status: "complete | partial | failed | blocked"
    changed_scope:
      - "<merged compact scope>"
    evidence:
      - "<merged compact evidence>"
    next_request: "<none or one supervisor decision>"
  worker_result:
    worker_role: "reporter"
    status: "complete | blocked"
    changed_scope:
      - "reporter_packet"
    evidence:
      - "<reporter gate status>"
    next_request: "<none or one supervisor decision>"
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
      - "archive or raw-data context"
      - "long private reasoning"
  korean_final_report: true
```

## Replacement Policy

The reporter is part of the active replacement path, but it must not delete,
rename, or weaken existing Codex skills. Existing project-local gates remain
domain authorities as compatibility targets selected and bounded by the
architecture chain.

## Validation

For this skill, run:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-reporter/scripts/validate_agent_reporter.py --dry-run
.venv\Scripts\python.exe .agents/skills/agent-reporter/scripts/reporter.py --worker-pool-packet-json "<json>" --worker-results-json "<json>" --format json
```

Also run `git diff --check` for documentation edits.

## Output

Answer in Korean with this compact shape:

```yaml
gate: agent_reporter
task_class: planning/read-only | narrow edit | Step/gate closure
reporter_status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
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
