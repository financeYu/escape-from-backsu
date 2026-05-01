---
name: agent-plan-review
description: Use as the plan-review role in the coordinator -> planner -> plan-review -> supervisor -> worker architecture. Checks planner packets for route alignment, scope safety, validation completeness, and approval requirements before supervisor execution.
---

# Agent Plan Review

## Purpose

Plan Review is the third role in the redesigned agent architecture. It consumes
a `planner_packet`, checks whether the plan preserves the user's goal, current
route, hard stops, selected gate, validation expectations, and context
firewall, then decides whether supervisor execution may begin.

This skill is review-only. It does not implement code, change the plan, run
workers, validate final task outputs, report final completion, commit, fetch,
pull, push, or replace existing project gates by itself.

During the transition, existing project-local Codex skills remain authoritative
for execution, validation, review, and finalization. Plan Review may approve a
supervisor handoff only when the reviewed plan stays inside those existing
gate boundaries.

## Architecture Position

```text
user
  -> coordinator
  -> planner
  <-> plan-review
  -> supervisor/root-agent when review passes without approval triggers
  -> user only when review fixes or separate approvals are required
  -> workers: coder, validator, reporter, tracker
```

## Required Input

Plan Review accepts only a compact `planner_packet` with:

- `user_goal`
- `task_class`
- `current_route`
- `selected_gate`
- `plan_status`
- `scope_lock`
- `ordered_plan`
- `validation_plan`
- `context_firewall`
- `plan_review_handoff`
- `supervisor_handoff`
- `korean_final_report`

Do not read archives, generated outputs, raw data, caches, charts, logs,
release evidence, subproject files, worker logs, or implementation details
while reviewing unless the planner packet explicitly names that exception.

## Review Responsibilities

Plan Review must check:

- current route is present and aligned
- selected gate is preserved and not bypassed
- scope lock has allowed and forbidden boundaries
- hard stops remain forbidden unless separate approval is required
- validation plan is present
- context firewall keeps upward context compact
- ordered plan exists and does not execute before review
- planner did not mark supervisor handoff ready before review

## User Approval Policy

Do not require user approval for every clean plan.

Require user approval only when:

- a review item failed and the plan must be changed before execution
- the requested change crosses a boundary that already requires separate
  approval, such as hard-stop activation or out-of-scope expansion

When review passes and no approval trigger exists, Plan Review may set
`supervisor_handoff.ready` to `true`.

When review fails, Plan Review must set `supervisor_handoff.ready` to `false`
and send the packet back to the planner with exact fixes. If the planner later
changes the plan to resolve failed review items, that revised plan requires
user approval before supervisor execution.

## Context Firewall

Plan Review must not request raw worker context. It may pass these fields to
supervisor, reporter, or the user:

- `status`
- `changed_scope`
- `evidence`
- `next_request`

Plan Review must not pass raw worker logs, full exploratory notes, generated
output dumps, archive context, raw data, or long private reasoning upward.

## Plan Review Packet Contract

Return a plan-review packet in this shape:

```yaml
plan_review_packet:
  user_goal: "<from planner>"
  task_class: "<from planner>"
  current_route: "<from planner>"
  selected_gate: "<from planner>"
  scope_lock:
    allowed:
      - "<from planner>"
    forbidden:
      - "<from planner>"
  validation_plan:
    - command: "<from planner>"
      purpose: "<from planner>"
  review_status: "approved_for_supervisor | needs_planner_fix | separate_approval_required | blocked"
  checklist:
    - id: "R1"
      check: "<review item>"
      passed: true
      message: "<compact result>"
      required_fix: "none"
  user_approval:
    required: false
    reason: "none | review_fix_required_after_plan_change | separate approval required"
  supervisor_handoff:
    ready: true
    reason: "review passed; no user approval trigger | blocked by review findings | separate approval required"
  planner_feedback:
    required: false
    fixes:
      - "<none or exact planner fix>"
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

Plan Review is part of the replacement path, but it must not delete, rename, or
bypass existing Codex skills. Existing project-local gates remain the authority
until coordinator, planner, plan-review, supervisor, coder, validator,
reporter, and tracker roles are all documented, validated, and accepted.

## Validation

For this skill, run:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-plan-review/scripts/validate_agent_plan_review.py --dry-run
.venv\Scripts\python.exe .agents/skills/agent-plan-review/scripts/plan_review.py --planner-packet-json "<json>" --format json
.venv\Scripts\python.exe .agents/skills/agent-coordinator/scripts/coordinator.py --user-goal "<goal>" --format json | .venv\Scripts\python.exe .agents/skills/agent-planner/scripts/planner.py --coordinator-packet-json - --format json | .venv\Scripts\python.exe .agents/skills/agent-plan-review/scripts/plan_review.py --planner-packet-json - --format json
```

Also run `git diff --check` for documentation edits.

## Output

Answer in Korean with this compact shape:

```yaml
gate: agent_plan_review
task_class: planning/read-only | narrow edit | Step/gate closure
plan_review_status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
selected_gate: "<project-local skill gate or approval blocker>"
scope_lock:
  allowed:
    - "<scope>"
  forbidden:
    - "<scope>"
validation:
  - "<command: pass/fail/not_run>"
next_architecture_component: "supervisor | worker | none"
remaining_risk:
  - "<none or compact risk>"
```
