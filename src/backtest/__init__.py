"""Compatibility package for the Quant-owned Backtest MVP.

New code should import from ``Quant_mvp.backtest_mvp``. This package remains as
the legacy ``src.backtest`` facade so existing Step 17/18/19 callers do not
break during the ownership transition.
"""

from Quant_mvp.backtest_mvp import (
    STEP17_BACKTEST_NOTICE,
    BacktestConfig,
    BacktestLimitationFlag,
    BacktestPeriodResult,
    BacktestSecurityResult,
    BacktestSummary,
    ConservativeBacktestResult,
    WalkForwardConfig,
    WalkForwardFoldResult,
    WalkForwardSummary,
    find_forbidden_backtest_input_columns,
    run_conservative_backtest,
    run_walk_forward_backtest,
    validate_backtest_price_input,
    validate_backtest_ranking_input,
)

__all__ = (
    "BacktestConfig",
    "BacktestLimitationFlag",
    "BacktestPeriodResult",
    "BacktestSecurityResult",
    "BacktestSummary",
    "ConservativeBacktestResult",
    "STEP17_BACKTEST_NOTICE",
    "WalkForwardConfig",
    "WalkForwardFoldResult",
    "WalkForwardSummary",
    "find_forbidden_backtest_input_columns",
    "run_conservative_backtest",
    "run_walk_forward_backtest",
    "validate_backtest_price_input",
    "validate_backtest_ranking_input",
)
