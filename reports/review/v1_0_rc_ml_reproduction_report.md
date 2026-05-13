# v1.0-rc ML Reproduction Report

- report_version: v1_0_rc_ml_reproduction_report_v1_0
- created_at: 2026-05-13T11:23:59+00:00
- route_scope: v1_0_rc_step3_ml_reproduction_freeze_trigger_check
- dataset_snapshot_ref: phase9_ml_reproduction_fixture_dataset_v1
- selector_run_id: selector_v1_0_rc_ml_reproduction_fixture
- freeze_trigger_confirmed: True
- freeze_trigger_verdict: PASS
- evidence_only_notice: ML reproduction report is evidence-only review support and does not authorize final freeze, production activation, recommendations, orders, or live execution.

| section | content | status |
|---|---|---|
| Dataset snapshot | range=2024-01-02..2024-12-31; universe=KOSPI200_candidate_only; horizon=1d/1w/1m; data_context=phase9_local_evidence_only_fixture; candidate_count=12 | PASS |
| Label manifest | label_contract_status=approved_label_manifest_available; approved_label_manifest_ref=reports/review/v1_0_rc_ml_reproduction_report.md#label-manifest; positive_count=6; negative_count=6; label_rule=positive if post-cost historical/simulated return >= 0.010, drawdown_abs <= 0.080, and coverage >= 0.850 | PASS |
| Feature allowlist | selected_fields=metric_values, coverage_summary, data_quality_summary, evidence_quality_flags, leakage_check_status, no_lookahead_check_status, rebalance_frequency, rebalance_disclosure, rebalancing_role, turnover_summary; blocked_feature_fields=none | PASS |
| Split policy | policy=phase9_time_split_walk_forward_fixture_v1; train=2024-01-02..2024-06-28; validation=2024-07-01..2024-09-30; out_of_sample=2024-10-01..2024-12-31; walk_forward_folds=3 | PASS |
| Leakage checks | evidence_leakage=pass_all; evidence_no_lookahead=pass_all; selector_leakage=pass; selector_no_lookahead=pass | PASS |
| Baseline | selector_type=deterministic_rule_based; selector_mode=rule_based_review_prioritization; trainability_status=ready_for_optional_baseline_ml; report_ml_result_recorded=True | PASS |
| ML result | model_family=LogisticRegression; model_training_performed=True; train_accuracy=1.0; validation_accuracy=1.0; out_of_sample_accuracy=1.0; label_feature_overlap_status=PASS; performance_claim_allowed=False | PASS |
| Profit reproduction | historical_simulated_post_cost_positive_avg=0.0435; historical_simulated_post_cost_negative_avg=-0.019667; cost_model=phase9_cost_model_10bps; slippage_model=phase9_slippage_model_5bps; costs_reflected=True | PASS |
| Stability | split_status=PASS; horizon_status=PASS; seed_status=PASS; tested_seeds=[11, 17, 23] | PASS |
| Failure cases | none_recorded_in_fixture | PASS |
| Guardrail result | no recommendation/order/transaction language detected in selector or manual-review packet | PASS |
| Verdict | freeze trigger confirmed for evidence-only manual-review support | PASS |

## Blockers
- none
