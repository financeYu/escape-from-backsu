"""Step 14 adoption synthesis contracts and guardrails.

This module fixes the schema for Adoption Synthesis rows. It does not create
rankings, calculate composite scores, emit trading decisions, run backtests, or
use valuation/fundamental data.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum
import re

import numpy as np
import pandas as pd

from src.composite.contracts import (
    DEFAULT_COMPOSITE_INPUT_REGISTRY,
    MVP_SCORE_NAMES,
    CompositeInputSpec,
)
from src.scores.schema import find_missing_columns, find_valuation_fundamental_columns
from src.selection.technical_selection_contracts import (
    ALLOWED_STEP13_COMPLEXITY_STATUSES,
    ALLOWED_STEP13_COVERAGE_STATUSES,
    ALLOWED_STEP13_ELIGIBILITY,
    ALLOWED_STEP13_FAMILIES,
    ALLOWED_STEP13_REDUNDANCY_STATUSES,
    ALLOWED_STEP13_REGIME_FIT_STATUSES,
    ALLOWED_STEP13_REVIEW_STATUSES,
    ALLOWED_STEP13_ROLES,
)


STEP14_ADOPTION_SYNTHESIS_NOTICE = "adoption synthesis material only"

STEP14_REQUIRED_ADOPTION_SYNTHESIS_COLUMNS: tuple[str, ...] = (
    "score_name",
    "family",
    "branch",
    "role",
    "eligibility",
    "source_review_status",
    "adoption_state",
    "adoption_reason",
    "evidence_sources",
    "limitations",
    "manual_review_required",
)

STEP14_OPTIONAL_ADOPTION_SYNTHESIS_COLUMNS: tuple[str, ...] = (
    "normalized_score_column",
    "score_input_column",
    "coverage_status",
    "redundancy_status",
    "complexity_status",
    "regime_fit_status",
    "downstream_usage_note",
)

STEP14_ADOPTION_SYNTHESIS_COLUMNS: tuple[str, ...] = (
    *STEP14_REQUIRED_ADOPTION_SYNTHESIS_COLUMNS,
    *STEP14_OPTIONAL_ADOPTION_SYNTHESIS_COLUMNS,
)


class Step14AdoptionState(str, Enum):
    """Step 14 synthesis states, not ranking buckets or trading decisions."""

    CORE_ADOPTED = "core_adopted"
    CONDITIONAL_ADOPTED = "conditional_adopted"
    TECHNICAL_ONLY = "technical_only"
    REGIME_ONLY = "regime_only"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    RESEARCH_ONLY = "research_only"
    REJECTED = "rejected"
    BLOCKED_BY_DATA = "blocked_by_data"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


ALLOWED_STEP14_ADOPTION_STATES = frozenset(state.value for state in Step14AdoptionState)

STEP14_FORBIDDEN_EXACT_COLUMNS = frozenset(
    {
        "rank",
        "ranking",
        "latest_rank",
        "latest_ranking",
        "technical_composite_score",
        "final_composite_score",
        "composite_score",
        "family_weighted_composite",
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
        "buy_signal",
        "sell_signal",
        "trading_signal",
        "valuation_score",
        "fundamental_score",
        "undervalued",
        "cheap",
        "bargain",
        "target_price",
        "expected_return",
        "position_size",
        "review_status",
        "adoption_decision",
        "final_adoption_status",
        "final_adoption_decision",
        "selected_score",
        "selected_for_composite",
    }
)

STEP14_FORBIDDEN_OUTPUT_COLUMNS = STEP14_FORBIDDEN_EXACT_COLUMNS

STEP14_FORBIDDEN_PREFIXES = (
    "rank_",
    "ranking_",
    "latest_rank",
    "latest_ranking",
    "technical_composite",
    "final_composite",
    "family_weighted",
    "forward_return",
    "future_return",
    "next_return",
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
)

STEP14_FORBIDDEN_SUFFIXES = (
    "_rank",
    "_ranking",
    "_signal",
    "_alpha",
    "_target_price",
    "_expected_return",
    "_position_size",
)

STEP14_FORBIDDEN_SUBSTRINGS = (
    "technical_composite_score",
    "technical_composite",
    "final_composite_score",
    "final_composite",
    "family_weighted_composite",
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

STEP14_FORBIDDEN_COLUMN_TOKENS = frozenset(
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

STEP14_FORBIDDEN_REPORT_LANGUAGE = frozenset(
    {
        "alpha evidence",
        "buy signal",
        "sell signal",
        "trading signal",
        "expected return",
        "expected_return",
        "future return",
        "future_return",
        "forward return",
        "forward_return",
        "backtest proves",
        "undervalued",
        "cheap",
        "bargain",
        "value stock",
        "target price",
        "target_price",
        "position size",
        "position_size",
        "latest ranking",
        "latest_ranking",
        "latest rank",
        "latest_rank",
        "technical_composite_score",
        "final_composite_score",
        "valuation_score",
        "실전 매수 후보",
        "수익률 보장",
        "최종 랭킹",
        "최종 채택 확정",
    }
)

STEP14_TEXT_COLUMNS = (
    "adoption_reason",
    "evidence_sources",
    "limitations",
    "downstream_usage_note",
)

CONSERVATIVE_STEP14_STATE_BY_SOURCE_REVIEW_STATUS: Mapping[str, frozenset[str]] = {
    "adopt_candidate": frozenset(ALLOWED_STEP14_ADOPTION_STATES),
    "conditional_candidate": frozenset(
        {
            Step14AdoptionState.CONDITIONAL_ADOPTED.value,
            Step14AdoptionState.TECHNICAL_ONLY.value,
            Step14AdoptionState.REGIME_ONLY.value,
            Step14AdoptionState.DIAGNOSTIC_ONLY.value,
            Step14AdoptionState.RESEARCH_ONLY.value,
            Step14AdoptionState.REJECTED.value,
            Step14AdoptionState.BLOCKED_BY_DATA.value,
            Step14AdoptionState.NEEDS_MANUAL_REVIEW.value,
        }
    ),
    "research_only": frozenset(
        {
            Step14AdoptionState.RESEARCH_ONLY.value,
            Step14AdoptionState.REJECTED.value,
            Step14AdoptionState.BLOCKED_BY_DATA.value,
            Step14AdoptionState.NEEDS_MANUAL_REVIEW.value,
        }
    ),
    "diagnostic_only": frozenset(
        {
            Step14AdoptionState.DIAGNOSTIC_ONLY.value,
            Step14AdoptionState.REGIME_ONLY.value,
            Step14AdoptionState.REJECTED.value,
            Step14AdoptionState.BLOCKED_BY_DATA.value,
            Step14AdoptionState.NEEDS_MANUAL_REVIEW.value,
        }
    ),
    "reject_candidate": frozenset(
        {
            Step14AdoptionState.REJECTED.value,
            Step14AdoptionState.NEEDS_MANUAL_REVIEW.value,
        }
    ),
    "blocked_by_data": frozenset(
        {
            Step14AdoptionState.BLOCKED_BY_DATA.value,
            Step14AdoptionState.REJECTED.value,
            Step14AdoptionState.NEEDS_MANUAL_REVIEW.value,
        }
    ),
    "needs_manual_review": frozenset(
        {
            Step14AdoptionState.NEEDS_MANUAL_REVIEW.value,
            Step14AdoptionState.BLOCKED_BY_DATA.value,
            Step14AdoptionState.REJECTED.value,
        }
    ),
}


@dataclass(frozen=True)
class Step14AdoptionSynthesisRow:
    """A single Step 14 adoption synthesis row.

    The row preserves Step 13 as source review material through
    `source_review_status`; `adoption_state` is the separate Step 14 synthesis
    result.
    """

    score_name: str
    family: str
    branch: str
    role: str
    eligibility: str
    source_review_status: str
    adoption_state: str
    adoption_reason: str
    evidence_sources: tuple[str, ...]
    limitations: tuple[str, ...]
    manual_review_required: bool
    normalized_score_column: str = ""
    score_input_column: str = ""
    coverage_status: str = ""
    redundancy_status: str = ""
    complexity_status: str = ""
    regime_fit_status: str = ""
    downstream_usage_note: str = ""
    schema_columns: tuple[str, ...] = field(
        default=STEP14_ADOPTION_SYNTHESIS_COLUMNS,
        init=False,
        repr=False,
        compare=False,
    )


def validate_adoption_state(
    adoption_state: Step14AdoptionState | str,
    *,
    context: str = "Step 14 adoption_state",
) -> str:
    """Validate one Step 14 adoption state and return its string value."""

    value = _enum_or_string_value(adoption_state)
    if value not in ALLOWED_STEP14_ADOPTION_STATES:
        raise ValueError(f"{context} contains unsupported adoption_state value: {value}")
    return value


def validate_adoption_synthesis_columns(
    columns: pd.DataFrame | Iterable[str],
    *,
    context: str = "Step 14 adoption synthesis output",
) -> None:
    """Validate required Step 14 output columns and hard-stop boundaries."""

    column_names = _column_names(columns)
    missing = find_missing_columns(column_names, STEP14_REQUIRED_ADOPTION_SYNTHESIS_COLUMNS)
    if missing:
        raise ValueError(f"{context} missing required columns: {', '.join(missing)}")
    assert_no_forbidden_adoption_columns(column_names, context=context)


def validate_adoption_synthesis_table(
    frame: pd.DataFrame,
    *,
    registry: Iterable[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
    require_all_scores: bool = False,
    context: str = "Step 14 adoption synthesis table",
) -> None:
    """Validate a Step 14 adoption synthesis table without ranking or scoring."""

    validate_adoption_synthesis_columns(frame, context=context)
    _assert_adoption_value_domains(frame, context=context)
    _assert_required_fields_non_empty(frame, context=context)
    _assert_manual_review_required_is_boolean(frame, context=context)
    _assert_needs_manual_review_is_marked(frame, context=context)
    _assert_known_unique_score_names(
        frame,
        registry=tuple(registry),
        require_all_scores=require_all_scores,
        context=context,
    )
    _assert_registry_metadata_alignment(frame, registry=tuple(registry), context=context)
    _assert_conservative_source_status_mapping(frame, context=context)
    _assert_text_columns_avoid_forbidden_adoption_language(frame, context=context)


def _assert_adoption_value_domains(frame: pd.DataFrame, *, context: str) -> None:
    required_domains = (
        ("family", ALLOWED_STEP13_FAMILIES),
        ("role", ALLOWED_STEP13_ROLES),
        ("eligibility", ALLOWED_STEP13_ELIGIBILITY),
        ("source_review_status", ALLOWED_STEP13_REVIEW_STATUSES),
        ("adoption_state", ALLOWED_STEP14_ADOPTION_STATES),
    )
    optional_domains = (
        ("coverage_status", ALLOWED_STEP13_COVERAGE_STATUSES),
        ("redundancy_status", ALLOWED_STEP13_REDUNDANCY_STATUSES),
        ("complexity_status", ALLOWED_STEP13_COMPLEXITY_STATUSES),
        ("regime_fit_status", ALLOWED_STEP13_REGIME_FIT_STATUSES),
    )
    for column, allowed in required_domains:
        _assert_allowed_values(frame, column, allowed, context=context)
    for column, allowed in optional_domains:
        _assert_optional_allowed_values(frame, column, allowed, context=context)


def find_forbidden_adoption_columns(columns: pd.DataFrame | Iterable[str]) -> list[str]:
    """Return Step 14 columns that imply ranking, scoring, trading, or valuation."""

    forbidden: list[str] = []
    for column in _column_names(columns):
        normalized = column.lower()
        tokens = set(normalized.split("_"))
        if (
            normalized in STEP14_FORBIDDEN_EXACT_COLUMNS
            or normalized.startswith(STEP14_FORBIDDEN_PREFIXES)
            or normalized.endswith(STEP14_FORBIDDEN_SUFFIXES)
            or any(substring in normalized for substring in STEP14_FORBIDDEN_SUBSTRINGS)
            or bool(tokens.intersection(STEP14_FORBIDDEN_COLUMN_TOKENS))
        ):
            forbidden.append(column)
    valuation_columns = find_valuation_fundamental_columns(_column_names(columns))
    return sorted(set(forbidden).union(valuation_columns))


def assert_no_forbidden_adoption_columns(
    columns: pd.DataFrame | Iterable[str],
    *,
    context: str = "Step 14 adoption synthesis output",
) -> None:
    """Reject Step 14 output columns that cross roadmap hard stops."""

    forbidden = find_forbidden_adoption_columns(columns)
    if forbidden:
        raise ValueError(
            f"{context} contains forbidden Step 14 adoption columns: "
            f"{', '.join(forbidden)}"
        )


def find_forbidden_adoption_language(text: str) -> list[str]:
    """Return forbidden generated-report phrases found in text."""

    lowered = text.lower()
    return [
        term
        for term in sorted(STEP14_FORBIDDEN_REPORT_LANGUAGE)
        if _contains_forbidden_term(lowered, term.lower())
    ]


def assert_no_forbidden_adoption_language(
    text: str,
    *,
    context: str = "Step 14 adoption synthesis report",
) -> None:
    """Reject Step 14 generated narrative that crosses roadmap boundaries."""

    violations = find_forbidden_adoption_language(text)
    if violations:
        raise ValueError(
            f"{context} contains forbidden Step 14 adoption language: "
            f"{', '.join(violations)}"
        )


def validate_adoption_report_text(
    text: str,
    *,
    context: str = "Step 14 adoption synthesis report",
    require_notice: bool = False,
) -> None:
    """Validate generated Step 14 narrative text."""

    assert_no_forbidden_adoption_language(text, context=context)
    if require_notice and STEP14_ADOPTION_SYNTHESIS_NOTICE not in text.lower():
        raise ValueError(f"{context} must include: {STEP14_ADOPTION_SYNTHESIS_NOTICE}")


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


def _assert_optional_allowed_values(
    frame: pd.DataFrame,
    column: str,
    allowed: frozenset[str],
    *,
    context: str,
) -> None:
    if column not in frame.columns:
        return
    values = frame[column]
    present = values.map(_is_non_empty_required_value)
    if not present.any():
        return
    invalid = sorted(set(values[present].astype("string")).difference(allowed))
    if invalid:
        raise ValueError(f"{context} contains unsupported {column} values: {', '.join(invalid)}")


def _assert_required_fields_non_empty(frame: pd.DataFrame, *, context: str) -> None:
    for column in STEP14_REQUIRED_ADOPTION_SYNTHESIS_COLUMNS:
        if column == "manual_review_required":
            continue
        present = frame[column].map(_is_non_empty_required_value)
        if not present.all():
            score_names = ", ".join(frame.loc[~present, "score_name"].astype("string"))
            raise ValueError(f"{context} {column} must be non-empty for: {score_names}")


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
    mask = frame["adoption_state"].eq(Step14AdoptionState.NEEDS_MANUAL_REVIEW.value)
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


def _assert_conservative_source_status_mapping(frame: pd.DataFrame, *, context: str) -> None:
    violations: list[str] = []
    for _, row in frame.iterrows():
        source_review_status = str(row["source_review_status"])
        adoption_state = str(row["adoption_state"])
        allowed = CONSERVATIVE_STEP14_STATE_BY_SOURCE_REVIEW_STATUS[source_review_status]
        if adoption_state not in allowed:
            violations.append(
                f"{row['score_name']}: {source_review_status} -> {adoption_state}"
            )
    if violations:
        raise ValueError(
            f"{context} contains unsupported source_review_status to adoption_state "
            f"promotion: {', '.join(violations)}"
        )


def _assert_text_columns_avoid_forbidden_adoption_language(
    frame: pd.DataFrame,
    *,
    context: str,
) -> None:
    text_parts: list[str] = []
    for column in STEP14_TEXT_COLUMNS:
        if column not in frame.columns:
            continue
        text_parts.extend(_stringify_text_value(value) for value in frame[column].dropna().tolist())
    assert_no_forbidden_adoption_language("\n".join(text_parts), context=context)


def _column_names(columns: pd.DataFrame | Iterable[str]) -> tuple[str, ...]:
    if isinstance(columns, pd.DataFrame):
        return tuple(str(column) for column in columns.columns)
    return tuple(str(column) for column in columns)


def _enum_or_string_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _is_non_empty_required_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set, frozenset)):
        return bool(value) and any(_is_non_empty_required_value(item) for item in value)
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return True
    if isinstance(missing, (bool, np.bool_)):
        return not bool(missing)
    return True


def _stringify_text_value(value: object) -> str:
    if isinstance(value, (list, tuple, set, frozenset)):
        return " ".join(str(item) for item in value)
    return str(value)


def _contains_forbidden_term(lowered: str, term: str) -> bool:
    if any(separator in term for separator in (" ", "_")) or re.search(r"[^\x00-\x7F]", term):
        return term in lowered
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", lowered) is not None


__all__ = (
    "ALLOWED_STEP14_ADOPTION_STATES",
    "CONSERVATIVE_STEP14_STATE_BY_SOURCE_REVIEW_STATUS",
    "STEP14_ADOPTION_SYNTHESIS_COLUMNS",
    "STEP14_ADOPTION_SYNTHESIS_NOTICE",
    "STEP14_FORBIDDEN_EXACT_COLUMNS",
    "STEP14_FORBIDDEN_OUTPUT_COLUMNS",
    "STEP14_FORBIDDEN_REPORT_LANGUAGE",
    "STEP14_OPTIONAL_ADOPTION_SYNTHESIS_COLUMNS",
    "STEP14_REQUIRED_ADOPTION_SYNTHESIS_COLUMNS",
    "Step14AdoptionState",
    "Step14AdoptionSynthesisRow",
    "assert_no_forbidden_adoption_columns",
    "assert_no_forbidden_adoption_language",
    "find_forbidden_adoption_columns",
    "find_forbidden_adoption_language",
    "validate_adoption_report_text",
    "validate_adoption_state",
    "validate_adoption_synthesis_columns",
    "validate_adoption_synthesis_table",
)
