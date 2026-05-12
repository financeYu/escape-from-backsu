from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.simulation_run_manifest import (  # noqa: E402
    build_simulation_run_manifest,
    validate_simulation_run_manifest,
)
from src.validation.horizon_policy import resolve_horizon_policy  # noqa: E402


def _manifest(horizon_id: str = "1d", **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "strategy_candidate_id": "sc_v1_0_rc_example",
        "strategy_candidate_ref": "Quant_mvp/config/v0_3_strategy_candidate_registry.toml",
        "date_range": {"start": "2026-01-02", "end": "2026-03-31"},
        "horizon_policy": resolve_horizon_policy(horizon_id),
        "created_at": "2026-05-12T00:00:00+00:00",
        "code_version": "local_test_version",
        "rebalance_disclosure": "rebalancing_is_part_of_tested_strategy_logic_for_historical_simulation_only",
    }
    values.update(overrides)
    return build_simulation_run_manifest(**values)


@pytest.mark.parametrize("horizon_id", ["1d", "1w", "1m"])
def test_simulation_run_manifest_builds_with_horizon_policy(horizon_id: str) -> None:
    manifest = _manifest(horizon_id)

    assert manifest["horizon_policy_id"] == horizon_id
    assert manifest["horizon_policy_snapshot"]["horizon_id"] == horizon_id
    assert manifest["signal_frequency"] == manifest["horizon_policy_snapshot"]["signal_frequency"]
    assert manifest["entry_lag_trading_days"] == manifest["horizon_policy_snapshot"]["entry_lag_trading_days"]
    assert (
        manifest["holding_period_trading_days"]
        == manifest["horizon_policy_snapshot"]["holding_period_trading_days"]
    )
    assert manifest["rebalance_frequency"] == manifest["horizon_policy_snapshot"]["rebalance_frequency"]
    assert manifest["label_horizon"] == manifest["horizon_policy_snapshot"]["label_horizon"]
    assert manifest["simulation_horizon"] == manifest["horizon_policy_snapshot"]["simulation_horizon"]
    assert manifest["calendar_policy"] == "trading_days"


def test_simulation_run_manifest_requires_horizon_policy_snapshot() -> None:
    manifest = _manifest("1d")
    manifest.pop("horizon_policy_snapshot")

    with pytest.raises(ValueError, match="missing required fields"):
        validate_simulation_run_manifest(manifest)


def test_simulation_run_manifest_rejects_live_execution() -> None:
    with pytest.raises(ValueError, match="live_execution_enabled"):
        _manifest(live_execution_enabled=True)


def test_simulation_run_manifest_rejects_brokerage_or_orders() -> None:
    with pytest.raises(ValueError, match="brokerage_integration_enabled"):
        _manifest(brokerage_integration_enabled=True)
    with pytest.raises(ValueError, match="order_generation_enabled"):
        _manifest(order_generation_enabled=True)


def test_simulation_run_manifest_rejects_user_facing_auto_rebalance_instruction() -> None:
    with pytest.raises(ValueError, match="user_facing_auto_rebalance_instruction_enabled"):
        _manifest(user_facing_auto_rebalance_instruction_enabled=True)


def test_simulation_run_manifest_requires_rebalance_disclosure() -> None:
    manifest = _manifest("1w")
    manifest["rebalance_disclosure"] = ""

    with pytest.raises(ValueError, match="requires rebalance_disclosure"):
        validate_simulation_run_manifest(manifest)


def test_simulation_run_manifest_preserves_evidence_only_notice() -> None:
    manifest = _manifest("1m")

    assert "candidate-only evidence-only" in manifest["evidence_only_notice"]
    assert manifest["live_execution_enabled"] is False
    assert manifest["brokerage_integration_enabled"] is False
    assert manifest["order_generation_enabled"] is False


def test_simulation_run_manifest_does_not_enable_phase4_weight_loop() -> None:
    with pytest.raises(ValueError, match="phase4_weight_loop_enabled"):
        _manifest(phase4_weight_loop_enabled=True)


def test_simulation_run_manifest_rejects_blocked_run_mode() -> None:
    with pytest.raises(ValueError, match="blocked or unsupported run_mode"):
        _manifest(run_mode="live_trading")
