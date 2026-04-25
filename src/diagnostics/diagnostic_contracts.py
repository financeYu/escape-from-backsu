"""Step 12 redundancy/correlation diagnostic contracts.

This module fixes the output schema and guardrails for Step 12 diagnostics.
It does not calculate correlations, create rankings, build composite scores,
label future returns, run backtests, or perform valuation/fundamental scoring.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import math
import tomllib

import pandas as pd

from src.scores.schema import IDENTITY_COLUMNS, require_columns


STEP12_REVIEW_MATERIAL_NOTICE = "diagnostic/review material only"

STEP12_PAIR_DIAGNOSTIC_COLUMNS: tuple[str, ...] = (
    "diagnostic_name",
    "score_left",
    "score_right",
    "normalization_scope",
    "start_date",
    "end_date",
    "observation_count",
    "cross_section_count",
    "spearman_correlation",
    "abs_spearman_correlation",
    "threshold_flag",
    "diagnostic_status",
    "insufficient_data_reason",
    "score_left_family",
    "score_right_family",
    "score_left_role",
    "score_right_role",
    "implementation_deviation_id",
    "notes",
)

STEP12_COVERAGE_SUMMARY_COLUMNS: tuple[str, ...] = (
    "diagnostic_name",
    "score_name",
    "score_family",
    "normalization_scope",
    "date",
    "ticker_count",
    "observation_count",
    "non_nan_observation_count",
    "coverage_ratio",
    "min_required_observations",
    "min_cross_section_count",
    "diagnostic_status",
    "insufficient_data_reason",
    "implementation_deviation_id",
    "notes",
)

STEP12_DEVIATION_LOG_COLUMNS: tuple[str, ...] = (
    "deviation_id",
    "step",
    "affected_field",
    "expected_behavior",
    "actual_behavior",
    "reason",
    "risk",
    "review_required",
    "created_at_utc",
)


class Step12DiagnosticStatus(str, Enum):
    """Diagnostic flags passed to Step 13 review.

    These values are not adoption or rejection decisions.
    """

    OK = "ok"
    WARN = "warn"
    BLOCK_CANDIDATE = "block_candidate"
    SEVERE_REDUNDANCY = "severe_redundancy"
    INSUFFICIENT_INPUT = "insufficient_input"
    INSUFFICIENT_DATA = "insufficient_data"
    CONFIG_MISSING = "config_missing"
    UNDEFINED_CORRELATION = "undefined_correlation"


ALLOWED_STEP12_DIAGNOSTIC_STATUSES = frozenset(status.value for status in Step12DiagnosticStatus)

FORBIDDEN_DIAGNOSTIC_OUTPUT_COLUMNS = frozenset(
    {
        "rank",
        "ranking",
        "latest_rank",
        "latest_ranking",
        "technical_composite_score",
        "final_composite_score",
        "forward_return",
        "future_return",
        "backtest_return",
        "alpha",
        "signal",
        "buy",
        "sell",
        "valuation_score",
        "undervalued",
        "cheap",
        "bargain",
    }
)

FORBIDDEN_DIAGNOSTIC_OUTPUT_PREFIXES = (
    "rank_",
    "ranking_",
    "latest_rank",
    "forward_return",
    "future_return",
    "backtest_",
    "alpha_",
    "signal_",
    "buy_",
    "sell_",
    "valuation_",
)

FORBIDDEN_DIAGNOSTIC_OUTPUT_SUFFIXES = (
    "_rank",
    "_ranking",
    "_signal",
    "_alpha",
)


@dataclass(frozen=True)
class Step12ThresholdPolicy:
    """Config-owned Step 12 redundancy and quality thresholds."""

    spearman_warn: float
    spearman_block: float
    min_cross_section_count: int
    min_non_nan_observations: int


def load_step12_threshold_policy(
    thresholds_config: str | Path | Mapping[str, object] = "Quant_mvp/config/thresholds.toml",
) -> Step12ThresholdPolicy:
    """Load required Step 12 thresholds without silent defaults."""

    config = _load_config(thresholds_config)
    redundancy = _mapping(config.get("redundancy", {}))
    quality = _mapping(config.get("quality", {}))
    policy = Step12ThresholdPolicy(
        spearman_warn=_required_probability(redundancy, "spearman_warn", "redundancy"),
        spearman_block=_required_probability(redundancy, "spearman_block", "redundancy"),
        min_cross_section_count=_required_positive_int(
            quality,
            "min_cross_section_count",
            "quality",
        ),
        min_non_nan_observations=_required_positive_int(
            quality,
            "min_non_nan_observations",
            "quality",
        ),
    )
    if policy.spearman_warn > policy.spearman_block:
        raise ValueError("Config value redundancy.spearman_warn cannot exceed spearman_block.")
    return policy


def find_forbidden_diagnostic_output_columns(columns: Iterable[str]) -> list[str]:
    """Return Step 12 output columns that cross hard-stop boundaries."""

    forbidden: list[str] = []
    for column in columns:
        normalized = column.lower()
        if (
            normalized in FORBIDDEN_DIAGNOSTIC_OUTPUT_COLUMNS
            or normalized.startswith(FORBIDDEN_DIAGNOSTIC_OUTPUT_PREFIXES)
            or normalized.endswith(FORBIDDEN_DIAGNOSTIC_OUTPUT_SUFFIXES)
        ):
            forbidden.append(column)
    return forbidden


def assert_no_forbidden_diagnostic_output_columns(
    frame: pd.DataFrame,
    *,
    context: str = "Step 12 diagnostics output",
) -> None:
    forbidden = find_forbidden_diagnostic_output_columns(frame.columns)
    if forbidden:
        raise ValueError(
            f"{context} contains forbidden diagnostic output columns: "
            f"{', '.join(forbidden)}"
        )


def validate_step12_pair_diagnostics(
    frame: pd.DataFrame,
    *,
    context: str = "Step 12 score pair diagnostics",
) -> None:
    """Validate score-pair diagnostics produced by the Step 12 engine/wrapper."""

    require_columns(frame, STEP12_PAIR_DIAGNOSTIC_COLUMNS, context=context)
    assert_no_forbidden_diagnostic_output_columns(frame, context=context)
    _assert_allowed_statuses(frame, context=context)
    _assert_no_identity_columns(frame, context=context)


def validate_step12_coverage_summary(
    frame: pd.DataFrame,
    *,
    context: str = "Step 12 coverage summary",
) -> None:
    """Validate Step 12 coverage summary output."""

    require_columns(frame, STEP12_COVERAGE_SUMMARY_COLUMNS, context=context)
    assert_no_forbidden_diagnostic_output_columns(frame, context=context)
    _assert_allowed_statuses(frame, context=context)


def validate_step12_deviation_log(
    frame: pd.DataFrame,
    *,
    context: str = "Step 12 implementation deviation log",
) -> None:
    """Validate optional implementation deviation log rows."""

    require_columns(frame, STEP12_DEVIATION_LOG_COLUMNS, context=context)
    assert_no_forbidden_diagnostic_output_columns(frame, context=context)
    if not frame["step"].astype("string").str.contains("Step 12", regex=False, na=False).all():
        raise ValueError(f"{context} rows must be explicitly labeled as Step 12.")


def validate_step12_diagnostics_bundle(
    *,
    pair_diagnostics: pd.DataFrame,
    coverage_summary: pd.DataFrame,
    deviation_log: pd.DataFrame | None = None,
) -> None:
    """Validate the integration-facing Step 12 diagnostic output bundle."""

    validate_step12_pair_diagnostics(pair_diagnostics)
    validate_step12_coverage_summary(coverage_summary)
    if deviation_log is not None:
        validate_step12_deviation_log(deviation_log)


def classify_spearman_diagnostic_status(
    spearman_correlation: object,
    *,
    observation_count: int,
    cross_section_count: int,
    policy: Step12ThresholdPolicy,
) -> Step12DiagnosticStatus:
    """Classify an already-computed Spearman value using config thresholds.

    This wrapper does not calculate the correlation and does not decide score
    adoption. It only converts the numeric diagnostic into a Step 13 review
    flag.
    """

    if (
        observation_count < policy.min_non_nan_observations
        or cross_section_count < policy.min_cross_section_count
    ):
        return Step12DiagnosticStatus.INSUFFICIENT_DATA
    try:
        value = float(spearman_correlation)
    except (TypeError, ValueError):
        return Step12DiagnosticStatus.UNDEFINED_CORRELATION
    if not math.isfinite(value):
        return Step12DiagnosticStatus.UNDEFINED_CORRELATION
    absolute = abs(value)
    if absolute >= policy.spearman_block:
        return Step12DiagnosticStatus.BLOCK_CANDIDATE
    if absolute >= policy.spearman_warn:
        return Step12DiagnosticStatus.WARN
    return Step12DiagnosticStatus.OK


def threshold_flag_for_status(status: Step12DiagnosticStatus | str) -> str:
    """Return a stable threshold flag for a Step 12 diagnostic status."""

    value = status.value if isinstance(status, Step12DiagnosticStatus) else str(status)
    if value == Step12DiagnosticStatus.BLOCK_CANDIDATE.value:
        return "spearman_block"
    if value == Step12DiagnosticStatus.SEVERE_REDUNDANCY.value:
        return "spearman_block"
    if value == Step12DiagnosticStatus.WARN.value:
        return "spearman_warn"
    if value == Step12DiagnosticStatus.INSUFFICIENT_INPUT.value:
        return "insufficient_input"
    if value == Step12DiagnosticStatus.INSUFFICIENT_DATA.value:
        return "insufficient_data"
    if value == Step12DiagnosticStatus.CONFIG_MISSING.value:
        return "config_missing"
    if value == Step12DiagnosticStatus.UNDEFINED_CORRELATION.value:
        return "undefined_correlation"
    return "none"


def _assert_allowed_statuses(frame: pd.DataFrame, *, context: str) -> None:
    statuses = frame["diagnostic_status"].astype("string").fillna("unknown")
    invalid = sorted(set(statuses).difference(ALLOWED_STEP12_DIAGNOSTIC_STATUSES))
    if invalid:
        raise ValueError(f"{context} contains unsupported diagnostic_status values: {', '.join(invalid)}")


def _assert_no_identity_columns(frame: pd.DataFrame, *, context: str) -> None:
    present = [column for column in IDENTITY_COLUMNS if column in frame.columns]
    if present:
        raise ValueError(
            f"{context} is pair-level output and must not include row identity columns: "
            f"{', '.join(present)}"
        )


def _load_config(config: str | Path | Mapping[str, object]) -> Mapping[str, object]:
    if isinstance(config, Mapping):
        return config
    path = Path(config)
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _required_probability(section: Mapping[str, object], key: str, section_name: str) -> float:
    value = _require_key(section, key, section_name)
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Config value {section_name}.{key} must be numeric.") from exc
    if not math.isfinite(parsed) or parsed < 0.0 or parsed > 1.0:
        raise ValueError(f"Config value {section_name}.{key} must be between 0 and 1.")
    return parsed


def _required_positive_int(section: Mapping[str, object], key: str, section_name: str) -> int:
    value = _require_key(section, key, section_name)
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Config value {section_name}.{key} must be a positive integer.") from exc
    if isinstance(value, bool) or parsed <= 0:
        raise ValueError(f"Config value {section_name}.{key} must be a positive integer.")
    return parsed


def _require_key(section: Mapping[str, object], key: str, section_name: str) -> object:
    if key not in section:
        raise ValueError(f"Missing required Step 12 config key: {section_name}.{key}")
    return section[key]


__all__ = (
    "ALLOWED_STEP12_DIAGNOSTIC_STATUSES",
    "FORBIDDEN_DIAGNOSTIC_OUTPUT_COLUMNS",
    "STEP12_COVERAGE_SUMMARY_COLUMNS",
    "STEP12_DEVIATION_LOG_COLUMNS",
    "STEP12_PAIR_DIAGNOSTIC_COLUMNS",
    "STEP12_REVIEW_MATERIAL_NOTICE",
    "Step12DiagnosticStatus",
    "Step12ThresholdPolicy",
    "assert_no_forbidden_diagnostic_output_columns",
    "classify_spearman_diagnostic_status",
    "find_forbidden_diagnostic_output_columns",
    "load_step12_threshold_policy",
    "threshold_flag_for_status",
    "validate_step12_coverage_summary",
    "validate_step12_deviation_log",
    "validate_step12_diagnostics_bundle",
    "validate_step12_pair_diagnostics",
)
