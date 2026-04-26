"""Shared Step 9 score output schema guardrails.

These helpers validate raw Research Tester score frames. They intentionally do
not normalize scores, create rankings, build composites, or run backtests.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from src.common_guardrails import (
    COMMON_FORBIDDEN_OUTPUT_COLUMNS,
    FORBIDDEN_VALUATION_INPUT_COLUMNS,
    FORBIDDEN_VALUATION_INPUT_PREFIXES,
    NORMALIZED_SCORE_OUTPUT_COLUMNS,
)


IDENTITY_COLUMNS = ("ticker", "date")
SCORE_METADATA_COLUMNS = (
    "score_warmup_state",
    "score_coverage_status",
    "score_data_quality_flag",
    "minimum_history_required",
)

FORBIDDEN_OUTPUT_COLUMNS = COMMON_FORBIDDEN_OUTPUT_COLUMNS | NORMALIZED_SCORE_OUTPUT_COLUMNS


def find_missing_columns(columns: Iterable[str], required_columns: Iterable[str]) -> list[str]:
    present = set(columns)
    return [column for column in required_columns if column not in present]


def require_columns(frame: pd.DataFrame, required_columns: Iterable[str], *, context: str) -> None:
    missing = find_missing_columns(frame.columns, required_columns)
    if missing:
        raise ValueError(f"{context} missing required columns: {', '.join(missing)}")


def find_forbidden_output_columns(columns: Iterable[str]) -> list[str]:
    forbidden: list[str] = []
    for column in columns:
        normalized = column.lower()
        if normalized in FORBIDDEN_OUTPUT_COLUMNS or normalized.endswith("_normalized"):
            forbidden.append(column)
    return forbidden


def assert_no_forbidden_output_columns(frame: pd.DataFrame, *, context: str) -> None:
    forbidden = find_forbidden_output_columns(frame.columns)
    if forbidden:
        raise ValueError(f"{context} contains forbidden output columns: {', '.join(forbidden)}")


def find_valuation_fundamental_columns(columns: Iterable[str]) -> list[str]:
    flagged: list[str] = []
    for column in columns:
        normalized = column.lower()
        if normalized in FORBIDDEN_VALUATION_INPUT_COLUMNS or normalized.startswith(
            FORBIDDEN_VALUATION_INPUT_PREFIXES
        ):
            flagged.append(column)
    return flagged


def assert_no_valuation_fundamental_columns(frame: pd.DataFrame, *, context: str) -> None:
    flagged = find_valuation_fundamental_columns(frame.columns)
    if flagged:
        raise ValueError(
            f"{context} contains valuation/fundamental columns not allowed in Step 9 "
            f"technical scoring: {', '.join(flagged)}"
        )


def validate_raw_score_output_frame(frame: pd.DataFrame, *, context: str) -> None:
    require_columns(frame, IDENTITY_COLUMNS, context=context)
    assert_no_forbidden_output_columns(frame, context=context)
    assert_no_valuation_fundamental_columns(frame, context=context)
