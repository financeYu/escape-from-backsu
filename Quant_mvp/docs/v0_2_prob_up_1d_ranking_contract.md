# v0.2 prob_up_1d ranking contract

## Purpose

This contract defines the v0.2 ranking behavior for
`final_composite_score` under `score_semantic_version = "v0_2_prob_up_1d"`.
It does not change the frozen v0.1 ranking path.

## Required Input

- `score_semantic_version == "v0_2_prob_up_1d"`
- `final_score_source == "prob_up_1d_candidate"`
- `final_composite_score` is a finite float in `[0.0, 1.0]`
- `calibration_gate_pass == true`
- `leakage_no_lookahead_gate_pass == true`
- `final_score_ranking_eligible == true`

Rows with missing, NaN, infinite, or out-of-range `final_composite_score` are
excluded from v0.2 probability ranking eligibility.

## Ranking Rule

Sort order:

1. `final_composite_score` descending.
2. `ticker` ascending.

Higher rank means higher estimated calibrated probability that
`adjusted_close` on the next business day is greater than `adjusted_close` on
the feature observation business day.

## Forbidden Behavior

- Do not rank candidate-only `prob_up_1d_candidate` directly.
- Do not fill missing `final_composite_score` from `technical_composite_score`.
- Do not rank rows without calibration PASS.
- Do not rank rows without leakage/no-lookahead PASS.
- Do not imply buy/sell/hold, expected return, guaranteed return, proven alpha,
  or investment advice.

## v0.1 Preservation

The frozen v0.1 ranking path remains unchanged:

```text
final_composite_score = technical_composite_score
sort = final_composite_score desc, ticker asc
```

## Implementation

Contract helper:

```text
src/scanner/v0_2_probability_ranking.py
```

Tests:

```text
Quant_mvp/tests/test_v0_2_prob_up_1d_ranking_contract.py
```
