# v0.2 final_score prob_up_1d contract

## Purpose

This contract defines the v0.2 semantic meaning of `final_composite_score`
after Quant governance approval
`QG_APPROVED_FINAL_SCORE_PROB_UP_1D_V0_2`.

It now has a v0.2 output-contract connection helper and validator. It does not
activate production ranking, report wording changes, model training, inference,
data ingestion, or generated report/output behavior.

## Version Split

### v0.1 Frozen Baseline

```text
final_composite_score = technical_composite_score
```

- Status: frozen baseline.
- Universe: KOSPI200 only.
- Meaning: technical-only final composite score.
- Change policy: do not change, reinterpret, or silently migrate this v0.1
  meaning.

### v0.2 Probability Semantic

```text
final_composite_score = prob_up_1d
```

For v0.2, `prob_up_1d` may be promoted only from `prob_up_1d_candidate` after
candidate ML validation, calibration, leakage, final score contract, ranking,
report wording, cross-step conflict, and `quant-review-gate` checks pass.

Until those gates pass, `prob_up_1d_candidate` remains candidate-only and must
not be written, displayed, sorted, or consumed as `final_composite_score`.

## v0.2 Output Contract Connection

The v0.2 final-score output contract is implemented in
`src/scores/v0_2_final_score.py`.

The only allowed v0.2 connection path is:

```text
prob_up_1d_candidate --calibration PASS--> final_composite_score
score_semantic_version = "v0_2_prob_up_1d"
final_score_source = "prob_up_1d_candidate"
```

Contract rules:

- `calibration_gate_pass` must be true before a v0.2 final score output can be
  built.
- `final_composite_score` must equal the calibrated `prob_up_1d_candidate`.
- `final_composite_score` must be a float score in `[0.0, 1.0]`.
- `score_semantic_version` must be `v0_2_prob_up_1d`.
- `final_score_source` must be `prob_up_1d_candidate`.
- `null`, `NaN`, and `inf` candidate rows are not rank eligible.
- Missing or invalid candidate rows must not be filled from
  `technical_composite_score`.
- The frozen v0.1 path remains
  `final_composite_score = technical_composite_score`.

The standalone validator is:

```powershell
python Quant_mvp/scripts/validate_v0_2_final_score_contract.py
```

## Score Meaning

| Field | Contract |
| --- | --- |
| Field name | `final_composite_score` |
| Semantic version metadata | `v0_2_prob_up_1d` |
| Definition | Estimated calibrated probability that `adjusted_close` on the next business day is greater than `adjusted_close` on the feature observation business day. |
| Mathematical label | `label_up_1d = 1 if adjusted_close[t+1 business day] > adjusted_close[t], else 0` |
| Score range | float in `[0.0, 1.0]` |
| Sort direction | descending |
| Higher-score meaning | Higher score means higher estimated probability of next-business-day `adjusted_close` increase. |
| Universe | KOSPI200 only for this route. |

## Missing Handling

- `null`, `NaN`, and `inf` values are invalid for final ranking.
- Rows with missing `final_composite_score` must be excluded from production
  ranking eligibility.
- Missing values must not be silently filled with `technical_composite_score`.
- Missing values must not be displayed as probability.
- Missing-value handling must be deterministic, auditable, and separate from
  the frozen v0.1 technical score.

## Calibration Status

- `final_composite_score` may be called a probability only after calibration
  gate PASS.
- Before calibration PASS, the output remains `prob_up_1d_candidate` and must
  not be used as `final_composite_score`.
- Calibration diagnostics are evaluation evidence only; they must not become
  model features, ranking features, or backtest feedback.

## Data Boundary

- Label source: adjusted-close-based label only.
- No backtest metric as feature.
- No future price, future volume, future rank, future report, or post-label
  information as feature.
- No valuation/fundamental activation unless separately approved.
- No financial, accounting, filing, PER, PBR, ROE, market-cap, analyst, or
  valuation field may enter `final_composite_score` under this route.
- No new universe, market, or vendor activation is authorized by this contract.

## Report Expression

Allowed wording after all required gates pass:

- "1영업일 뒤 adjusted_close 상승확률 추정값"
- "검증된 v0.2 확률형 최종 스코어"
- "상승확률 점수"

Forbidden wording:

- "매수"
- "매도"
- "보유"
- "추천"
- "확정 상승"
- "수익 보장"
- "기대수익률"
- "초과수익 보장"
- "검증된 알파"
- "proven alpha"
- "guaranteed return"
- "investment advice"
- "buy/sell/hold"

## Runtime Boundary

This output-contract connection does not activate production ranking or report
behavior. A later implementation gate must separately prove:

1. Candidate ML validation PASS.
2. Calibration gate PASS.
3. No-lookahead and leakage tests PASS.
4. Final score missing policy implemented as `exclude_from_ranking`.
5. Ranking contract updated and validated.
6. Report wording forbidden check PASS.
7. Cross-Step Conflict Checkpoint PASS.
8. `quant-review-gate` final PASS.

Runtime replacement remains blocked until all checks pass.

## Downstream Ranking And Report Contracts

- Ranking contract:
  `Quant_mvp/docs/v0_2_prob_up_1d_ranking_contract.md`
- Report wording contract:
  `Quant_mvp/docs/v0_2_prob_up_1d_report_wording_contract.md`

The ranking contract requires `score_semantic_version = "v0_2_prob_up_1d"`,
finite `final_composite_score` in `[0.0, 1.0]`, calibration PASS metadata,
leakage/no-lookahead PASS metadata, and no technical-score fallback.

The report wording contract describes `final_composite_score` as
"1영업일 뒤 adjusted_close 상승확률 추정값" or equivalent approved
probability-score wording, and rejects buy/sell/hold, expected-return,
guaranteed-return, proven-alpha, and investment-advice claims.
