"""Configuration loading for Step 10B cross-sectional normalization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .normalization_common import (
    load_toml,
    optional_float,
    positive_int,
    validate_percentile_bounds,
    validate_positive_clip,
)


@dataclass(frozen=True)
class CrossSectionalNormalizationConfig:
    """Configuration for same-date cross-sectional robust z-score normalization."""

    min_count: int = 20
    mad_scale_factor: float = 1.4826
    winsorize_lower_pct: float | None = None
    winsorize_upper_pct: float | None = None
    zscore_clip: float | None = None

    def __post_init__(self) -> None:
        if self.min_count < 1:
            raise ValueError("min_count must be at least 1.")
        if self.mad_scale_factor <= 0:
            raise ValueError("mad_scale_factor must be positive.")
        validate_percentile_bounds(self.winsorize_lower_pct, self.winsorize_upper_pct)
        validate_positive_clip(self.zscore_clip)


def load_cross_sectional_normalization_config(
    *,
    thresholds_config_path: str | Path = "Quant_mvp/config/thresholds.toml",
) -> CrossSectionalNormalizationConfig:
    """Load Step 10B cross-sectional normalization defaults from Quant config."""

    thresholds_config = load_toml(Path(thresholds_config_path))
    quality = thresholds_config.get("quality", {})
    outliers = thresholds_config.get("outliers", {})
    return CrossSectionalNormalizationConfig(
        min_count=positive_int(
            quality.get("min_cross_section_count"),
            "quality.min_cross_section_count",
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
