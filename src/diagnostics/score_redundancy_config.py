"""Step 12 score redundancy and correlation diagnostics.

This module computes same-date cross-sectional Spearman correlations between
normalized/component score columns. It is diagnostic review material only: it
does not create rankings, composite scores, signals, valuation fields,
forward-return labels, or backtest outputs.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import tomllib

import numpy as np


class ScoreRedundancyConfigError(ValueError):
    """Raised when Step 12 threshold config is missing or invalid."""


@dataclass(frozen=True)
class ScoreRedundancyConfig:
    """Config values required for Step 12 redundancy diagnostics."""

    min_cross_section_count: int
    min_non_nan_observations: int
    spearman_warn: float
    spearman_block: float

    def __post_init__(self) -> None:
        if self.min_cross_section_count < 1:
            raise ValueError("min_cross_section_count must be at least 1.")
        if self.min_non_nan_observations < 1:
            raise ValueError("min_non_nan_observations must be at least 1.")
        _validate_threshold(self.spearman_warn, "spearman_warn")
        _validate_threshold(self.spearman_block, "spearman_block")
        if self.spearman_warn > self.spearman_block:
            raise ValueError("spearman_warn cannot exceed spearman_block.")


def load_score_redundancy_config(
    *,
    thresholds_config_path: str | Path = "Quant_mvp/config/thresholds.toml",
) -> ScoreRedundancyConfig:
    """Load Step 12 thresholds from Quant config without hardcoded fallback."""

    config = _load_toml(Path(thresholds_config_path))
    quality = _mapping(config.get("quality", {}))
    redundancy = _mapping(config.get("redundancy", {}))
    missing = [
        key
        for key, value in (
            ("quality.min_cross_section_count", quality.get("min_cross_section_count")),
            ("quality.min_non_nan_observations", quality.get("min_non_nan_observations")),
            ("redundancy.spearman_warn", redundancy.get("spearman_warn")),
            ("redundancy.spearman_block", redundancy.get("spearman_block")),
        )
        if value is None
    ]
    if missing:
        raise ScoreRedundancyConfigError(
            "config_missing: " + ", ".join(missing)
        )
    return ScoreRedundancyConfig(
        min_cross_section_count=_positive_int(
            quality.get("min_cross_section_count"),
            "quality.min_cross_section_count",
        ),
        min_non_nan_observations=_positive_int(
            quality.get("min_non_nan_observations"),
            "quality.min_non_nan_observations",
        ),
        spearman_warn=_threshold_float(
            redundancy.get("spearman_warn"),
            "redundancy.spearman_warn",
        ),
        spearman_block=_threshold_float(
            redundancy.get("spearman_block"),
            "redundancy.spearman_block",
        ),
    )

def _load_toml(path: Path) -> Mapping[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)

def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}

def _positive_int(value: object, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ScoreRedundancyConfigError(
            f"config_invalid: {name} must be a positive integer"
        ) from exc
    if isinstance(value, bool) or parsed <= 0:
        raise ScoreRedundancyConfigError(
            f"config_invalid: {name} must be a positive integer"
        )
    return parsed

def _threshold_float(value: object, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ScoreRedundancyConfigError(
            f"config_invalid: {name} must be numeric"
        ) from exc
    try:
        _validate_threshold(parsed, name)
    except ValueError as exc:
        raise ScoreRedundancyConfigError(f"config_invalid: {exc}") from exc
    return parsed

def _validate_threshold(value: float, name: str) -> None:
    if not np.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError(f"{name} must be between 0 and 1.")

__all__ = (
    "ScoreRedundancyConfig",
    "ScoreRedundancyConfigError",
    "load_score_redundancy_config",
)
