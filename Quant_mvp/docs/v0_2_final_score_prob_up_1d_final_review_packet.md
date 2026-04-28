# v0.2 final score prob_up_1d final review packet

## Final Definition

In `v0_2_prob_up_1d` semantic version, `final_composite_score` is the
calibrated estimated probability that `adjusted_close` will be higher on the
next business day than on the feature observation business day.

## Gate Summary

| Gate | Result | Evidence |
| --- | --- | --- |
| governance approval | PASS | `QG_APPROVED_FINAL_SCORE_PROB_UP_1D_V0_2` |
| score semantic contract | PASS | `Quant_mvp/docs/v0_2_final_score_prob_up_1d_contract.md` |
| candidate ML validation | PASS | `Quant_mvp/docs/v0_2_prob_up_1d_candidate_ml_validation_report.md` |
| no-lookahead | PASS | candidate ML tests and guardrails |
| leakage prevention | PASS | candidate ML tests and guardrails |
| adjusted_close label | PASS | `test_prob_up_1d_label_uses_adjusted_close_next_business_day` |
| calibration | PASS | calibration metrics and `calibration_gate_pass` tests |
| final score contract | PASS | `Quant_mvp/scripts/validate_v0_2_final_score_contract.py` |
| ranking contract | PASS | `Quant_mvp/tests/test_v0_2_prob_up_1d_ranking_contract.py` |
| report wording forbidden check | PASS | `Quant_mvp/scripts/check_report_forbidden_wording.py` |
| cross-step conflict | PASS | `Quant_mvp/docs/v0_2_final_score_prob_up_1d_cross_step_conflict_report.md` |
| quant-review-gate | PASS | `.agents/skills/quant-review-gate/scripts/validate_review_gate.sh` |

## Validation Commands

| Command | Result |
| --- | --- |
| `bash .agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh` | PASS |
| `python -m pytest tests/test_v0_2_prob_up_1d_candidate.py Quant_mvp/tests/test_v0_2_final_score_prob_up_1d_contract.py Quant_mvp/tests/test_v0_2_prob_up_1d_ranking_contract.py Quant_mvp/tests/test_report_wording_forbidden_prob_up_1d.py` | PASS |
| `python Quant_mvp/scripts/validate_v0_2_final_score_contract.py` | PASS |
| `python Quant_mvp/scripts/check_report_forbidden_wording.py` | PASS |
| `python scripts/build_review_packet.py --step "post-MVP v0.2 predictive probability score route" --stage "quant-review-gate final PASS"` | PASS |
| `bash .agents/skills/quant-review-gate/scripts/validate_review_gate.sh` | PASS |
| `git diff --check` | PASS |

## Scope Boundaries

- KOSPI200 only.
- v0.2+ only.
- MVP v0.1 remains frozen with
  `final_composite_score = technical_composite_score`.
- No KOSDAQ150, futures, options, Nasdaq, overseas universe, valuation,
  fundamental scoring, trading recommendation, expected-return claim,
  guaranteed-return claim, or proven-alpha claim is activated.

## Verdict

quant-review-gate final review: PASS.
