# v0.2 Predictive Probability Score Route

Status: active candidate-only implementation route for post-MVP v0.2. This
route redesigns v0.2 around a candidate one-day probability score and now
allows scoped `prob_up_1d_candidate` implementation in a separate role
branch/worktree. It does not approve production ranking activation, trading
recommendations, `final_composite_score` replacement, valuation/fundamental
scoring, data-ingestion changes, or universe expansion.

## Route Goal

The v0.2 candidate score is:

- `prob_up_1d_candidate`

Intended candidate semantics:

- Higher score means higher model-estimated probability that
  `adjusted_close[t+1] > adjusted_close[t]`.
- Output must remain candidate-only until implementation, validation, audit,
  and adoption gates pass.
- The candidate score must not be presented as a trading recommendation,
  proven alpha, expected return, or guaranteed probability.

## Replaced v0.2 Assumption

The previous v0.2 technical score-revision route is superseded as the primary
v0.2 design target. The old technical candidate scores are no longer direct
production score candidates in this route.

They may be used only as:

- `old_score_features`: model features available at or before `decision_time`
- diagnostics for feature quality, stability, and coverage
- evaluation-only comparison material

They must not be silently redefined to fit the predictive target.

## Label Contract Summary

Candidate label:

```text
up_1d_label = adjusted_close[t+1] > adjusted_close[t]
```

Rules:

- `up_1d_label` is a future label and must never be used as a live scoring
  input.
- Training and evaluation may use labels only inside an approved supervised
  learning workflow.
- Rows without a known next trading-day adjusted close are non-evaluable for
  training/evaluation.
- Label construction must use split-adjusted prices under the approved
  adjustment policy.

## Feature Boundary

Allowed feature families:

- frozen MVP v0.1 technical score outputs available at or before
  `decision_time`
- old v0.2 technical/diagnostic candidate features from
  `docs/extension/v0_2_raw_feature_lineage_contract.md`
- same-date KOSPI200 eligibility metadata available at `decision_time`
- missingness, warmup, and coverage flags available at `decision_time`

Forbidden model features:

- future returns, forward labels, realized future performance
- backtest returns, backtest hit rates, realized alpha, or post-hoc evaluation
  metrics
- valuation, fundamental, accounting, analyst, filing, or market-capitalization
  data
- generated report text, chart images, local caches, or manual analyst notes

## Backtest And Evaluation Boundary

Backtest and evaluation outputs are allowed only as evaluation artifacts.

They may be used for:

- leakage checks
- calibration diagnostics
- baseline comparison
- stability review
- limitation reporting

They must not be used to:

- create live scoring features
- directly set model weights
- tune parameters without a separately approved research protocol
- activate production ranking
- claim trading utility or expected return

## Output Semantics

Allowed candidate outputs:

- `prob_up_1d_candidate`: numeric candidate probability in `[0, 1]`
- `prob_up_1d_score`: optional `0-100` presentation of
  `prob_up_1d_candidate`
- `candidate_probability_rank`: review-only ordering for diagnostics and
  adoption review

Forbidden active outputs before adoption:

- production `rank`
- active `technical_composite_score` replacement
- active `final_composite_score` replacement
- buy/sell/hold signals
- expected-return fields

## Required Remaining Gates

Implementation remains blocked until these are frozen or completed:

- predictive timing and no-lookahead contract
- old-score feature and evaluation boundary contract
- normalized probability output contract
- config ownership contract
- validation profile
- generated-output boundary
- scope watchdog review
- `review_mvp` specialist review for code/config/schema implementation
- cross-step conflict checkpoint
