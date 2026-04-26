"""Backward-compatible facade for the Step 7 technical indicator layer.

The implementation is split across focused modules:

- ``indicator_config`` for config dataclasses and loading
- ``indicator_engine`` for raw OHLCV-derived indicator calculation
- ``indicator_io`` for pipeline artifact writing
- ``indicator_cli`` for CLI handling
- ``indicator_summary`` for summary/report construction

This facade preserves the historical ``src.indicators.technical`` import path.
It does not create scores, rankings, composites, adoption decisions, or
backtests.
"""

from __future__ import annotations

from .indicator_cli import main
from .indicator_config import (
    DEFAULT_INPUT_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_SUMMARY_REPORT_PATH,
    DEFAULT_VALIDATION_REPORT_PATH,
    IndicatorConfig,
    IndicatorPaths,
    IndicatorWindows,
    load_indicator_config,
)
from .indicator_engine import (
    FORBIDDEN_OUTPUT_TOKENS,
    OUTPUT_METADATA_COLUMNS,
    REQUIRED_OHLCV_COLUMNS,
    calculate_technical_indicators,
)
from .indicator_io import IndicatorResult, run_indicator_pipeline_from_config


__all__ = [
    "DEFAULT_INPUT_PATH",
    "DEFAULT_OUTPUT_PATH",
    "DEFAULT_SUMMARY_REPORT_PATH",
    "DEFAULT_VALIDATION_REPORT_PATH",
    "FORBIDDEN_OUTPUT_TOKENS",
    "IndicatorConfig",
    "IndicatorPaths",
    "IndicatorResult",
    "IndicatorWindows",
    "OUTPUT_METADATA_COLUMNS",
    "REQUIRED_OHLCV_COLUMNS",
    "calculate_technical_indicators",
    "load_indicator_config",
    "main",
    "run_indicator_pipeline_from_config",
]


if __name__ == "__main__":
    raise SystemExit(main())
