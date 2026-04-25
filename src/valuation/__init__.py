"""Step 18 valuation/fundamental candidate-only utilities.

The package defines sidecar candidate data contracts and guardrails only. It
does not activate valuation/fundamental scoring, production ranking, or
backtest inputs.
"""

from src.valuation.contracts import (
    STEP18_CANDIDATE_SCHEMA_COLUMNS,
    STEP18_OPTIONAL_CANDIDATE_COLUMNS,
    MetricCategory,
    ValuationCandidateRecord,
)
from src.valuation.registry import (
    DEFAULT_STEP18_METRIC_REGISTRY,
    MetricSpec,
    load_metric_registry,
    metric_registry_by_name,
)
from src.valuation.reports import build_step18_candidate_report
from src.valuation.validation import (
    assert_no_step18_score_contamination,
    validate_candidate_records,
)

__all__ = (
    "DEFAULT_STEP18_METRIC_REGISTRY",
    "STEP18_CANDIDATE_SCHEMA_COLUMNS",
    "STEP18_OPTIONAL_CANDIDATE_COLUMNS",
    "MetricCategory",
    "MetricSpec",
    "ValuationCandidateRecord",
    "assert_no_step18_score_contamination",
    "build_step18_candidate_report",
    "load_metric_registry",
    "metric_registry_by_name",
    "validate_candidate_records",
)
