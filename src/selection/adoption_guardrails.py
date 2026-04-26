"""Step 14 adoption synthesis column and language guardrails."""

from __future__ import annotations

from collections.abc import Iterable
import re

import numpy as np
import pandas as pd

from src.scores.schema import find_valuation_fundamental_columns, require_columns

from .adoption_compat import (
    STEP14_ADOPTION_MATERIAL_NOTICE,
    STEP14_REQUIRED_ADOPTION_TABLE_COLUMNS,
    contract_find_forbidden_adoption_columns,
    contract_validate_adoption_synthesis_table,
)
from .adoption_rules import (
    STEP14_ALLOWED_BOUNDARY_PHRASES,
    STEP14_FORBIDDEN_COLUMN_TOKENS,
    STEP14_FORBIDDEN_EXACT_COLUMNS,
    STEP14_FORBIDDEN_LANGUAGE_TERMS,
    STEP14_FORBIDDEN_PREFIXES,
    STEP14_FORBIDDEN_SUBSTRINGS,
    STEP14_FORBIDDEN_SUFFIXES,
    STEP14_OPTIONAL_TEXT_COLUMNS,
    STEP14_TEXT_COLUMNS,
)
from .adoption_states import ALLOWED_STEP14_ADOPTION_STATES


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


def reject_step14_forbidden_input_columns(
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


__all__ = (
    "STEP14_FORBIDDEN_LANGUAGE_TERMS",
    "find_forbidden_step14_output_columns",
    "reject_step14_forbidden_columns",
    "reject_step14_forbidden_input_columns",
    "validate_step14_adoption_language",
    "validate_step14_adoption_table",
)
