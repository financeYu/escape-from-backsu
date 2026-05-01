---
name: quant-research-artifact-review
description: Use for review-only checks of active v0.3 Quant research-to-adoption artifacts and generated ledgers: ResearchHypothesis, StrategyHypothesis, StrategyCandidate, EvaluationEvidence, AdoptionCandidate, selector inputs, feedback queues, manifests, and handoff packets. Checks schema completeness, artifact linkage, status transitions, evidence requirements, no-feedback boundaries, generated-output custody, and selector claim-leakage boundaries. Does not generate candidates, run backtests, expand data ingestion, trigger production activation, or approve live trading/adoption.
---

# Quant Research Artifact Review

## Purpose

Review active v0.3 research-to-adoption artifacts without turning review into
implementation, backtesting, production activation, or adoption approval.

This skill is a review gate for generated or source-controlled v0.3 research
artifacts. It checks whether each artifact can safely move to the next v0.3
stage:

1. ResearchHypothesis
2. StrategyHypothesis
3. StrategyCandidate
4. EvaluationEvidence
5. AdoptionCandidate

It does not create the next artifact, run simulations, select winners, approve
live trading, or trigger production activation.

## Authority And Loading

Read in order:

1. `docs/root_hard_stops.md`
2. `docs/roadmap_status.md`
3. this `SKILL.md`
4. affected subproject `AGENTS.md`
5. targeted artifact files, manifests, or small fixtures named by the task

Generated outputs are normally outside default context. Read generated v0.3
outputs only when the user explicitly asks to review, audit, validate, or
summarize those artifacts, or when a manifest is needed to verify custody.

Do not load archived v0.1/v0.2 material unless the task names a provenance,
regression, compatibility, release/freeze, or contract-boundary check.

## Allowed Scope

- Review ResearchHypothesis schema completeness and next-action quality.
- Review StrategyHypothesis testability: signal, entry, exit, holding period,
  rebalance, universe, benchmark, metrics, and failure definition.
- Review StrategyCandidate registry readiness: ID, version, status,
  experiment scope, data requirements, acceptance criteria, required evidence,
  blockers, and next action.
- Review EvaluationEvidence custody: linked candidate, run configuration,
  benchmark, metrics, no-lookahead checks, transaction-cost sensitivity,
  limitations, and no-feedback boundary.
- Review AdoptionCandidate packets as review-preferred only, not adoption or
  trading approval.
- Review generated-output custody and `.gitignore` behavior.
- Review chain linkage across artifacts and manifests.
- Review paper-claim leakage into selector/evaluator preference signals.

## Forbidden Scope

Return `NEEDS FIX` if the task asks this skill to:

- generate or mutate strategy candidates, evidence, rankings, reports, or live
  runtime outputs
- run backtests or simulations
- add market-data ingestion, universe expansion, live vendor assumptions, or
  new production features
- trigger automatic production activation
- treat paper claim language as selector/evaluator preference signal instead of
  a neutral risk flag

## Review Procedure

For the scoped artifacts:

1. Identify the current stage and expected previous/next stage.
2. Verify the artifact has a stable ID and links to its required parent.
3. Verify schema fields are present and populated with measurable values where
   the schema requires testability.
4. Verify status semantics are conservative:
   - `ready` status requires data, rules, evaluation scope, and evidence
     requirements.
   - non-ready status requires blockers or minimal fixes.
   - AdoptionCandidate requires EvaluationEvidence.
5. Verify no artifact bypasses the required flow:
   ResearchHypothesis -> StrategyHypothesis -> StrategyCandidate ->
   EvaluationEvidence -> AdoptionCandidate.
6. Verify no paper claim language is used as selector/evaluator preference
   signal except as a boolean or neutral risk flag.
7. Verify no generated output is source-controlled unless explicitly promoted
   as a small review fixture.
8. Verify no evidence, backtest metric, or review result triggers automatic
   production activation.

## Stage-Specific Checks

ResearchHypothesis:

- Requires market mechanism, required data, falsification test, risks,
  evidence quality, confidence level, next action, and reason.
- `convert_to_strategy_hypothesis` requires usable next-stage input.
- `needs_more_research` or `reject` requires blocker or minimal fix.

StrategyHypothesis:

- Requires signal definition, calculation window, entry rule, exit rule,
  holding period, rebalance rule, universe filter, benchmark, primary metric,
  null hypothesis, expected positive pattern, expected failure case, and data
  requirements.
- `ready_for_candidate_registry` requires measurable rules and next-stage
  input.

StrategyCandidate:

- Requires candidate ID, linked StrategyHypothesis ID, version, status,
  experiment scope, test period, data requirements, feature requirements,
  acceptance criteria, rejection criteria, required evidence, blockers, next
  action, and reason.
- `ready_for_eval` requires EvaluationEvidence next-stage input and no blocking
  issues.

EvaluationEvidence:

- Requires linked candidate ID/version, run configuration, data snapshot or
  provenance, benchmark, primary/secondary metrics, limitations, no-lookahead
  checks, no-feedback check, and generated-output custody.
- Must not trigger automatic production activation.

AdoptionCandidate:

- Requires linked EvaluationEvidence, reason for review preference, unresolved
  risks, limitations, rollback or rejection path, and explicit statement that
  it is review-preferred only.
- Must not be represented as live trading approval.

## Output

Report in Korean:

```yaml
gate: quant_research_artifact_review
task_class: planning/read-only | narrow edit | Step/gate closure
review_scope:
  - "<artifact or path>"
artifact_stage: ResearchHypothesis | StrategyHypothesis | StrategyCandidate | EvaluationEvidence | AdoptionCandidate | mixed
gate_result: PASS | NEEDS FIX
findings:
  - "<severity and concrete issue, or none>"
schema_check:
  - "<pass/fail item>"
linkage_check:
  - "<pass/fail item>"
evidence_check:
  - "<pass/fail item>"
boundary_check:
  - "<pass/fail item>"
generated_output_check:
  - "<pass/fail/not_applicable item>"
validation_evidence:
  - "<command or inspection evidence>"
remaining_risk:
  - "<none or compact risk>"
next_v0_3_artifact:
  - "ResearchHypothesis | StrategyHypothesis | StrategyCandidate | EvaluationEvidence | AdoptionCandidate | none"
status: COMPLETE | PARTIALLY COMPLETE | NEEDS FIX
```

Use `PASS` only when the reviewed artifact is complete enough for its declared
status and does not violate project hard stops. Otherwise use `NEEDS FIX` with
the smallest concrete repair.

## Validation

For this skill contract itself, run:

```bash
powershell -ExecutionPolicy Bypass -File scripts\run_bash_validator.ps1 .agents\skills\quant-research-artifact-review\scripts\validate_research_artifact_review.sh
```
