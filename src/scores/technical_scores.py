"""Step 9 integrated raw technical score entrypoint.

This module combines Part A and Part B Research Tester raw score outputs. It
does not normalize scores, rank stocks, build composites, calculate forward
returns, or run backtests.
"""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from .mean_reversion_scores import (
    PartAScoreConfig,
    calculate_step9_part_a_raw_scores,
)
from .schema import (
    IDENTITY_COLUMNS,
    SCORE_METADATA_COLUMNS,
    assert_no_forbidden_output_columns,
    assert_no_valuation_fundamental_columns,
    validate_raw_score_output_frame,
)
from .score_contracts import PART_A_MISSING_REASON_COLUMNS, PART_A_RAW_COLUMNS
from .trend_vol_flow_scores import (
    PART_B_MISSING_REASON_COLUMNS,
    PART_B_RAW_SCORE_COLUMNS,
    TrendVolFlowScoreWindows,
    calculate_trend_vol_flow_raw_scores,
)


ALL_STEP9_RAW_SCORE_COLUMNS = (
    *PART_A_RAW_COLUMNS,
    *PART_B_RAW_SCORE_COLUMNS,
)
ALL_STEP9_MISSING_REASON_COLUMNS = (
    *PART_A_MISSING_REASON_COLUMNS,
    *PART_B_MISSING_REASON_COLUMNS,
)


def calculate_all_raw_scores(
    frame: pd.DataFrame,
    *,
    part_a_config: PartAScoreConfig | None = None,
    part_b_windows: TrendVolFlowScoreWindows | None = None,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """Return integrated Step 9 raw scores for the eight MVP candidates."""

    assert_no_forbidden_output_columns(frame, context="Step 9 integrated score input")
    assert_no_valuation_fundamental_columns(frame, context="Step 9 integrated score input")

    part_a = calculate_step9_part_a_raw_scores(
        frame,
        config=part_a_config,
        as_of_date=as_of_date,
    )
    part_b = calculate_trend_vol_flow_raw_scores(frame, windows=part_b_windows)
    _assert_same_identity(part_a, part_b)

    output = part_a.loc[:, list(IDENTITY_COLUMNS)].copy()
    for column in PART_A_RAW_COLUMNS:
        output[column] = part_a[column]
    for column in PART_B_RAW_SCORE_COLUMNS:
        output[column] = part_b[column]

    output["score_warmup_state"] = _combine_warmup_state(
        part_a["score_warmup_state"],
        part_b["score_warmup_state"],
    )
    output["score_coverage_status"] = _coverage_status(output, ALL_STEP9_RAW_SCORE_COLUMNS)
    output["score_data_quality_flag"] = _combine_quality_flags(
        part_a["score_data_quality_flag"],
        part_b["score_data_quality_flag"],
    )
    output["minimum_history_required"] = pd.concat(
        [
            pd.to_numeric(part_a["minimum_history_required"], errors="coerce"),
            pd.to_numeric(part_b["minimum_history_required"], errors="coerce"),
        ],
        axis=1,
    ).max(axis=1).astype("Int64")

    for column in PART_A_MISSING_REASON_COLUMNS:
        output[column] = part_a[column]
    for column in PART_B_MISSING_REASON_COLUMNS:
        output[column] = part_b[column]

    output = output[
        [
            *IDENTITY_COLUMNS,
            *ALL_STEP9_RAW_SCORE_COLUMNS,
            *SCORE_METADATA_COLUMNS,
            *ALL_STEP9_MISSING_REASON_COLUMNS,
        ]
    ]
    validate_raw_score_output_frame(output, context="Step 9 integrated raw score output")
    return output.reset_index(drop=True)


def _assert_same_identity(left: pd.DataFrame, right: pd.DataFrame) -> None:
    left_key = left.loc[:, list(IDENTITY_COLUMNS)].reset_index(drop=True)
    right_key = right.loc[:, list(IDENTITY_COLUMNS)].reset_index(drop=True)
    if not left_key.equals(right_key):
        raise ValueError("Part A and Part B raw score outputs are not aligned by ticker/date.")


def _combine_warmup_state(left: pd.Series, right: pd.Series) -> pd.Series:
    states = pd.concat([left.astype("string"), right.astype("string")], axis=1)
    combined = pd.Series("ready", index=states.index, dtype="string")
    combined = combined.mask(states.eq("unknown").any(axis=1), "unknown")
    combined = combined.mask(
        states.eq("blocked_by_missing_dependency").any(axis=1),
        "blocked_by_missing_dependency",
    )
    combined = combined.mask(states.eq("warmup").any(axis=1), "warmup")
    combined = combined.mask(states.eq("insufficient_history").any(axis=1), "insufficient_history")
    return combined


def _coverage_status(frame: pd.DataFrame, raw_columns: tuple[str, ...]) -> pd.Series:
    present_count = frame.loc[:, list(raw_columns)].notna().sum(axis=1)
    status = pd.Series("blocked", index=frame.index, dtype="string")
    status = status.mask(present_count.gt(0), "partial")
    status = status.mask(present_count.eq(len(raw_columns)), "adequate")
    return status


def _combine_quality_flags(left: pd.Series, right: pd.Series) -> pd.Series:
    combined: list[str] = []
    for left_value, right_value in zip(left.fillna("unknown"), right.fillna("unknown")):
        flags: set[str] = set()
        for value in (left_value, right_value):
            for flag in str(value).split(";"):
                normalized = flag.strip()
                if normalized and normalized != "valid":
                    flags.add(normalized)
        combined.append(";".join(sorted(flags)) if flags else "valid")
    return pd.Series(combined, index=left.index, dtype="string")
