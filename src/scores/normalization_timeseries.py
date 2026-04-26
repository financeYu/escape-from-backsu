"""Backward-compatible public API for Step 10A time-series normalization.

Implementation details live in ``timeseries_config.py``,
``timeseries_engine.py``, and ``normalization_common.py``.
"""

from __future__ import annotations

from .normalization_common import apply_clipping, apply_winsorization
from .timeseries_config import (
    TimeSeriesNormalizationConfig,
    load_timeseries_normalization_config,
)
from .timeseries_engine import (
    NORMALIZATION_SCOPE,
    ROBUST_ZSCORE_COLUMN,
    STATUS_INSUFFICIENT_HISTORY,
    STATUS_INVALID_RAW_SCORE,
    STATUS_MISSING_RAW_SCORE,
    STATUS_OK,
    STATUS_WARMUP,
    STATUS_ZERO_SCALE,
    TICKER_PATTERN,
    TIME_SERIES_STATUSES,
    normalize_timeseries_score,
    normalize_timeseries_scores,
    robust_zscore_expanding,
)

__all__ = [
    "NORMALIZATION_SCOPE",
    "ROBUST_ZSCORE_COLUMN",
    "STATUS_INSUFFICIENT_HISTORY",
    "STATUS_INVALID_RAW_SCORE",
    "STATUS_MISSING_RAW_SCORE",
    "STATUS_OK",
    "STATUS_WARMUP",
    "STATUS_ZERO_SCALE",
    "TICKER_PATTERN",
    "TIME_SERIES_STATUSES",
    "TimeSeriesNormalizationConfig",
    "apply_clipping",
    "apply_winsorization",
    "load_timeseries_normalization_config",
    "normalize_timeseries_score",
    "normalize_timeseries_scores",
    "robust_zscore_expanding",
]
