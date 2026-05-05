# Agent Replacement Migration Status

This file tracks one-by-one replacement of old project-local Codex process
entry points into the active agent architecture.

Status values:

- `COMPLETE`: the entry point is routed through the architecture chain and has
  focused validation evidence.
- `ACTIVE_COMPATIBILITY`: the old path remains available only as a domain
  compatibility target selected and bounded by the architecture chain.
- `PENDING`: not migrated yet.

| Order | Existing entry point | New owner | Compatibility target | Status | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | Root task intake | `agent-coordinator` | selected domain gate | `COMPLETE` | `AGENTS.md` routes through active architecture first; coordinator routes replacement requests to `agent-replacement`; no worker, domain gate, implementation, validation, or completion acceptance begins before supervisor approval; end-to-end chain reaches `worker_pool_status=ready_for_worker_execution`. |
| 2 | Manual planning | `agent-planner` | selected validation plan | `COMPLETE` | Coordinator routes manual planning requests such as `plan this work` to `agent-planner`; planner validator is required in the coordinator validation plan. |
| 3 | Plan review | `agent-plan-review` | selected hard-stop/scope checks | `COMPLETE` | Coordinator routes normal plan-review requests such as `plan review this plan` to `agent-plan-review`; explicit replacement requests route to `agent-replacement`. |
| 4 | Root orchestration | `agent-supervisor` | `quant-work-cycle` for implementation | `COMPLETE` | Coordinator routes root orchestration requests such as `orchestrate this implementation` to `agent-supervisor`; explicit replacement or continuation requests route to `agent-replacement`. |
| 5 | Direct implementation | `agent-worker-pool` `coder` | approved file operations | `COMPLETE` | Coordinator routes direct implementation requests to `agent-worker-pool`; worker-pool validator checks coder dry-run file operations, scope locking, assigned plan-step coverage, and raw-context blocking. |
| 6 | Direct validation | `agent-worker-pool` `validator` | assigned validator commands | `COMPLETE` | Coordinator routes direct validation requests to `agent-worker-pool`; worker-pool validator checks validator pass/fix/block behavior, assigned plan-step evidence, scope safety, and hard-stop markers. |
| 7 | Workflow status | `agent-worker-pool` `tracker` | compact state transitions | `COMPLETE` | Coordinator routes workflow status requests to `agent-worker-pool`; worker-pool validator checks coder-to-validator and validator-to-reporter transitions, out-of-order blocking, and failed-validation fix routing. |
| 8 | Final reporting | `agent-reporter` | compact Korean report | `COMPLETE` | Coordinator routes final reporting requests to `agent-reporter`; reporter validator checks compact worker-result collection, tracker `ready_for_reporter`, raw-context blocking, oversized-field blocking, and supervisor-summary output. |

Next replacement target: `none`.
