---
name: quant-strategy-adoption-gate
description: Use for v0.3 strategy-selection/adoption route planning and proposal-only governance: StrategyCandidate registry, StrategyHypothesis intake, strategy-level ML evaluator/selector, historical simulation review metrics, candidate adoption gates, and routing to existing Quant gates. This skill is candidate-only and does not authorize production activation.
---

# Quant Strategy Adoption Gate

## Purpose

Route v0.3 strategy-selection/adoption work without repeating long guardrails
in every prompt.

This gate is proposal/candidate-only unless `docs/root_hard_stops.md` and
`docs/roadmap_status.md` explicitly open the v0.3 route. It does not activate
strategy implementation, model training, backtests, production ranking, report
behavior, `final_composite_score` replacement, valuation/fundamental scoring,
data-ingestion expansion, universe expansion, or trading recommendations.

Authority check: read `docs/root_hard_stops.md` and `docs/roadmap_status.md`
before treating any v0.3 work as more than proposal/candidate-only routing.

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

Use this skill for v0.3 strategy-selection/adoption planning or proposal work:

- `StrategyHypothesis` intake from research EvidenceCards
- `StrategyCandidate` registry contracts
- strategy-level candidate ML evaluator/selector contracts
- historical simulation metric contracts for candidate comparison
- candidate adoption gate, rejection, rollback, or retirement policy
- v0.3 route validator and router maintenance

## Route Relationships

- Use `.agents/skills/quant-candidate-ml-gate/SKILL.md` first when work needs
  `prob_up_1d_candidate`, candidate probability sidecars, feature table,
  label-separated training/evaluation, or leakage checks.
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
- proposal-only route docs, schemas, and validator checks
- adoption review eligibility definitions
- generated-output, report wording, and no-feedback boundaries as contracts
- routing to existing owner gates

## Hard Blocks

Block or return `NEEDS FIX` for:

- active v0.3 implementation scope unless root authority explicitly opens it
- production ranking activation
- report behavior change
- `final_composite_score` replacement or silent redefinition
- strategy implementation or optimization loop
- model training or production model connection
- backtest execution
- valuation/fundamental scoring activation
- financial/fundamental data in `technical_composite_score` or
  `final_composite_score`
- new market-data ingestion or universe expansion
- backtest metrics as model features, score weights, ranking inputs, or
  automatic model-selection triggers
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
validation:
  - "<command: pass/fail/not_run - short evidence>"
remaining_risks:
  - "<none or compact risk>"
status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
```
