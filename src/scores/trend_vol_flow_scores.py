"""Step 9 Part B raw score calculations.

This module implements only raw Research Tester candidate values for the
breakout, squeeze, flow, and trend-efficiency score families. It intentionally
does not produce normalized scores, rankings, composites, trading signals, or
backtest fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import re
import tomllib
from typing import Iterable, Mapping

import pandas as pd

from .schema import (
    assert_no_forbidden_output_columns,
    assert_no_valuation_fundamental_columns,
)


PART_B_RAW_SCORE_COLUMNS = (
    "donchian_breakout_distance_raw",
    "bollinger_width_squeeze_raw",
    "cmf_confirmation_raw",
    "efficiency_ratio_trend_raw",
)
PART_B_MISSING_REASON_COLUMNS = tuple(
    column.removesuffix("_raw") + "_missing_reason" for column in PART_B_RAW_SCORE_COLUMNS
)
PART_B_SCORE_NAMES = (
    "donchian_breakout_distance",
    "bollinger_width_squeeze",
    "cmf_confirmation",
    "efficiency_ratio_trend",
)
IDENTITY_COLUMNS = ("ticker", "date")
TICKER_PATTERN = re.compile(r"^[0-9A-Z]{6}$")
METADATA_COLUMNS = (
    "score_warmup_state",
    "score_coverage_status",
    "score_data_quality_flag",
    "minimum_history_required",
)
FORBIDDEN_OUTPUT_COLUMNS = {
    "rank",
    "ranking",
    "latest_rank",
    "normalized_score",
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
}


@dataclass(frozen=True)
class TrendVolFlowScoreWindows:
    """Config-selected windows for Step 9 Part B raw scores."""

    donchian: int
    bollinger: int
    cmf: int
    efficiency_ratio: int
    minimum_history_required: int


def load_part_b_score_windows(
    *,
    windows_config_path: str | Path = "Quant_mvp/config/windows.toml",
    scores_config_path: str | Path = "Quant_mvp/config/scores.toml",
) -> TrendVolFlowScoreWindows:
    """Load Step 9 Part B score windows and minimum history from config."""

    windows_config = _load_toml(Path(windows_config_path))
    scores_config = _load_toml(Path(scores_config_path))
    minimum_history_by_score = _part_b_minimum_history_by_score(scores_config)
    return TrendVolFlowScoreWindows(
        donchian=_positive_int(
            windows_config.get("indicators", {}).get("donchian"),
            "indicators.donchian",
            "Quant_mvp/config/windows.toml",
        ),
        bollinger=_positive_int(
            windows_config.get("indicators", {}).get("bollinger"),
            "indicators.bollinger",
            "Quant_mvp/config/windows.toml",
        ),
        cmf=_positive_int(
            windows_config.get("indicators", {}).get("cmf"),
            "indicators.cmf",
            "Quant_mvp/config/windows.toml",
        ),
        efficiency_ratio=_positive_int(
            windows_config.get("statistics", {}).get("efficiency_ratio"),
            "statistics.efficiency_ratio",
            "Quant_mvp/config/windows.toml",
        ),
        minimum_history_required=max(minimum_history_by_score.values()),
    )


def calculate_trend_vol_flow_raw_scores(
    frame: pd.DataFrame,
    *,
    windows: TrendVolFlowScoreWindows | None = None,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """Calculate Step 9 Part B raw scores from Step 7 indicator output.

    The returned frame contains only identity columns, raw Part B score columns,
    score-level metadata, and score-specific missing reason columns.
    """

    config = windows or load_part_b_score_windows()
    data = _prepare_input(frame, as_of_date=as_of_date)
    history_count = _score_history_count(data)
    group_size = data.groupby("ticker", sort=False)["date"].transform("size")
    enough_history = history_count.ge(config.minimum_history_required) & group_size.ge(
        config.minimum_history_required
    )
    warmup_state = _score_warmup_state(
        history_count=history_count,
        group_size=group_size,
        minimum_history_required=config.minimum_history_required,
    )

    output = data.loc[:, list(IDENTITY_COLUMNS)].copy()
    output["minimum_history_required"] = config.minimum_history_required

    raw_results: dict[str, pd.Series] = {}
    missing_reasons: dict[str, pd.Series] = {}

    raw, reason = _donchian_breakout_distance(data, config, enough_history, warmup_state)
    raw_results["donchian_breakout_distance_raw"] = raw
    missing_reasons["donchian_breakout_distance_missing_reason"] = reason

    raw, reason = _bollinger_width_squeeze(data, config, enough_history, warmup_state)
    raw_results["bollinger_width_squeeze_raw"] = raw
    missing_reasons["bollinger_width_squeeze_missing_reason"] = reason

    raw, reason = _cmf_confirmation(data, config, enough_history, warmup_state)
    raw_results["cmf_confirmation_raw"] = raw
    missing_reasons["cmf_confirmation_missing_reason"] = reason

    raw, reason = _efficiency_ratio_trend(data, config, enough_history, warmup_state)
    raw_results["efficiency_ratio_trend_raw"] = raw
    missing_reasons["efficiency_ratio_trend_missing_reason"] = reason

    for column in PART_B_RAW_SCORE_COLUMNS:
        output[column] = raw_results[column]

    output["score_warmup_state"] = _aggregate_warmup_state(
        warmup_state, list(missing_reasons.values())
    )
    output["score_coverage_status"] = _coverage_status(output, PART_B_RAW_SCORE_COLUMNS)
    output["score_data_quality_flag"] = _data_quality_flags(
        data=data,
        warmup_state=warmup_state,
        missing_reasons=list(missing_reasons.values()),
    )

    for column in PART_B_MISSING_REASON_COLUMNS:
        output[column] = missing_reasons[column]

    _assert_no_forbidden_outputs(output)
    return output.reset_index(drop=True)


def _prepare_input(
    frame: pd.DataFrame,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None,
) -> pd.DataFrame:
    assert_no_forbidden_output_columns(frame, context="Step 9 Part B input")
    assert_no_valuation_fundamental_columns(frame, context="Step 9 Part B input")

    missing = [column for column in IDENTITY_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required identity columns: {', '.join(missing)}")

    data = frame.copy()
    data["ticker"] = data["ticker"].astype("string").str.strip()
    valid_ticker = data["ticker"].map(
        lambda value: isinstance(value, str) and bool(TICKER_PATTERN.fullmatch(value)),
        na_action="ignore",
    ).fillna(False)
    if (~valid_ticker).any():
        raise ValueError("Step 9 Part B input ticker must be six-character string values.")

    data["date"] = pd.to_datetime(data["date"], errors="raise")
    _assert_no_future_dates(data["date"], as_of_date=as_of_date)
    if data.duplicated(list(IDENTITY_COLUMNS)).any():
        duplicates = data.loc[data.duplicated(list(IDENTITY_COLUMNS), keep=False), list(IDENTITY_COLUMNS)]
        first = duplicates.sort_values(list(IDENTITY_COLUMNS)).iloc[0]
        raise ValueError(
            "Duplicate ticker/date rows are not allowed in Step 9 score input: "
            f"ticker={first['ticker']}, date={first['date'].date()}"
        )
    return data.sort_values(list(IDENTITY_COLUMNS), kind="mergesort").reset_index(drop=True)


def _score_history_count(data: pd.DataFrame) -> pd.Series:
    if "history_count" in data.columns:
        parsed = pd.to_numeric(data["history_count"], errors="coerce")
        computed = data.groupby("ticker", sort=False).cumcount() + 1
        return parsed.fillna(computed).astype("int64")
    return (data.groupby("ticker", sort=False).cumcount() + 1).astype("int64")


def _score_warmup_state(
    *,
    history_count: pd.Series,
    group_size: pd.Series,
    minimum_history_required: int,
) -> pd.Series:
    state = pd.Series("ready", index=history_count.index, dtype="string")
    state = state.mask(history_count.lt(minimum_history_required), "warmup")
    state = state.mask(group_size.lt(minimum_history_required), "insufficient_history")
    return state


def _donchian_breakout_distance(
    data: pd.DataFrame,
    config: TrendVolFlowScoreWindows,
    enough_history: pd.Series,
    warmup_state: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    high_col = f"donchian_high_prior_{config.donchian}"
    required = ("close", high_col)
    missing_dependency = _missing_dependency(data, required)
    if missing_dependency:
        return _blocked_score(data.index), _reason_series(
            data.index, warmup_state, enough_history, missing_dependency=True
        )

    close = _numeric(data["close"])
    prior_high = _numeric(data[high_col])
    valid_denominator = prior_high.gt(0)
    raw = (close / prior_high.where(valid_denominator)) - 1.0
    raw = raw.where(enough_history)
    return raw, _reason_series(
        data.index,
        warmup_state,
        enough_history,
        values=raw,
        denominator_invalid=prior_high.notna() & ~valid_denominator,
    )


def _bollinger_width_squeeze(
    data: pd.DataFrame,
    config: TrendVolFlowScoreWindows,
    enough_history: pd.Series,
    warmup_state: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    width_col = f"bollinger_width_{config.bollinger}"
    if _missing_dependency(data, (width_col,)):
        return _blocked_score(data.index), _reason_series(
            data.index, warmup_state, enough_history, missing_dependency=True
        )

    width = _numeric(data[width_col])
    raw = -width
    raw = raw.where(enough_history)
    return raw, _reason_series(data.index, warmup_state, enough_history, values=raw)


def _cmf_confirmation(
    data: pd.DataFrame,
    config: TrendVolFlowScoreWindows,
    enough_history: pd.Series,
    warmup_state: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    cmf_col = f"cmf_{config.cmf}"
    if _missing_dependency(data, (cmf_col,)):
        return _blocked_score(data.index), _reason_series(
            data.index, warmup_state, enough_history, missing_dependency=True
        )

    raw = _numeric(data[cmf_col]).where(enough_history)
    return raw, _reason_series(data.index, warmup_state, enough_history, values=raw)


def _efficiency_ratio_trend(
    data: pd.DataFrame,
    config: TrendVolFlowScoreWindows,
    enough_history: pd.Series,
    warmup_state: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    efficiency_col = f"efficiency_ratio_{config.efficiency_ratio}"
    if _missing_dependency(data, (efficiency_col,)):
        return _blocked_score(data.index), _reason_series(
            data.index, warmup_state, enough_history, missing_dependency=True
        )

    efficiency_ratio = _numeric(data[efficiency_col])
    trend_direction = _trend_direction(data, config.efficiency_ratio)
    if trend_direction is None:
        return _blocked_score(data.index), _reason_series(
            data.index, warmup_state, enough_history, missing_dependency=True
        )

    raw = (trend_direction * efficiency_ratio).where(enough_history)
    return raw, _reason_series(data.index, warmup_state, enough_history, values=raw)


def _trend_direction(data: pd.DataFrame, window: int) -> pd.Series | None:
    return_col = f"return_{window}d"
    endpoint_change = None
    if "close" in data.columns:
        endpoint_change = data.groupby("ticker", sort=False)["close"].transform(
            lambda values: _numeric(values).diff(window)
        )

    if return_col in data.columns:
        reference = _numeric(data[return_col])
        if endpoint_change is not None:
            reference = reference.fillna(endpoint_change)
    elif endpoint_change is not None:
        reference = endpoint_change
    else:
        return None

    direction = pd.Series(0.0, index=data.index, dtype="float64")
    direction = direction.mask(reference.gt(0), 1.0)
    direction = direction.mask(reference.lt(0), -1.0)
    direction = direction.where(reference.notna())
    return direction


def _missing_dependency(data: pd.DataFrame, columns: Iterable[str]) -> bool:
    return any(column not in data.columns for column in columns)


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _load_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _positive_int(value: object, name: str, source: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{source} {name} must be a positive integer.") from exc
    if isinstance(value, bool) or parsed <= 0:
        raise ValueError(f"{source} {name} must be a positive integer.")
    return parsed


def _part_b_minimum_history_by_score(scores_config: Mapping[str, object]) -> dict[str, int]:
    score_entries = scores_config.get("scores", [])
    values: dict[str, int] = {}
    if isinstance(score_entries, list):
        for entry in score_entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("score_id") or entry.get("name")
            if isinstance(name, str) and name in PART_B_SCORE_NAMES:
                values[name] = _positive_int(
                    entry.get("minimum_history"),
                    f"{name}.minimum_history",
                    "Quant_mvp/config/scores.toml",
                )

    missing = [score_name for score_name in PART_B_SCORE_NAMES if score_name not in values]
    if missing:
        raise ValueError(
            "Quant_mvp/config/scores.toml missing Part B minimum_history for: "
            f"{', '.join(missing)}"
        )
    return values


def _assert_no_future_dates(
    dates: pd.Series,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None,
) -> None:
    if as_of_date is None:
        return
    cutoff = _as_timestamp(as_of_date)
    future_mask = dates.dt.normalize() > cutoff
    if future_mask.any():
        first_future = dates.loc[future_mask].min().date()
        raise ValueError(
            "Step 9 Part B input contains future dates after "
            f"{cutoff.date()}: first={first_future}"
        )


def _as_timestamp(value: date | datetime | pd.Timestamp | str) -> pd.Timestamp:
    if isinstance(value, pd.Timestamp):
        return pd.Timestamp(value.date())
    if isinstance(value, datetime):
        return pd.Timestamp(value.date())
    return pd.Timestamp(value)


def _blocked_score(index: pd.Index) -> pd.Series:
    return pd.Series(float("nan"), index=index, dtype="float64")


def _reason_series(
    index: pd.Index,
    warmup_state: pd.Series,
    enough_history: pd.Series,
    *,
    values: pd.Series | None = None,
    missing_dependency: bool = False,
    denominator_invalid: pd.Series | None = None,
) -> pd.Series:
    reason = pd.Series("", index=index, dtype="string")
    reason = reason.mask(~enough_history, warmup_state)
    if missing_dependency:
        return reason.mask(reason.eq(""), "missing_dependency")

    if denominator_invalid is not None:
        reason = reason.mask(reason.eq("") & denominator_invalid, "zero_denominator")
    if values is not None:
        reason = reason.mask(reason.eq("") & values.isna(), "missing_required_input")
    return reason


def _aggregate_warmup_state(
    warmup_state: pd.Series, missing_reasons: list[pd.Series]
) -> pd.Series:
    aggregated = warmup_state.copy()
    all_missing_dependency = pd.concat(
        [reason.eq("missing_dependency") for reason in missing_reasons], axis=1
    ).all(axis=1)
    return aggregated.mask(aggregated.eq("ready") & all_missing_dependency, "blocked_by_missing_dependency")


def _coverage_status(frame: pd.DataFrame, raw_columns: Iterable[str]) -> pd.Series:
    present_count = frame.loc[:, list(raw_columns)].notna().sum(axis=1)
    total_count = len(tuple(raw_columns))
    status = pd.Series("blocked", index=frame.index, dtype="string")
    status = status.mask(present_count.gt(0), "partial")
    status = status.mask(present_count.eq(total_count), "adequate")
    return status


def _data_quality_flags(
    *,
    data: pd.DataFrame,
    warmup_state: pd.Series,
    missing_reasons: list[pd.Series],
) -> pd.Series:
    row_reasons = pd.concat(missing_reasons, axis=1)
    flags: list[str] = []
    for row_index, row in row_reasons.iterrows():
        row_flags: set[str] = set()
        ticker = data.loc[row_index, "ticker"]
        if pd.isna(ticker) or not TICKER_PATTERN.fullmatch(str(ticker)):
            if re.fullmatch(r"\d{1,5}", str(ticker)):
                row_flags.add("leading_zero_lost")
            else:
                row_flags.add("invalid_ticker")

        if warmup_state.loc[row_index] == "warmup":
            row_flags.add("warmup")
        elif warmup_state.loc[row_index] == "insufficient_history":
            row_flags.add("insufficient_history")

        if (row == "missing_dependency").any() or (row == "missing_required_input").any():
            row_flags.add("missing_required_input")
        if (row == "zero_denominator").any():
            row_flags.add("invalid_numeric")

        flags.append(";".join(sorted(row_flags)) if row_flags else "valid")
    return pd.Series(flags, index=data.index, dtype="string")


def _assert_no_forbidden_outputs(frame: pd.DataFrame) -> None:
    forbidden = [
        column
        for column in frame.columns
        if column in FORBIDDEN_OUTPUT_COLUMNS
        or column.endswith("_normalized")
        or column in {"normalized_score_time_series", "normalized_score_cross_sectional"}
    ]
    if forbidden:
        raise ValueError(f"Forbidden Step 9 Part B output columns: {forbidden}")
