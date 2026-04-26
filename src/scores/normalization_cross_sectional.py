"""Backward-compatible public API for Step 10B cross-sectional normalization.

Implementation details live in ``cross_sectional_config.py``,
``cross_sectional_engine.py``, and ``normalization_common.py``.
"""

from __future__ import annotations

from .cross_sectional_config import (
    CrossSectionalNormalizationConfig,
    load_cross_sectional_normalization_config,
)
from .cross_sectional_engine import (
    BLOCKING_QUALITY_FLAGS,
    ELIGIBLE_COVERAGE_STATUSES,
    FLAG_ORDER,
    SCORE_METADATA_COLUMNS,
    STEP9_RAW_SCORE_COLUMNS,
    eligible_cross_sectional_observations,
    normalize_cross_sectional_score,
    normalize_cross_sectional_scores,
    prepare_cross_sectional_input_frame,
    robust_zscore_cross_sectional,
    score_name_from_raw_column,
)

__all__ = [
    "BLOCKING_QUALITY_FLAGS",
    "CrossSectionalNormalizationConfig",
    "ELIGIBLE_COVERAGE_STATUSES",
    "FLAG_ORDER",
    "SCORE_METADATA_COLUMNS",
    "STEP9_RAW_SCORE_COLUMNS",
    "eligible_cross_sectional_observations",
    "load_cross_sectional_normalization_config",
    "normalize_cross_sectional_score",
    "normalize_cross_sectional_scores",
    "prepare_cross_sectional_input_frame",
    "robust_zscore_cross_sectional",
    "score_name_from_raw_column",
]
