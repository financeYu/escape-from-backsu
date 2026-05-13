from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.evaluation_evidence_v1 import (  # noqa: E402
    build_dry_run_evidence_summary_from_weight_config_record,
    build_evaluation_evidence_v1,
    load_evaluation_evidence_config,
    validate_evaluation_evidence_v1,
    validate_selector_feature_allowlist,
)
from Quant_mvp.backtest_mvp.simulation_run_manifest import build_simulation_run_manifest  # noqa: E402
from Quant_mvp.backtest_mvp.weight_config_loop import build_weight_config_loop_plan  # noqa: E402
from src.validation.horizon_policy import resolve_horizon_policy  # noqa: E402


def _manifest(horizon_id: str = "1d", run_mode: str = "candidate_only_backtest") -> dict[str, object]:
    policy = resolve_horizon_policy(horizon_id)
    return build_simulation_run_manifest(
        strategy_candidate_id=f"sc_v1_0_rc_{horizon_id}",
        strategy_candidate_ref="Quant_mvp/config/v0_3_strategy_candidate_registry.toml",
        date_range={"start": "2026-01-02", "end": "2026-03-31"},
        horizon_policy=policy,
        run_mode=run_mode,
        created_at="2026-05-12T00:00:00+00:00",
        rebalance_disclosure="historical_simulated_rebalancing_context_only_not_user_instruction",
    )


def _candidate_result(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "candidate_id": "sc_v1_0_rc_1d",
        "strategy_candidate_id": "sc_v1_0_rc_1d",
        "strategy_candidate_ref": "Quant_mvp/config/v0_3_strategy_candidate_registry.toml",
        "metric_values": {
            "realized_return_summary": 0.12,
            "realized_drawdown_summary": -0.08,
            "coverage_ratio": 0.91,
            "invalid_period_count": 0,
        },
        "metric_units": {
            "realized_return_summary": "historical_ratio",
            "realized_drawdown_summary": "historical_ratio",
            "coverage_ratio": "ratio",
            "invalid_period_count": "count",
        },
        "coverage_summary": {"coverage_ratio": 0.91, "invalid_period_count": 0},
        "data_quality_summary": {"missing_data_count": 0, "flags": []},
        "turnover_summary": {"realized_turnover_summary": 0.2},
        "leakage_check_status": "pass",
        "no_lookahead_check_status": "pass",
        "rebalancing_role": "tested_strategy_logic",
        "rebalance_disclosure": "historical simulated rebalancing was part of tested strategy logic only",
    }
    result.update(overrides)
    return result


@pytest.mark.parametrize("horizon_id", ["1d", "1w", "1m"])
def test_evaluation_evidence_v1_builds_for_horizon_fixtures(horizon_id: str) -> None:
    manifest = _manifest(horizon_id)
    result = _candidate_result(
        candidate_id=f"sc_v1_0_rc_{horizon_id}",
        strategy_candidate_id=f"sc_v1_0_rc_{horizon_id}",
    )

    evidence = build_evaluation_evidence_v1(
        candidate_result=result,
        simulation_run_manifest=manifest,
        horizon_policy_snapshot=manifest["horizon_policy_snapshot"],
        created_at="2026-05-12T00:00:00+00:00",
    )

    assert evidence["horizon_policy_id"] == horizon_id
    assert evidence["horizon_policy_snapshot"]["horizon_id"] == horizon_id
    assert evidence["simulation_run_manifest_snapshot"]["run_id"] == manifest["run_id"]
    assert evidence["live_execution_enabled"] is False
    assert evidence["production_ranking_update_enabled"] is False


def test_evaluation_evidence_v1_builds_from_candidate_only_simulation() -> None:
    manifest = _manifest("1w", run_mode="candidate_only_simulation")
    evidence = build_evaluation_evidence_v1(
        candidate_result=_candidate_result(candidate_id="sc_v1_0_rc_1w", strategy_candidate_id="sc_v1_0_rc_1w"),
        simulation_run_manifest=manifest,
        horizon_policy_snapshot=manifest["horizon_policy_snapshot"],
        created_at="2026-05-12T00:00:00+00:00",
    )

    assert evidence["evidence_mode"] == "candidate_only_simulation_evidence"


def test_evaluation_evidence_v1_requires_horizon_policy_snapshot() -> None:
    manifest = _manifest()
    evidence = build_evaluation_evidence_v1(
        candidate_result=_candidate_result(),
        simulation_run_manifest=manifest,
        horizon_policy_snapshot=manifest["horizon_policy_snapshot"],
        created_at="2026-05-12T00:00:00+00:00",
    )
    evidence.pop("horizon_policy_snapshot")

    with pytest.raises(ValueError, match="missing required fields"):
        validate_evaluation_evidence_v1(evidence)


def test_evaluation_evidence_v1_requires_simulation_run_manifest() -> None:
    manifest = _manifest()
    evidence = build_evaluation_evidence_v1(
        candidate_result=_candidate_result(),
        simulation_run_manifest=manifest,
        horizon_policy_snapshot=manifest["horizon_policy_snapshot"],
        created_at="2026-05-12T00:00:00+00:00",
    )
    evidence.pop("simulation_run_manifest_snapshot")

    with pytest.raises(ValueError, match="missing required fields"):
        validate_evaluation_evidence_v1(evidence)


def test_evaluation_evidence_v1_rejects_candidate_manifest_mismatch() -> None:
    manifest = _manifest()

    with pytest.raises(ValueError, match="candidate_id must match"):
        build_evaluation_evidence_v1(
            candidate_result=_candidate_result(candidate_id="different_candidate"),
            simulation_run_manifest=manifest,
            horizon_policy_snapshot=manifest["horizon_policy_snapshot"],
            created_at="2026-05-12T00:00:00+00:00",
        )


def test_evaluation_evidence_v1_rejects_manifest_ref_mismatch() -> None:
    manifest = _manifest()
    evidence = build_evaluation_evidence_v1(
        candidate_result=_candidate_result(),
        simulation_run_manifest=manifest,
        horizon_policy_snapshot=manifest["horizon_policy_snapshot"],
        created_at="2026-05-12T00:00:00+00:00",
    )
    evidence["simulation_run_manifest_ref"] = "different_run_id"

    with pytest.raises(ValueError, match="ref must match"):
        validate_evaluation_evidence_v1(evidence)


def test_evaluation_evidence_v1_includes_weight_config_snapshot_when_available() -> None:
    plan = build_weight_config_loop_plan(created_at="2026-05-12T00:00:00+00:00")
    record = plan["records"][0]

    evidence = build_dry_run_evidence_summary_from_weight_config_record(
        record,
        created_at="2026-05-12T00:00:00+00:00",
    )

    assert evidence["evidence_mode"] == "dry_run_evidence_summary"
    assert evidence["weight_config_snapshot"]["weight_config_id"] == record["weight_config_id"]
    assert evidence["simulation_run_manifest_snapshot"]["weight_config_snapshot"]["weight_config_id"] == record["weight_config_id"]


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
def test_evaluation_evidence_v1_rejects_prohibited_flags(flag: str) -> None:
    manifest = _manifest()
    evidence = build_evaluation_evidence_v1(
        candidate_result=_candidate_result(),
        simulation_run_manifest=manifest,
        horizon_policy_snapshot=manifest["horizon_policy_snapshot"],
        created_at="2026-05-12T00:00:00+00:00",
    )
    evidence[flag] = True

    with pytest.raises(ValueError, match=flag):
        validate_evaluation_evidence_v1(evidence)


def test_evaluation_evidence_v1_rejects_future_return_prediction_claims() -> None:
    manifest = _manifest()

    with pytest.raises(ValueError, match="blocked EvaluationEvidenceV1 metric names"):
        build_evaluation_evidence_v1(
            candidate_result=_candidate_result(metric_values={"expected_return": 0.2}),
            simulation_run_manifest=manifest,
            horizon_policy_snapshot=manifest["horizon_policy_snapshot"],
            created_at="2026-05-12T00:00:00+00:00",
        )


def test_evaluation_evidence_v1_requires_rebalance_disclosure() -> None:
    manifest = _manifest("1m")
    evidence = build_evaluation_evidence_v1(
        candidate_result=_candidate_result(
            candidate_id="sc_v1_0_rc_1m",
            strategy_candidate_id="sc_v1_0_rc_1m",
            rebalance_disclosure="",
        ),
        simulation_run_manifest=manifest,
        horizon_policy_snapshot=manifest["horizon_policy_snapshot"],
        created_at="2026-05-12T00:00:00+00:00",
    )
    evidence["rebalance_disclosure"] = ""

    with pytest.raises(ValueError, match="rebalance disclosure"):
        validate_evaluation_evidence_v1(evidence)


def test_evaluation_evidence_v1_selector_allowlist_blocks_prohibited_fields() -> None:
    with pytest.raises(ValueError, match="blocked fields"):
        validate_selector_feature_allowlist(["metric_values", "future_return"])


def test_evaluation_evidence_v1_loads_metric_allowlist_config() -> None:
    config = load_evaluation_evidence_config()

    assert "realized_return_summary" in config["metric_allowlist"]["allowed_metric_names"]
    assert "expected_return" in config["metric_allowlist"]["blocked_metric_names"]
