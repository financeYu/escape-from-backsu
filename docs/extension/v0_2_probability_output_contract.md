# v0.2 Probability Output Contract

Status: frozen probability output contract for the post-MVP `v0.2 predictive
probability score route`. This contract does not approve runtime model
implementation, production ranking, or trading use.

## Output Fields

Allowed candidate output fields:

- `prob_up_1d_candidate`
- `prob_up_1d_score`
- `prob_up_1d_validity_flag`
- `prob_up_1d_model_version`
- `prob_up_1d_feature_set_version`
- `prob_up_1d_decision_time`

## Score Direction

`prob_up_1d_candidate`:

- range: `[0, 1]`
- meaning: candidate model-estimated probability that
  `adjusted_close[t+1] > adjusted_close[t]`
- higher value: higher candidate estimated probability of `up_1d_label`

`prob_up_1d_score`:

- range: `[0, 100]`
- mapping: `prob_up_1d_candidate * 100`
- use: presentation and review only until adoption

## Candidate-Only Status

The output must be labeled candidate-only until all required gates pass.

Forbidden wording before adoption:

- buy/sell/hold
- expected return
- guaranteed probability
- proven alpha
- production ranking
- trading signal

## Invalid And Missing Rows

Rows must be marked invalid or non-evaluable when:

- required old-score features are missing
- warmup or insufficient-history rules fail
- source availability timing is unresolved
- same-date KOSPI200 eligibility is unavailable
- model version or feature-set version is missing

Invalid rows must not receive optimistic fills.

## Calibration Boundary

Calibration diagnostics are required before adoption. Until calibration review
passes, `prob_up_1d_candidate` must be described as a candidate model estimate,
not as a proven true probability.

Required calibration review inputs:

- calibration curve or reliability table
- Brier score or equivalent probability-quality diagnostic
- time-split validation result
- baseline comparison
- limitations and drift risks

## Ranking Boundary

`candidate_probability_rank` may be generated only as a review artifact after
generated-output boundaries are frozen. It must not replace production `rank`
or `final_composite_score` without a later adoption gate.
