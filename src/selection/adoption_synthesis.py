"""Step 14 adoption synthesis engine.

This module converts Step 13 technical review recommendations into conservative
Step 14 adoption synthesis material. It does not calculate rankings, composite
scores, trading outputs, future returns, backtests, or valuation/fundamental
judgments.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from enum import Enum
import re
from typing import Any

import numpy as np
import pandas as pd

from src.scores.schema import find_valuation_fundamental_columns, require_columns

try:
    from .adoption_synthesis_contracts import (
        ALLOWED_STEP14_ADOPTION_STATES as CONTRACT_ALLOWED_STEP14_ADOPTION_STATES,
        STEP14_ADOPTION_SYNTHESIS_COLUMNS as CONTRACT_STEP14_ADOPTION_SYNTHESIS_COLUMNS,
        STEP14_ADOPTION_SYNTHESIS_NOTICE as CONTRACT_STEP14_ADOPTION_SYNTHESIS_NOTICE,
        STEP14_OPTIONAL_ADOPTION_SYNTHESIS_COLUMNS as CONTRACT_OPTIONAL_STEP14_COLUMNS,
        STEP14_REQUIRED_ADOPTION_SYNTHESIS_COLUMNS as CONTRACT_REQUIRED_STEP14_COLUMNS,
        find_forbidden_adoption_columns as contract_find_forbidden_adoption_columns,
        validate_adoption_synthesis_table as contract_validate_adoption_synthesis_table,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - exercised when Worker A is not present.
    if exc.name not in {
        "src.selection.adoption_synthesis_contracts",
        "selection.adoption_synthesis_contracts",
        "adoption_synthesis_contracts",
    }:
        raise
    CONTRACT_ALLOWED_STEP14_ADOPTION_STATES = None
    CONTRACT_STEP14_ADOPTION_SYNTHESIS_COLUMNS = None
    CONTRACT_STEP14_ADOPTION_SYNTHESIS_NOTICE = None
    CONTRACT_OPTIONAL_STEP14_COLUMNS = ()
    CONTRACT_REQUIRED_STEP14_COLUMNS = None
    contract_find_forbidden_adoption_columns = None
    contract_validate_adoption_synthesis_table = None


STEP14_CONTRACT_NOTICE = CONTRACT_STEP14_ADOPTION_SYNTHESIS_NOTICE or "adoption synthesis material only"
STEP14_ADOPTION_MATERIAL_NOTICE = STEP14_CONTRACT_NOTICE

FALLBACK_REQUIRED_STEP14_COLUMNS: tuple[str, ...] = (
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
FALLBACK_OPTIONAL_STEP14_COLUMNS: tuple[str, ...] = (
    "normalized_score_column",
    "score_input_column",
    "coverage_status",
    "redundancy_status",
    "complexity_status",
    "regime_fit_status",
    "downstream_usage_note",
)

STEP14_REQUIRED_ADOPTION_TABLE_COLUMNS: tuple[str, ...] = (
    CONTRACT_REQUIRED_STEP14_COLUMNS or FALLBACK_REQUIRED_STEP14_COLUMNS
)
STEP14_OPTIONAL_ADOPTION_TABLE_COLUMNS: tuple[str, ...] = tuple(
    CONTRACT_OPTIONAL_STEP14_COLUMNS or FALLBACK_OPTIONAL_STEP14_COLUMNS
)
STEP14_ADOPTION_TABLE_COLUMNS: tuple[str, ...] = tuple(
    CONTRACT_STEP14_ADOPTION_SYNTHESIS_COLUMNS
    or (*FALLBACK_REQUIRED_STEP14_COLUMNS, *FALLBACK_OPTIONAL_STEP14_COLUMNS)
)

STEP14_INPUT_REQUIRED_COLUMNS: tuple[str, ...] = (
    "score_name",
    "family",
    "branch",
    "role",
    "eligibility",
    "review_status",
    "evidence_sources",
    "manual_review_required",
)


class AdoptionState(str, Enum):
    """Step 14 synthesis states, not downstream ranking or trading decisions."""

    CORE_ADOPTED = "core_adopted"
    CONDITIONAL_ADOPTED = "conditional_adopted"
    TECHNICAL_ONLY = "technical_only"
    REGIME_ONLY = "regime_only"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    RESEARCH_ONLY = "research_only"
    REJECTED = "rejected"
    BLOCKED_BY_DATA = "blocked_by_data"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


ALLOWED_STEP14_ADOPTION_STATES = frozenset(
    CONTRACT_ALLOWED_STEP14_ADOPTION_STATES or frozenset(state.value for state in AdoptionState)
)

STEP14_FORBIDDEN_EXACT_COLUMNS = frozenset(
    {
        "rank",
        "ranking",
        "latest_rank",
        "latest_ranking",
        "score_rank",
        "score_ranking",
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
        "buy_signal",
        "sell_signal",
        "valuation_score",
        "fundamental_score",
        "undervalued",
        "cheap",
        "bargain",
        "target_price",
        "expected_return",
        "position_size",
        "recommendation",
        "review_status",
        "selected_score",
        "selected_for_composite",
    }
)
STEP14_FORBIDDEN_PREFIXES = (
    "rank_",
    "ranking_",
    "latest_rank",
    "score_rank",
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

STEP14_FORBIDDEN_LANGUAGE_TERMS = frozenset(
    {
        "rank",
        "ranking",
        "latest rank",
        "latest_rank",
        "latest ranking",
        "latest_ranking",
        "technical_composite_score",
        "final_composite_score",
        "composite score",
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
    }
)

STEP14_ALLOWED_BOUNDARY_PHRASES = (
    "not ranking, not composite score, not backtest, not trading signal, and not valuation",
)

STEP14_TEXT_COLUMNS = ("adoption_reason", "evidence_sources", "limitations")
STEP14_OPTIONAL_TEXT_COLUMNS = ("downstream_usage_note",)

BLOCKING_COVERAGE_STATUSES = frozenset(
    {
        "blocked_by_data",
        "insufficient_input",
        "insufficient_data",
        "config_missing",
    }
)
BLOCKING_REDUNDANCY_STATUSES = frozenset(
    {
        "config_missing",
        "insufficient_input",
        "insufficient_data",
    }
)
UNCLEAR_REDUNDANCY_STATUSES = frozenset(
    {
        "undefined_correlation",
        "unknown",
    }
)
SEVERE_REDUNDANCY_STATUSES = frozenset(
    {
        "severe_redundancy",
        "block_candidate",
    }
)
ACCEPTABLE_COVERAGE_STATUSES = frozenset({"ok"})
ACCEPTABLE_REDUNDANCY_STATUSES = frozenset({"ok"})
CONTEXT_ROLES = frozenset({"setup_context", "confirmation"})
DIAGNOSTIC_ROLES = frozenset({"diagnostic_context"})


def synthesize_adoption_states(
    review_rows: pd.DataFrame | Iterable[Mapping[str, Any] | object],
) -> pd.DataFrame:
    """Convert Step 13 review rows into Step 14 adoption synthesis rows.

    Input order is preserved. The returned table is not sorted by quality,
    strength, return, or any other ranking-shaped concept.
    """

    return build_adoption_synthesis_table(review_rows)


def synthesize_adoption_from_review_rows(
    review_rows: pd.DataFrame | Iterable[Mapping[str, Any] | object],
) -> pd.DataFrame:
    """Alias for callers that name the Step 13 source explicitly."""

    return build_adoption_synthesis_table(review_rows)


def build_adoption_synthesis_table(
    review_rows: pd.DataFrame | Iterable[Mapping[str, Any] | object],
) -> pd.DataFrame:
    """Build a Step 14 adoption synthesis table from Step 13 review material."""

    review_frame = _coerce_review_rows_to_frame(review_rows)
    require_columns(
        review_frame,
        STEP14_INPUT_REQUIRED_COLUMNS,
        context="Step 14 adoption synthesis input",
    )
    _reject_step14_forbidden_input_columns(review_frame, context="Step 14 adoption synthesis input")

    rows = [_build_adoption_row(row) for _, row in review_frame.iterrows()]
    output = pd.DataFrame(rows, columns=STEP14_ADOPTION_TABLE_COLUMNS)
    validate_step14_adoption_table(output)
    return output


def build_step14_adoption_bundle(
    review_rows: pd.DataFrame | Iterable[Mapping[str, Any] | object],
) -> dict[str, pd.DataFrame]:
    """Build Step 14 adoption rows plus compact state-count material."""

    adoption_table = build_adoption_synthesis_table(review_rows)
    state_counts = _count_frame(adoption_table, "adoption_state", "score_count")
    manual_review_counts = _count_frame(
        adoption_table,
        "manual_review_required",
        "score_count",
    )
    return {
        "adoption_table": adoption_table,
        "state_counts": state_counts,
        "manual_review_counts": manual_review_counts,
    }


def find_forbidden_step14_output_columns(columns: Iterable[str]) -> list[str]:
    """Return columns that cross Step 14 hard-stop boundaries."""

    if contract_find_forbidden_adoption_columns is not None:
        return contract_find_forbidden_adoption_columns(columns)

    forbidden: list[str] = []
    for column in columns:
        normalized = str(column).lower()
        tokens = set(normalized.split("_"))
        if (
            normalized in STEP14_FORBIDDEN_EXACT_COLUMNS
            or normalized.startswith(STEP14_FORBIDDEN_PREFIXES)
            or normalized.endswith(STEP14_FORBIDDEN_SUFFIXES)
            or any(substring in normalized for substring in STEP14_FORBIDDEN_SUBSTRINGS)
            or bool(tokens.intersection(STEP14_FORBIDDEN_COLUMN_TOKENS))
        ):
            forbidden.append(str(column))
    valuation_columns = find_valuation_fundamental_columns(columns)
    return sorted(set(forbidden).union(valuation_columns))


def reject_step14_forbidden_columns(
    frame: pd.DataFrame,
    *,
    context: str = "Step 14 adoption synthesis output",
) -> None:
    """Reject columns that imply ranking, composite, backtest, trading, or valuation output."""

    forbidden = find_forbidden_step14_output_columns(frame.columns)
    if forbidden:
        raise ValueError(
            f"{context} contains forbidden Step 14 output columns: "
            f"{', '.join(forbidden)}"
        )


def _reject_step14_forbidden_input_columns(
    frame: pd.DataFrame,
    *,
    context: str,
) -> None:
    """Reject hard-stop columns in Step 13 source material while allowing review_status input."""

    forbidden = [
        column
        for column in find_forbidden_step14_output_columns(frame.columns)
        if column != "review_status"
    ]
    if forbidden:
        raise ValueError(
            f"{context} contains forbidden Step 14 output columns: "
            f"{', '.join(forbidden)}"
        )


def validate_step14_adoption_table(
    frame: pd.DataFrame,
    *,
    context: str = "Step 14 adoption synthesis table",
) -> None:
    """Validate Step 14 synthesis rows without making downstream decisions."""

    require_columns(frame, STEP14_REQUIRED_ADOPTION_TABLE_COLUMNS, context=context)
    reject_step14_forbidden_columns(frame, context=context)
    invalid_states = sorted(
        set(frame["adoption_state"].astype("string")).difference(ALLOWED_STEP14_ADOPTION_STATES)
    )
    if invalid_states:
        raise ValueError(
            f"{context} contains unsupported adoption_state values: "
            f"{', '.join(invalid_states)}"
        )
    _assert_manual_review_required_is_boolean(frame, context=context)
    _assert_text_columns_non_empty(frame, context=context)
    _assert_text_columns_avoid_forbidden_language(frame, context=context)
    if contract_validate_adoption_synthesis_table is not None:
        contract_validate_adoption_synthesis_table(frame, require_all_scores=False, context=context)


def validate_step14_adoption_language(
    text: str,
    *,
    context: str = "Step 14 adoption synthesis material",
    require_notice: bool = True,
) -> None:
    """Reject narrative that crosses Step 14 hard-stop language boundaries."""

    lowered = text.lower()
    if require_notice and STEP14_ADOPTION_MATERIAL_NOTICE not in lowered:
        raise ValueError(f"{context} must include: {STEP14_ADOPTION_MATERIAL_NOTICE}")
    screened = _strip_allowed_boundary_phrases(lowered)
    violations = [
        term
        for term in sorted(STEP14_FORBIDDEN_LANGUAGE_TERMS)
        if _contains_forbidden_term(screened, term)
    ]
    if violations:
        raise ValueError(f"{context} contains forbidden Step 14 language: {', '.join(violations)}")


def _build_adoption_row(row: pd.Series) -> dict[str, object]:
    state, reason, limitations, manual_review_required = _classify_adoption_state(row)
    validate_step14_adoption_language(reason, context="Step 14 adoption_reason", require_notice=False)
    validate_step14_adoption_language(limitations, context="Step 14 limitations", require_notice=False)
    validate_step14_adoption_language(
        str(row["evidence_sources"]),
        context="Step 14 evidence_sources",
        require_notice=False,
    )
    return {
        "score_name": str(row["score_name"]),
        "family": str(row["family"]),
        "branch": str(row["branch"]),
        "role": str(row["role"]),
        "eligibility": str(row["eligibility"]),
        "source_review_status": _status_value(row["review_status"]),
        "adoption_state": state.value,
        "adoption_reason": reason,
        "evidence_sources": str(row["evidence_sources"]),
        "limitations": limitations,
        "manual_review_required": manual_review_required,
        "normalized_score_column": _optional_string(row, "normalized_score_column"),
        "score_input_column": _optional_string(row, "score_input_column"),
        "coverage_status": _optional_string(row, "coverage_status"),
        "redundancy_status": _optional_string(row, "redundancy_status"),
        "complexity_status": _optional_string(row, "complexity_status"),
        "regime_fit_status": _optional_string(row, "regime_fit_status"),
        "downstream_usage_note": "Step 15 may consume this row only after its own contract.",
    }


def _classify_adoption_state(row: pd.Series) -> tuple[AdoptionState, str, str, bool]:
    review_status = _status_value(row["review_status"])
    eligibility = _status_value(row["eligibility"])
    role = _status_value(row["role"])
    branch = _status_value(row["branch"])
    coverage_status = _status_value(row.get("coverage_status", "unknown"))
    redundancy_status = _status_value(row.get("redundancy_status", "unknown"))
    manual_review_input = _as_bool(row["manual_review_required"])

    if review_status == "blocked_by_data":
        return _decision(
            AdoptionState.BLOCKED_BY_DATA,
            "Step 13 review marks required input material as blocked by data.",
            "Blocked rows require upstream data repair before any later use.",
            manual_review_input,
        )
    if review_status == "needs_manual_review":
        return _decision(
            AdoptionState.NEEDS_MANUAL_REVIEW,
            "Step 13 review leaves an unresolved manual review requirement.",
            "Manual review must resolve the open issue before this row can be adopted.",
            True,
        )
    if review_status == "reject_candidate":
        return _decision(
            AdoptionState.REJECTED,
            "Step 13 review rejected the candidate on technical review grounds.",
            "Rejected rows are retained only for traceability.",
            manual_review_input,
        )
    if review_status == "research_only":
        return _decision(
            AdoptionState.RESEARCH_ONLY,
            "Step 13 review keeps the row as research material only.",
            "Additional evidence or clearer implementation support is required.",
            manual_review_input,
        )
    if review_status == "diagnostic_only":
        return _decision(
            AdoptionState.DIAGNOSTIC_ONLY,
            "Step 13 review marks the row as diagnostic material only.",
            "Diagnostic rows remain context or validation material.",
            manual_review_input,
        )
    if _is_diagnostic_only(branch=branch, eligibility=eligibility, role=role):
        return _decision(
            AdoptionState.DIAGNOSTIC_ONLY,
            "Diagnostic branch or diagnostic role prevents core adoption.",
            "Diagnostic rows remain context or validation material.",
            manual_review_input,
        )
    if manual_review_input:
        return _decision(
            AdoptionState.NEEDS_MANUAL_REVIEW,
            "Step 13 review carries an unresolved manual review requirement.",
            "Manual review must resolve the open issue before this row can be adopted.",
            True,
        )
    if coverage_status in BLOCKING_COVERAGE_STATUSES:
        return _decision(
            AdoptionState.BLOCKED_BY_DATA,
            f"Coverage status {coverage_status} blocks automatic adoption.",
            "Coverage must be repaired before this row can be adopted.",
            True,
        )
    if redundancy_status in BLOCKING_REDUNDANCY_STATUSES:
        return _decision(
            AdoptionState.BLOCKED_BY_DATA,
            f"Redundancy status {redundancy_status} blocks automatic adoption.",
            "Diagnostic input must be repaired before this row can be adopted.",
            True,
        )
    if redundancy_status in UNCLEAR_REDUNDANCY_STATUSES:
        return _decision(
            AdoptionState.NEEDS_MANUAL_REVIEW,
            f"Redundancy status {redundancy_status} leaves distinctness unresolved.",
            "Manual review must resolve the unclear redundancy result.",
            True,
        )
    if role == "setup_context":
        return _decision(
            AdoptionState.REGIME_ONLY,
            "Setup context role is kept as regime material, not core adoption.",
            "Regime-only rows can provide context but do not become core rows here.",
            False,
        )
    if role == "confirmation":
        return _decision(
            AdoptionState.CONDITIONAL_ADOPTED,
            "Confirmation role can support adoption only as conditional material.",
            "Confirmation rows need explicit downstream design before stronger use.",
            True,
        )
    if review_status == "conditional_candidate" or eligibility == "conditional":
        return _decision(
            AdoptionState.CONDITIONAL_ADOPTED,
            "Step 13 review or Step 11 eligibility is conditional.",
            "Conditional rows retain one or more unresolved technical constraints.",
            True,
        )
    if redundancy_status in SEVERE_REDUNDANCY_STATUSES:
        return _decision(
            AdoptionState.CONDITIONAL_ADOPTED,
            f"Redundancy status {redundancy_status} prevents core adoption.",
            "Redundancy must be resolved before stronger adoption can be considered.",
            True,
        )
    if review_status == "adopt_candidate":
        if _clean_core_candidate(
            eligibility=eligibility,
            role=role,
            coverage_status=coverage_status,
            redundancy_status=redundancy_status,
        ):
            return _decision(
                AdoptionState.CORE_ADOPTED,
                "Eligible technical candidate has acceptable coverage and no blocking review flags.",
                "This is Step 14 synthesis material only and assigns no downstream weight.",
                False,
            )
        return _decision(
            AdoptionState.CONDITIONAL_ADOPTED,
            "Adopt candidate is downgraded because at least one core condition is not clean.",
            "The unresolved condition must be reviewed before stronger adoption.",
            True,
        )
    return _decision(
        AdoptionState.NEEDS_MANUAL_REVIEW,
        f"Unrecognized or unsupported Step 13 review status {review_status} requires review.",
        "Unknown statuses are not interpreted optimistically.",
        True,
    )


def _decision(
    state: AdoptionState,
    reason: str,
    limitations: str,
    manual_review_required: bool,
) -> tuple[AdoptionState, str, str, bool]:
    return state, reason, limitations, bool(manual_review_required)


def _clean_core_candidate(
    *,
    eligibility: str,
    role: str,
    coverage_status: str,
    redundancy_status: str,
) -> bool:
    return (
        eligibility == "eligible"
        and role not in CONTEXT_ROLES
        and role not in DIAGNOSTIC_ROLES
        and coverage_status in ACCEPTABLE_COVERAGE_STATUSES
        and redundancy_status in ACCEPTABLE_REDUNDANCY_STATUSES
    )


def _is_diagnostic_only(*, branch: str, eligibility: str, role: str) -> bool:
    return branch == "diagnostic" or eligibility == "diagnostic_only" or role in DIAGNOSTIC_ROLES


def _coerce_review_rows_to_frame(
    review_rows: pd.DataFrame | Iterable[Mapping[str, Any] | object],
) -> pd.DataFrame:
    if isinstance(review_rows, pd.DataFrame):
        return review_rows.copy()
    return pd.DataFrame([_row_to_mapping(row) for row in review_rows])


def _row_to_mapping(row: Mapping[str, Any] | object) -> Mapping[str, Any]:
    if isinstance(row, Mapping):
        return row
    if isinstance(row, pd.Series):
        return row.to_dict()
    if hasattr(row, "_asdict"):
        return row._asdict()
    if hasattr(row, "__dict__"):
        return vars(row)
    try:
        return dict(row)  # type: ignore[arg-type]
    except TypeError as exc:
        raise TypeError("Step 14 review rows must be mapping-like or row objects.") from exc


def _status_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    if pd.isna(value):
        return "unknown"
    return str(value).strip()


def _optional_string(row: pd.Series, column: str) -> str:
    if column not in row:
        return ""
    value = row[column]
    if pd.isna(value):
        return ""
    return str(value)


def _as_bool(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    raise ValueError("Step 14 manual_review_required values must be boolean.")


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


def _assert_text_columns_non_empty(frame: pd.DataFrame, *, context: str) -> None:
    for column in STEP14_TEXT_COLUMNS:
        present = _non_empty_string_mask(frame[column])
        if not present.all():
            score_names = ", ".join(frame.loc[~present, "score_name"].astype("string"))
            raise ValueError(f"{context} {column} must be non-empty for: {score_names}")


def _assert_text_columns_avoid_forbidden_language(frame: pd.DataFrame, *, context: str) -> None:
    for column in (*STEP14_TEXT_COLUMNS, *STEP14_OPTIONAL_TEXT_COLUMNS):
        if column not in frame.columns:
            continue
        for value in frame[column].dropna().tolist():
            validate_step14_adoption_language(
                str(value),
                context=f"{context} {column}",
                require_notice=False,
            )


def _non_empty_string_mask(series: pd.Series) -> pd.Series:
    text = series.astype("string")
    return (text.notna() & text.str.strip().ne("")).fillna(False)


def _strip_allowed_boundary_phrases(lowered: str) -> str:
    screened = lowered
    for phrase in STEP14_ALLOWED_BOUNDARY_PHRASES:
        screened = screened.replace(phrase, "")
    return screened


def _contains_forbidden_term(lowered: str, term: str) -> bool:
    if " " in term or "_" in term:
        return term in lowered
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", lowered) is not None


def _count_frame(frame: pd.DataFrame, column: str, count_column: str) -> pd.DataFrame:
    counts = frame[column].value_counts().sort_index()
    return counts.rename_axis(column).reset_index(name=count_column)


__all__ = (
    "ALLOWED_STEP14_ADOPTION_STATES",
    "STEP14_ADOPTION_MATERIAL_NOTICE",
    "STEP14_ADOPTION_TABLE_COLUMNS",
    "STEP14_FORBIDDEN_LANGUAGE_TERMS",
    "AdoptionState",
    "build_adoption_synthesis_table",
    "build_step14_adoption_bundle",
    "find_forbidden_step14_output_columns",
    "reject_step14_forbidden_columns",
    "synthesize_adoption_from_review_rows",
    "synthesize_adoption_states",
    "validate_step14_adoption_language",
    "validate_step14_adoption_table",
)
