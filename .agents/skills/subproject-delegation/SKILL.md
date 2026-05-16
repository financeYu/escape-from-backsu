---
name: subproject-delegation
description: Use when work can be owned by a subproject or subfunction lane and should be delegated there to preserve root context, avoid duplicate writes, and keep exploration inside the owning workspace or AGENTS.md boundary.
---

# Subproject Delegation

## Purpose

Keep root orchestration thin when a task can be handled by an owning
subproject, subfunction lane, or role worktree.

This skill governs delegation and context boundaries only. It does not
authorize quant logic, score semantics, ranking/report behavior, backtest
behavior, data ingestion, universe expansion, live trading, production
activation, valuation activation, Git remote work, staging, or commits.

## When To Use

Use this skill under the architecture chain when any of these are true:

- the task is contained in one subproject such as `chart_mvp`,
  `Quant_mvp/research_mvp`, `review_mvp`, or another owner lane
- the task is mostly exploration, file discovery, or local validation inside a
  subproject
- a subproject `AGENTS.md`, validator, or workflow owns the local process
- root would otherwise need to read many subproject files or raw worker notes
- multiple agents could accidentally write the same file or artifact

Do not use it to bypass root hard stops, selected domain gates, or required
review. Root still owns final route selection, cross-lane handoff shape,
activation boundaries, and completion acceptance.

## Delegation Principle

Root should delegate subproject-contained exploration, implementation, and
validation to the owning subproject or role worktree whenever feasible.

Root keeps only:

- current task
- selected architecture gate and domain compatibility gate
- allowed scope and forbidden scope
- required output
- validation commands
- compact result contract

The subproject keeps:

- local file discovery
- local implementation details
- local test output
- local exploratory notes
- local blockers and fix attempts

Only compact summaries come back to root.

## Duplicate Write Rule

Before assigning work, root or supervisor must name a single write owner for
each file, directory, or generated artifact.

- One writer per path at a time.
- Parallel work may proceed only with disjoint write sets.
- Explorers may read overlapping scope, but they must not write.
- Validators may inspect changed scope, but they must not rewrite coder output.
- If ownership is unclear, stop and request a narrower scope lock.

## Context Firewall

Subproject workers may return only:

- `status`
- `changed_scope`
- `evidence`
- `next_request`

They must not return raw logs, full exploratory notes, generated output dumps,
archive or raw-data context, broad file listings, or long private reasoning.

For subproject exploration, root should ask for a bounded answer such as:

- "which file owns this behavior?"
- "which validator should run?"
- "what exact write scope is needed?"
- "what blocker prevents delegation?"

## Required Handoff Packet

When delegating, root or supervisor must provide:

```yaml
subproject_handoff:
  owner_lane: "<subproject or role worktree>"
  task: "<bounded task>"
  read_scope:
    - "<allowed discovery path>"
  write_scope:
    - "<single-owner path or none>"
  forbidden_scope:
    - "<hard stop or cross-lane boundary>"
  local_instructions:
    - "read only the subproject AGENTS.md, one active packet, one needed domain stub, and targeted files"
  validation_commands:
    - "<subproject or root .venv command>"
  result_contract:
    upward_allowed:
      - "status"
      - "changed_scope"
      - "evidence"
      - "next_request"
    upward_forbidden:
      - "raw logs"
      - "full exploratory notes"
      - "generated output dumps"
      - "archive or raw-data context"
      - "duplicate write ownership"
```

## Architecture Integration

- `agent-coordinator` selects this skill when the request is subproject-owned
  or asks for subproject delegation/context separation.
- `agent-planner` records the subproject owner, disjoint write scope, and
  validation plan.
- `agent-plan-review` blocks plans that omit the owner lane or allow duplicate
  writes.
- `agent-supervisor` creates bounded worker packets and keeps root from
  reading subproject exploration details directly.
- `agent-worker-pool` enforces single-writer scope and compact worker results.
- `agent-reporter` summarizes only compact worker results for root/user.

## Validation

Run:

```powershell
.venv\Scripts\python.exe .agents/skills/subproject-delegation/scripts/validate_subproject_delegation.py --dry-run
git diff --check
```

When this skill changes architecture routing, also run the affected
architecture role validators.

## Output

Answer in Korean with this compact shape:

```yaml
gate: subproject_delegation
gate_result: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
owner_lane: "<subproject/worktree or none>"
scope_lock:
  read:
    - "<path>"
  write:
    - "<path or none>"
  forbidden:
    - "<boundary>"
duplicate_write_status: "single_owner | blocked | not_applicable"
validation:
  - "<command: pass/fail/not_run>"
remaining_risk:
  - "<none or compact risk>"
```
