from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.evaluation_evidence_v1 import build_evaluation_evidence_v1  # noqa: E402
from Quant_mvp.backtest_mvp.selector_evaluator_v1 import (  # noqa: E402
    build_rule_based_selector_score_manifest_v1,
    build_selector_feature_matrix_v1,
    build_selector_input_manifest_v1,
    build_selector_trainability_report_v1,
    validate_selector_score_manifest_v1,
)
from Quant_mvp.backtest_mvp.simulation_run_manifest import build_simulation_run_manifest  # noqa: E402
from src.validation.horizon_policy import resolve_horizon_policy  # noqa: E402


def _evidence(candidate_id: str, coverage_ratio: float = 0.9, role: str = "evaluation_mechanics") -> dict[str, object]:
    policy = resolve_horizon_policy("1d")
    manifest = build_simulation_run_manifest(
        strategy_candidate_id=candidate_id,
        strategy_candidate_ref="Quant_mvp/config/v0_3_strategy_candidate_registry.toml",
        date_range={"start": "2026-01-02", "end": "2026-03-31"},
        horizon_policy=policy,
        created_at="2026-05-12T00:00:00+00:00",
        rebalance_disclosure="historical simulated rebalancing context only not user instruction",
    )
    return build_evaluation_evidence_v1(
        candidate_result={
            "candidate_id": candidate_id,
            "strategy_candidate_id": candidate_id,
            "strategy_candidate_ref": "Quant_mvp/config/v0_3_strategy_candidate_registry.toml",
            "metric_values": {
                "realized_return_summary": 0.10,
                "realized_drawdown_summary": -0.06,
                "coverage_ratio": coverage_ratio,
            },
            "coverage_summary": {"coverage_ratio": coverage_ratio},
            "data_quality_summary": {"missing_data_count": 0},
            "turnover_summary": {"realized_turnover_summary": 0.15},
            "leakage_check_status": "pass",
            "no_lookahead_check_status": "pass",
            "rebalancing_role": role,
            "rebalance_disclosure": "historical simulated rebalancing context only not user instruction",
        },
        simulation_run_manifest=manifest,
        horizon_policy_snapshot=manifest["horizon_policy_snapshot"],
        created_at="2026-05-12T00:00:00+00:00",
    )


def _selector_outputs() -> tuple[dict[str, object], list[dict[str, object]], dict[str, object], dict[str, object]]:
    evidences = [_evidence("sc_selector_a", 0.95), _evidence("sc_selector_b", 0.60, "material_effect_on_candidate_evidence")]
    input_manifest = build_selector_input_manifest_v1(
        evidences,
        selector_run_id="selector_test_run",
        created_at="2026-05-12T00:00:00+00:00",
    )
    rows = build_selector_feature_matrix_v1(evidences, input_manifest=input_manifest)
    trainability = build_selector_trainability_report_v1(
        rows,
        selector_run_id=input_manifest["selector_run_id"],
        created_at="2026-05-12T00:00:00+00:00",
    )
    score_manifest = build_rule_based_selector_score_manifest_v1(
        rows,
        input_manifest=input_manifest,
        trainability_report=trainability,
        created_at="2026-05-12T00:00:00+00:00",
    )
    return input_manifest, rows, trainability, score_manifest


def test_selector_feature_matrix_uses_evaluation_evidence_allowlist_only() -> None:
    input_manifest, rows, _trainability, _score_manifest = _selector_outputs()

    selected = set(input_manifest["selected_feature_fields"])
    assert selected.issubset(set(_evidence("allowlist_probe")["selector_feature_allowlist"]))
    assert all(set(row["feature_values"]) == selected for row in rows)


def test_selector_feature_matrix_blocks_future_or_prohibited_fields() -> None:
    evidence = _evidence("sc_selector_blocked")

    with pytest.raises(ValueError, match="outside allowlist"):
        build_selector_input_manifest_v1([evidence], selected_feature_fields=["metric_values", "future_return"])


def test_selector_feature_matrix_requires_evidence_refs_to_match_input_manifest() -> None:
    first = _evidence("sc_selector_a")
    second = _evidence("sc_selector_b")
    input_manifest = build_selector_input_manifest_v1(
        [first],
        selector_run_id="selector_mismatch",
        created_at="2026-05-12T00:00:00+00:00",
    )

    with pytest.raises(ValueError, match="input_evidence_refs"):
        build_selector_feature_matrix_v1([second], input_manifest=input_manifest)


def test_selector_trainability_report_handles_insufficient_data_without_training() -> None:
    _input_manifest, _rows, trainability, _score_manifest = _selector_outputs()

    assert trainability["trainability_status"] == "trainability_check_only"
    assert trainability["model_training_performed"] is False
    assert trainability["ml_baseline_status"] == "safely_skipped"


def test_rule_based_selector_outputs_review_priorities() -> None:
    _input_manifest, _rows, _trainability, score_manifest = _selector_outputs()

    assert score_manifest["selector_mode"] == "rule_based_review_prioritization"
    assert score_manifest["manual_review_required"] is True
    assert len(score_manifest["candidate_review_priorities"]) == 2
    assert all(priority["manual_review_required"] is True for priority in score_manifest["candidate_review_priorities"])


def test_selector_score_manifest_requires_feature_rows_to_match_input_manifest() -> None:
    input_manifest, rows, trainability, _score_manifest = _selector_outputs()
    rows = rows[:1]

    with pytest.raises(ValueError, match="feature rows must match"):
        build_rule_based_selector_score_manifest_v1(
            rows,
            input_manifest=input_manifest,
            trainability_report=trainability,
            created_at="2026-05-12T00:00:00+00:00",
        )


def test_selector_score_manifest_requires_trainability_selector_run_id_match() -> None:
    input_manifest, rows, trainability, _score_manifest = _selector_outputs()
    trainability["selector_run_id"] = "different_selector_run"

    with pytest.raises(ValueError, match="selector_run_id"):
        build_rule_based_selector_score_manifest_v1(
            rows,
            input_manifest=input_manifest,
            trainability_report=trainability,
            created_at="2026-05-12T00:00:00+00:00",
        )


def test_rule_based_selector_is_deterministic() -> None:
    first = _selector_outputs()[3]
    second = _selector_outputs()[3]

    assert first == second


@pytest.mark.parametrize(
    "flag",
    [
        "live_execution_enabled",
        "brokerage_integration_enabled",
        "order_generation_enabled",
        "user_facing_auto_rebalance_instruction_enabled",
        "production_ranking_update_enabled",
        "valuation_fundamental_active_scoring_enabled",
    ],
)
def test_selector_score_manifest_rejects_blocked_flags(flag: str) -> None:
    score_manifest = _selector_outputs()[3]
    score_manifest[flag] = True

    with pytest.raises(ValueError, match=flag):
        validate_selector_score_manifest_v1(score_manifest)


@pytest.mark.parametrize("phrase", ["buy", "sell", "hold", "signal to trade", "rebalance now", "future return"])
def test_selector_score_manifest_rejects_prohibited_language(phrase: str) -> None:
    score_manifest = _selector_outputs()[3]
    score_manifest["candidate_review_priorities"][0]["reason_codes"].append(phrase)

    with pytest.raises(ValueError, match="prohibited language"):
        validate_selector_score_manifest_v1(score_manifest)


def test_selector_retains_rebalance_disclosure_as_context_only() -> None:
    _input_manifest, _rows, _trainability, score_manifest = _selector_outputs()

    assert "rebalance_material_to_evidence" in score_manifest["reason_codes"]
    assert score_manifest["user_facing_auto_rebalance_instruction_enabled"] is False


def test_selector_does_not_modify_production_ranking() -> None:
    score_manifest = _selector_outputs()[3]

    assert score_manifest["production_ranking_update_enabled"] is False
