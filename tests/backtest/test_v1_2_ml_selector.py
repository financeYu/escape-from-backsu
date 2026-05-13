from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.ml_selector_v1_2 import (  # noqa: E402
    BaselineMLSelectorConfig,
    audit_v1_2_feature_leakage,
    build_v1_2_selector_feature_matrix_manifest,
    run_v1_2_baseline_ml_selector_application,
    validate_v1_2_ml_selector_artifacts,
)
from Quant_mvp.backtest_mvp.net_profitability_runner_v1 import (  # noqa: E402
    NetProfitabilityRunnerConfig,
    run_net_profitability_evidence_v1_1,
)


def _records() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(8):
        quality = float(index)
        rows.append(
            {
                "candidate_id": f"sc_v1_2_{index}",
                "selector_score": 95.0 - 6.0 * quality,
                "gross_return": 0.025 + 0.014 * quality,
                "benchmark_return": 0.025,
                "turnover": 0.72 - 0.055 * quality,
                "volatility": 0.22 - 0.012 * quality,
                "max_drawdown": -0.16 + 0.012 * quality,
                "coverage_ratio": 0.82 + 0.015 * quality,
                "date_range": {
                    "start": f"2025-{index + 1:02d}-01",
                    "end": f"2025-{index + 1:02d}-28",
                },
                "leakage_check_status": "pass",
                "no_lookahead_check_status": "pass",
                "rebalance_frequency": "monthly",
                "rebalancing_role": "material_effect_on_candidate_evidence",
                "rebalance_disclosure": (
                    "historical simulated monthly rebalancing materially affects "
                    "candidate evidence context only"
                ),
            }
        )
    return rows


def _v1_1_artifacts() -> dict[str, object]:
    return run_net_profitability_evidence_v1_1(
        _records(),
        config=NetProfitabilityRunnerConfig(top_k=3, cost_rate=0.003, slippage_rate=0.001),
    )


def _v1_2_artifacts() -> dict[str, object]:
    v1_1 = _v1_1_artifacts()
    return run_v1_2_baseline_ml_selector_application(
        v1_1["evaluation_evidence_v1"],
        rule_selector_score_manifest=v1_1["selector_score_manifest"],
        config=BaselineMLSelectorConfig(
            selector_run_id="v1_2_test_selector",
            top_k=3,
            minimum_candidate_count=6,
            minimum_training_rows=4,
        ),
    )


def test_v1_2_ml_selector_builds_required_artifacts() -> None:
    artifacts = _v1_2_artifacts()

    validate_v1_2_ml_selector_artifacts(artifacts)
    assert artifacts["v1_2_ml_trainability_report"]["trainability_status"] == "pass"
    assert artifacts["v1_2_linear_baseline_model_manifest"]["model_status"] == "trained_for_review_priority"
    tree_manifest = artifacts["v1_2_tree_challenger_model_manifest"]
    assert "GradientBoostingRegressor" in tree_manifest["model_types"]
    assert tree_manifest["configured_tree_challengers"] == ["GradientBoostingRegressor", "LightGBMRegressor"]
    assert tree_manifest["tree_challenger_policy"] == "compare_available_tree_models_then_average_for_review_priority"
    status_by_model = {item["model_type"]: item["status"] for item in tree_manifest["tree_challenger_status"]}
    assert status_by_model["GradientBoostingRegressor"] == "trained"
    assert status_by_model["LightGBMRegressor"] in {"trained", "skipped_dependency_unavailable"}
    assert artifacts["v1_2_walk_forward_validation_report"]["walk_forward_split_count"] >= 1
    assert artifacts["v1_2_selector_score_manifest"]["selector_mode"] == "baseline_ml_review_prioritization"
    assert artifacts["v1_2_selector_score_manifest"]["selector_score_model_sources"] == [
        "linear_baseline",
        "tree_challenger",
    ]


def test_v1_2_feature_matrix_uses_allowlisted_sources_and_separates_target() -> None:
    artifacts = _v1_2_artifacts()
    feature_manifest = artifacts["v1_2_selector_feature_matrix_manifest"]
    target_manifest = artifacts["v1_2_label_target_manifest"]

    assert feature_manifest["label_separation_status"] == "target_manifest_separate_from_feature_matrix"
    assert target_manifest["label_separation_status"] == "separate_target_manifest_not_feature_input"
    assert "net_return" not in feature_manifest["feature_names"]
    assert all("review_target_value" not in row for row in feature_manifest["rows"])


def test_v1_2_leakage_audit_blocks_label_like_feature_name() -> None:
    v1_1 = _v1_1_artifacts()

    with pytest.raises(ValueError, match="label-like"):
        build_v1_2_selector_feature_matrix_manifest(
            v1_1["evaluation_evidence_v1"],
            selector_run_id="v1_2_bad_feature",
            config=BaselineMLSelectorConfig(feature_names=("net_return",)),
        )


def test_v1_2_leakage_audit_fails_failed_boundary_status() -> None:
    artifacts = _v1_2_artifacts()
    feature_manifest = artifacts["v1_2_selector_feature_matrix_manifest"]
    target_manifest = artifacts["v1_2_label_target_manifest"]
    feature_manifest["rows"][0]["no_lookahead_check_status"] = "fail"

    audit = audit_v1_2_feature_leakage(feature_manifest, target_manifest)

    assert audit["status"] == "fail"
    assert "failed_evidence_boundary_status" in audit["blocked_reasons"]


def test_v1_2_rule_vs_ml_comparison_uses_top_k_net_evidence() -> None:
    artifacts = _v1_2_artifacts()
    comparison = artifacts["v1_2_rule_vs_ml_comparison_report"]

    assert comparison["top_k"] == 3
    assert comparison["ml_top_k_average_net_evidence"] > comparison["rule_top_k_average_net_evidence"]
    assert comparison["ml_minus_rule_top_k_net_evidence"] > 0


def test_v1_2_selector_output_keeps_manual_review_boundary() -> None:
    artifacts = _v1_2_artifacts()
    score_manifest = artifacts["v1_2_selector_score_manifest"]

    assert score_manifest["manual_review_required"] is True
    assert score_manifest["production_ranking_update_enabled"] is False
    assert score_manifest["order_generation_enabled"] is False
    assert score_manifest["live_execution_enabled"] is False


def test_v1_2_selector_artifacts_reject_prohibited_language() -> None:
    artifacts = _v1_2_artifacts()
    artifacts["v1_2_rule_vs_ml_comparison_report"]["bad_text"] = "expected return"

    with pytest.raises(ValueError, match="prohibited language"):
        validate_v1_2_ml_selector_artifacts(artifacts)


def test_v1_2_selector_artifacts_are_json_serializable() -> None:
    artifacts = _v1_2_artifacts()

    text = json.dumps(artifacts, sort_keys=True)
    assert "v1_2_selector_score_manifest" in text
    assert "brokerage_integration_enabled" in text
