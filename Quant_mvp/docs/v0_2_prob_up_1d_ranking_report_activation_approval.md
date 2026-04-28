# v0.2 ranking and report activation approval

## Approval Title

v0.2 ranking and report activation for final_composite_score prob_up_1d semantics

## Approval Token

`QG_APPROVED_RANKING_REPORT_PROB_UP_1D_V0_2`

## Explicit Approval Statement

Quant governance approves opening the v0.2 ranking and report activation route
for `final_composite_score` under the `v0_2_prob_up_1d` semantic version only
after the final-score probability contract, candidate ML validation,
calibration, no-lookahead/leakage, ranking contract, report wording, cross-step
conflict, and quant-review-gate checks pass.

This approval does not activate ranking/report code by itself.

## Scope

- Universe: KOSPI200 only.
- Version: v0.2+ only.
- Frozen baseline: no change to MVP v0.1.
- No KOSDAQ150, futures, options, Nasdaq, overseas universe, valuation,
  fundamental scoring, trading recommendation, expected-return claim, or
  guaranteed outcome activation.

## Ranking Meaning

- Ranking is sorted by `final_composite_score` descending.
- Higher rank means higher estimated calibrated probability of
  next-business-day `adjusted_close` increase.
- Ranking does not mean buy recommendation, expected return, guaranteed
  outperformance, proven alpha, or investment advice.

## Ranking Eligibility

Rows are eligible for v0.2 probability ranking only when all conditions hold:

- `score_semantic_version == "v0_2_prob_up_1d"`.
- `final_composite_score` is a non-null finite float in `[0.0, 1.0]`.
- Calibration gate is PASS.
- Leakage/no-lookahead gate is PASS.
- `final_score_source == "prob_up_1d_candidate"`.
- Invalid final scores are excluded.
- Candidate-only `prob_up_1d_candidate` is not ranked directly.
- `technical_composite_score` is not used as fallback for missing probability
  final scores.

## Tie Handling

Use existing deterministic project convention unless a later contract states a
more specific v0.2 rule:

1. `final_composite_score` descending.
2. `ticker` ascending.

The v0.1 tie convention remains unchanged.

## Report Wording

Allowed wording:

- "1영업일 뒤 adjusted_close 상승확률 추정값"
- "상승확률 기반 순위"
- "v0.2 확률형 최종 스코어"

Forbidden wording:

- "매수"
- "매도"
- "보유"
- "추천"
- "투자 조언"
- "확정 상승"
- "수익 보장"
- "기대수익률"
- "초과수익"
- "검증된 알파"
- "proven alpha"
- "guaranteed return"
- "expected return"
- "buy"
- "sell"
- "hold"

## User-Facing Disclaimer

This score is a model-estimated probability signal for research/scanning use
and is not investment advice.

## Hard Stop Release Condition

Ranking/report activation remains blocked until all v0.2 probability final
score gates pass and quant-review-gate records PASS.
