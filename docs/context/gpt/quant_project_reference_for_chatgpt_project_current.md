# Quant Project Current Context

Generated at: 2026-05-16T06:55:25+09:00
Workspace: `repository root`
Project target: `current_quant_project`
Context key: `quant_project_current_context`

This file is the only local context snapshot kept by the master workspace.
Older local snapshots managed by this script are removed during refresh.
No paid API upload is performed by this local-only workflow.

## User-Requested Context Policy

- Refresh only when the user explicitly requests this ChatGPT reference update.
- Keep latest-only local retention and exclude secrets, caches, charts, and generated data.
- Exclude prohibited action, recommendation, activation, guarantee, and unsupported-performance phrase examples from GPT-facing output.
- Route to `docs/root_hard_stops.md` for exact forbidden wording instead of copying those phrases into GPT context.

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
quality/profitability layer, v1.6 high-confidence prediction,
robustness, and reproducibility integration. The current post-v1.0 stage is
v2.0 evidence-readiness preparation: v2.0 checks whether staged v1.1 through
- omitted 102 additional lines for compact context

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
  summary, directional expected-return and confidence summaries when
  validated, risk flags, coverage gaps, current-condition status, diagnostic
- omitted 24 additional lines for compact context

## Cross-Step Conflict Checkpoint

- Run `docs/cross_step_conflict_check.md` when a gate-critical stage ends or a Step closes.
- Use `scripts/build_review_packet.py` for compact review input.

## Active Guardrails

- Manual-review evidence support only; activation or instruction framing stays out of GPT-facing wording.
- Prohibited phrase examples are intentionally excluded from this GPT-facing snapshot.
- See `docs/root_hard_stops.md#forbidden-scope-without-explicit-approval` for exact authority wording.

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
- v1.2 ML selector application: `docs/extension/v1_2_baseline_ml_selector_application.md`.
- v1.3 cost, turnover, and liquidity reliability layer: `docs/extension/v1_3_cost_turnover_liquidity_reliability_layer.md`.

[Context truncated by `max_chars`; consult repository docs for full detail.]
