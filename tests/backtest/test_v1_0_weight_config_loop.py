from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.weight_config_loop import (  # noqa: E402
    build_weight_config_loop_plan,
    load_weight_config_candidates,
)


def _write_config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "weight_config_loop.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _default_config_text() -> str:
    return (PROJECT_ROOT / "config" / "weight_config_loop.toml").read_text(encoding="utf-8")


def test_weight_config_loads_explicit_candidates() -> None:
    candidates = load_weight_config_candidates(created_at="2026-05-12T00:00:00+00:00")

    assert [candidate.weight_config_id for candidate in candidates] == [
        "wc_v1_0_rc_equal_technical_statistical",
        "wc_v1_0_rc_momentum_tilt",
        "wc_v1_0_rc_volatility_tilt",
    ]
    assert candidates[0].score_weights == {
        "technical_momentum_layer": 0.5,
        "statistical_volatility_layer": 0.5,
    }


def test_weight_config_rejects_duplicate_ids(tmp_path: Path) -> None:
    config = _default_config_text().replace(
        "weight_config_id = \"wc_v1_0_rc_momentum_tilt\"",
        "weight_config_id = \"wc_v1_0_rc_equal_technical_statistical\"",
    )

    with pytest.raises(ValueError, match="duplicate weight_config_id"):
        load_weight_config_candidates(config_path=_write_config(tmp_path, config))


def test_weight_config_rejects_invalid_weights(tmp_path: Path) -> None:
    config = _default_config_text().replace("technical_momentum_layer = 0.7", "technical_momentum_layer = -0.1")

    with pytest.raises(ValueError, match="non-negative"):
        load_weight_config_candidates(config_path=_write_config(tmp_path, config))


def test_weight_config_enforces_max_candidate_count(tmp_path: Path) -> None:
    config = _default_config_text().replace("max_candidate_count = 3", "max_candidate_count = 2")

    with pytest.raises(ValueError, match="exceeds max_candidate_count"):
        load_weight_config_candidates(config_path=_write_config(tmp_path, config))


def test_weight_config_loop_is_deterministic() -> None:
    first = build_weight_config_loop_plan(created_at="2026-05-12T00:00:00+00:00")
    second = build_weight_config_loop_plan(created_at="2026-05-12T00:00:00+00:00")

    assert first == second


def test_weight_config_loop_keeps_evaluation_mode_snapshots_consistent() -> None:
    plan = build_weight_config_loop_plan(
        evaluation_mode="candidate_only_backtest",
        created_at="2026-05-12T00:00:00+00:00",
    )
    record = plan["records"][0]

    assert plan["evaluation_mode"] == "candidate_only_backtest"
    assert record["evaluation_mode"] == "candidate_only_backtest"
    assert record["weight_config_snapshot"]["evaluation_mode"] == "candidate_only_backtest"
    assert record["simulation_run_manifest_snapshot"]["run_mode"] == "candidate_only_backtest"


@pytest.mark.parametrize("horizon_id", ["1d", "1w", "1m"])
def test_weight_config_loop_uses_horizon_policy_snapshot(horizon_id: str) -> None:
    plan = build_weight_config_loop_plan(
        horizon_policy_id=horizon_id,
        created_at="2026-05-12T00:00:00+00:00",
    )

    assert plan["horizon_policy_id"] == horizon_id
    assert plan["horizon_policy_snapshot"]["horizon_id"] == horizon_id
    for record in plan["records"]:
        assert record["weight_config_snapshot"]["horizon_policy_snapshot"]["horizon_id"] == horizon_id


def test_weight_config_loop_creates_simulation_run_manifest() -> None:
    plan = build_weight_config_loop_plan(created_at="2026-05-12T00:00:00+00:00")
    record = plan["records"][0]
    manifest = record["simulation_run_manifest_snapshot"]

    assert record["simulation_run_manifest_ref"] == manifest["run_id"]
    assert manifest["horizon_policy_snapshot"]["horizon_id"] == "1d"
    assert manifest["weight_config_snapshot"]["weight_config_id"] == record["weight_config_id"]
    assert manifest["live_execution_enabled"] is False
    assert manifest["brokerage_integration_enabled"] is False
    assert manifest["order_generation_enabled"] is False


def test_weight_config_loop_keeps_rebalance_disclosure() -> None:
    plan = build_weight_config_loop_plan(
        horizon_policy_id="1w",
        created_at="2026-05-12T00:00:00+00:00",
    )
    record = plan["records"][0]

    assert record["rebalance_frequency"] == "weekly"
    assert "not_user_instruction" in record["rebalance_disclosure"]
    assert record["simulation_run_manifest_snapshot"]["rebalance_frequency"] == "weekly"


def test_weight_config_loop_uses_configured_rebalance_disclosure(tmp_path: Path) -> None:
    custom_disclosure = "custom_configured_rebalance_disclosure_not_user_instruction"
    config = _default_config_text().replace(
        "rebalancing_is_historical_simulation_context_only_not_user_instruction",
        custom_disclosure,
    )
    plan = build_weight_config_loop_plan(
        config_path=_write_config(tmp_path, config),
        created_at="2026-05-12T00:00:00+00:00",
    )
    record = plan["records"][0]

    assert record["rebalance_disclosure"] == custom_disclosure
    assert record["simulation_run_manifest_snapshot"]["rebalance_disclosure"] == custom_disclosure


def test_weight_config_loop_rejects_live_execution_mode() -> None:
    with pytest.raises(ValueError, match="blocked or unsupported WeightConfig evaluation_mode"):
        build_weight_config_loop_plan(evaluation_mode="live_trading")


def test_weight_config_loop_rejects_trade_signal_language() -> None:
    with pytest.raises(ValueError, match="blocked or unsupported WeightConfig evaluation_mode"):
        build_weight_config_loop_plan(evaluation_mode="trade_signal")


def test_weight_config_loop_does_not_modify_production_ranking() -> None:
    plan = build_weight_config_loop_plan(created_at="2026-05-12T00:00:00+00:00")

    assert plan["production_ranking_changed"] is False
    assert plan["best_weight_selected"] is False


def test_weight_config_loop_does_not_enable_phase6_evidence_v1() -> None:
    plan = build_weight_config_loop_plan(created_at="2026-05-12T00:00:00+00:00")

    assert plan["phase6_evidence_v1_enabled"] is False


def test_weight_config_cannot_use_inactive_or_diagnostic_reference_layer_as_active_weight(
    tmp_path: Path,
) -> None:
    config = _default_config_text().replace(
        "statistical_volatility_layer = 0.5",
        "diagnostic_data_quality_layer = 0.5",
        1,
    )

    with pytest.raises(ValueError, match="cannot be used as active weight"):
        load_weight_config_candidates(config_path=_write_config(tmp_path, config))


def test_weight_config_can_use_allowed_active_technical_layer_fixture() -> None:
    plan = build_weight_config_loop_plan(created_at="2026-05-12T00:00:00+00:00")
    first_weights = plan["records"][0]["weight_config_snapshot"]["score_weights"]

    assert set(first_weights) == {"technical_momentum_layer", "statistical_volatility_layer"}
