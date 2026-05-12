# Roadmap Status

This file keeps only the latest route state needed for current work. Completed
v0.1/v0.2 implementation and validation history are archived reference
material, not default context. Use `docs/context/archive/` or
`docs/roadmap_archive/` only for named conflict, regression, provenance,
compatibility, hard-stop, or release-evidence checks.

## Current Route State

Post-MVP `v0.3 research-to-strategy adoption route` is ACTIVE as the evidence
and input-preparation lane. Post-MVP `v0.4 ML selector application route` is
ACTIVE as the evidence-only application lane that consumes v0.3 selector
feature matrix and label manifest artifacts. Post-MVP `v0.5 personal decision
support route` is ACTIVE as a contract-only private review route that consumes
v0.3/v0.4 artifacts read-only and emits manual-check support packets only.
`v1.0-rc evidence-only readiness route` is ACTIVE through Phase 3 only as a
pre-freeze readiness lane for scope/freeze planning, next-day / 1D audit,
`HorizonPolicy`, and `SimulationRunManifest`.

Product goal:

- collect research, papers, and strategy ideas
- structure those ideas as quant strategy candidates
- backtest or simulate each strategy candidate in an evidence-only lane
- use machine learning or evaluation algorithms to select review-preferred
  candidates
- check what historical return, risk, and performance characteristics may be
  supported by the adopted-candidate evidence

Direction lock:

- v0.3 product_goal is the current evidence route memory.
- v0.4 consumes v0.3 feature matrix and label manifest artifacts as read-only
  inputs for trainability checks, optional baseline selector fitting, optional
  selector score manifests, and `AdoptionCandidate` review prioritization.
- v0.5 consumes v0.3 evidence and v0.4 diagnostics as read-only inputs for
  `PersonalDecisionSupportPacket` preparation. It may organize evidence,
  coverage gaps, risk flags, cost-sensitivity flags, and manual review
  checklists, but it must not generate order instructions, position sizing, or
  future-return claims.
- v1.0-rc Phase 0 through Phase 3 prepare evidence-only readiness contracts.
  They do not authorize final v1.0 freeze, tags, pushes, production
  activation, live execution, valuation/fundamental activation, futures
  activation, or Phase 4+ implementation.
- Do not route routine v0.3 work back through archived v0.1/v0.2 standards.
- If a task is blocked, choose the next concrete v0.3 artifact:
  `ResearchHypothesis`, `StrategyHypothesis`, `StrategyCandidate`,
  `EvaluationEvidence`, or `AdoptionCandidate`.

Current baseline facts:

- v0.1 is archived as a frozen historical baseline reference.
- v0.2 is archived as a supporting probability compatibility reference.
- Archived v0.1/v0.2 material must not be mixed into current v0.3 progress
  unless a named provenance/regression/compatibility check requires it.
- v0.3 is the active route for research intake, strategy candidate structure,
  evidence-only backtest/simulation, selector/evaluator review, and adoption
  evidence.
- v0.4 is the active route for ML/rule selector application. It does not
  authorize live trading, order generation, buy/sell recommendation language,
  production activation, new market-data ingestion, or universe expansion.
- v0.5 is the active contract-only route for private personal decision support.
  It does not authorize live trading, brokerage integration, order generation,
  buy/sell/hold imperative language, automatic rebalance, move-to-cash
  instructions, production activation, new market-data ingestion, universe
  expansion, or valuation/fundamental scoring activation.
- v1.0-rc Phase 0 and Phase 1 are complete as readiness planning and audit
  documents. Phase 2 and Phase 3 are complete as `HorizonPolicy` and
  `SimulationRunManifest` readiness contracts. Phase 4+ remains unopened.

Current active route skill:

- `.agents/skills/quant-strategy-adoption-gate/SKILL.md`
  - applies to v0.3/v0.4 evidence work and v1.0-rc readiness contracts

Current active root orchestration:

- `.agents/skills/agent-coordinator/SKILL.md`
- `.agents/skills/agent-planner/SKILL.md`
- `.agents/skills/agent-plan-review/SKILL.md`
- `.agents/skills/agent-supervisor/SKILL.md`
- `.agents/skills/agent-worker-pool/SKILL.md`
- `.agents/skills/agent-reporter/SKILL.md`
- `.agents/skills/agent-replacement/SKILL.md`

The architecture chain is now the default root work process. Existing
project-local route and review gates remain domain authorities, but routine
work reaches them as compatibility targets selected and bounded by the
architecture chain.

Current execution invariant: no worker, selected domain gate, implementation,
validation, or completion acceptance begins before `agent-coordinator` ->
`agent-planner` -> `agent-plan-review` -> `agent-supervisor` has selected and
approved the route. Worker-pool and reporter steps run only after that approved
supervisor handoff.

Completion review gate:

- `.agents/skills/quant-review-gate/SKILL.md`

Archived/supporting probability compatibility route:

- `.agents/skills/quant-candidate-ml-gate/SKILL.md`
- `.agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh`
- Use only when a task explicitly touches archived/supporting
  `prob_up_1d_candidate` compatibility.

## Active v0.3 Work Lanes

| Lane | Active purpose | Primary output |
| --- | --- | --- |
| Research intake | collect papers, research notes, EvidenceCards, and strategy ideas | `ResearchHypothesis` |
| Strategy structure | convert ideas into testable strategy hypotheses and candidate records | `StrategyHypothesis`, `StrategyCandidate` |
| Chart runtime/data support | maintain Quant-owned chart runtime and approved local daily price handoff support | validated Quant-local price inputs or runtime support packet |
| Backtest/simulation | evaluate candidates historically with no-lookahead and no-feedback checks | `EvaluationEvidence` |
| ML/evaluator selector | compare allowlisted evidence summaries and select review-preferred candidates | `AdoptionCandidate` |
| v0.4 selector application | consume v0.3 feature matrix and label manifest for trainability, optional baseline fit, and optional review-prioritization score manifests | trainability manifest, optional model manifest, optional selector score manifest |
| v0.5 personal decision support | consume v0.3/v0.4 artifacts read-only and organize private manual-check support packets with fail-closed current-condition checks | `PersonalDecisionSupportPacket`, `CurrentConditionSnapshot` |
| Adoption evidence | summarize historical return/risk/performance characteristics for review | adoption review packet |

## Active Route Artifacts

- `docs/extension/v0_3_research_to_strategy_adoption_route.md`
- `docs/extension/v0_3_strategy_hypothesis_intake_contract.md`
- `docs/extension/v0_3_strategy_candidate_registry_contract.md`
- `docs/extension/v0_3_evaluation_evidence_contract.md`
- `docs/extension/v0_3_kospi200_historical_universe_tracking_contract.md`
- `docs/extension/v0_3_adoption_candidate_selector_gate.md`
- `docs/extension/v0_3_production_activation_decision_gate.md`
- `docs/extension/v0_3_review_packet.md`
- `docs/extension/v0_4_ml_selector_application_route.md`
- `docs/extension/v0_4_selector_model_training_contract.md`
- `docs/extension/v0_4_selector_model_manifest_contract.md`
- `docs/extension/v0_5_pre_entry_gap_assessment.md`
- `docs/extension/v0_5_personal_decision_support_route.md`
- `docs/extension/v0_5_current_condition_snapshot_contract.md`
- `docs/extension/v1_0_freeze_plan.md`
- `docs/extension/v1_0_scope_boundary.md`
- `docs/extension/v1_0_next_day_hardcoding_audit.md`
- `docs/extension/v1_0_horizon_policy_contract.md`
- `docs/extension/v1_0_simulation_run_manifest_contract.md`
- `config/horizon_policy.toml`
- `docs/context/EXTENSION_REGISTRY.toml`

## Archived v0.1/v0.2 References

- Archive routing packet: `docs/roadmap_archive/v0_1_v0_2_archive.md`
- Archive index: `docs/context/ARCHIVE_INDEX.md`
- v0.1 frozen baseline reference:
  `docs/context/MVP_V0_1_BASELINE.md`
- v0.1 contract manifest reference:
  `docs/context/MVP_V0_1_CONTRACT_MANIFEST.toml`
- v0.2 predictive probability route reference:
  `docs/extension/v0_2_predictive_probability_route.md`
- v0.2 probability output contract reference:
  `docs/extension/v0_2_probability_output_contract.md`

Archived references are not current progress. They are opened only for named
provenance, regression, compatibility, release/freeze, or contract-boundary
checks.

## Current Authorization

Allowed now:

- v0.3 route docs, contracts, schemas, validators, fixtures, and review packets
- research idea intake and provenance/license/evidence mapping
- candidate-only StrategyHypothesis and StrategyCandidate artifacts
- candidate-only backtest/simulation tasks in approved owner lanes
- EvaluationEvidence output and evidence-only comparison summaries
- ML or rule-based selector/evaluator artifacts that consume allowlisted
  evidence summaries and emit AdoptionCandidate review packets
- v0.4 baseline selector trainability checks, model manifests when training
  succeeds, and selector score manifests limited to AdoptionCandidate review
  prioritization
- v0.5 personal decision support contracts and packets limited to evidence
  summary, risk flags, coverage gaps, current-condition status, diagnostic
  references, and manual review checklists
- v1.0-rc Phase 0 through Phase 3 readiness artifacts limited to scope/freeze
  planning, next-day / 1D hardcoding audit, `HorizonPolicy`, and
  `SimulationRunManifest`
- historical return/risk/performance summaries when framed as evidence only

Still blocked without later explicit approval:

- live trading, brokerage integration, order generation, or real-money execution
- valuation/fundamental scoring activation
- new market-data ingestion or universe expansion
- final v1.0 freeze, tag, release, push, or production-readiness declaration
- v1.0-rc Phase 4+ implementation without a later explicit task approval

## Parallel Workspace Policy

Step 15+ implementation, review, audit/scope-watchdog, research, chart runtime,
and master integration work remain separated by role branch/worktree.

`C:\Users\jjaew\Project\master_mvp` remains the integration, verification, and
status-control workspace unless a task explicitly selects a role worktree.
`chart_mvp` and `Quant_mvp/research_mvp` are Quant_mvp subfunction lanes for
route ownership, even when their physical directories are separated for runtime
or ingestion isolation. Handing data or packets among these Quant lanes is a
Quant-local owner-lane handoff, not a cross-project handoff.

## Overall Step State

| Step | Status |
| --- | --- |
| Step 1 | COMPLETE or mostly complete |
| Step 2 | COMPLETE |
| Step 3 | COMPLETE |
| Step 4 | COMPLETE |
| Step 5 | COMPLETE |
| Step 6 | COMPLETE |
| Step 7 | COMPLETE |
| Step 8 | COMPLETE |
| Step 9 | COMPLETE |
| Step 10 | COMPLETE |
| Step 11 | COMPLETE |
| Step 12 | COMPLETE |
| Step 13 | COMPLETE |
| Step 14 | COMPLETE |
| Step 15 | COMPLETE |
| Step 16 | COMPLETE |
| Step 17 | COMPLETE |
| Step 18 | COMPLETE |
| Step 19 | COMPLETE |
| Step 20 | COMPLETE / KOSPI200 MVP Completeness Hardening and Final Done Validation |
| post-MVP v0.1 KOSPI200 technical MVP | ARCHIVED / frozen baseline reference |
| post-MVP v0.2 predictive probability score route | ARCHIVED / supporting compatibility reference |
| post-MVP v0.3 research-to-strategy adoption route | ACTIVE |
| post-MVP v0.4 ML selector application route | ACTIVE / consumes v0.3 inputs read-only |
| post-MVP v0.5 personal decision support route | ACTIVE / contract-only private review packets |
| v1.0-rc Phase 0 preflight / scope boundary | COMPLETE / readiness planning only |
| v1.0-rc Phase 1 next-day / 1D hardcoding audit | COMPLETE / readiness audit only |
| v1.0-rc Phase 2 HorizonPolicy | COMPLETE / readiness contract |
| v1.0-rc Phase 3 SimulationRunManifest | COMPLETE / readiness contract |
| v1.0-rc Phase 4+ modules | NOT OPEN / requires later explicit task approval |

## Baseline Contracts

- Archived v0.1 contracts remain frozen references.
- MVP universe remains KOSPI200 unless a later route explicitly opens another
  universe.
- Backtest and simulation outputs are evaluation evidence only.
- Generated evidence reports, runtime outputs, chart images, local caches, raw
  market data, `.env`, and secrets are not default context.
- v0.3 evidence must not become automatic production activation.
- v0.4 selector outputs must not become trade signals, order instructions,
  runtime ranking activation, or production activation.
- v0.5 personal decision support outputs must not become order instructions,
  automatic position sizing, buy/sell/hold imperatives, move-to-cash commands,
  runtime ranking activation, or production activation.
- v1.0-rc readiness outputs must not become final release evidence, production
  activation, live execution, valuation/fundamental activation, futures/index
  activation, or Phase 4+ implementation without later explicit approval.

## Research Ingestion State

- Research ingestion now supports v0.3 idea intake and StrategyHypothesis
  drafting.
- EvidenceCards remain evidence/provenance records, not score definitions or
  adoption decisions.
- Paper-reported backtests are diagnostic metadata until reproduced through an
  approved v0.3 evaluation lane.
- PDF full-text download remains subject to license, source/access, and local
  custody checks.

## Guardrails

- no future data
- no lookahead
- config-first implementation
- documented strategy candidate before evaluation
- predeclared evaluation criteria before backtest/simulation
- no automatic production activation from evaluation evidence
- no active valuation/fundamental activation while valuation status is
  candidate-only
- no price-only evidence as valuation language

## Detailed History Locations

- Compact post-Step20 baseline: `docs/context/MVP_V0_1_BASELINE.md`
- Context routing index: `docs/context/CONTEXT_ROUTING_INDEX.md`
- Archive index: `docs/context/ARCHIVE_INDEX.md`
- Release evidence: `docs/releases/`
- Contracts: `docs/contracts/step20_composite_contract.md`,
  `docs/contracts/step20_ranking_contract.md`

## Cross-Step Conflict Checkpoint

Run a Cross-Step Conflict Checkpoint whenever an important in-Step stage ends
and before each Step is closed.

Use `docs/cross_step_conflict_check.md` and generate a compact review packet
with:

```powershell
python scripts/build_review_packet.py --step "<current step>" --stage "<stage name>"
```

Completed Step artifacts are trusted by default. The checkpoint checks only
whether the current stage conflicts with roadmap order, hard stops,
cross-project handoffs, generated-output boundaries, context-routing
boundaries, or unresolved carry-forward risks.
