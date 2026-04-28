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
5. A triggered Codex skill, affected subproject `AGENTS.md`, one active packet,
   one needed domain stub, and targeted files.

The user's prompt defines only this gate's concrete goal and requested
deliverables. Reusable process, guardrail, validation policy, and route state
belong in docs or project-local skills.

## Current Baseline

- The active route is post-MVP `v0.3 research-to-strategy adoption route`.
- v0.1 and v0.2 are archived reference states. They are not current progress
  and must not be loaded into active context unless a named
  provenance/regression/compatibility check requires them.
- Step 20 and KOSPI200 technical MVP v0.1 remain frozen historical baseline
  references under archive routing.
- v0.2 `prob_up_1d_candidate` remains an archived/supporting compatibility
  artifact only. It is not the product goal and is not an active route.
- Use `.agents/skills/quant-strategy-adoption-gate/SKILL.md` for v0.3
  strategy-selection/adoption work and `.agents/skills/quant-review-gate/SKILL.md`
  before accepting completion.
- Use `.agents/skills/quant-candidate-ml-gate/SKILL.md` only when a task
  explicitly requests archived/supporting `prob_up_1d_candidate` compatibility,
  candidate probability sidecars, feature tables, label-separated
  training/evaluation, or leakage checks.

## Archive Separation

- v0.1 and v0.2 are separated from active v0.3 progress in
  `docs/roadmap_archive/v0_1_v0_2_archive.md`.
- Default work must treat v0.3 as the only active route.
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
live trading, investment recommendations, production ranking/report changes, or
future-performance guarantees.

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
- "Superior strategy" language means evidence-preferred candidate selection
  inside v0.3 review. It must not be interpreted as a production claim,
  trading recommendation, proven alpha, expected return, or future-performance
  guarantee.

## Authorized Active Scope

The active v0.3 route authorizes candidate/evidence work only:

- research intake and source/provenance/license mapping for strategy ideas
- `ResearchHypothesis` and `StrategyHypothesis` drafting
- `StrategyCandidate` registry, schema, fixtures, and validation checks
- candidate-only strategy definition artifacts with conceptual signal,
  entry/exit, risk-rule, and evaluation criteria fields
- approved-lane backtest or simulation execution that writes
  `EvaluationEvidence` only, with no production score/ranking/report feedback
- evidence-only historical return, risk, drawdown, volatility, turnover, and
  comparison summaries for candidate review
- ML or rule-based selector/evaluator work that consumes allowlisted candidate
  evidence summaries and emits `AdoptionCandidate` review packets only
- validation tests, route validators, no-lookahead checks, point-in-time checks,
  no-feedback checks, and review packets
- work in the approved separate role branch/worktree for the owning lane

## Forbidden Scope Without Explicit Approval

- KOSDAQ150, futures, options, Nasdaq/overseas, or multi-universe activation.
- New market-data ingestion or live vendor assumptions.
- Live trading, brokerage integration, order generation, or real-money
  execution.
- Production ranking activation or ranking generation unless a later active
  route explicitly authorizes it.
- Production report behavior changes unless a later active route explicitly
  authorizes them.
- Runtime score semantic changes outside an approved score/runtime gate.
- `final_composite_score` replacement or silent score redefinition.
- Financial/fundamental data in `technical_composite_score` or
  `final_composite_score`.
- Valuation/fundamental scoring activation.
- Backtest metrics as production score weights, production ranking inputs,
  runtime model features, or automatic production activation triggers.
- Backtest feedback into v0.1/v0.2 scoring, ranking, or model feature
  construction.
- Trading recommendations, buy/sell/hold instructions, proven-alpha claims,
  expected-return promises, profitability-proof wording, or future-performance
  guarantees.

## Route Ownership

- Research lane owns source intake, EvidenceCard linkage, and
  `ResearchHypothesis` drafting.
- Quant strategy/governance lane owns `StrategyHypothesis` and
  `StrategyCandidate` contracts, registry fields, and scope boundaries.
- Backtest/simulation lane owns approved candidate-only historical evaluation
  runs and `EvaluationEvidence` output.
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
3. triggered skill from `.agents/skills`
4. affected subproject `AGENTS.md`
5. one active packet
6. one domain stub only when needed
7. targeted files

## Generated Output Boundary

Generated reports, runtime outputs, chart images, caches, raw market data,
`.env`, and secrets are not default context and are not source-controlled
unless explicitly promoted as small review fixtures.

v0.3 evidence-only outputs may be generated under documented evidence paths,
but they must not become production score, ranking, report, model-feature, or
activation inputs without a later explicit route approval.

GPT-facing references under `docs/context/gpt/` are not refreshed by default.
Refresh them only when the user explicitly requests a GPT or ChatGPT context
update.

## Gate-End Status

At the end of a Step or assigned gate, report exactly one of:

- `COMPLETE`
- `PARTIALLY COMPLETE`
- `NEEDS FIX`
