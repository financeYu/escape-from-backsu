"""Score calculation and Step 10 normalization boundary.

This package exposes Research Tester raw score helpers plus Step 10
time-series and cross-sectional normalization primitives. Ranking, composites,
valuation scoring, and backtests remain outside this package's current scope.
"""

from .normalization_cross_sectional import (
    CrossSectionalNormalizationConfig,
    load_cross_sectional_normalization_config,
    normalize_cross_sectional_score,
    normalize_cross_sectional_scores,
    robust_zscore_cross_sectional,
)
from .normalization_diagnostics import (
    build_normalization_diagnostics,
    summarize_normalization_coverage,
)
from .normalization_timeseries import (
    TimeSeriesNormalizationConfig,
    apply_clipping,
    apply_winsorization,
    load_timeseries_normalization_config,
    normalize_timeseries_score,
    normalize_timeseries_scores,
    robust_zscore_expanding,
)
from .prob_up_1d_candidate import (
    CANDIDATE_SIDECAR_RANK_COLUMN,
    DECISION_TIME_COLUMN,
    DEFAULT_FEATURE_SET_VERSION,
    DEFAULT_LABEL_CONTRACT_VERSION,
    DEFAULT_SIDECAR_FILENAME_TEMPLATE,
    DEFAULT_SIDECAR_MANIFEST_TEMPLATE,
    EXECUTION_TIME_COLUMN,
    FEATURE_SET_VERSION_COLUMN,
    LABEL_AVAILABILITY_TIME_COLUMN,
    LABEL_CONTRACT_VERSION_COLUMN,
    LABEL_TIME_COLUMN,
    PROBABILITY_COLUMN,
    ProbUp1DConfig,
    ProbUp1DSidecarExportResult,
    build_prob_up_1d_candidate_sidecar_ranking,
    build_prob_up_1d_dataset,
    export_prob_up_1d_candidate_sidecar,
    fit_prob_up_1d_candidate_model,
    predict_prob_up_1d_candidate,
    run_prob_up_1d_candidate_pipeline,
)
from .technical_scores import calculate_all_raw_scores

__all__ = (
    "CANDIDATE_SIDECAR_RANK_COLUMN",
    "CrossSectionalNormalizationConfig",
    "DECISION_TIME_COLUMN",
    "DEFAULT_FEATURE_SET_VERSION",
    "DEFAULT_LABEL_CONTRACT_VERSION",
    "DEFAULT_SIDECAR_FILENAME_TEMPLATE",
    "DEFAULT_SIDECAR_MANIFEST_TEMPLATE",
    "EXECUTION_TIME_COLUMN",
    "FEATURE_SET_VERSION_COLUMN",
    "LABEL_AVAILABILITY_TIME_COLUMN",
    "LABEL_CONTRACT_VERSION_COLUMN",
    "LABEL_TIME_COLUMN",
    "PROBABILITY_COLUMN",
    "ProbUp1DConfig",
    "ProbUp1DSidecarExportResult",
    "TimeSeriesNormalizationConfig",
    "apply_clipping",
    "apply_winsorization",
    "build_normalization_diagnostics",
    "build_prob_up_1d_candidate_sidecar_ranking",
    "build_prob_up_1d_dataset",
    "calculate_all_raw_scores",
    "export_prob_up_1d_candidate_sidecar",
    "fit_prob_up_1d_candidate_model",
    "load_cross_sectional_normalization_config",
    "load_timeseries_normalization_config",
    "normalize_cross_sectional_score",
    "normalize_cross_sectional_scores",
    "normalize_timeseries_score",
    "normalize_timeseries_scores",
    "predict_prob_up_1d_candidate",
    "robust_zscore_cross_sectional",
    "robust_zscore_expanding",
    "run_prob_up_1d_candidate_pipeline",
    "summarize_normalization_coverage",
)
