# v0.2 final score prob_up_1d cross-step conflict report

## Scope

Cross-step checkpoint for the v0.2 route that promotes
`prob_up_1d_candidate` into `final_composite_score` only under
`score_semantic_version = "v0_2_prob_up_1d"`.

Generated review packet:

```text
docs/current_review_packet.md
```

## Checklist

| Check | Result | Evidence |
| --- | --- | --- |
| v0.1 frozen baseline changed | PASS | Existing v0.1 `latest_ranking_builder.py` still sets `final_composite_score = technical_composite_score`; v0.2 uses separate helpers. |
| KOSPI200 scope preserved | PASS | Governance, score, ranking, and report contracts state KOSPI200 only. |
| KOSDAQ150/futures/options/Nasdaq activation | PASS | No such activation is added. |
| valuation/fundamental score activation | PASS | No valuation/fundamental input enters `technical_composite_score` or `final_composite_score`. |
| backtest metrics as feature or score | PASS | Candidate guardrails reject backtest/evaluation metric feature leakage. |
| final_composite_score silent semantic change | PASS | v0.1 and v0.2 semantics are split by `score_semantic_version`. |
| report trading recommendation wording | PASS | v0.2 report wording guardrail rejects buy/sell/hold, Korean trading terms, expected-return, guarantee, and proven-alpha wording. |
| ranking directly uses candidate-only output | PASS | v0.2 ranking requires `final_composite_score` and rejects direct `prob_up_1d_candidate` ranking. |
| probability wording before calibration PASS | PASS | final score and ranking helpers require calibration PASS metadata. |
| no-lookahead/leakage gate bypass | PASS | candidate ML tests and ranking metadata require leakage/no-lookahead PASS. |

## Validation Evidence

| Command | Result |
| --- | --- |
| `bash .agents/skills/quant-candidate-ml-gate/scripts/validate_gate_contract.sh` | PASS |
| `python -m pytest tests/test_v0_2_prob_up_1d_candidate.py Quant_mvp/tests/test_v0_2_final_score_prob_up_1d_contract.py Quant_mvp/tests/test_v0_2_prob_up_1d_ranking_contract.py Quant_mvp/tests/test_report_wording_forbidden_prob_up_1d.py` | PASS |
| `python Quant_mvp/scripts/validate_v0_2_final_score_contract.py` | PASS |
| `python Quant_mvp/scripts/check_report_forbidden_wording.py` | PASS |
| `python scripts/build_review_packet.py --step "post-MVP v0.2 predictive probability score route" --stage "v0.2 final score prob_up_1d cross-step conflict checkpoint"` | PASS |
| `git diff --check` | PASS |

## Conflicts Found

None.

## Conflicts Resolved

- Step 4 pytest blocker resolved by running the v0.2 final-score tests with the
  bundled Python runtime after installing `pytest` into that runtime.
- Step 5 ranking/report approval blocker resolved by adding
  `QG_APPROVED_RANKING_REPORT_PROB_UP_1D_V0_2`.
- Step 6 ranking/report contract blocker resolved by adding v0.2 ranking and
  report wording contracts, helpers, scripts, and tests.

## Unresolved Conflicts

None.

## Verdict

Cross-step conflict checkpoint: PASS.

`quant-review-gate` may proceed.
