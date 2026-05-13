# v1.3 Cost, Turnover, Liquidity Reliability Layer

This document records the v1.3 reliability layer contract opened by
`docs/extension/v1_x_staged_release_plan.md`.

The v1.3 goal is to check whether candidate profitability evidence remains
reviewable after explicit cost profile, turnover, and liquidity reliability
assumptions are applied. It is evidence-only, candidate-only, and
manual-review-support only. It is not a deployable return model, execution
workflow, production ranking replacement, or automatic rebalance workflow.

## Implementation

- Module: `Quant_mvp/backtest_mvp/cost_liquidity_reliability_v1_3.py`
- Test: `tests/backtest/test_v1_3_cost_liquidity_reliability.py`
- Owner lane: Quant backtest/simulation plus quant governance
- Completion gate: `.agents/skills/quant-review-gate/SKILL.md`

## Inputs

Inputs are read-only `EvaluationEvidenceV1` records from v1.1 or later
approved historical or simulated evidence.

Required evidence fields:

- `candidate_id`
- `evidence_id`
- `metric_values.realized_return_summary.gross_return`
- `metric_values.realized_return_summary.net_return`
- `metric_values.realized_turnover_summary`
- `metric_values.realized_cost_summary.cost_drag`
- `date_range`
- `leakage_check_status`
- `no_lookahead_check_status`

Candidate-level liquidity handoff rows may provide:

- `candidate_id`
- `evidence_id`
- `average_traded_value`: average traded value proxy, interpreted as KRW
  amount in v1.3
- `market_cap_proxy`
- `capacity_reference_amount`
- `liquidity_proxy_source_ref`: source, as-of date, and calculation-window
  reference, for example `approved_local_liquidity_snapshot_YYYYMMDD`

The helper `build_v1_3_candidate_liquidity_handoff` normalizes these rows into
`v1_3_candidate_liquidity_handoff`. If liquidity records are missing for a
candidate, v1.3 does not infer liquidity from price-only evidence. The handoff
row is marked `missing`, the liquidity guard row is marked `warn` with
`liquidity_proxy_missing`, and the data gap is carried into the manual review
section. Extra handoff rows whose `candidate_id` does not exactly match an
`EvaluationEvidenceV1` candidate are reported as `candidate_id_mismatch` in
the handoff data-gap summary. Duplicate liquidity handoff rows for the same
`candidate_id` are rejected instead of being merged or silently overwritten.

The chart/runtime data-support lane may provide a local generated handoff
source such as
`chart_mvp/data/v1_3_liquidity/v1_3_candidate_liquidity_handoff_records_latest.csv`.
That file remains a generated data-support artifact from the Quant chart lane.
v1.3 consumes only the normalized candidate-level handoff fields and keeps the
result evidence-only and manual-review-support only. If the local handoff file
covers only a subset of `EvaluationEvidenceV1` candidates, uncovered candidates
remain `warn` with `liquidity_proxy_missing` until an approved candidate-level
handoff row is supplied.

## Outputs

The runner emits these artifact keys:

- `v1_3_candidate_liquidity_handoff`
- `v1_3_cost_profile_registry`
- `v1_3_turnover_penalty_report`
- `v1_3_liquidity_guard_report`
- `v1_3_rebalance_sensitivity_report`
- `v1_3_gross_vs_net_evidence_summary`
- `v1_3_manual_review_cost_risk_section`

Every candidate row carries a `cost_profile_ref`. Gross evidence, source net
evidence, and v1.3 adjusted net evidence are reported separately.

## Candidate Liquidity Handoff

`v1_3_candidate_liquidity_handoff` is the required candidate-level bridge
between approved liquidity proxy inputs and the v1.3 reliability runner. It
does not collect new market data and does not infer liquidity from price-only
evidence.

Handoff row status:

- `complete`: traded-value, market-cap proxy, capacity reference, and source
  reference are present
- `partial`: at least one liquidity proxy field is missing
- `missing`: no liquidity proxy row was provided for that candidate

`complete` means the required handoff fields are present. It does not by
itself mean the liquidity thresholds are satisfied.

`liquidity_sufficiently_checked` is true only when all of these are true:

- `candidate_id` matches an `EvaluationEvidenceV1` candidate exactly
- `average_traded_value` exists
- `market_cap_proxy` exists
- `capacity_reference_amount` exists
- `liquidity_proxy_source_ref` exists
- `average_traded_value >= 5_000_000_000`
- `capacity_reference_amount <= average_traded_value * 0.05`
- no liquidity block reason exists
- no liquidity warn reason exists

## Reliability States

Turnover status:

- `pass`: turnover and cost drag are within configured thresholds
- `warn`: turnover or cost drag is elevated
- `block`: turnover or cost drag breaches the configured block threshold

Liquidity status:

- `pass`: liquidity proxies are present and satisfy the sufficiency checks
- `warn`: liquidity proxy row is missing, a required liquidity proxy field is
  missing, source reference is missing, average traded value is greater than
  `1_000_000_000` and below `5_000_000_000`, or
  `capacity_reference_amount > average_traded_value * 0.05`
- `block`: `average_traded_value <= 1_000_000_000`

Block reasons take priority over warn reasons for the final status. Warn
reasons are still retained in `reason_codes` so manual review can see every
limitation.

## Completion Criteria

v1.3 is complete when:

- cost profile versioning is recorded and each evidence row has a
  `cost_profile_ref`
- candidate-level liquidity handoff rows exist for every evidence candidate
- candidate and aggregate turnover penalty metrics are emitted
- liquidity status is separated as `pass`, `warn`, or `block`
- gross evidence and net evidence are reported separately
- daily, weekly, and monthly sensitivity labels can be compared as historical
  or simulated context
- manual review cost/liquidity limitations are summarized
- focused cost profile, turnover, liquidity guard, disclosure, and guardrail
  tests pass

## Data Gap Handling

Current v1.1/v1.2 candidate-level evidence contains turnover and cost drag, but
it does not always contain traded-value, market-cap, or capacity-reference
liquidity proxies. v1.3 therefore supports reliability reporting even when
liquidity data is incomplete, but the affected candidates remain `warn` until
approved liquidity inputs are provided. Price data alone is not used to
estimate liquidity. Candidate-level liquidity proxy handoff input is required
for liquidity sufficiency. Missing `market_cap_proxy`, missing
`capacity_reference_amount`, or missing `liquidity_proxy_source_ref` means the
candidate is not sufficiently checked for v1.3 liquidity reliability.

## Completion Statement

Candidate profitability evidence can be reviewed with explicit cost profile,
turnover, and liquidity reliability status, while missing liquidity data remains
visible as a manual review limitation.
