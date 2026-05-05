# Quant Project Current Context

Generated at: 2026-05-06T02:55:26+09:00
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

Post-MVP `v0.3 research-to-strategy adoption route` is ACTIVE. The product goal
is now the end-to-end strategy discovery and evidence loop, not the standalone
v0.2 probability route.
Product goal:
- collect research, papers, and strategy ideas
- structure those ideas as quant strategy candidates
- backtest or simulate each strategy candidate in an evidence-only lane
- use machine learning or evaluation algorithms to select review-preferred
  candidates
- check what historical return, risk, and performance characteristics may be
  supported by the adopted-candidate evidence
Direction lock:
- v0.3 product_goal is the current route memory.
- Do not route routine v0.3 work back through archived v0.1/v0.2 standards.
- If a task is blocked, choose the next concrete v0.3 artifact:
  `ResearchHypothesis`, `StrategyHypothesis`, `StrategyCandidate`,
  `EvaluationEvidence`, or `AdoptionCandidate`.
Current baseline facts:
- omitted 33 additional lines for compact context

## Current Authorization

Allowed now:
- v0.3 route docs, contracts, schemas, validators, fixtures, and review packets
- research idea intake and provenance/license/evidence mapping
- candidate-only StrategyHypothesis and StrategyCandidate artifacts
- candidate-only backtest/simulation tasks in approved owner lanes
- EvaluationEvidence output and evidence-only comparison summaries
- ML or rule-based selector/evaluator artifacts that consume allowlisted
  evidence summaries and emit AdoptionCandidate review packets
- historical return/risk/performance summaries when framed as evidence only
Still blocked without later explicit approval:
- live trading, brokerage integration, order generation, or real-money execution
- valuation/fundamental scoring activation
- new market-data ingestion or universe expansion

## Cross-Step Conflict Checkpoint

- Run `docs/cross_step_conflict_check.md` when a gate-critical stage ends or a Step closes.
- Use `scripts/build_review_packet.py` for compact review input.

## Active Guardrails

- KOSDAQ150, futures, options, Nasdaq/overseas, or multi-universe activation.
- New market-data ingestion or live vendor assumptions.
- Live trading, brokerage integration, order generation, or real-money
  execution.
- Valuation/fundamental scoring activation.

## Route-Only References

- Root compact hard stops: `docs/root_hard_stops.md`.
- Current roadmap status: `docs/roadmap_status.md`.
- Extension registry: `docs/context/EXTENSION_REGISTRY.toml`.
- Active v0.3 route: `docs/extension/v0_3_research_to_strategy_adoption_route.md`.
- Strategy hypothesis intake: `docs/extension/v0_3_strategy_hypothesis_intake_contract.md`.
- Strategy candidate registry: `docs/extension/v0_3_strategy_candidate_registry_contract.md`.
- Evaluation evidence contract: `docs/extension/v0_3_evaluation_evidence_contract.md`.
- Adoption selector gate: `docs/extension/v0_3_adoption_candidate_selector_gate.md`.
- Active route skill: `.agents/skills/quant-strategy-adoption-gate/SKILL.md`.
- Active architecture skills: `.agents/skills/agent-coordinator/SKILL.md` through `.agents/skills/agent-reporter/SKILL.md`.
- Completion review gate: `.agents/skills/quant-review-gate/SKILL.md`.
- GPT context refresh skill: `.agents/skills/gpt-context-refresh/SKILL.md`.
- Archive lookup: `docs/context/ARCHIVE_INDEX.md`.
