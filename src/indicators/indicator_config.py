"""Step 7 technical indicator config contracts and loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


DEFAULT_INPUT_PATH = "data/processed/daily_ohlcv.csv"
DEFAULT_OUTPUT_PATH = "data/processed/technical_indicators.csv"
DEFAULT_SUMMARY_REPORT_PATH = "reports/indicators/indicator_summary.md"
DEFAULT_VALIDATION_REPORT_PATH = "reports/indicators/indicator_validation_summary.csv"


@dataclass(frozen=True)
class IndicatorPaths:
    """Config-derived Step 7 input and output paths."""

    input_path: str = DEFAULT_INPUT_PATH
    output_path: str = DEFAULT_OUTPUT_PATH
    summary_report_path: str = DEFAULT_SUMMARY_REPORT_PATH
    validation_report_path: str = DEFAULT_VALIDATION_REPORT_PATH


@dataclass(frozen=True)
class IndicatorWindows:
    """Config-derived lookback windows for raw technical indicators."""

    returns: dict[str, int]
    volatility: dict[str, int]
    indicators: dict[str, int]
    statistics: dict[str, int]
    warmup: dict[str, int]


@dataclass(frozen=True)
class IndicatorConfig:
    """Full Step 7 config resolved from data and window TOML files."""

    paths: IndicatorPaths
    windows: IndicatorWindows


def load_indicator_config(
    *,
    data_config_path: str | Path = "config/data.toml",
    windows_config_path: str | Path = "config/windows.toml",
) -> IndicatorConfig:
    """Load Step 7 paths and windows from config files."""

    data_config = _load_toml(Path(data_config_path))
    windows_config = _load_toml(Path(windows_config_path))

    indicator_paths = data_config.get("indicators", {})
    paths = IndicatorPaths(
        input_path=str(indicator_paths.get("input_price_path", DEFAULT_INPUT_PATH)),
        output_path=str(indicator_paths.get("output_path", DEFAULT_OUTPUT_PATH)),
        summary_report_path=str(
            indicator_paths.get("summary_report_path", DEFAULT_SUMMARY_REPORT_PATH)
        ),
        validation_report_path=str(
            indicator_paths.get("validation_report_path", DEFAULT_VALIDATION_REPORT_PATH)
        ),
    )
    windows = IndicatorWindows(
        returns=_positive_ints(windows_config.get("returns", {}), "returns"),
        volatility=_positive_ints(windows_config.get("volatility", {}), "volatility"),
        indicators=_positive_ints(windows_config.get("indicators", {}), "indicators"),
        statistics=_positive_ints(windows_config.get("statistics", {}), "statistics"),
        warmup=_positive_ints(windows_config.get("warmup", {}), "warmup"),
    )
    return IndicatorConfig(paths=paths, windows=windows)


def _load_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _positive_ints(mapping: object, section: str) -> dict[str, int]:
    if not isinstance(mapping, dict):
        return {}
    values: dict[str, int] = {}
    for key, value in mapping.items():
        if key == "notes":
            continue
        try:
            int_value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"config/windows.toml [{section}] {key} must be a positive integer."
            ) from exc
        if isinstance(value, bool) or int_value <= 0:
            raise ValueError(
                f"config/windows.toml [{section}] {key} must be a positive integer."
            )
        values[str(key)] = int_value
    return values


__all__ = [
    "DEFAULT_INPUT_PATH",
    "DEFAULT_OUTPUT_PATH",
    "DEFAULT_SUMMARY_REPORT_PATH",
    "DEFAULT_VALIDATION_REPORT_PATH",
    "IndicatorConfig",
    "IndicatorPaths",
    "IndicatorWindows",
    "load_indicator_config",
]
