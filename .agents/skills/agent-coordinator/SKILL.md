---
name: agent-coordinator
description: Use as the entry role for the coordinator -> planner -> plan-review -> supervisor -> worker architecture. Converts user natural language into a compact planner prompt while preserving project hard stops and preventing worker context overflow.
---

# Agent Coordinator

## Purpose

The coordinator is the entry role for the redesigned agent architecture. It
turns the user's natural-language request into a compact planner prompt that is
safe for the current project route.

This skill is an intake and routing compiler only. It does not implement code,
review plans, supervise workers, validate outputs, report completion, commit,
fetch, pull, push, or replace existing project gates by itself.

The coordinator is the first compatibility layer before the existing Codex
skills are replaced. During the transition, it must select or name the current
project-local gate skill that still owns execution authority.

## Architecture Position

```text
user
  -> coordinator
  -> planner
  <-> plan-review
  -> user approval or feedback
  -> supervisor/root-agent
  -> workers: coder, validator, reporter, tracker
```

## Required Inputs

Before producing a planner prompt, the coordinator must use only the minimum
default context:

- latest user request
- `docs/root_hard_stops.md`
- `docs/roadmap_status.md`
- this skill document
- targeted route or skill names only when needed

Do not read archives, generated outputs, raw data, caches, charts, logs,
release evidence, or subproject files during coordinator intake unless the user
names a conflict, regression, provenance, release, or compatibility check.

## Coordinator Responsibilities

The coordinator must produce one compact planner prompt that includes:

- normalized user goal
- task classification: `planning/read-only`, `narrow edit`, or
  `Step/gate closure`
- selected current project-local skill gate or `none yet`
- allowed scope
- forbidden scope
- expected planner output
- required validation expectations
- context firewall rules
- Korean final report requirement
- open questions only when a safe assumption would cross a hard stop

The coordinator must preserve the current route. For this workspace, routine
work stays aligned to the active v0.3 candidate/evidence route unless the user
explicitly asks for a named archive, provenance, regression, or compatibility
check.

## Context Firewall

The coordinator must prevent worker context from overflowing upward into
planner, plan-review, or user-facing layers.

Allowed upward information from lower layers is limited to:

- `status`: complete, partial, failed, or blocked
- `changed_scope`: files, directories, or artifacts touched
- `evidence`: validation commands and compact results
- `next_request`: the single decision or approval needed from the parent role

Forbidden upward information:

- raw worker logs
- full exploratory notes
- failed implementation attempts unless they change the next decision
- long chain-of-thought or private reasoning
- generated artifacts unless promoted by an explicit review path
- broad file dumps or archive context

The coordinator must never ask the planner to ingest raw worker context. If a
later stage returns excessive context, the coordinator must request a compact
summary using the allowed upward fields.

## Planner Prompt Contract

Return a planner prompt in this shape:

```yaml
coordinator_packet:
  user_goal: "<normalized goal>"
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

## Replacement Policy

The coordinator starts the architecture replacement path but must not delete,
rename, or bypass existing Codex skills until the new architecture has all of
these roles documented and validated:

- coordinator
- planner
- plan-review
- supervisor/root-agent
- coder
- validator
- reporter
- tracker

Until then, the coordinator wraps the existing project-local gates as
compatibility targets. Existing gates remain the authority for execution,
validation, review, and finalization.

## Validation

For this skill, run:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-coordinator/scripts/validate_agent_coordinator.py --dry-run
.venv\Scripts\python.exe .agents/skills/agent-coordinator/scripts/coordinator.py --user-goal "<goal>" --format json
```

Also run `git diff --check` for documentation edits.

## Output

Answer in Korean with this compact shape:

```yaml
gate: agent_coordinator
task_class: planning/read-only | narrow edit | Step/gate closure
coordinator_status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
selected_gate: "<project-local skill gate or none yet>"
allowed_scope:
  - "<scope>"
forbidden_scope:
  - "<scope>"
context_firewall:
  upward_allowed:
    - "status"
    - "changed_scope"
    - "evidence"
    - "next_request"
  upward_forbidden:
    - "<blocked context type>"
validation:
  - "<command: pass/fail/not_run>"
next_architecture_component: "planner | plan-review | supervisor | worker | none"
remaining_risk:
  - "<none or compact risk>"
```
