# ML Candidate Reports Boundary

`reports/ml_candidate/` is reserved for documentation and future candidate-only
ML sidecar artifacts. This directory must not contain generated runtime outputs
unless a later task explicitly promotes a small fixture for review.

## Allowed Semantics

- `prob_up_1d_candidate` means the candidate-only modeled probability that
  `adjusted_close[t+1] > adjusted_close[t]`.
- Higher values mean higher modeled probability only.
- Candidate sidecar ranking may sort by `prob_up_1d_candidate` descending and
  `ticker` ascending for ties.
- Candidate artifacts are evaluation/research sidecars and do not activate
  production ranking.

## Required Timing Fields

Candidate outputs should include:

- `ticker`
- `date`
- `decision_time`
- `execution_time`
- `label_time`
- `label_availability_time`
- `prob_up_1d_candidate`
- `prob_up_1d_candidate_status`
- `prob_up_1d_candidate_sample_role`

Training/evaluation label tables may include:

- `up_1d_label`
- `up_1d_label_available`

Label fields must stay out of inference-time feature rows.

## Forbidden Boundaries

Candidate artifacts in this directory must not:

- replace `technical_composite_score` or `final_composite_score`
- write or activate production `rank`
- feed production reports, GUI ordering, or score adoption decisions
- use backtest or evaluation outputs as model features
- use valuation/fundamental data such as PER, PBR, ROE, filings, or accounting
  fields
- contain buy/sell/hold, expected-return, proven-alpha, or recommendation
  language

## Generated Output Policy

Generated reports, model outputs, local caches, raw market data, and chart
images remain outside source control by default. If evidence is needed for
review, use a small explicit fixture path with root/master approval and explain
why it is safe to commit.
