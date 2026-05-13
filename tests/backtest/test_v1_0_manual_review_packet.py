from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.evaluation_evidence_v1 import build_evaluation_evidence_v1  # noqa: E402
from Quant_mvp.backtest_mvp.manual_review_packet_v1 import (  # noqa: E402
    build_manual_review_packet_v1,
    validate_manual_review_packet_v1,
)
from Quant_mvp.backtest_mvp.selector_evaluator_v1 import (  # noqa: E402
    build_rule_based_selector_score_manifest_v1,
    build_selector_feature_matrix_v1,
    build_selector_input_manifest_v1,
    build_selector_trainability_report_v1,
)
from Quant_mvp.backtest_mvp.simulation_run_manifest import build_simulation_run_manifest  # noqa: E402
from src.validation.horizon_policy import resolve_horizon_policy  # noqa: E402


def _evidence() -> dict[str, object]:
    policy = resolve_horizon_policy("1d")
    manifest = build_simulation_run_manifest(
        strategy_candidate_id="sc_manual_review",
        strategy_candidate_ref="Quant_mvp/config/v0_3_strategy_candidate_registry.toml",
        date_range={"start": "2026-01-02", "end": "2026-03-31"},
        horizon_policy=policy,
        created_at="2026-05-12T00:00:00+00:00",
        rebalance_disclosure="historical simulated rebalancing context only not user instruction",
    )
    return build_evaluation_evidence_v1(
        candidate_result={
            "candidate_id": "sc_manual_review",
            "strategy_candidate_id": "sc_manual_review",
            "strategy_candidate_ref": "Quant_mvp/config/v0_3_strategy_candidate_registry.toml",
            "metric_values": {
                "realized_return_summary": 0.08,
                "realized_drawdown_summary": -0.04,
                "coverage_ratio": 0.8,
            },
            "coverage_summary": {"coverage_ratio": 0.8, "invalid_period_count": 1},
            "data_quality_summary": {"missing_data_count": 2, "flags": ["missing_data_present"]},
            "turnover_summary": {"realized_turnover_summary": 0.2},
            "leakage_check_status": "pass",
            "no_lookahead_check_status": "pass",
            "rebalancing_role": "material_effect_on_candidate_evidence",
            "rebalance_disclosure": "historical simulated rebalancing materially affects candidate evidence context only",
        },
        simulation_run_manifest=manifest,
        horizon_policy_snapshot=manifest["horizon_policy_snapshot"],
        created_at="2026-05-12T00:00:00+00:00",
    )


def _selector_manifest(evidence: dict[str, object]) -> dict[str, object]:
    input_manifest = build_selector_input_manifest_v1(
        [evidence],
        selector_run_id="selector_manual_review",
        created_at="2026-05-12T00:00:00+00:00",
    )
    rows = build_selector_feature_matrix_v1([evidence], input_manifest=input_manifest)
    trainability = build_selector_trainability_report_v1(
        rows,
        selector_run_id="selector_manual_review",
        created_at="2026-05-12T00:00:00+00:00",
    )
    return build_rule_based_selector_score_manifest_v1(
        rows,
        input_manifest=input_manifest,
        trainability_report=trainability,
        created_at="2026-05-12T00:00:00+00:00",
    )


def _packet() -> dict[str, object]:
    evidence = _evidence()
    selector = _selector_manifest(evidence)
    return build_manual_review_packet_v1(
        evidence=evidence,
        selector_score_manifest=selector,
        created_at="2026-05-12T00:00:00+00:00",
    )


def test_manual_review_packet_builds_from_selector_and_evidence() -> None:
    packet = _packet()

    assert packet["packet_mode"] == "manual_review_only"
    assert packet["candidate_id"] == "sc_manual_review"
    assert packet["selector_score_manifest_ref"] == "selector_manual_review"
    assert packet["manual_review_required"] is True


def test_manual_review_packet_preserves_evidence_refs() -> None:
    packet = _packet()

    assert packet["evidence_summary"]["evidence_id"] in packet["evidence_refs"]


def test_manual_review_packet_requires_matching_selector_priority() -> None:
    evidence = _evidence()
    selector = _selector_manifest(evidence)
    selector["candidate_review_priorities"] = []

    with pytest.raises(ValueError, match="matching selector review priority"):
        build_manual_review_packet_v1(
            evidence=evidence,
            selector_score_manifest=selector,
            created_at="2026-05-12T00:00:00+00:00",
        )


def test_manual_review_packet_includes_rebalance_disclosure_when_required() -> None:
    packet = _packet()

    assert "historical simulated rebalancing" in packet["rebalance_disclosure"]
    assert packet["rebalancing_role"] == "material_effect_on_candidate_evidence"
    assert "rebalance_material_to_evidence" in packet["risk_flags"]


def test_manual_review_packet_includes_manual_checklist_and_coverage_gaps() -> None:
    packet = _packet()

    assert "confirm_selector_priority_is_review_prioritization_not_action" in packet["manual_review_checklist"]
    assert "invalid_periods_present" in packet["coverage_gaps"]
    assert "missing_data_present" in packet["data_quality_flags"]


@pytest.mark.parametrize(
    "flag",
    [
        "live_execution_enabled",
        "brokerage_integration_enabled",
        "order_generation_enabled",
        "user_facing_auto_rebalance_instruction_enabled",
        "automatic_position_sizing_enabled",
        "move_to_cash_enabled",
        "production_ranking_update_enabled",
        "valuation_fundamental_active_scoring_enabled",
    ],
)
def test_manual_review_packet_rejects_blocked_flags(flag: str) -> None:
    packet = _packet()
    packet[flag] = True

    with pytest.raises(ValueError, match=flag):
        validate_manual_review_packet_v1(packet)


@pytest.mark.parametrize(
    "phrase",
    [
        "buy",
        "sell",
        "hold",
        "trade signal",
        "order instruction",
        "automatic rebalance instruction",
        "position sizing instruction",
        "move to cash",
        "future return",
        "expected return",
        "proven alpha",
    ],
)
def test_manual_review_packet_rejects_prohibited_language(phrase: str) -> None:
    packet = _packet()
    packet["evidence_summary"]["bad_phrase"] = phrase

    with pytest.raises(ValueError, match="prohibited language"):
        validate_manual_review_packet_v1(packet)


def test_manual_review_packet_does_not_modify_production_ranking() -> None:
    packet = _packet()

    assert packet["production_ranking_update_enabled"] is False
    assert packet["valuation_fundamental_active_scoring_enabled"] is False
