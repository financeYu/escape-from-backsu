# v0.2 final_composite_score predictive probability semantic approval

## Approval Title

v0.2 final_composite_score predictive probability semantic approval

## Approval Token

`QG_APPROVED_FINAL_SCORE_PROB_UP_1D_V0_2`

## Explicit Approval Statement

Quant governance explicitly approves replacing the v0.2 runtime meaning of
`final_composite_score` with the validated, calibrated `prob_up_1d_candidate`
output, after all candidate ML, leakage, contract, ranking, report wording,
cross-step conflict, and quant-review-gate checks pass.

This approval opens the governance route only. It does not by itself implement
or activate runtime scoring, production ranking, report wording changes, model
training, inference, data ingestion, or generated output changes.

## Scope

- KOSPI200 only.
- v0.2+ only.
- No change to the frozen MVP v0.1 baseline.
- No KOSDAQ150, futures, options, Nasdaq, overseas universe, valuation or
  fundamental activation, or trading recommendation activation.

## Old Meaning

For MVP v0.1:

```text
final_composite_score = technical_composite_score
```

This frozen v0.1 meaning remains unchanged.

## New Meaning

For v0.2, after all required gates pass:

```text
final_composite_score = validated and calibrated estimate of the probability
that adjusted_close at the next business day is greater than adjusted_close at
the observation day.
```

The approved semantic source is the validated, calibrated
`prob_up_1d_candidate` output under the v0.2 final score gate sequence.

## Non-Goals

- No buy/sell/hold recommendation.
- No expected return claim.
- No proven alpha claim.
- No guaranteed price movement claim.
- No backtest feedback into scoring.
- No valuation or fundamental input into `final_composite_score`.
- No silent redefinition of the frozen MVP v0.1 `final_composite_score`.
- No production ranking, report, GUI, scanner, or runtime behavior change in
  this approval packet.

## Hard Stop Release Condition

`final_composite_score` replacement remains blocked until all required gates
pass:

1. Candidate ML validation PASS.
2. No-lookahead and leakage tests PASS.
3. Score semantic contract updated for the v0.2 meaning.
4. Final score contract updated.
5. Ranking contract updated.
6. Report wording forbidden check PASS.
7. Cross-Step Conflict Checkpoint PASS.
8. `quant-review-gate` final PASS.

Until every item passes, `prob_up_1d_candidate` remains non-runtime or
candidate-gated according to the current active route, and
`final_composite_score` replacement remains prohibited.

## Boundary Notes

- The approval token authorizes the future governance route, not immediate
  implementation.
- Future implementation must preserve the frozen MVP v0.1 technical-only
  baseline and use explicit v0.2+ score semantic versioning.
- Future implementation must not use valuation/fundamental data, backtest
  metrics, realized future returns, labels, generated outputs, or report fields
  as scoring/model features.
- Future runtime activation must remain config- and contract-driven and must
  keep old and new score meanings separated.
