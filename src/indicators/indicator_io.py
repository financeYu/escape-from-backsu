"""Step 7 indicator pipeline IO and artifact writing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .indicator_config import load_indicator_config
from .indicator_engine import calculate_technical_indicators
from .indicator_summary import (
    build_indicator_summary,
    indicator_validation_summary_frame,
    write_indicator_summary_report,
)


@dataclass(frozen=True)
class IndicatorResult:
    """Written Step 7 artifacts and summary metrics."""

    indicators: pd.DataFrame
    validation_summary: pd.DataFrame
    summary: dict[str, object]
    output_path: Path
    summary_report_path: Path
    validation_report_path: Path


def run_indicator_pipeline_from_config(
    *,
    project_root: str | Path = ".",
    data_config_path: str | Path = "config/data.toml",
    windows_config_path: str | Path = "config/windows.toml",
) -> IndicatorResult:
    """Run Step 7 indicator calculation and write configured artifacts."""

    root = Path(project_root)
    config = load_indicator_config(
        data_config_path=root / data_config_path,
        windows_config_path=root / windows_config_path,
    )
    input_path = _resolve_path(root, config.paths.input_path)
    output_path = _resolve_path(root, config.paths.output_path)
    summary_report_path = _resolve_path(root, config.paths.summary_report_path)
    validation_report_path = _resolve_path(root, config.paths.validation_report_path)

    frame = pd.read_csv(input_path, dtype={"ticker": "string"})
    indicators = calculate_technical_indicators(frame, windows=config.windows)
    summary = build_indicator_summary(
        indicators,
        input_path=config.paths.input_path,
        output_path=config.paths.output_path,
        windows=config.windows,
    )
    validation_summary = indicator_validation_summary_frame(summary)

    _write_csv(indicators, output_path)
    _write_csv(validation_summary, validation_report_path)
    write_indicator_summary_report(summary, summary_report_path)
    return IndicatorResult(
        indicators=indicators,
        validation_summary=validation_summary,
        summary=summary,
        output_path=output_path,
        summary_report_path=summary_report_path,
        validation_report_path=validation_report_path,
    )


def _resolve_path(root: Path, path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return root / candidate


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")


__all__ = [
    "IndicatorResult",
    "run_indicator_pipeline_from_config",
]
