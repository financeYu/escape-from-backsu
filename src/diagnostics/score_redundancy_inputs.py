"""Step 12 score redundancy and correlation diagnostics.

This module computes same-date cross-sectional Spearman correlations between
normalized/component score columns. It is diagnostic review material only: it
does not create rankings, composite scores, signals, valuation fields,
forward-return labels, or backtest outputs.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY, CompositeInputSpec
from src.scores.schema import IDENTITY_COLUMNS, require_columns

from .score_redundancy_guardrails import (
    _assert_no_forbidden_step12_input_columns,
    _assert_no_valuation_fundamental_columns,
    _has_blocking_quality_flag,
)

VALID_NORMALIZED_STATUSES = frozenset({"adequate", "ok"})


@dataclass(frozen=True)
class RedundancyScoreInput:
    """One score column used by Step 12 diagnostics."""

    score_name: str
    normalized_column: str
    status_column: str | None = None
    quality_flag_column: str | None = None
    score_family: str = "unknown"
    score_role: str = "unknown"
    normalization_scope: str = "unknown"

    def __post_init__(self) -> None:
        if self.normalized_column.endswith("_raw"):
            raise ValueError(
                "Step 12 redundancy diagnostics require normalized/component "
                "score columns, not raw score columns."
            )

def score_inputs_from_registry(
    registry: Sequence[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
) -> tuple[RedundancyScoreInput, ...]:
    """Build Step 12 score inputs from the Step 11 component registry."""

    return tuple(
        RedundancyScoreInput(
            score_name=spec.score_name,
            normalized_column=spec.normalized_column,
            status_column=spec.status_column,
            quality_flag_column=spec.quality_flag_column,
            score_family=spec.family,
            score_role=spec.role.value,
            normalization_scope=spec.normalization_scope.value,
        )
        for spec in registry
    )

def score_inputs_from_columns(score_columns: Sequence[str]) -> tuple[RedundancyScoreInput, ...]:
    """Build generic Step 12 score inputs from explicit component columns."""

    return tuple(
        RedundancyScoreInput(
            score_name=_score_name_from_normalized_column(column),
            normalized_column=column,
            normalization_scope=_normalization_scope_from_column(column),
        )
        for column in score_columns
    )

def prepare_redundancy_input_frame(
    frame: pd.DataFrame,
    *,
    score_inputs: Sequence[RedundancyScoreInput],
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Validate identity and preserve ticker/date alignment for diagnostics."""

    require_columns(frame, IDENTITY_COLUMNS, context="Step 12 redundancy input")
    _assert_no_forbidden_step12_input_columns(frame)
    _assert_no_valuation_fundamental_columns(frame)

    present_score_columns = [
        score_input.normalized_column
        for score_input in score_inputs
        if score_input.normalized_column in frame.columns
    ]
    optional_metadata = [
        column
        for score_input in score_inputs
        for column in (score_input.status_column, score_input.quality_flag_column)
        if column and column in frame.columns
    ]
    selected = list(dict.fromkeys([*IDENTITY_COLUMNS, *present_score_columns, *optional_metadata]))
    prepared = frame.loc[:, selected].copy()
    prepared["ticker"] = _coerce_ticker(prepared["ticker"])
    parsed_dates = pd.to_datetime(prepared["date"], errors="coerce")
    if parsed_dates.isna().any():
        bad_count = int(parsed_dates.isna().sum())
        raise ValueError(f"Step 12 redundancy input contains {bad_count} invalid date value(s).")
    prepared["date"] = parsed_dates.dt.normalize()
    if as_of_date is not None:
        parsed_as_of = pd.Timestamp(as_of_date).normalize()
        if prepared["date"].gt(parsed_as_of).any():
            raise ValueError("Step 12 redundancy input contains dates after as_of_date.")
    duplicate_mask = prepared.duplicated(list(IDENTITY_COLUMNS), keep=False)
    if duplicate_mask.any():
        duplicates = prepared.loc[duplicate_mask, list(IDENTITY_COLUMNS)]
        preview = duplicates.head(5).to_dict(orient="records")
        raise ValueError(f"Duplicate ticker/date rows are not allowed: {preview}")
    return prepared.sort_values(["date", "ticker"]).reset_index(drop=True)

def _resolve_score_inputs(
    score_inputs: Sequence[RedundancyScoreInput] | None,
    score_columns: Sequence[str] | None,
) -> tuple[RedundancyScoreInput, ...]:
    if score_inputs is not None and score_columns is not None:
        raise ValueError("Provide either score_inputs or score_columns, not both.")
    if score_inputs is not None:
        return tuple(score_inputs)
    if score_columns is not None:
        return score_inputs_from_columns(score_columns)
    return score_inputs_from_registry()

def _numeric_score_values(frame: pd.DataFrame, score_input: RedundancyScoreInput) -> pd.Series:
    numeric = pd.to_numeric(frame[score_input.normalized_column], errors="coerce")
    valid = _finite_mask(numeric)
    if score_input.status_column and score_input.status_column in frame.columns:
        status = frame[score_input.status_column].astype("string").fillna("unknown")
        valid &= status.isin(VALID_NORMALIZED_STATUSES)
    if score_input.quality_flag_column and score_input.quality_flag_column in frame.columns:
        valid &= ~frame[score_input.quality_flag_column].map(_has_blocking_quality_flag)
    return numeric.where(valid)

def _missing_score_columns(
    frame: pd.DataFrame, score_inputs: Sequence[RedundancyScoreInput]
) -> tuple[str, ...]:
    return tuple(
        score_input.normalized_column
        for score_input in score_inputs
        if score_input.normalized_column not in frame.columns
    )

def _coerce_ticker(series: pd.Series) -> pd.Series:
    invalid: list[object] = []
    coerced: list[str] = []
    for value in series:
        if pd.isna(value) or not isinstance(value, str) or len(value) != 6:
            invalid.append(value)
            coerced.append("")
        else:
            coerced.append(value)
    if invalid:
        raise ValueError(
            "ticker must be a six-character string with leading zeros preserved."
        )
    return pd.Series(coerced, index=series.index, dtype="string")

def _finite_mask(series: pd.Series) -> pd.Series:
    values = np.isfinite(series.to_numpy(dtype=float, na_value=np.nan))
    return pd.Series(values, index=series.index)

def _score_name_from_normalized_column(column: str) -> str:
    if column.endswith("_cross_sectional_robust_z"):
        return column[: -len("_cross_sectional_robust_z")]
    if column.endswith("_ts_robust_zscore"):
        return column[: -len("_ts_robust_zscore")]
    return column

def _normalization_scope_from_column(column: str) -> str:
    if "_cross_sectional_" in column:
        return "cross_sectional"
    if "_ts_" in column:
        return "time_series"
    return "unknown"

__all__ = (
    "RedundancyScoreInput",
    "prepare_redundancy_input_frame",
    "score_inputs_from_columns",
    "score_inputs_from_registry",
)
