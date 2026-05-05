# Agent Workflow

## Source of truth

The workflow follows `AGENTS.md`, `../docs/root_hard_stops.md`, and
`../docs/roadmap_status.md`.

The active root process is the agent architecture chain:

```text
agent-coordinator -> agent-planner -> agent-plan-review -> agent-supervisor
  -> agent-worker-pool -> agent-reporter
```

Existing Quant gates and historical technical roles remain compatibility
targets selected and bounded by that chain. They are not direct root entry
points for routine work.

## Active route

The current route is post-MVP `v0.3 research-to-strategy adoption route`.
Routine work should produce or protect one of these active artifacts:

- `ResearchHypothesis`
- `StrategyHypothesis`
- `StrategyCandidate`
- `EvaluationEvidence`
- `AdoptionCandidate`

The archived v0.1 technical scanner and v0.2 probability route remain
reference-only unless root names a provenance, regression, freeze, or
compatibility check.

## Architecture stages

### Stage 1: Coordinator

`agent-coordinator` normalizes the user goal, classifies the task as
`planning/read-only`, `narrow edit`, or `Step/gate closure`, selects the
project-local compatibility gate, and sets the context firewall.

### Stage 2: Planner

`agent-planner` turns the coordinator packet into an ordered plan, scope lock,
validation plan, and plan-review handoff. It does not implement or approve its
own plan.

### Stage 3: Plan Review

`agent-plan-review` checks route alignment, selected-gate compatibility,
hard-stop safety, validation completeness, and whether separate approval is
needed before supervisor execution.

### Stage 4: Supervisor

`agent-supervisor` converts an approved plan-review packet into bounded worker
packets. Git remote work, staging, and commits remain disabled.

### Stage 5: Worker Pool

`agent-worker-pool` normalizes the supervisor packet into bounded `coder`,
`validator`, `tracker`, and `reporter` contracts. Workers return only compact
`status`, `changed_scope`, `evidence`, and `next_request` fields.

### Stage 6: Reporter

`agent-reporter` collects compact worker results and prepares the Korean
supervisor/user report. It must reject raw logs, raw context, generated-output
dumps, archive context, and long exploratory notes.

## Compatibility targets

Use the narrowest project-local gate under the architecture chain:

- `agent-replacement` for architecture migration and entry-point replacement
- `quant-work-cycle` for implementation cycles
- `quant-strategy-adoption-gate` for active v0.3 strategy adoption work
- `quant-candidate-ml-gate` only for explicitly requested archived/supporting
  `prob_up_1d_candidate` compatibility
- `quant-subproject-audit-gate` for Quant-wide audit or scope-watchdog work
- `quant-review-gate` before accepting completion

## Historical technical roles

The old technical workflow is preserved only as a compatibility model for
archived baseline checks or explicitly assigned technical-score work:

- Score Architect defines and classifies technical score candidates.
- Research Tester implements predefined score definitions and diagnostics.
- Technical Selection Reviewer compares reproducible score outputs.

These roles must not bypass the architecture chain and must not be used as the
default v0.3 entry point.

## Valuation boundary

Valuation and fundamental analysis remain separated in
`../.agents/skills/valuation_review/SKILL.md`. Quant technical or research work
must not perform valuation review, activate valuation/fundamental scoring, or
claim valuation support from price-only evidence.

## Global guardrails

All active work must enforce:

- conservative quant engineering
- config-first implementation
- no lookahead
- no future data
- no silent score or route redefinition
- no valuation claims from price-only evidence
- evidence-only v0.3 adoption outputs
- no live trading, order generation, data-ingestion expansion, universe
  expansion, or production activation without explicit approval
