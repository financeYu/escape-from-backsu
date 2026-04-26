"""Configuration loading for Step 10A time-series normalization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .normalization_common import (
    load_toml,
    optional_float,
    positive_int,
    positive_int_or_none,
    validate_clip_bounds,
    validate_percentile_bounds,
)


@dataclass(frozen=True)
class TimeSeriesNormalizationConfig:
    """Configuration for ticker-local robust z-score normalization.

    ``window=None`` means expanding context. A positive ``window`` means each
    row uses at most that many same-ticker rows ending at the current row.
    """

    window: int | None = 252
    min_periods: int = 60
    mad_scale: float = 1.4826
    iqr_scale: float = 1.349
    use_iqr_fallback: bool = True
    winsorize_lower_pct: float | None = 0.01
    winsorize_upper_pct: float | None = 0.99
    clip_lower: float | None = None
    clip_upper: float | None = None

    def __post_init__(self) -> None:
        if self.window is not None and self.window <= 0:
            raise ValueError("Time-series normalization window must be positive or None.")
        if self.min_periods <= 0:
            raise ValueError("Time-series normalization min_periods must be positive.")
        if self.mad_scale <= 0:
            raise ValueError("MAD scale must be positive.")
        if self.iqr_scale <= 0:
            raise ValueError("IQR scale must be positive.")
        validate_percentile_bounds(self.winsorize_lower_pct, self.winsorize_upper_pct)
        validate_clip_bounds(self.clip_lower, self.clip_upper)


def load_timeseries_normalization_config(
    *,
    windows_config_path: str | Path = "Quant_mvp/config/windows.toml",
    thresholds_config_path: str | Path = "Quant_mvp/config/thresholds.toml",
) -> TimeSeriesNormalizationConfig:
    """Load Step 10A time-series normalization defaults from Quant config."""

    windows_config = load_toml(Path(windows_config_path))
    thresholds_config = load_toml(Path(thresholds_config_path))
    normalization = windows_config.get("normalization", {})
    quality = thresholds_config.get("quality", {})
    outliers = thresholds_config.get("outliers", {})
    return TimeSeriesNormalizationConfig(
        window=positive_int_or_none(
            normalization.get("time_series_window"),
            "normalization.time_series_window",
        ),
        min_periods=positive_int(
            quality.get("min_non_nan_observations"),
            "quality.min_non_nan_observations",
        ),
        winsorize_lower_pct=optional_float(
            outliers.get("winsorize_lower_pct"),
            "outliers.winsorize_lower_pct",
        ),
        winsorize_upper_pct=optional_float(
            outliers.get("winsorize_upper_pct"),
            "outliers.winsorize_upper_pct",
        ),
    )
