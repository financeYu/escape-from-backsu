# v1.2 Baseline ML Selector Application

This document records the v1.2 selector application contract opened by
`docs/extension/v1_x_staged_release_plan.md`.

The v1.2 goal is to check whether a small ML selector can improve manual
review prioritization versus the v1.1 rule baseline when both are evaluated
against historical or simulated net-of-cost evidence. It is not a deployable
return model, execution signal, production ranking replacement, or automatic
rebalance workflow.

## Implementation

- Module: `Quant_mvp/backtest_mvp/ml_selector_v1_2.py`
- Test: `tests/backtest/test_v1_2_ml_selector.py`
- Owner lane: Quant ML/evaluator
- Completion gate: `.agents/skills/quant-review-gate/SKILL.md`

## Inputs

Inputs are read-only `EvaluationEvidenceV1` records produced from approved
historical or simulated evidence, normally from v1.1 net profitability
artifacts.

The selector uses only allowlisted `EvaluationEvidenceV1` fields as feature
sources:

- `metric_values`
- `coverage_summary`
- `data_quality_summary`
- `evidence_quality_flags`
- `leakage_check_status`
- `no_lookahead_check_status`
- `rebalancing_role`
- `turnover_summary`
- `date_range`

The review target is stored separately in `v1_2_label_target_manifest` as a
historical or simulated net evidence value. It is not included in feature rows.

## Outputs

The runner emits these artifact keys:

- `v1_2_ml_trainability_report`
- `v1_2_selector_feature_matrix_manifest`
- `v1_2_label_target_manifest`
- `v1_2_leakage_audit`
- `v1_2_linear_baseline_model_manifest`
- `v1_2_tree_challenger_model_manifest`
- `v1_2_walk_forward_validation_report`
- `v1_2_selector_score_manifest`
- `v1_2_rule_vs_ml_comparison_report`

`v1_2_selector_score_manifest` uses the existing
`SelectorScoreManifestV1` contract and remains `AdoptionCandidate`
review-priority output only.

## Completion Criteria

v1.2 is complete when:

- trainability is explicitly `pass` or `skipped` with reasons
- leakage audit passes for allowlisted features and no-lookahead status
- at least one time-ordered walk-forward split is produced when trainable
- Ridge and ElasticNet linear baseline manifests are recorded
- GradientBoostingRegressor and LightGBM challenger comparison status is
  recorded; unavailable optional ML packages must be explicit skips
- rule baseline versus ML review-priority top-k net evidence comparison is
  emitted
- selector output remains manual-review support only
- `technical_composite_score` and `final_composite_score` are not modified
- focused ML manifest, feature allowlist, leakage, and selector output tests
  pass

## Completion Statement

ML selector application can use only allowlisted historical or simulated
evidence to produce review-priority candidates and compare against the rule
baseline on net-of-cost evidence.
