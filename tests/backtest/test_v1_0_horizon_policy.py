from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.validation.horizon_policy import resolve_horizon_policy  # noqa: E402
from Quant_mvp.backtest_mvp.contracts import BacktestConfig  # noqa: E402


def test_horizon_policy_loads_1d() -> None:
    policy = resolve_horizon_policy("1d")

    assert policy.horizon_id == "1d"
    assert policy.signal_frequency == "daily"
    assert policy.entry_lag_trading_days == 1
    assert policy.holding_period_trading_days == 1
    assert policy.rebalance_frequency == "daily"
    assert policy.label_horizon == "1d"
    assert policy.simulation_horizon == "1d"
    assert policy.calendar_policy == "trading_days"


def test_horizon_policy_loads_1w() -> None:
    policy = resolve_horizon_policy("1w")

    assert policy.horizon_id == "1w"
    assert policy.signal_frequency == "weekly"
    assert policy.entry_lag_trading_days == 1
    assert policy.holding_period_trading_days == 5
    assert policy.rebalance_frequency == "weekly"
    assert policy.label_horizon == "1w"
    assert policy.simulation_horizon == "1w"
    assert policy.calendar_policy == "trading_days"


def test_horizon_policy_loads_5d() -> None:
    policy = resolve_horizon_policy("5d")

    assert policy.horizon_id == "5d"
    assert policy.signal_frequency == "weekly"
    assert policy.entry_lag_trading_days == 1
    assert policy.holding_period_trading_days == 5
    assert policy.rebalance_frequency == "weekly"
    assert policy.label_horizon == "5d"
    assert policy.simulation_horizon == "5d"
    assert policy.calendar_policy == "trading_days"


def test_horizon_policy_loads_20d() -> None:
    policy = resolve_horizon_policy("20d")

    assert policy.horizon_id == "20d"
    assert policy.signal_frequency == "monthly"
    assert policy.entry_lag_trading_days == 1
    assert policy.holding_period_trading_days == 20
    assert policy.rebalance_frequency == "monthly"
    assert policy.label_horizon == "20d"
    assert policy.simulation_horizon == "20d"
    assert policy.calendar_policy == "trading_days"


def test_horizon_policy_loads_1m() -> None:
    policy = resolve_horizon_policy("1m")

    assert policy.horizon_id == "1m"
    assert policy.signal_frequency == "monthly"
    assert policy.entry_lag_trading_days == 1
    assert policy.holding_period_trading_days == 21
    assert policy.rebalance_frequency == "monthly"
    assert policy.label_horizon == "1m"
    assert policy.simulation_horizon == "1m"
    assert policy.calendar_policy == "trading_days"


def test_horizon_policy_default_is_explicit_1d() -> None:
    policy = resolve_horizon_policy()

    assert policy.horizon_id == "1d"
    assert policy.defaulted is True
    assert "backward_compatible_1d_default" in policy.default_reason


def test_horizon_policy_rejects_unknown_horizon() -> None:
    with pytest.raises(ValueError, match="unknown HorizonPolicy horizon_id"):
        resolve_horizon_policy("2w")


def test_horizon_policy_fields_are_not_conflated() -> None:
    policy = resolve_horizon_policy("1w")

    assert set(policy.to_dict()).issuperset(
        {
            "label_horizon",
            "holding_period_trading_days",
            "simulation_horizon",
            "entry_lag_trading_days",
            "signal_frequency",
            "rebalance_frequency",
            "calendar_policy",
        }
    )
    assert policy.label_horizon == "1w"
    assert policy.simulation_horizon == "1w"
    assert policy.holding_period_trading_days == 5
    assert policy.entry_lag_trading_days == 1


def test_horizon_policy_rebalance_frequency_is_simulation_only() -> None:
    policy = resolve_horizon_policy("1m")

    assert policy.rebalance_frequency == "monthly"
    assert policy.rebalance_disclosure_required is True
    assert "live" not in policy.to_dict()


def test_backtest_config_can_be_created_from_horizon_policy_without_changing_legacy_constructor() -> None:
    legacy = BacktestConfig()
    config = BacktestConfig.from_horizon_policy("5d", top_n=3)

    assert legacy.holding_period_days == 20
    assert config.holding_period_days == 5
    assert config.execution_lag_days == 1
    assert config.rebalance_frequency == "weekly"
    assert config.top_n == 3


def test_backtest_config_uses_20d_horizon_for_monthly_rebalance() -> None:
    config = BacktestConfig.from_horizon_policy("20d", top_n=3)

    assert config.holding_period_days == 20
    assert config.execution_lag_days == 1
    assert config.rebalance_frequency == "monthly"
