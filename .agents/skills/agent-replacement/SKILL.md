---
name: agent-replacement
description: Use for Phase 7 activation and migration of existing project-local Codex skill entry points into the coordinator -> planner -> plan-review -> supervisor -> worker-pool -> reporter architecture.
---

# Agent Replacement

## Purpose

Agent Replacement is the Phase 7 gate for replacing the old project-local
Codex work process with the active agent architecture.

This skill governs process migration only. It does not authorize quant logic,
score semantics, data-ingestion expansion, universe expansion, live trading,
production activation, valuation/fundamental activation, Git remote work,
staging, committing, or deletion of existing project-local gates.

The active root process is:

```text
coordinator
  -> planner
  -> plan-review
  -> supervisor
  -> worker pool
       -> coder
       -> validator
       -> tracker
       -> reporter
  -> reporter result collection
```

## Replacement Status

Status: `active_compatibility_mode`.

Existing project-local gates remain domain authorities as compatibility
targets selected and bounded by the architecture chain. They are no longer the
default root entry point for routine work.

## Required Input

Before replacing an old entry point, root must provide a compact replacement
packet:

- current replacement target
- task classification: `planning/read-only`, `narrow edit`, or
  `Step/gate closure`
- selected architecture gate
- selected domain compatibility gate, or `none`
- role-level resource usage profile
- allowed scope
- forbidden scope
- validation commands
- Korean final report format
- Git policy: `fetch=false`, `pull=false`, `push=false`, `commit=false`,
  `stage=false`

## Replacement Rules

- Replace one entry point or owner at a time.
- Keep the old domain gate and the new architecture path side by side until
  validators pass.
- Do not delete, rename, or weaken a project-local gate until its authority is
  represented in the new role chain and root accepts the migration.
- Preserve root hard stops, route ownership, validation evidence, context
  firewall rules, and Korean report discipline.
- Existing quant gates may be selected as domain compatibility targets, but
  they must not bypass coordinator, planner, plan-review, supervisor,
  worker-pool, or reporter routing for routine work.
- Replacement must not expand universe, data ingestion, live trading,
  production activation, or valuation/fundamental activation.

## Migration Map

| Existing entry point | New owner | Compatibility target |
| --- | --- | --- |
| Root task intake | `agent-coordinator` | selected domain gate |
| Manual planning | `agent-planner` | selected validation plan |
| Plan review | `agent-plan-review` | selected hard-stop/scope checks |
| Root orchestration | `agent-supervisor` | `quant-work-cycle` for implementation |
| Direct implementation | `agent-worker-pool` `coder` | approved file operations |
| Direct validation | `agent-worker-pool` `validator` | assigned validator commands |
| Workflow status | `agent-worker-pool` `tracker` | compact state transitions |
| Final reporting | `agent-reporter` | compact Korean report |
| Subproject-contained work | `subproject-delegation` under the architecture chain | owning subproject/worktree |

## Migration Status

Track one-by-one migration in:

```text
.agents/skills/agent-replacement/MIGRATION_STATUS.md
```

Completed entry points: `Root task intake`, `Manual planning`, `Plan review`,
`Root orchestration`, `Direct implementation`, `Direct validation`,
`Workflow status`, `Final reporting`.

Next replacement target: `none`.

## Validation

For this skill, run:

```powershell
.venv\Scripts\python.exe .agents/skills/agent-replacement/scripts/validate_agent_replacement.py --dry-run
.venv\Scripts\python.exe .agents/skills/agent-coordinator/scripts/coordinator.py --user-goal "<replacement goal>" --format json
```

Also run all active architecture role validators, the end-to-end architecture
chain, and `git diff --check`.

## Output

Answer in Korean with this compact shape:

```yaml
gate: agent_replacement
task_class: planning/read-only | narrow edit | Step/gate closure
replacement_status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
selected_architecture_gate: "<agent-* skill>"
selected_domain_gate: "<domain compatibility gate or none>"
scope_lock:
  allowed:
    - "<scope>"
  forbidden:
    - "<scope>"
validation:
  - "<command: pass/fail/not_run>"
migration_status: "active_compatibility_mode | blocked | not_started"
remaining_risk:
  - "<none or compact risk>"
```
