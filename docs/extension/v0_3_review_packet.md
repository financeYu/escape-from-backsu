# v0.3 Research-to-Strategy Adoption Review Packet

Status: compact active-route review packet.
Route: `strategy_adoption_v0_3`.
Scope: candidate/evidence strategy adoption route.

This packet summarizes the active v0.3 route as an evidence route, not as a
production activation. It supports research intake, strategy candidate
structure, candidate-only backtest/simulation evidence, selector/evaluator
review, and adoption evidence. It does not authorize production
activation or live trading.

## Reviewed Route Artifacts

Stage 1 route activation and registration:

- `docs/context/EXTENSION_REGISTRY.toml`
- `docs/extension/v0_3_research_to_strategy_adoption_route.md`

Stage 2 research intake:

- `docs/extension/v0_3_strategy_hypothesis_intake_contract.md`

Stage 3 candidate registry:

- `docs/extension/v0_3_strategy_candidate_registry_contract.md`

Stage 4 backtest/simulation evidence:

- `docs/extension/v0_3_evaluation_evidence_contract.md`

Stage 5 selector/adoption evidence:

- `docs/extension/v0_3_adoption_candidate_selector_gate.md`
- `docs/extension/v0_3_production_activation_decision_gate.md`

## Flow Review

The route flow is:

`ResearchHypothesis -> StrategyHypothesis -> StrategyCandidate -> EvaluationEvidence -> AdoptionCandidate`

Flow meaning:

- `ResearchHypothesis`: research-grounded idea with source/evidence/license
  limitations.
- `StrategyHypothesis`: pre-evaluation hypothesis derived from research
  evidence, not an adoption claim.
- `StrategyCandidate`: candidate-only registry record with required data,
  universe, conceptual signal, entry/exit, risk rule, and evaluation criteria.
- `EvaluationEvidence`: evidence-only historical backtest/simulation packet
  with return/risk/performance summaries, no-lookahead, point-in-time,
  generated-output, and no-feedback checks.
- `AdoptionCandidate`: selector/evaluator-produced review candidate with
  limitations, reason codes, confidence, relative review ordering when present,
  and required review; production activation remains blocked.

## Scope Conflict Check

v0.1 frozen baseline:

- No KOSPI200 universe expansion is authorized.
- No new market-data ingestion assumption is authorized.

v0.2 `prob_up_1d_candidate` route:

- No replacement or reinterpretation of `prob_up_1d_candidate` is authorized.
- No historical evaluation metric may trigger automatic production activation.
- Probability sidecar, feature-table, label, training/evaluation, leakage, or
  label-separated pipeline work remains routed to
  `.agents/skills/quant-candidate-ml-gate/SKILL.md`.

Generated-output boundary:

- Proposed evaluation reports stay under evidence-only paths such as
  `Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/*.md`,
  `Quant_mvp/backtest_mvp/docs/v0_3_candidate_comparison/*.md`, or
  `Quant_mvp/backtest_mvp/reports/v0_3/evidence_only/`.
- Generated reports, runtime outputs, chart images, caches, raw data, `.env`,
  and secrets remain outside default context unless explicitly promoted as
  small review fixtures.

## Activation Leak Check

Activation leak check:

- No route document authorizes automatic production activation.
- No route document authorizes live trading or real-trade connection.
- `docs/extension/v0_3_production_activation_decision_gate.md` is explicitly a
  blocked separate approval route.

## Validation Evidence Summary

Local checks run during packet closure:

- `python -c "import tomllib; tomllib.load(open('docs/context/EXTENSION_REGISTRY.toml','rb'))"` should pass before closure.
- `git diff --check` should pass before closure.
- Required v0.3 artifact reference checks should pass before closure.
- Production activation leak checks should pass before closure.
- Bash-based strategy/review validators are expected to remain blocked in this
  Windows workspace when WSL/bash is unavailable.

## Closure Judgment

The v0.3 Research-to-Strategy Adoption Pipeline is active as a
candidate/evidence route.

It remains blocked for:

- live trading
- automatic production activation

## Next Approval Agenda

Next agenda:

1. Create or update concrete ResearchHypothesis and StrategyHypothesis intake
   packets.
2. Create or update the StrategyCandidate registry and schema validation.
3. Run approved candidate-only backtest/simulation tasks and record
   EvaluationEvidence.
4. Run selector/evaluator review over allowlisted evidence summaries and record
   AdoptionCandidate packets.
5. Consider a separate future production activation decision review only after
   evidence, limitations, and required reviews are explicit.
