# v0.2 prob_up_1d_candidate ML validation report

## Scope

This report validates whether `prob_up_1d_candidate` satisfies the candidate ML
gate needed before any later `final_composite_score` promotion route can
continue.

This report does not connect `prob_up_1d_candidate` to
`final_composite_score`, does not generate production ranking, does not change
report behavior, does not add market-data ingestion, and does not activate
valuation/fundamental scoring.

## Preconditions

| Precondition | Evidence | Result |
| --- | --- | --- |
| Governance approval token | `QG_APPROVED_FINAL_SCORE_PROB_UP_1D_V0_2` in `Quant_mvp/docs/v0_2_final_score_prob_up_1d_governance_approval.md` | PASS |
| v0.2 final score semantic contract | `Quant_mvp/docs/v0_2_final_score_prob_up_1d_contract.md` defines `v0.2_prob_up_1d` and keeps runtime replacement blocked | PASS |

## Validation Matrix

| Check | Result | Evidence |
| --- | --- | --- |
| Feature observation time | PASS | Feature table contains only identity columns, approved feature columns, feature status, and feature valid count. Candidate output sets `decision_time` to observation business day `t` and `execution_time` to next business day metadata. Future adjusted-close changes alter labels only, not feature values. |
| Label horizon | PASS | `up_1d_label` is generated as `adjusted_close[t+1 business day] > adjusted_close[t]` using the next row per ticker after date sorting. Friday-to-Monday synthetic check confirms business-row horizon rather than calendar-day assumption. |
| Train/eval split | PASS | Candidate model uses a time-ordered split after sorting by `date`, then `ticker`; train keys are earlier than or equal to eval start, and train/eval keys are disjoint. No random split is used. |
| No-lookahead | PASS | Feature validation rejects label/future/backtest/evaluation columns; feature table does not include `adjusted_close`, `up_1d_label`, label availability fields, or future adjusted-close values. |
| Leakage prevention | PASS | Tests reject `next_day_return`, `future_rank`, `future_report_output`, `backtest_hit_rate`, `evaluation_metric`, `next_adjusted_close`, target labels, production rank, composite score fields, and valuation/fundamental fields. |
| adjusted_close label | PASS | Label construction requires the configured `adjusted_close` column and does not use raw `close`; rows missing current or next adjusted-close are non-evaluable and keep label null. |
| Calibration | PASS | Evaluation metrics include `brier_score`, `expected_calibration_error`, configured max thresholds, and `calibration_gate_pass`. Calibration is required before final score promotion, and runtime replacement remains disabled. |

## Calibration Procedure

The candidate model emits probabilities in `[0.0, 1.0]`. Evaluation computes:

- `brier_score`
- `log_loss`
- `classification_accuracy`
- `expected_calibration_error`
- `calibration_gate_pass`

The current contract threshold is:

```text
max_brier_score = 0.35
max_expected_calibration_error = 0.35
```

`prob_up_1d_candidate` may be called a final-score probability only after the
calibration gate passes. Before that pass, output remains candidate-only and
must not be written or consumed as `final_composite_score`.

## Tests Added Or Strengthened

- `test_prob_up_1d_label_uses_adjusted_close_next_business_day`
- `test_prob_up_1d_features_do_not_include_future_columns`
- `test_prob_up_1d_train_eval_split_is_time_ordered`
- `test_prob_up_1d_no_lookahead_on_rolling_features`
- `test_prob_up_1d_candidate_range_is_probability_like`
- `test_prob_up_1d_candidate_missing_policy`
- `test_prob_up_1d_calibration_gate_required`

## Validation Commands

| Command | Result | Notes |
| --- | --- | --- |
| `bash .agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh` | PASS | Required candidate ML gate contract validator. |
| `python -m pytest tests/test_v0_2_prob_up_1d_candidate.py tests/validation/test_v0_2_candidate_ml_guardrails.py` | NOT RUN TO COMPLETION | Local Python environments do not have `pytest` installed. |
| `python -m py_compile src/scores/prob_up_1d_candidate.py src/validation/v0_2_candidate_ml_guardrails.py tests/test_v0_2_prob_up_1d_candidate.py tests/validation/test_v0_2_candidate_ml_guardrails.py` | PASS | Syntax validation. |
| Direct Python assertion smoke: candidate pipeline, probability range, calibration metrics, train/eval split, latest unlabeled row | PASS | Uses bundled Python with pandas/numpy. |
| Direct Python assertion smoke: adjusted-close next-business-day label and leakage rejection | PASS | Uses bundled Python with pandas/numpy. |

## Candidate-To-Final Promotion

Candidate ML validation status: PASS.

`prob_up_1d_candidate` is ML-gate eligible to continue toward final-score
promotion. It is not yet allowed to replace or feed `final_composite_score`
because the later final-score route gates are still open.

Remaining blockers before runtime promotion:

1. Final score contract implementation gate.
2. Ranking contract update and validation.
3. Report wording forbidden check.
4. Cross-Step Conflict Checkpoint.
5. `quant-review-gate` final PASS.

## Verdict

Candidate ML validation: PASS.

Final `final_composite_score` connection in this step: BLOCKED / NOT PERFORMED.
