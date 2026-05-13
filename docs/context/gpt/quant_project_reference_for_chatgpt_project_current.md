# Quant Project Current Context

Generated at: 2026-05-14T02:07:46+09:00
Workspace: `repository root`
Project target: `current_quant_project`
Context key: `quant_project_current_context`

This file is the only local context snapshot kept by the master workspace.
Older local snapshots managed by this script are removed during refresh.
No paid API upload is performed by this local-only workflow.

## User-Requested Context Policy

- Refresh only when the user explicitly requests this ChatGPT reference update.
- Keep latest-only local retention and exclude secrets, caches, charts, and generated data.

## Authority Order

1. User's latest explicit instruction
2. Root `AGENTS.md`
3. `docs/root_hard_stops.md`
4. `docs/roadmap_status.md`
5. Active architecture skill chain and selected project-local gate
6. Targeted source, tests, docs, and config

## Current Roadmap Position

Post-MVP `v0.3 research-to-strategy adoption route` is ACTIVE as the evidence
and input-preparation lane. Post-MVP `v0.4 ML selector application route` is
ACTIVE as the evidence-only application lane that consumes v0.3 selector
feature matrix and label manifest artifacts. Post-MVP `v0.5 personal decision
support route` is ACTIVE as a contract-only private review route that consumes
v0.3/v0.4 artifacts read-only and emits manual-check support packets only.
`v1.0-rc evidence-only readiness route` is ACTIVE through Phase 9 only as a
pre-freeze readiness lane for scope/freeze planning, next-day / 1D audit,
`HorizonPolicy`, `SimulationRunManifest`, `WeightConfig` loop,
`LayerRegistry`, `EvaluationEvidenceV1`, ML/rule selector/evaluator,
`ManualReviewPacket`, and freeze-readiness validation packets. Local v1.0
freeze is COMPLETE. Post-v1.0 development is now staged as v1.x releases:
v1.1 net profitability evidence runner, v1.2 baseline ML selector
application, v1.3 cost/turnover/liquidity reliability layer, v1.4
point-in-time revision layer, v1.5 point-in-time valuation plus
quality/profitability layer, v1.6 confidence/robustness/review-priority
integration, then a v2.0 readiness packet.
Product goal:
- omitted 86 additional lines for compact context

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
- omitted 16 additional lines for compact context

## Cross-Step Conflict Checkpoint

- Run `docs/cross_step_conflict_check.md` when a gate-critical stage ends or a Step closes.
- Use `scripts/build_review_packet.py` for compact review input.

## Active Guardrails

- KOSDAQ150, futures, options, Nasdaq/overseas, or multi-universe activation.
- New market-data ingestion or live vendor assumptions.
- Live trading, brokerage integration, order generation, or real-money
  execution.
- Buy/sell recommendation language or trade-signal framing for selector
  outputs.
- Order instructions, automatic position sizing, automatic rebalance,
  move-to-cash commands, or future-return prediction claims from v0.5 decision
  support packets.
- Valuation/fundamental scoring activation.
- v1.0 tag, release, push, or production-readiness declaration from freeze
  artifacts without explicit end-stage instruction.
- Production ranking replacement, automatic rebalance instructions,
  buy/sell/hold wording, future-return claims, or proven-alpha language from
- omitted 1 additional lines for compact context

## Route-Only References

- Root compact hard stops: `docs/root_hard_stops.md`.
- Current roadmap status: `docs/roadmap_status.md`.
- Extension registry: `docs/context/EXTENSION_REGISTRY.toml`.
- Active v0.3 route: `docs/extension/v0_3_research_to_strategy_adoption_route.md`.
- Strategy hypothesis intake: `docs/extension/v0_3_strategy_hypothesis_intake_contract.md`.
- Strategy candidate registry: `docs/extension/v0_3_strategy_candidate_registry_contract.md`.
- Evaluation evidence contract: `docs/extension/v0_3_evaluation_evidence_contract.md`.
- Adoption selector gate: `docs/extension/v0_3_adoption_candidate_selector_gate.md`.
- v1.x staged release plan: `docs/extension/v1_x_staged_release_plan.md`.

[Context truncated by `max_chars`; consult repository docs for full detail.]
