"""Step 13 technical selection review contracts and guardrails.

This module fixes the review-table schema for the Technical Selection Reviewer.
It does not calculate rankings, composite scores, trading signals, future
returns, backtest labels, or valuation/fundamental scores.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
import re

import numpy as np
import pandas as pd

from src.composite.contracts import (
    DEFAULT_COMPOSITE_INPUT_REGISTRY,
    MVP_SCORE_NAMES,
    CompositeEligibility,
    CompositeInputSpec,
    CompositeRole,
)
from src.scores.schema import find_valuation_fundamental_columns, require_columns


STEP13_REVIEW_MATERIAL_NOTICE = "technical review material only"

STEP13_REVIEW_TABLE_COLUMNS: tuple[str, ...] = (
    "score_name",
    "family",
    "branch",
    "role",
    "eligibility",
    "normalized_score_column",
    "score_input_column",
    "coverage_status",
    "redundancy_status",
    "complexity_status",
    "regime_fit_status",
    "review_status",
    "review_reason",
    "evidence_sources",
    "manual_review_required",
)


class Step13CoverageStatus(str, Enum):
    """Coverage review labels derived from Step 10/12 material."""

    OK = "ok"
    WARN = "warn"
    INSUFFICIENT_INPUT = "insufficient_input"
    INSUFFICIENT_DATA = "insufficient_data"
    BLOCKED_BY_DATA = "blocked_by_data"
    UNKNOWN = "unknown"


class Step13RedundancyStatus(str, Enum):
    """Redundancy review labels passed from Step 12 diagnostics."""

    OK = "ok"
    WARN = "warn"
    BLOCK_CANDIDATE = "block_candidate"
    SEVERE_REDUNDANCY = "severe_redundancy"
    INSUFFICIENT_INPUT = "insufficient_input"
    INSUFFICIENT_DATA = "insufficient_data"
    CONFIG_MISSING = "config_missing"
    UNDEFINED_CORRELATION = "undefined_correlation"
    UNKNOWN = "unknown"


class Step13ComplexityStatus(str, Enum):
    """Implementation and interpretability cost labels for review material."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXCESSIVE_COMPLEXITY = "excessive_complexity"
    UNKNOWN = "unknown"


class Step13RegimeFitStatus(str, Enum):
    """Market-structure and regime-fit review labels."""

    BROAD = "broad"
    REGIME_SPECIFIC = "regime_specific"
    DIAGNOSTIC_CONTEXT = "diagnostic_context"
    UNCLEAR = "unclear"
    BLOCKED_BY_DATA = "blocked_by_data"
    UNKNOWN = "unknown"


class Step13ReviewStatus(str, Enum):
    """Step 13 technical review recommendations, not final adoption states."""

    ADOPT_CANDIDATE = "adopt_candidate"
    CONDITIONAL_CANDIDATE = "conditional_candidate"
    RESEARCH_ONLY = "research_only"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    REJECT_CANDIDATE = "reject_candidate"
    BLOCKED_BY_DATA = "blocked_by_data"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


ALLOWED_STEP13_COVERAGE_STATUSES = frozenset(status.value for status in Step13CoverageStatus)
ALLOWED_STEP13_REDUNDANCY_STATUSES = frozenset(status.value for status in Step13RedundancyStatus)
ALLOWED_STEP13_COMPLEXITY_STATUSES = frozenset(status.value for status in Step13ComplexityStatus)
ALLOWED_STEP13_REGIME_FIT_STATUSES = frozenset(status.value for status in Step13RegimeFitStatus)
ALLOWED_STEP13_REVIEW_STATUSES = frozenset(status.value for status in Step13ReviewStatus)

ALLOWED_STEP13_ROLES = frozenset(role.value for role in CompositeRole)
ALLOWED_STEP13_ELIGIBILITY = frozenset(status.value for status in CompositeEligibility)
ALLOWED_STEP13_BRANCHES = frozenset({spec.branch for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY})
ALLOWED_STEP13_FAMILIES = frozenset({spec.family for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY})

STEP13_FORBIDDEN_EXACT_COLUMNS = frozenset(
    {
        "rank",
        "ranking",
        "latest_rank",
        "latest_ranking",
        "technical_composite_score",
        "final_composite_score",
        "composite_score",
        "family_weighted_score",
        "forward_return",
        "future_return",
        "next_return",
        "next_period_return",
        "backtest_return",
        "alpha",
        "signal",
        "buy",
        "sell",
        "valuation_score",
        "fundamental_score",
        "undervalued",
        "cheap",
        "bargain",
        "target_price",
        "expected_return",
        "position_size",
        "recommendation",
        "adoption_status",
        "adoption_decision",
        "final_adoption_status",
        "final_adoption_decision",
        "selected_score",
        "selected_for_composite",
    }
)
STEP13_FORBIDDEN_PREFIXES = (
    "rank_",
    "ranking_",
    "latest_rank",
    "forward_return",
    "future_return",
    "next_period_return",
    "backtest_",
    "alpha_",
    "signal_",
    "buy_",
    "sell_",
    "valuation_",
    "fundamental_",
    "target_price",
    "expected_return",
    "position_size",
    "final_adoption",
    "adoption_",
)
STEP13_FORBIDDEN_SUFFIXES = (
    "_rank",
    "_ranking",
    "_signal",
    "_alpha",
    "_target_price",
    "_expected_return",
    "_position_size",
)
STEP13_FORBIDDEN_SUBSTRINGS = (
    "technical_composite_score",
    "technical_composite",
    "final_composite_score",
    "final_composite",
    "composite_score",
    "family_weighted_score",
    "forward_return",
    "future_return",
    "backtest_return",
    "valuation_score",
    "target_price",
    "expected_return",
    "position_size",
    "latest_ranking",
    "latest_rank",
)
STEP13_FORBIDDEN_COLUMN_TOKENS = frozenset(
    {
        "rank",
        "ranking",
        "alpha",
        "signal",
        "buy",
        "sell",
        "cheap",
        "bargain",
        "undervalued",
    }
)

STEP13_FORBIDDEN_LANGUAGE_TERMS = frozenset(
    {
        "rank",
        "ranking",
        "latest rank",
        "latest_rank",
        "latest ranking",
        "latest_ranking",
        "technical_composite_score",
        "final_composite_score",
        "forward return",
        "forward_return",
        "future return",
        "future_return",
        "backtest",
        "backtest_return",
        "alpha",
        "signal",
        "buy",
        "sell",
        "valuation",
        "valuation_score",
        "undervalued",
        "cheap",
        "bargain",
        "target price",
        "target_price",
        "expected return",
        "expected_return",
        "position size",
        "position_size",
        "core_adopted",
        "conditional_adopted",
        "technical_only",
        "regime_only",
        "rejected",
    }
)

STEP13_TEXT_COLUMNS = ("review_reason", "evidence_sources")


@dataclass(frozen=True)
class Step13ReviewBundle:
    """Integration-facing Step 13 review bundle.

    `review_table` is the only canonical Step 13 table in Worker A's contract.
    Optional source tables can be carried for Worker B integration checks, but
    they are still screened for Step 13 forbidden output columns.
    """

    review_table: pd.DataFrame
    source_tables: Mapping[str, pd.DataFrame] | None = None


def find_forbidden_step13_output_columns(columns: Iterable[str]) -> list[str]:
    """Return output columns that cross Step 13 hard-stop boundaries."""

    forbidden: list[str] = []
    for column in columns:
        normalized = column.lower()
        tokens = set(normalized.split("_"))
        if (
            normalized in STEP13_FORBIDDEN_EXACT_COLUMNS
            or normalized.startswith(STEP13_FORBIDDEN_PREFIXES)
            or normalized.endswith(STEP13_FORBIDDEN_SUFFIXES)
            or any(substring in normalized for substring in STEP13_FORBIDDEN_SUBSTRINGS)
            or bool(tokens.intersection(STEP13_FORBIDDEN_COLUMN_TOKENS))
        ):
            forbidden.append(column)
    valuation_columns = find_valuation_fundamental_columns(columns)
    return sorted(set(forbidden).union(valuation_columns))


def reject_step13_forbidden_columns(
    frame: pd.DataFrame,
    *,
    context: str = "Step 13 review output",
) -> None:
    """Reject columns that imply ranking, composite, backtest, or valuation output."""

    forbidden = find_forbidden_step13_output_columns(frame.columns)
    if forbidden:
        raise ValueError(
            f"{context} contains forbidden Step 13 output columns: "
            f"{', '.join(forbidden)}"
        )


def validate_step13_status_values(
    frame: pd.DataFrame,
    *,
    context: str = "Step 13 review table",
) -> None:
    """Validate Step 13 status vocabularies without making review decisions."""

    require_columns(
        frame,
        (
            "family",
            "branch",
            "role",
            "eligibility",
            "coverage_status",
            "redundancy_status",
            "complexity_status",
            "regime_fit_status",
            "review_status",
            "manual_review_required",
        ),
        context=context,
    )
    _assert_allowed_values(frame, "family", ALLOWED_STEP13_FAMILIES, context=context)
    _assert_allowed_values(frame, "branch", ALLOWED_STEP13_BRANCHES, context=context)
    _assert_allowed_values(frame, "role", ALLOWED_STEP13_ROLES, context=context)
    _assert_allowed_values(frame, "eligibility", ALLOWED_STEP13_ELIGIBILITY, context=context)
    _assert_allowed_values(frame, "coverage_status", ALLOWED_STEP13_COVERAGE_STATUSES, context=context)
    _assert_allowed_values(frame, "redundancy_status", ALLOWED_STEP13_REDUNDANCY_STATUSES, context=context)
    _assert_allowed_values(frame, "complexity_status", ALLOWED_STEP13_COMPLEXITY_STATUSES, context=context)
    _assert_allowed_values(frame, "regime_fit_status", ALLOWED_STEP13_REGIME_FIT_STATUSES, context=context)
    _assert_allowed_values(frame, "review_status", ALLOWED_STEP13_REVIEW_STATUSES, context=context)
    _assert_manual_review_required_is_boolean(frame, context=context)
    _assert_needs_manual_review_is_marked(frame, context=context)


def validate_step13_review_table(
    frame: pd.DataFrame,
    *,
    registry: Iterable[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
    require_all_scores: bool = False,
    context: str = "Step 13 review table",
) -> None:
    """Validate the Step 13 technical review recommendation table.

    This function validates schema, status vocabulary, upstream Step 11
    metadata alignment, and hard-stop boundaries. It does not score, rank,
    adopt, backtest, or value any candidate.
    """

    require_columns(frame, STEP13_REVIEW_TABLE_COLUMNS, context=context)
    reject_step13_forbidden_columns(frame, context=context)
    validate_step13_status_values(frame, context=context)
    _assert_known_unique_score_names(
        frame,
        registry=tuple(registry),
        require_all_scores=require_all_scores,
        context=context,
    )
    _assert_registry_metadata_alignment(frame, registry=tuple(registry), context=context)
    _assert_review_input_columns_present(frame, context=context)
    _assert_text_columns_non_empty(frame, context=context)
    _assert_text_columns_avoid_forbidden_language(frame, context=context)


def validate_step13_review_bundle(
    bundle: Step13ReviewBundle | Mapping[str, object],
    *,
    require_all_scores: bool = True,
) -> None:
    """Validate a Worker B integration bundle that contains Step 13 output."""

    review_table = _extract_review_table(bundle)
    validate_step13_review_table(
        review_table,
        require_all_scores=require_all_scores,
        context="Step 13 review bundle review_table",
    )
    for name, frame in _iter_bundle_frames(bundle):
        reject_step13_forbidden_columns(frame, context=f"Step 13 review bundle {name}")


def validate_step13_review_language(
    text: str,
    *,
    context: str = "Step 13 generated review material",
) -> None:
    """Reject generated narrative that crosses Step 13 review boundaries."""

    lowered = text.lower()
    violations = [
        term
        for term in sorted(STEP13_FORBIDDEN_LANGUAGE_TERMS)
        if _contains_forbidden_term(lowered, term)
    ]
    if violations:
        raise ValueError(f"{context} contains forbidden Step 13 language: {', '.join(violations)}")
    if STEP13_REVIEW_MATERIAL_NOTICE not in lowered:
        raise ValueError(f"{context} must include: {STEP13_REVIEW_MATERIAL_NOTICE}")


def _assert_allowed_values(
    frame: pd.DataFrame,
    column: str,
    allowed: frozenset[str],
    *,
    context: str,
) -> None:
    values = frame[column].astype("string").fillna("unknown")
    invalid = sorted(set(values).difference(allowed))
    if invalid:
        raise ValueError(f"{context} contains unsupported {column} values: {', '.join(invalid)}")


def _assert_manual_review_required_is_boolean(
    frame: pd.DataFrame,
    *,
    context: str,
) -> None:
    invalid = [
        index
        for index, value in frame["manual_review_required"].items()
        if not isinstance(value, (bool, np.bool_))
    ]
    if invalid:
        raise ValueError(f"{context} manual_review_required must contain boolean values.")


def _assert_needs_manual_review_is_marked(frame: pd.DataFrame, *, context: str) -> None:
    mask = frame["review_status"].eq(Step13ReviewStatus.NEEDS_MANUAL_REVIEW.value)
    if mask.any():
        flags = frame.loc[mask, "manual_review_required"]
        if not flags.map(lambda value: bool(value)).all():
            raise ValueError(
                f"{context} rows with needs_manual_review must set manual_review_required."
            )


def _assert_known_unique_score_names(
    frame: pd.DataFrame,
    *,
    registry: tuple[CompositeInputSpec, ...],
    require_all_scores: bool,
    context: str,
) -> None:
    score_names = tuple(frame["score_name"].astype("string"))
    if len(score_names) != len(set(score_names)):
        raise ValueError(f"{context} contains duplicate score_name values.")
    known = {spec.score_name for spec in registry}
    unknown = sorted(set(score_names).difference(known))
    if unknown:
        raise ValueError(f"{context} contains unknown score_name values: {', '.join(unknown)}")
    if require_all_scores and set(score_names) != set(MVP_SCORE_NAMES):
        missing = sorted(set(MVP_SCORE_NAMES).difference(score_names))
        extra = sorted(set(score_names).difference(MVP_SCORE_NAMES))
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        raise ValueError(f"{context} must include all eight Step 9 MVP scores ({'; '.join(details)}).")


def _assert_registry_metadata_alignment(
    frame: pd.DataFrame,
    *,
    registry: tuple[CompositeInputSpec, ...],
    context: str,
) -> None:
    by_name = {spec.score_name: spec for spec in registry}
    for _, row in frame.iterrows():
        score_name = str(row["score_name"])
        spec = by_name[score_name]
        observed = (
            str(row["family"]),
            str(row["branch"]),
            str(row["role"]),
            str(row["eligibility"]),
        )
        expected = (
            spec.family,
            spec.branch,
            spec.role.value,
            spec.eligibility.value,
        )
        if observed != expected:
            raise ValueError(
                f"{context} row for {score_name} must preserve Step 11 "
                "family/branch/role/eligibility metadata."
            )


def _assert_review_input_columns_present(frame: pd.DataFrame, *, context: str) -> None:
    normalized_present = _non_empty_string_mask(frame["normalized_score_column"])
    score_input_present = _non_empty_string_mask(frame["score_input_column"])
    missing = ~(normalized_present | score_input_present)
    if missing.any():
        score_names = ", ".join(frame.loc[missing, "score_name"].astype("string"))
        raise ValueError(
            f"{context} rows must include normalized_score_column or score_input_column: "
            f"{score_names}"
        )

    raw_in_normalized = frame.loc[
        normalized_present
        & frame["normalized_score_column"].astype("string").str.strip().str.endswith("_raw"),
        "score_name",
    ]
    if not raw_in_normalized.empty:
        raise ValueError(
            f"{context} normalized_score_column must not point to raw score columns: "
            f"{', '.join(raw_in_normalized.astype('string'))}"
        )


def _assert_text_columns_non_empty(frame: pd.DataFrame, *, context: str) -> None:
    for column in STEP13_TEXT_COLUMNS:
        present = _non_empty_string_mask(frame[column])
        if not present.all():
            score_names = ", ".join(frame.loc[~present, "score_name"].astype("string"))
            raise ValueError(f"{context} {column} must be non-empty for: {score_names}")


def _assert_text_columns_avoid_forbidden_language(frame: pd.DataFrame, *, context: str) -> None:
    text = "\n".join(
        str(value)
        for column in STEP13_TEXT_COLUMNS
        for value in frame[column].dropna().tolist()
    )
    lowered = text.lower()
    violations = [
        term
        for term in sorted(STEP13_FORBIDDEN_LANGUAGE_TERMS)
        if _contains_forbidden_term(lowered, term)
    ]
    if violations:
        raise ValueError(f"{context} contains forbidden Step 13 language: {', '.join(violations)}")


def _non_empty_string_mask(series: pd.Series) -> pd.Series:
    text = series.astype("string")
    return (text.notna() & text.str.strip().ne("")).fillna(False)


def _extract_review_table(bundle: Step13ReviewBundle | Mapping[str, object]) -> pd.DataFrame:
    if isinstance(bundle, Step13ReviewBundle):
        return bundle.review_table
    if "review_table" not in bundle:
        raise ValueError("Step 13 review bundle missing review_table.")
    review_table = bundle["review_table"]
    if not isinstance(review_table, pd.DataFrame):
        raise TypeError("Step 13 review bundle review_table must be a pandas DataFrame.")
    return review_table


def _iter_bundle_frames(
    bundle: Step13ReviewBundle | Mapping[str, object],
) -> Iterable[tuple[str, pd.DataFrame]]:
    if isinstance(bundle, Step13ReviewBundle):
        yield "review_table", bundle.review_table
        if bundle.source_tables:
            for name, frame in bundle.source_tables.items():
                yield name, frame
        return
    for name, value in bundle.items():
        if isinstance(value, pd.DataFrame):
            yield str(name), value


def _contains_forbidden_term(lowered: str, term: str) -> bool:
    if " " in term or "_" in term:
        return term in lowered
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", lowered) is not None


__all__ = (
    "ALLOWED_STEP13_COVERAGE_STATUSES",
    "ALLOWED_STEP13_REDUNDANCY_STATUSES",
    "ALLOWED_STEP13_COMPLEXITY_STATUSES",
    "ALLOWED_STEP13_REGIME_FIT_STATUSES",
    "ALLOWED_STEP13_REVIEW_STATUSES",
    "STEP13_REVIEW_MATERIAL_NOTICE",
    "STEP13_REVIEW_TABLE_COLUMNS",
    "Step13ComplexityStatus",
    "Step13CoverageStatus",
    "Step13RedundancyStatus",
    "Step13RegimeFitStatus",
    "Step13ReviewBundle",
    "Step13ReviewStatus",
    "find_forbidden_step13_output_columns",
    "reject_step13_forbidden_columns",
    "validate_step13_review_bundle",
    "validate_step13_review_language",
    "validate_step13_review_table",
    "validate_step13_status_values",
)
