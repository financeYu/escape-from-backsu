---
name: quant-strategy-adoption-gate
description: Use for v0.3 strategy-selection/adoption route planning and candidate/evidence governance: StrategyCandidate registry, StrategyHypothesis intake, strategy-level ML evaluator/selector, historical simulation review metrics, candidate adoption gates, and routing to existing Quant gates. This skill is proposal/candidate-only for production behavior and does not authorize production activation.
---

# Quant Strategy Adoption Gate

## Purpose

Route v0.3 strategy-selection/adoption work without repeating long guardrails
in every prompt.

This gate is proposal/candidate-only for production behavior unless
`docs/root_hard_stops.md` and `docs/roadmap_status.md` explicitly open a
narrower v0.3 candidate/evidence route. It does not activate live trading,
production ranking, report behavior, `final_composite_score` replacement,
valuation/fundamental scoring, data-ingestion expansion, universe expansion, or
trading recommendations.

Current root authority opens v0.3 as an active candidate/evidence route:
research intake, StrategyHypothesis and StrategyCandidate structure,
candidate-only backtest/simulation evidence, ML or rule-based
selector/evaluator review, and AdoptionCandidate evidence packets.

Authority check: read `docs/root_hard_stops.md` and `docs/roadmap_status.md`
before treating any v0.3 work as more than proposal/candidate-only routing.

## Product Goal Anchor

Every v0.3 task must serve this route memory:

- collect research, papers, and strategy ideas
- structure those ideas as quant strategy candidates
- backtest or simulate each strategy candidate in an evidence-only lane
- use machine learning or evaluation algorithms to select evidence-preferred
  strategy candidates for review
- check what historical return, risk, and performance characteristics may be
  supported by the adopted-candidate evidence

Do not let archived v0.1/v0.2 standards become the default route for this work.
Use archived v0.1/v0.2 material only for named provenance, regression,
compatibility, release/freeze, or contract-boundary checks.

## Direction-Lock Procedure

When a v0.3 task appears blocked or ambiguous:

1. Keep v0.3 as the active route.
2. Identify the next concrete artifact:
   `ResearchHypothesis`, `StrategyHypothesis`, `StrategyCandidate`,
   `EvaluationEvidence`, or `AdoptionCandidate`.
3. Route only the missing artifact, schema, validator, or owner-lane handoff.
4. Return `NEEDS FIX` only with the exact missing v0.3 artifact/check.
5. Do not loop through archived v0.1/v0.2 logic unless the task explicitly
   asks for `prob_up_1d_candidate` compatibility or historical provenance.

"Superior strategy" means an evidence-preferred candidate for review. It is
not a production claim, trading recommendation, proven alpha, expected return,
or future-performance guarantee.

## Loading Process

Read in order:

1. `docs/root_hard_stops.md`
2. `docs/roadmap_status.md`
3. this `SKILL.md`
4. affected subproject `AGENTS.md`
5. one active task packet when present
6. one needed domain stub only when required
7. targeted files only

Do not read archives, generated outputs, raw data, caches, charts, logs, or
release evidence unless the user names a conflict, regression, provenance, or
release check.

## Use When

Use this skill for active v0.3 strategy-selection/adoption candidate/evidence
work:

- `StrategyHypothesis` intake from research EvidenceCards
- `StrategyCandidate` registry contracts
- strategy-level candidate ML evaluator/selector contracts
- historical simulation metric contracts for candidate comparison
- candidate-only backtest/simulation evidence routing
- selector/evaluator review packets for review-preferred candidates
- candidate adoption gate, rejection, rollback, or retirement policy
- v0.3 route validator and router maintenance
- v0.1/v0.2 archive separation when it protects active v0.3 context

## Route Relationships

- Use `.agents/skills/quant-candidate-ml-gate/SKILL.md` only when work
  explicitly needs archived/supporting `prob_up_1d_candidate` compatibility,
  candidate probability sidecars, feature table, label-separated
  training/evaluation, or leakage checks.
- Use `.agents/skills/score-runtime-semantics-gate/SKILL.md` for runtime
  score, ranking, report, sidecar meaning, `final_composite_score`, or
  production semantic changes.
- Use `.agents/skills/quant-subproject-audit-gate/SKILL.md` for Quant
  subproject-wide audit or scope-watchdog work.
- Use `.agents/skills/quant-review-gate/SKILL.md` before accepting completion.
- Use `.agents/skills/quant-git-finalize/SKILL.md` only after review gate
  `PASS`.

## Allowed Scope

- candidate-only strategy-selection/adoption contracts
- active route docs, schemas, fixtures, and validator checks
- research intake and StrategyHypothesis drafting
- StrategyCandidate registry and schema validation
- candidate-only backtest/simulation evidence in approved owner lanes
- ML or rule-based selector/evaluator outputs limited to AdoptionCandidate
  review packets
- adoption review eligibility definitions
- generated-output, report wording, and no-feedback boundaries as contracts
- routing to existing owner gates

## Hard Blocks

Block or return `NEEDS FIX` for:

- active v0.3 work outside the candidate/evidence scope opened by root
- backtest/simulation execution without an approved owner-lane task,
  predeclared evaluation criteria, no-lookahead checks, generated-output
  boundary, and no-feedback checks
- production ranking activation
- report behavior change
- `final_composite_score` replacement or silent redefinition
- live trading, order generation, or brokerage integration
- production strategy implementation or optimization loop
- production model connection
- valuation/fundamental scoring activation
- financial/fundamental data in `technical_composite_score` or
  `final_composite_score`
- new market-data ingestion or universe expansion
- backtest metrics as production model features, score weights, ranking inputs,
  or automatic production activation triggers
- trading recommendations, buy/sell/hold, proven-alpha, expected-return, or
  profitability-proof wording

## Validation

For this gate itself, run:

```bash
bash .agents/skills/quant-strategy-adoption-gate/scripts/validate_strategy_adoption_gate.sh
```

For candidate probability inputs, also run the candidate ML gate validator when
applicable:

```bash
bash .agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh
```

For docs/config/schema edits, run `git diff --check` and targeted forbidden
wording checks. Always report checks that were not run and why.

## Output

Answer in Korean with this compact shape:

```yaml
gate: quant_strategy_adoption
task_class: planning/read-only | narrow edit | Step/gate closure
scope: proposal_only | candidate_only | blocked | needs_root_approval
owner_lane: research | quant_strategy | backtest_ml | quant_governance | mixed
allowed_outputs:
  - "<current deliverable>"
blocked_outputs:
  - "<forbidden scope or none>"
product_goal_alignment:
  - "<which v0.3 product goal item this serves>"
next_v0_3_artifact:
  - "ResearchHypothesis | StrategyHypothesis | StrategyCandidate | EvaluationEvidence | AdoptionCandidate | none"
validation:
  - "<command: pass/fail/not_run - short evidence>"
remaining_risks:
  - "<none or compact risk>"
status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
```
