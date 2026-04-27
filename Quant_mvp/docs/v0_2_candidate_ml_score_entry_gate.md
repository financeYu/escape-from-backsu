# v0.2 Candidate ML Score Entry Gate

Status: entry gate only. This document prepares a future candidate-only ML
score implementation path. It does not implement model training, inference,
runtime ranking generation, production report behavior, or production score
activation.

## Completion Target

The v0.2 candidate-only completion target is:

> Using only data available as of the decision date / today's available dataset, compute `prob_up_1d_candidate` and generate a sidecar candidate-only ranking artifact ordered by that candidate score.

Clarifications:

- This is a candidate-only ML ranking artifact.
- It does not replace `final_composite_score`.
- It leaves production ranking behavior unchanged.
- It does not change existing reports.
- It does not create trading recommendations.
- It preserves the frozen MVP v0.1 KOSPI200 technical-only baseline.

## `prob_up_1d_candidate` Semantics

- field name: `prob_up_1d_candidate`
- meaning: model-estimated candidate probability that
  `adjusted_close[t+1] > adjusted_close[t]`
- allowed range: `0.0` to `1.0`
- status: candidate-only
- production status: not a production score
- signal boundary: not a trading direction signal
- return boundary: not a return-forecast field or profitability claim

## Label Contract

- label: `adjusted_close[t+1] > adjusted_close[t]`
- suggested label column: `label_up_1d`
- `adjusted_close[t+1]` may be used only as label material.
- Future price, future return, realized return, and label-derived columns must
  not be training or inference features.
- Rows without an available next-period label may be used for current
  candidate inference only; they must not be forced into labeled evaluation.

## Timing Contract

Required timing fields:

- `decision_time`: time at which all candidate features are considered known.
- `execution_time`: next candidate timing reference after `decision_time`.
- `label_time`: time represented by the future adjusted close used in the
  label.
- `label_availability_time`: time when the label can actually be known.

Rules:

- Every feature must be available at or before `decision_time`.
- `label_time` is after the decision date.
- `label_availability_time` is when the label can actually be known.
- Today/as-of-date inference must run without labels.
- Missing and warmup state must not be filled with optimistic values.
- Any deterministic imputation or exclusion rule must be documented before
  implementation.

## No-Lookahead Contract

- Feature builders must not read rows after `decision_time`.
- Labels must be stored separately from feature rows.
- Label-derived fields must be rejected as features.
- Backtest, evaluation, or realized outcome fields must be rejected as features.
- Current as-of-date output must be valid without requiring `label_up_1d`.

## Sidecar Ranking Boundary

The candidate-only sidecar artifact may be sorted by:

1. `prob_up_1d_candidate` descending
2. `ticker` ascending as the tie-breaker

Boundary rules:

- The artifact must be clearly named candidate-only and sidecar.
- It must not overwrite latest production ranking.
- It must not be consumed by final production reports.
- It must not modify `technical_composite_score`.
- It must not modify `final_composite_score`.
- It must not alter GUI, scanner, or report ordering unless a later explicit
  route opens a candidate-only display path.

## Backtest And Evaluation Boundary

- Model evaluation is allowed only for candidate model assessment.
- Evaluation/backtest output is evaluation-only.
- Evaluation output must not feed upstream scoring, ranking, reports, model
  feature construction, or production adoption.
- Result-based parameter optimization is forbidden unless separately approved
  under a bounded, predeclared, walk-forward protocol.
- Wording that implies recommendations, strategy superiority, performance
  proof, alpha proof, or return forecasting is forbidden.

## Future Implementation Gate Checklist

Before implementation begins, confirm:

- `adjusted_close` availability is confirmed.
- Decision-date feature availability is confirmed.
- Feature allowlist or feature-family allowlist is defined.
- Label generation contract is fixed.
- Timing fields are fixed.
- No-lookahead tests are planned.
- Sidecar output path is planned.
- Production ranking remains untouched.
- Final score remains untouched.
- Forbidden wording guardrail is planned.
- Cross-Step Conflict Checkpoint trigger is documented.

## Validation Checklist

Future implementation validation must include:

- label correctness test
- no-lookahead feature availability test
- as-of-date inference without labels
- sidecar sort test
- candidate-only naming test
- production ranking untouched test
- `technical_composite_score` untouched test
- `final_composite_score` untouched test
- forbidden wording guardrail test
- generated-output boundary check

## Entry Gate Verdict

This entry gate is prepared for future implementation planning only. It does
not authorize model training, inference, runtime ranking generation, report
changes, final score changes, production adoption, new data ingestion, valuation
activation, or universe expansion.
