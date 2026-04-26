"""Step 10B normalization diagnostics.

Diagnostics are review material only. They summarize coverage, missingness,
warmup state, quality flags, and cross-sectional normalization events without
creating rankings, composites, signals, forward returns, or backtests.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import numpy as np

from .normalization_cross_sectional import (
    STEP9_RAW_SCORE_COLUMNS,
    eligible_cross_sectional_observations,
    prepare_cross_sectional_input_frame,
    score_name_from_raw_column,
)
from .schema import IDENTITY_COLUMNS


def summarize_normalization_coverage(
    frame: pd.DataFrame,
    raw_score_columns: Sequence[str] | None = None,
    *,
    normalized_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return per-score coverage and normalization event counts.

    Input ``frame`` follows the Step 9 raw score schema. Optional
    ``normalized_frame`` should be the output of
    ``normalize_cross_sectional_scores`` or ``normalize_cross_sectional_score``.
    Counts are diagnostics only and must not be interpreted as alpha evidence.
    """

    selected_columns = _select_raw_columns(frame, raw_score_columns)
    prepared = prepare_cross_sectional_input_frame(frame, raw_score_columns=selected_columns)
    rows = [
        _normalization_coverage_row(
            prepared,
            raw_column,
            normalized_frame=normalized_frame,
        )
        for raw_column in selected_columns
    ]
    return pd.DataFrame(rows)


def _normalization_coverage_row(
    prepared: pd.DataFrame,
    raw_column: str,
    *,
    normalized_frame: pd.DataFrame | None,
) -> dict[str, object]:
    score_name = score_name_from_raw_column(raw_column)
    numeric = pd.to_numeric(prepared[raw_column], errors="coerce")
    finite = _finite_numeric_mask(numeric)
    eligible = eligible_cross_sectional_observations(prepared, raw_column)
    row_count = int(len(prepared))
    valid_observation_count = int(eligible.sum())
    coverage_ratio = valid_observation_count / row_count if row_count else 0.0
    event_counts = _normalization_event_counts(normalized_frame, score_name)
    return {
        "diagnostic_name": "coverage",
        "score_name": score_name,
        "raw_column": raw_column,
        "normalization_scope": "cross_sectional",
        "row_count": row_count,
        "valid_observation_count": valid_observation_count,
        "missing_count": int((~finite).sum()),
        "coverage_ratio": coverage_ratio,
        "warmup_count": _status_count(prepared, "score_warmup_state", "warmup"),
        "insufficient_history_count": _status_count(
            prepared, "score_warmup_state", "insufficient_history"
        ),
        "blocked_coverage_count": _status_count(prepared, "score_coverage_status", "blocked"),
        "winsorized_count": event_counts["winsorized_count"],
        "clipped_count": event_counts["clipped_count"],
        "zero_scale_fallback_count": event_counts["zero_scale_fallback_count"],
        "zero_dispersion_count": event_counts["zero_dispersion_count"],
        "insufficient_cross_section_count": event_counts[
            "insufficient_cross_section_count"
        ],
        "diagnostic_status": _coverage_status(coverage_ratio, valid_observation_count),
        "notes": "diagnostic_only_review_material",
    }


def _status_count(frame: pd.DataFrame, column: str, status: str) -> int:
    return int(frame[column].astype("string").eq(status).sum())


def build_normalization_diagnostics(
    frame: pd.DataFrame,
    raw_score_columns: Sequence[str] | None = None,
    *,
    normalized_frame: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Build Step 10B cross-sectional diagnostics.

    Returned tables:
    - ``score_coverage``: per-score coverage and event counts
    - ``date_cross_sectional_valid_count``: same-date eligible counts per score
    - ``ticker_available_observation_count``: ticker-level available counts
    - ``normalization_event_counts``: winsor/clip/zero-scale/missing counts
    - ``warmup_distribution``: row-level warmup state distribution
    - ``data_quality_flag_distribution``: parsed row-level quality flag counts
    - ``coverage_status_distribution``: row-level coverage status distribution
    """

    selected_columns = _select_raw_columns(frame, raw_score_columns)
    prepared = prepare_cross_sectional_input_frame(frame, raw_score_columns=selected_columns)
    score_coverage = summarize_normalization_coverage(
        prepared,
        selected_columns,
        normalized_frame=normalized_frame,
    )
    diagnostics = {
        "score_coverage": score_coverage,
        "date_cross_sectional_valid_count": _date_valid_counts(prepared, selected_columns),
        "ticker_available_observation_count": _ticker_available_counts(
            prepared, selected_columns
        ),
        "normalization_event_counts": _event_count_table(
            prepared, selected_columns, normalized_frame
        ),
        "warmup_distribution": _value_distribution(
            prepared,
            "score_warmup_state",
            output_column="warmup_status",
        ),
        "data_quality_flag_distribution": _quality_flag_distribution(prepared),
        "coverage_status_distribution": _value_distribution(
            prepared,
            "score_coverage_status",
            output_column="coverage_status",
        ),
    }
    return diagnostics


def _select_raw_columns(
    frame: pd.DataFrame, raw_score_columns: Sequence[str] | None
) -> tuple[str, ...]:
    if raw_score_columns is not None:
        return tuple(raw_score_columns)
    present = set(frame.columns)
    selected = tuple(column for column in STEP9_RAW_SCORE_COLUMNS if column in present)
    if not selected:
        selected = tuple(column for column in frame.columns if column.endswith("_raw"))
    if not selected:
        raise ValueError("No raw score columns were provided or found.")
    return selected


def _date_valid_counts(
    prepared: pd.DataFrame, raw_score_columns: Sequence[str]
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for raw_column in raw_score_columns:
        score_name = score_name_from_raw_column(raw_column)
        eligible = eligible_cross_sectional_observations(prepared, raw_column)
        numeric = pd.to_numeric(prepared[raw_column], errors="coerce")
        finite = _finite_numeric_mask(numeric)
        working = prepared.loc[:, [*IDENTITY_COLUMNS]].copy()
        working["_eligible"] = eligible
        working["_missing"] = ~finite
        grouped = working.groupby("date", sort=True)
        rows.extend(
            _date_valid_count_row(score_name, raw_column, date_value, group)
            for date_value, group in grouped
        )
    return pd.DataFrame(rows)


def _date_valid_count_row(
    score_name: str,
    raw_column: str,
    date_value: object,
    group: pd.DataFrame,
) -> dict[str, object]:
    return {
        "diagnostic_name": "date_cross_sectional_valid_count",
        "score_name": score_name,
        "raw_column": raw_column,
        "normalization_scope": "cross_sectional",
        "date": date_value,
        "ticker_count": int(len(group)),
        "cross_sectional_valid_count": int(group["_eligible"].sum()),
        "missing_count": int(group["_missing"].sum()),
        "diagnostic_status": "info",
        "notes": "same_date_only",
    }


def _ticker_available_counts(
    prepared: pd.DataFrame, raw_score_columns: Sequence[str]
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for raw_column in raw_score_columns:
        score_name = score_name_from_raw_column(raw_column)
        eligible = eligible_cross_sectional_observations(prepared, raw_column)
        numeric = pd.to_numeric(prepared[raw_column], errors="coerce")
        finite = _finite_numeric_mask(numeric)
        working = prepared.loc[:, ["ticker"]].copy()
        working["_eligible"] = eligible
        working["_missing"] = ~finite
        grouped = working.groupby("ticker", sort=True)
        rows.extend(
            _ticker_available_count_row(score_name, raw_column, ticker, group)
            for ticker, group in grouped
        )
    return pd.DataFrame(rows)


def _ticker_available_count_row(
    score_name: str,
    raw_column: str,
    ticker: object,
    group: pd.DataFrame,
) -> dict[str, object]:
    return {
        "diagnostic_name": "ticker_available_observation_count",
        "score_name": score_name,
        "raw_column": raw_column,
        "normalization_scope": "cross_sectional",
        "ticker": ticker,
        "available_observation_count": int(group["_eligible"].sum()),
        "missing_count": int(group["_missing"].sum()),
        "diagnostic_status": "info",
        "notes": "no_time_series_normalization",
    }


def _event_count_table(
    prepared: pd.DataFrame,
    raw_score_columns: Sequence[str],
    normalized_frame: pd.DataFrame | None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for raw_column in raw_score_columns:
        score_name = score_name_from_raw_column(raw_column)
        numeric = pd.to_numeric(prepared[raw_column], errors="coerce")
        finite = _finite_numeric_mask(numeric)
        event_counts = _normalization_event_counts(normalized_frame, score_name)
        rows.append(
            {
                "diagnostic_name": "normalization_event_counts",
                "score_name": score_name,
                "raw_column": raw_column,
                "normalization_scope": "cross_sectional",
                "missing_count": int((~finite).sum()),
                **event_counts,
                "diagnostic_status": "info",
                "notes": "diagnostic_only_review_material",
            }
        )
    return pd.DataFrame(rows)


def _normalization_event_counts(
    normalized_frame: pd.DataFrame | None, score_name: str
) -> dict[str, int]:
    counts = {
        "winsorized_count": 0,
        "clipped_count": 0,
        "zero_scale_fallback_count": 0,
        "zero_dispersion_count": 0,
        "insufficient_cross_section_count": 0,
    }
    if normalized_frame is None:
        return counts
    prefix = f"{score_name}_cross_sectional"
    winsorized = f"{prefix}_winsorized"
    clipped = f"{prefix}_clipped"
    scale_method = f"{prefix}_scale_method"
    quality_flag = f"{prefix}_quality_flag"
    if winsorized in normalized_frame:
        counts["winsorized_count"] = int(normalized_frame[winsorized].fillna(False).sum())
    if clipped in normalized_frame:
        counts["clipped_count"] = int(normalized_frame[clipped].fillna(False).sum())
    if scale_method in normalized_frame:
        scale = normalized_frame[scale_method].astype("string")
        counts["zero_scale_fallback_count"] = int(scale.eq("iqr_fallback").sum())
        counts["zero_dispersion_count"] = int(scale.eq("zero_dispersion").sum())
    if quality_flag in normalized_frame:
        counts["insufficient_cross_section_count"] = int(
            normalized_frame[quality_flag]
            .astype("string")
            .str.contains("insufficient_cross_section", regex=False, na=False)
            .sum()
        )
    return counts


def _value_distribution(
    frame: pd.DataFrame,
    column: str,
    *,
    output_column: str,
) -> pd.DataFrame:
    counts = (
        frame[column]
        .astype("string")
        .fillna("unknown")
        .value_counts(dropna=False)
        .rename_axis(output_column)
        .reset_index(name="row_count")
    )
    counts.insert(0, "diagnostic_name", f"{output_column}_distribution")
    counts["diagnostic_status"] = "info"
    return counts


def _quality_flag_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    counts: dict[str, int] = {}
    for value in frame["score_data_quality_flag"].astype("string").fillna("unknown"):
        parts = [part.strip() for part in str(value).split(";") if part.strip()]
        if not parts:
            parts = ["unknown"]
        for part in parts:
            counts[part] = counts.get(part, 0) + 1
    rows = [
        {
            "diagnostic_name": "data_quality_flag_distribution",
            "data_quality_flag": flag,
            "row_count": count,
            "diagnostic_status": "info",
        }
        for flag, count in sorted(counts.items())
    ]
    return pd.DataFrame(rows)


def _coverage_status(coverage_ratio: float, valid_observation_count: int) -> str:
    if valid_observation_count <= 0:
        return "blocked"
    if coverage_ratio < 0.60:
        return "warn"
    return "pass"


def _finite_numeric_mask(series: pd.Series) -> pd.Series:
    values = np.isfinite(series.to_numpy(dtype=float, na_value=np.nan))
    return pd.Series(values, index=series.index)
