---
name: agent-planner
description: Use as the planning role in the coordinator -> planner -> plan-review -> supervisor -> worker architecture. Converts a coordinator_packet into an ordered, scope-locked plan and plan-review handoff without executing work.
---

# Agent Planner

## Purpose

The planner is the second role in the redesigned agent architecture. It
consumes a `coordinator_packet` and produces an ordered plan that can be checked
by plan-review before any supervisor or worker execution begins.

This skill is planning-only. It does not implement code, approve its own plan,
supervise workers, validate final outputs, report completion, commit, fetch,
pull, push, or replace existing project gates by itself.

During the transition, existing project-local Codex skills remain authoritative
for execution, validation, review, and finalization. The planner may name them
as compatibility targets but must not bypass them.

## Architecture Position

```text
user
  -> coordinator
  -> planner
  <-> plan-review
  -> supervisor/root-agent when plan-review passes without approval triggers
  -> user only when review fixes or separate approvals are required
  -> workers: coder, validator, reporter, tracker
```

## Required Input

The planner accepts only a compact `coordinator_packet` with:

- `user_goal`
- `task_class`
- `current_route`
- `selected_gate`
- `allowed_scope`
- `forbidden_scope`
- `planner_must_output`
- `validation_expectations`
- `context_firewall`
- `korean_final_report`
- `open_questions`

Do not read archives, generated outputs, raw data, caches, charts, logs,
release evidence, subproject files, or worker logs while planning unless the
coordinator packet explicitly names that exception.

## Planner Responsibilities

The planner must produce:

- ordered plan
- scope lock
- validation plan
- risk checks
- plan-review handoff
- supervisor handoff placeholder

The planner must preserve the selected compatibility gate. If the coordinator
packet says `separate root approval required before gate selection`, the planner
must return a blocked plan with only the approval request and no execution
steps.

## Context Firewall

The planner must not request raw worker context. It may pass these fields to
plan-review, supervisor, or reporter:

- `status`
- `changed_scope`
- `evidence`
- `next_request`

The planner must not pass raw worker logs, full exploratory notes, generated
output dumps, archive context, or long private reasoning upward.

## Planner Packet Contract

Return a planner packet in this shape:

```yaml
planner_packet:
  user_goal: "<from coordinator>"
  task_class: "<from coordinator>"
  current_route: "<from coordinator>"
  selected_gate: "<from coordinator>"
  plan_status: "ready_for_plan_review | blocked"
  scope_lock:
    allowed:
      - "<allowed scope>"
    forbidden:
      - "<forbidden scope>"
  ordered_plan:
    - id: "P1"
      role: "planner | plan-review | supervisor"
      action: "<bounded action>"
      output: "<expected output>"
  validation_plan:
    - command: "<command or not_applicable>"
      purpose: "<why this check exists>"
  context_firewall:
    upward_allowed:
      - "status"
      - "changed_scope"
      - "evidence"
      - "next_request"
    upward_forbidden:
      - "<blocked context type>"
  plan_review_handoff:
    required_checks:
      - "scope lock"
      - "hard-stop safety"
      - "selected gate compatibility"
      - "validation plan completeness"
    approval_question: "<none or exact approval needed>"
  supervisor_handoff:
    ready: false
    reason: "waiting for plan-review decision | blocked by coordinator approval request"
  korean_final_report: true
```

## Replacement Policy

The planner is part of the replacement path, but it must not delete, rename, or
bypass existing Codex skills. Existing project-local gates remain the authority
until coordinator, planner, plan-review, supervisor, coder, validator, reporter,
and tracker roles are all documented, validated, and accepted.

## Validation

For this skill, run:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-planner/scripts/validate_agent_planner.py --dry-run
.venv\Scripts\python.exe .agents/skills/agent-planner/scripts/planner.py --coordinator-packet-json "<json>" --format json
.venv\Scripts\python.exe .agents/skills/agent-coordinator/scripts/coordinator.py --user-goal "<goal>" --format json | .venv\Scripts\python.exe .agents/skills/agent-planner/scripts/planner.py --coordinator-packet-json - --format json
```

Also run `git diff --check` for documentation edits.

## Output

Answer in Korean with this compact shape:

```yaml
gate: agent_planner
task_class: planning/read-only | narrow edit | Step/gate closure
planner_status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
selected_gate: "<project-local skill gate or approval blocker>"
scope_lock:
  allowed:
    - "<scope>"
  forbidden:
    - "<scope>"
validation:
  - "<command: pass/fail/not_run>"
next_architecture_component: "plan-review | supervisor | worker | none"
remaining_risk:
  - "<none or compact risk>"
```
