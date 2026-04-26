"""Build Step 14 adoption synthesis tables from Step 13 review rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from src.scores.schema import require_columns

from .adoption_compat import STEP14_ADOPTION_TABLE_COLUMNS
from .adoption_guardrails import (
    reject_step14_forbidden_input_columns,
    validate_step14_adoption_language,
    validate_step14_adoption_table,
)
from .adoption_rules import STEP14_INPUT_REQUIRED_COLUMNS
from .adoption_states import classify_adoption_state, status_value


def synthesize_adoption_states(
    review_rows: pd.DataFrame | Iterable[Mapping[str, Any] | object],
) -> pd.DataFrame:
    """Convert Step 13 technical review recommendations into Step 14 rows."""

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
    reject_step14_forbidden_input_columns(
        review_frame,
        context="Step 14 adoption synthesis input",
    )

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


def _build_adoption_row(row: pd.Series) -> dict[str, object]:
    state, reason, limitations, manual_review_required = classify_adoption_state(row)
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
        "source_review_status": status_value(row["review_status"]),
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


def _optional_string(row: pd.Series, column: str) -> str:
    if column not in row:
        return ""
    value = row[column]
    if pd.isna(value):
        return ""
    return str(value)


def _count_frame(frame: pd.DataFrame, column: str, count_column: str) -> pd.DataFrame:
    counts = frame[column].value_counts().sort_index()
    return counts.rename_axis(column).reset_index(name=count_column)


__all__ = (
    "build_adoption_synthesis_table",
    "build_step14_adoption_bundle",
    "synthesize_adoption_from_review_rows",
    "synthesize_adoption_states",
)
