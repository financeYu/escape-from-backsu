"""Public facade for Step 15 latest ranking output.

The implementation lives in smaller policy, builder, and validation modules so
external imports can keep using ``src.scanner.latest_ranking`` while the
internals stay easier to review.
"""

from __future__ import annotations

from src.scanner.latest_ranking_builder import build_latest_ranking_output
from src.scanner.latest_ranking_policy import (
    DEFAULT_STEP15_RANKING_POLICY,
    STEP15_ALLOWED_COVERAGE_STATUSES,
    STEP15_ALLOWED_VALIDITY_FLAGS,
    STEP15_BASE_OUTPUT_COLUMNS,
    STEP15_BLOCKING_ROW_COVERAGE_STATUSES,
    STEP15_DIRECT_RANKING_STATES,
    STEP15_LATEST_RANKING_NOTICE,
    Step15CoverageStatus,
    Step15RankingPolicy,
    Step15ValidityFlag,
)
from src.scanner.latest_ranking_validation import (
    STEP15_FORBIDDEN_EXACT_COLUMNS,
    STEP15_FORBIDDEN_PREFIXES,
    STEP15_FORBIDDEN_SUFFIXES,
    assert_no_forbidden_step15_columns,
    find_forbidden_step15_columns,
    validate_step15_inputs,
    validate_step15_latest_ranking_output,
)

__all__ = (
    "DEFAULT_STEP15_RANKING_POLICY",
    "STEP15_BASE_OUTPUT_COLUMNS",
    "STEP15_DIRECT_RANKING_STATES",
    "STEP15_LATEST_RANKING_NOTICE",
    "Step15CoverageStatus",
    "Step15RankingPolicy",
    "Step15ValidityFlag",
    "assert_no_forbidden_step15_columns",
    "build_latest_ranking_output",
    "find_forbidden_step15_columns",
    "validate_step15_inputs",
    "validate_step15_latest_ranking_output",
)
