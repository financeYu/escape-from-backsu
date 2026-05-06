# Root Hard Stops

This is the current project authority document. `AGENTS.md` is only the compact
router/constitution, and `docs/roadmap_status.md` is the latest route state.
Use `docs/project_checklist.md` only for named historical roadmap-order,
provenance, regression, hard-stop, or release-evidence questions not answered
here.

## Authority Order

1. User's latest explicit instruction.
2. `AGENTS.md` for the always-on router.
3. `docs/root_hard_stops.md` for active project authority and hard stops.
4. `docs/roadmap_status.md` for current route state.
5. The active agent architecture skill chain, the selected project/domain gate,
   affected subproject `AGENTS.md`, one active packet, one needed domain stub,
   and targeted files.

The user's prompt defines only this gate's concrete goal and requested
deliverables. Reusable process, guardrail, validation policy, and route state
belong in docs or project-local skills.

## Current Baseline

- The active route is post-MVP `v0.3 research-to-strategy adoption route` for
  evidence preparation and input artifact ownership.
- The active selector-application route is `v0.4 ML selector application`.
  v0.4 consumes v0.3 feature matrix and label manifest artifacts as read-only
  inputs for trainability checks, optional baseline model fitting, optional
  selector scoring, and `AdoptionCandidate` review prioritization.
- v0.1 and v0.2 are archived reference states. They are not current progress
  and must not be loaded into active context unless a named
  provenance/regression/compatibility check requires them.
- Step 20 and KOSPI200 technical MVP v0.1 remain frozen historical baseline
  references under archive routing.
- v0.2 `prob_up_1d_candidate` remains an archived/supporting compatibility
  artifact only. It is not the product goal and is not an active route.
- Use `.agents/skills/quant-strategy-adoption-gate/SKILL.md` for v0.3
  strategy-selection/adoption work and v0.4 evidence-only selector
  application work. Use `.agents/skills/quant-review-gate/SKILL.md` before
  accepting completion.
- Use `.agents/skills/quant-candidate-ml-gate/SKILL.md` only when a task
  explicitly requests archived/supporting `prob_up_1d_candidate` compatibility,
  candidate probability sidecars, feature tables, label-separated
  training/evaluation, or leakage checks.
- The active root work process is the agent architecture chain:
  `agent-coordinator` -> `agent-planner` -> `agent-plan-review` ->
  `agent-supervisor` -> `agent-worker-pool` -> `agent-reporter`, with
  `agent-replacement` governing migration of existing Codex skill entry points.
  Existing project-local gates remain domain authorities as compatibility
  targets selected and bounded by that chain. Routine work must treat these as
  compatibility targets selected and bounded by the active architecture chain,
  not as direct root entry points.
- Future root instructions must pass through at least
  `agent-coordinator` -> `agent-planner` -> `agent-plan-review` ->
  `agent-supervisor` before any worker, selected domain gate, implementation,
  validation, or completion acceptance begins. Worker-pool and reporter steps
  are downstream of the approved supervisor handoff.

## Archive Separation

- v0.1 and v0.2 are separated from active v0.3 progress in
  `docs/roadmap_archive/v0_1_v0_2_archive.md`.
- Default evidence-preparation work must treat v0.3 as the active input route.
  Default ML/rule selector application work must treat v0.4 as the active
  evidence-only application route and must not modify v0.3 input artifacts.
- Archived v0.1/v0.2 files are lookup references only, not active task packets,
  roadmaps, implementation instructions, or current progress status.
- Do not import archived v0.1/v0.2 context into active GPT/Codex context by
  default.
- Open archived v0.1/v0.2 material only for a named regression, provenance,
  compatibility, release/freeze, or contract-boundary check.

## Product Goal

v0.3 is focused on the end-to-end strategy discovery and evidence loop:

- collect research, papers, and strategy ideas
- structure those ideas as quant strategy candidates
- backtest or simulate each strategy candidate in an evidence-only lane
- use machine learning or evaluation algorithms to select review-preferred
  candidates
- check what historical return, risk, and performance characteristics may be
  supported by the adopted-candidate evidence

These goals are evidence and review goals. They do not by themselves authorize
live trading or production activation.

v0.4 starts after v0.3 feature matrix and label manifest preparation. It may
check trainability, fit a baseline selector only when positive and negative
classes and candidate-level evidence exist, and emit review-prioritization
manifests. It is not a future-return prediction claim, trade signal, runtime
ranking activation, or production activation path.

## Direction Lock

- All current planning, edits, validators, and review packets must align to the
  v0.3 product goal above.
- If a task feels blocked, route to the next v0.3 artifact in the flow instead
  of falling back to v0.1/v0.2 roadmap logic.
- The next artifact must be one of: `ResearchHypothesis`,
  `StrategyHypothesis`, `StrategyCandidate`, `EvaluationEvidence`, or
  `AdoptionCandidate`.
- A gate must return a concrete v0.3 next action or `NEEDS FIX`; it must not
  loop through archived v0.1/v0.2 context unless the task names a
  provenance/regression/compatibility check.

## Decision Output Discipline

Judgment-style root responses must start with a concrete conclusion. The
conclusion must be one of:

- `proceed`
- `blocked`
- `defer`
- `separate approval required`

"May be possible", "needs review", and "depends on the situation" are not valid
standalone conclusions. If uncertainty exists, convert it into explicit
validation items, blocking conditions, or the next required task.

The v0.3 strategy evaluation and adoption flow must converge toward a
review-preferred strategy candidate under the available evidence. If the
available evidence does not support selecting one candidate, the gate must say
`selection unavailable / evidence insufficient`, name the missing evidence, and
name the single highest-priority next task. Do not close with an open-ended
"multiple candidates remain possible" conclusion.

At minimum, review-preferred candidate selection must consider:

- performance relative to the benchmark
- risk-adjusted performance
- drawdown
- volatility
- turnover
- exposure stability
- cost/slippage sensitivity
- leakage and no-lookahead risk
- overfitting risk
- walk-forward or out-of-sample stability

## Authorized Active Scope

The active v0.3 route authorizes candidate/evidence work only:

- research intake and source/provenance/license mapping for strategy ideas
- `ResearchHypothesis` and `StrategyHypothesis` drafting
- `StrategyCandidate` registry, schema, fixtures, and validation checks
- candidate-only strategy definition artifacts with conceptual signal,
  entry/exit, risk-rule, and evaluation criteria fields
- approved-lane backtest or simulation execution that writes
  `EvaluationEvidence` only
- evidence-only historical return, risk, drawdown, volatility, turnover, and
  comparison summaries for candidate review
- ML or rule-based selector/evaluator work that consumes allowlisted candidate
  evidence summaries and emits `AdoptionCandidate` review packets only
- v0.4 trainability manifests, model manifests when training succeeds, and
  selector score manifests framed only as `AdoptionCandidate` review
  prioritization inputs
- validation tests, route validators, no-lookahead checks, point-in-time checks,
  no-feedback checks, and review packets
- work in the approved separate role branch/worktree for the owning lane

## Forbidden Scope Without Explicit Approval

- KOSDAQ150, futures, options, Nasdaq/overseas, or multi-universe activation.
- New market-data ingestion or live vendor assumptions.
- Live trading, brokerage integration, order generation, or real-money
  execution.
- Buy/sell recommendation language or trade-signal framing for selector
  outputs.
- Valuation/fundamental scoring activation.

## Route Ownership

- Research lane owns source intake, EvidenceCard linkage, and
  `ResearchHypothesis` drafting. The active research-ingestion implementation
  lives under `Quant_mvp/research_mvp` as a Quant_mvp subfunction lane.
- Quant strategy/governance lane owns `StrategyHypothesis` and
  `StrategyCandidate` contracts, registry fields, and scope boundaries.
- Backtest/simulation lane owns approved candidate-only historical evaluation
  runs and `EvaluationEvidence` output.
- Chart/runtime/data-support lane owns KOSPI200 chart runtime, local daily
  price collection/cache mechanics, chart outputs, and runtime scanners as a
  Quant_mvp subfunction lane, currently housed at `chart_mvp` for packaging
  and runtime separation. Quant-approved chart price outputs may be handed to
  Quant evidence lanes through explicit owner-lane scope locks and validation;
  this is a Quant-local handoff, not a cross-project handoff.
- ML/evaluator lane owns selector or evaluation algorithms that compare
  allowlisted evidence summaries and produce `AdoptionCandidate` review output.
- Root/master owns route state, cross-lane handoff shape, activation boundaries,
  and final review-gate acceptance.

## Context Boundary

Completed v0.1/v0.2 outputs are trusted as archived references by default. Do
not read archives, old Step detail, validation logs, generated packets, raw
data, caches, charts, or runtime reports unless a named conflict, regression,
provenance, compatibility question, or release/freeze verification requires it.
Start such lookup from `docs/context/ARCHIVE_INDEX.md` and read the narrowest
file needed.

Default task context is:

1. this file
2. `docs/roadmap_status.md`
3. active architecture skill from `.agents/skills`
4. selected project/domain gate from `.agents/skills`
5. affected subproject `AGENTS.md`
6. one active packet
7. one domain stub only when needed
8. targeted files

## Generated Output Boundary

Generated reports, runtime outputs, chart images, caches, raw market data,
`.env`, and secrets are not default context and are not source-controlled
unless explicitly promoted as small review fixtures.

v0.3 evidence-only outputs may be generated under documented evidence paths,
but they must not become automatic production activation inputs without a later
explicit route approval.

GPT-facing references under `docs/context/gpt/` are not refreshed by default.
Refresh them only when the user explicitly requests a GPT or ChatGPT context
update.

## Gate-End Status

At the end of a Step or assigned gate, report exactly one of:

- `COMPLETE`
- `PARTIALLY COMPLETE`
- `NEEDS FIX`
