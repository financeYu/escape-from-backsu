"""Step 10A ticker-local time-series normalization primitives.

This module implements only time-series normalization. It does not perform
cross-sectional normalization, ranking, composite scoring, valuation scoring,
forward-return labeling, or backtesting.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
import math
import re

import pandas as pd

from src.preprocess.schema_validator import KOSPI200_SYMBOL_POLICY, SymbolPolicy

from .normalization_common import (
    clip_series_to_bounds,
    clip_value_to_bounds,
    finite_mask,
    positive_finite,
    to_numeric_series,
)
from .timeseries_config import (
    TimeSeriesNormalizationConfig,
    load_timeseries_normalization_config,
)
from .schema import (
    IDENTITY_COLUMNS,
    assert_no_forbidden_output_columns,
    assert_no_valuation_fundamental_columns,
    require_columns,
)


NORMALIZATION_SCOPE = "time_series"
ROBUST_ZSCORE_COLUMN = "robust_zscore"
STATUS_OK = "ok"
STATUS_WARMUP = "warmup"
STATUS_INSUFFICIENT_HISTORY = "insufficient_history"
STATUS_MISSING_RAW_SCORE = "missing_raw_score"
STATUS_INVALID_RAW_SCORE = "invalid_raw_score"
STATUS_ZERO_SCALE = "zero_scale"
TIME_SERIES_STATUSES = frozenset(
    {
        STATUS_OK,
        STATUS_WARMUP,
        STATUS_INSUFFICIENT_HISTORY,
        STATUS_MISSING_RAW_SCORE,
        STATUS_INVALID_RAW_SCORE,
        STATUS_ZERO_SCALE,
    }
)
TICKER_PATTERN = re.compile(KOSPI200_SYMBOL_POLICY.valid_pattern)


def normalize_timeseries_scores(
    frame: pd.DataFrame,
    *,
    raw_score_columns: Sequence[str] | None = None,
    config: TimeSeriesNormalizationConfig | None = None,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> pd.DataFrame:
    """Normalize one or more Step 9 raw score columns ticker-by-ticker.

    Input schema:
    - required: `ticker`, `date`, and each selected raw score column
    - optional: `score_warmup_state` or `warmup_state`
    - optional: `minimum_history_required`

    Output schema:
    - identity: `ticker`, `date`
    - per raw score:
      - `{score_name}_ts_robust_zscore`
      - `{score_name}_ts_status`
      - `{score_name}_ts_coverage_status`
      - `{score_name}_ts_data_quality_flag`
      - `{score_name}_ts_observation_count`
      - `{score_name}_ts_scale`
      - `{score_name}_ts_scale_method`
      - `{score_name}_ts_winsorized_value`
      - `{score_name}_ts_was_winsorized`
      - `{score_name}_ts_was_clipped`

    The output is time-series context only. It is not a rank, not a same-date
    cross-sectional normalization, not a composite score, and not a backtest
    label.
    """

    selected = tuple(raw_score_columns or _infer_raw_score_columns(frame.columns))
    if not selected:
        raise ValueError("At least one raw score column is required for Step 10A normalization.")

    data = _prepare_timeseries_input(
        frame,
        required_columns=selected,
        symbol_policy=symbol_policy,
    )
    return _normalize_timeseries_outputs(data, selected, config=config)


def _normalize_timeseries_outputs(
    data: pd.DataFrame,
    selected: Sequence[str],
    *,
    config: TimeSeriesNormalizationConfig | None,
) -> pd.DataFrame:
    output = data.loc[:, list(IDENTITY_COLUMNS)].copy()
    for raw_score_column in selected:
        score_output = _normalize_prepared_timeseries_score(
            data,
            raw_score_column=raw_score_column,
            config=config or load_timeseries_normalization_config(),
        )
        for column in score_output.columns:
            if column not in IDENTITY_COLUMNS:
                output[column] = score_output[column]
    return output.reset_index(drop=True)


def normalize_timeseries_score(
    frame: pd.DataFrame,
    raw_score_column: str,
    *,
    score_name: str | None = None,
    config: TimeSeriesNormalizationConfig | None = None,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> pd.DataFrame:
    """Normalize a single raw score column using ticker-local history only.

    The function sorts by `ticker`, `date`, rejects duplicate ticker/date pairs,
    preserves leading-zero tickers as strings, and calculates each row from same
    ticker observations with `date <= current date`.
    """

    data = _prepare_timeseries_input(
        frame,
        required_columns=(raw_score_column,),
        symbol_policy=symbol_policy,
    )
    return _normalize_prepared_timeseries_score(
        data,
        raw_score_column=raw_score_column,
        score_name=score_name,
        config=config or load_timeseries_normalization_config(),
    ).reset_index(drop=True)


def robust_zscore_expanding(
    values: Iterable[object],
    *,
    min_periods: int = 60,
    winsorize_lower_pct: float | None = 0.01,
    winsorize_upper_pct: float | None = 0.99,
    clip_lower: float | None = None,
    clip_upper: float | None = None,
    use_iqr_fallback: bool = True,
) -> pd.DataFrame:
    """Return expanding robust z-scores for a single already-ordered series.

    The current row is included in its own context. Future rows are never used.
    Returned columns are `robust_zscore`, `status`, `data_quality_flag`,
    `observation_count`, `scale`, `scale_method`, `winsorized_value`,
    `was_winsorized`, and `was_clipped`.
    """

    config = TimeSeriesNormalizationConfig(
        window=None,
        min_periods=min_periods,
        winsorize_lower_pct=winsorize_lower_pct,
        winsorize_upper_pct=winsorize_upper_pct,
        clip_lower=clip_lower,
        clip_upper=clip_upper,
        use_iqr_fallback=use_iqr_fallback,
    )
    series = pd.Series(values)
    return _normalize_series_online(series, config=config)


def apply_winsorization(
    values: Iterable[object],
    *,
    lower_pct: float | None = 0.01,
    upper_pct: float | None = 0.99,
) -> pd.DataFrame:
    """Winsorize finite numeric values and return value plus diagnostics."""

    from .normalization_common import apply_winsorization as common_apply_winsorization

    return common_apply_winsorization(
        values, lower_pct=lower_pct, upper_pct=upper_pct
    )


def apply_clipping(
    values: Iterable[object],
    *,
    lower: float | None = None,
    upper: float | None = None,
) -> pd.DataFrame:
    """Clip finite numeric values to explicit bounds and return diagnostics."""

    from .normalization_common import apply_clipping as common_apply_clipping

    return common_apply_clipping(values, lower=lower, upper=upper)


def _normalize_prepared_timeseries_score(
    data: pd.DataFrame,
    *,
    raw_score_column: str,
    config: TimeSeriesNormalizationConfig,
    score_name: str | None = None,
) -> pd.DataFrame:
    prefix = score_name or raw_score_column.removesuffix("_raw")
    normalized_groups: list[pd.DataFrame] = []
    for _, group in data.groupby("ticker", sort=False):
        normalized = _normalize_series_online(
            group[raw_score_column],
            config=config,
            upstream_warmup=_optional_column(group, ("score_warmup_state", "warmup_state")),
            minimum_history=_optional_column(group, ("minimum_history_required",)),
        )
        normalized.index = group.index
        normalized_groups.append(normalized)

    normalized_data = pd.concat(normalized_groups).sort_index()
    output = data.loc[:, list(IDENTITY_COLUMNS)].copy()
    output[f"{prefix}_ts_robust_zscore"] = normalized_data[ROBUST_ZSCORE_COLUMN].astype("Float64")
    output[f"{prefix}_ts_status"] = normalized_data["status"].astype("string")
    output[f"{prefix}_ts_coverage_status"] = normalized_data["coverage_status"].astype("string")
    output[f"{prefix}_ts_data_quality_flag"] = normalized_data["data_quality_flag"].astype("string")
    output[f"{prefix}_ts_observation_count"] = normalized_data["observation_count"].astype("Int64")
    output[f"{prefix}_ts_scale"] = normalized_data["scale"].astype("Float64")
    output[f"{prefix}_ts_scale_method"] = normalized_data["scale_method"].astype("string")
    output[f"{prefix}_ts_winsorized_value"] = normalized_data["winsorized_value"].astype("Float64")
    output[f"{prefix}_ts_was_winsorized"] = normalized_data["was_winsorized"].astype("boolean")
    output[f"{prefix}_ts_was_clipped"] = normalized_data["was_clipped"].astype("boolean")
    return output


def _normalize_series_online(
    raw_values: Iterable[object],
    *,
    config: TimeSeriesNormalizationConfig,
    upstream_warmup: pd.Series | None = None,
    minimum_history: pd.Series | None = None,
) -> pd.DataFrame:
    raw = pd.Series(raw_values).reset_index(drop=True)
    numeric = to_numeric_series(raw)
    finite = finite_mask(numeric)
    invalid = raw.notna() & (~finite) & numeric.notna()
    invalid = invalid | (raw.notna() & numeric.isna())
    missing = raw.isna()
    finite_values = numeric.where(finite)

    columns = _empty_timeseries_result_columns()
    warmup_values = (
        upstream_warmup.reset_index(drop=True).astype("string") if upstream_warmup is not None else None
    )
    minimum_history_values = (
        pd.to_numeric(minimum_history.reset_index(drop=True), errors="coerce")
        if minimum_history is not None
        else None
    )

    for position in range(len(raw)):
        _append_timeseries_row(
            columns,
            raw=raw,
            numeric=numeric,
            finite_values=finite_values,
            missing=missing,
            invalid=invalid,
            position=position,
            config=config,
            warmup_values=warmup_values,
            minimum_history_values=minimum_history_values,
        )

    return _timeseries_result_frame(columns, raw.index)


def _timeseries_result_frame(
    columns: dict[str, list[object]],
    index: pd.Index,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            ROBUST_ZSCORE_COLUMN: columns["normalized_values"],
            "status": columns["statuses"],
            "coverage_status": columns["coverage_statuses"],
            "data_quality_flag": columns["quality_flags"],
            "observation_count": columns["observation_counts"],
            "scale": columns["scales"],
            "scale_method": columns["scale_methods"],
            "winsorized_value": columns["winsorized_values"],
            "was_winsorized": columns["was_winsorized"],
            "was_clipped": columns["was_clipped"],
        },
        index=index,
    )


def _empty_timeseries_result_columns() -> dict[str, list[object]]:
    return {
        "normalized_values": [],
        "statuses": [],
        "coverage_statuses": [],
        "quality_flags": [],
        "observation_counts": [],
        "scales": [],
        "scale_methods": [],
        "winsorized_values": [],
        "was_winsorized": [],
        "was_clipped": [],
    }


def _append_timeseries_row(
    columns: dict[str, list[object]],
    *,
    raw: pd.Series,
    numeric: pd.Series,
    finite_values: pd.Series,
    missing: pd.Series,
    invalid: pd.Series,
    position: int,
    config: TimeSeriesNormalizationConfig,
    warmup_values: pd.Series | None,
    minimum_history_values: pd.Series | None,
) -> None:
    context = _context_values(finite_values, position=position, window=config.window)
    row = _evaluate_timeseries_row(
        raw=raw,
        numeric=numeric,
        context=context,
        missing=missing,
        invalid=invalid,
        position=position,
        config=config,
        warmup_values=warmup_values,
        minimum_history_values=minimum_history_values,
    )
    _append_timeseries_result(columns, row, observation_count=int(context.count()))


def _evaluate_timeseries_row(
    *,
    raw: pd.Series,
    numeric: pd.Series,
    context: pd.Series,
    missing: pd.Series,
    invalid: pd.Series,
    position: int,
    config: TimeSeriesNormalizationConfig,
    warmup_values: pd.Series | None,
    minimum_history_values: pd.Series | None,
) -> dict[str, object]:
    upstream_status = _upstream_status(warmup_values, position)
    row_min_periods = _row_min_periods(config.min_periods, minimum_history_values, position)
    if upstream_status is not None:
        return _empty_timeseries_row(upstream_status)
    if bool(missing.iloc[position]):
        return _empty_timeseries_row(STATUS_MISSING_RAW_SCORE)
    if bool(invalid.iloc[position]):
        return _empty_timeseries_row(STATUS_INVALID_RAW_SCORE)
    if int(context.count()) < row_min_periods:
        return _empty_timeseries_row(STATUS_WARMUP)

    return _robust_zscore_for_context(
        context.astype(float),
        current_raw=float(numeric.iloc[position]),
        config=config,
    )


def _empty_timeseries_row(status: str) -> dict[str, object]:
    return {
        "value": pd.NA,
        "status": status,
        "scale": pd.NA,
        "scale_method": pd.NA,
        "winsorized_value": pd.NA,
        "was_winsorized": False,
        "was_clipped": False,
    }


def _append_timeseries_result(
    columns: dict[str, list[object]],
    row: dict[str, object],
    *,
    observation_count: int,
) -> None:
    status = str(row["status"])
    was_winsorized = bool(row["was_winsorized"])
    was_clipped = bool(row["was_clipped"])
    columns["normalized_values"].append(row["value"])
    columns["statuses"].append(status)
    columns["coverage_statuses"].append("adequate" if status == STATUS_OK else "blocked")
    columns["quality_flags"].append(_quality_flag(status, was_winsorized, was_clipped))
    columns["observation_counts"].append(observation_count)
    columns["scales"].append(row["scale"])
    columns["scale_methods"].append(row["scale_method"])
    columns["winsorized_values"].append(row["winsorized_value"])
    columns["was_winsorized"].append(was_winsorized)
    columns["was_clipped"].append(was_clipped)


def _robust_zscore_for_context(
    context: pd.Series,
    *,
    current_raw: float,
    config: TimeSeriesNormalizationConfig,
) -> dict[str, object]:
    winsorized_context, winsorized_current, was_winsorized = _winsorized_context(
        context,
        current_raw=current_raw,
        config=config,
    )

    median = float(winsorized_context.median())
    scale, scale_method = _timeseries_scale(winsorized_context, median, config)
    if not positive_finite(scale):
        return _zero_scale_timeseries_row(winsorized_current, was_winsorized)

    value = (winsorized_current - median) / scale
    clipped = apply_clipping([value], lower=config.clip_lower, upper=config.clip_upper)
    clipped_value = clipped.loc[0, "value"]
    return {
        "value": float(clipped_value) if pd.notna(clipped_value) else pd.NA,
        "status": STATUS_OK,
        "scale": scale,
        "scale_method": scale_method,
        "winsorized_value": winsorized_current,
        "was_winsorized": was_winsorized,
        "was_clipped": bool(clipped.loc[0, "was_clipped"]),
    }


def _winsorized_context(
    context: pd.Series,
    *,
    current_raw: float,
    config: TimeSeriesNormalizationConfig,
) -> tuple[pd.Series, float, bool]:
    if config.winsorize_lower_pct is None and config.winsorize_upper_pct is None:
        return context.copy(), current_raw, False

    lower = (
        float(context.quantile(config.winsorize_lower_pct))
        if config.winsorize_lower_pct is not None
        else None
    )
    upper = (
        float(context.quantile(config.winsorize_upper_pct))
        if config.winsorize_upper_pct is not None
        else None
    )
    winsorized_context = clip_series_to_bounds(context, lower, upper)
    winsorized_current = float(clip_value_to_bounds(current_raw, lower, upper))
    was_winsorized = not math.isclose(
        winsorized_current, current_raw, rel_tol=0.0, abs_tol=0.0
    )
    return winsorized_context, winsorized_current, was_winsorized


def _timeseries_scale(
    winsorized_context: pd.Series,
    median: float,
    config: TimeSeriesNormalizationConfig,
) -> tuple[float, str]:
    mad = float((winsorized_context - median).abs().median())
    scale = mad * config.mad_scale
    if positive_finite(scale):
        return scale, "mad"
    if config.use_iqr_fallback:
        iqr = float(winsorized_context.quantile(0.75) - winsorized_context.quantile(0.25))
        fallback_scale = iqr / config.iqr_scale
        if positive_finite(fallback_scale):
            return fallback_scale, "iqr"
    return scale, "mad"


def _zero_scale_timeseries_row(
    winsorized_current: float,
    was_winsorized: bool,
) -> dict[str, object]:
    return {
        "value": pd.NA,
        "status": STATUS_ZERO_SCALE,
        "scale": pd.NA,
        "scale_method": pd.NA,
        "winsorized_value": winsorized_current,
        "was_winsorized": was_winsorized,
        "was_clipped": False,
    }


def _prepare_timeseries_input(
    frame: pd.DataFrame,
    *,
    required_columns: Sequence[str],
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> pd.DataFrame:
    require_columns(frame, (*IDENTITY_COLUMNS, *required_columns), context="Step 10A input")
    assert_no_forbidden_output_columns(frame, context="Step 10A input")
    assert_no_valuation_fundamental_columns(frame, context="Step 10A input")

    data = frame.copy()
    data["ticker"] = data["ticker"].astype("string").str.strip()
    valid_ticker = data["ticker"].map(
        lambda value: isinstance(value, str) and symbol_policy.is_valid(value),
        na_action="ignore",
    ).fillna(False)
    if (~valid_ticker).any():
        raise ValueError(f"Step 10A input ticker must preserve {symbol_policy.display_rule}.")

    data["date"] = pd.to_datetime(data["date"], errors="raise")
    if data.duplicated(list(IDENTITY_COLUMNS)).any():
        duplicates = data.loc[
            data.duplicated(list(IDENTITY_COLUMNS), keep=False),
            list(IDENTITY_COLUMNS),
        ]
        first = duplicates.sort_values(list(IDENTITY_COLUMNS)).iloc[0]
        raise ValueError(
            "Duplicate ticker/date rows are not allowed in Step 10A normalization input: "
            f"ticker={first['ticker']}, date={first['date'].date()}"
        )
    return data.sort_values(list(IDENTITY_COLUMNS), kind="mergesort").reset_index(drop=True)


def _infer_raw_score_columns(columns: Iterable[str]) -> list[str]:
    return [column for column in columns if column.endswith("_raw")]


def _context_values(series: pd.Series, *, position: int, window: int | None) -> pd.Series:
    start = 0 if window is None else max(0, position + 1 - window)
    return series.iloc[start : position + 1].dropna()


def _optional_column(frame: pd.DataFrame, candidates: Sequence[str]) -> pd.Series | None:
    for column in candidates:
        if column in frame.columns:
            return frame[column]
    return None


def _upstream_status(upstream_warmup: pd.Series | None, position: int) -> str | None:
    if upstream_warmup is None:
        return None
    value = upstream_warmup.iloc[position]
    if value == STATUS_INSUFFICIENT_HISTORY:
        return STATUS_INSUFFICIENT_HISTORY
    if value == STATUS_WARMUP:
        return STATUS_WARMUP
    return None


def _row_min_periods(
    config_min_periods: int,
    minimum_history_values: pd.Series | None,
    position: int,
) -> int:
    if minimum_history_values is None or pd.isna(minimum_history_values.iloc[position]):
        return config_min_periods
    return max(config_min_periods, int(minimum_history_values.iloc[position]))


def _quality_flag(status: str, was_winsorized: bool, was_clipped: bool) -> str:
    if status == STATUS_OK:
        return "clipped_outlier" if was_winsorized or was_clipped else "valid"
    if status == STATUS_WARMUP:
        return "warmup"
    if status == STATUS_INSUFFICIENT_HISTORY:
        return "insufficient_history"
    if status == STATUS_MISSING_RAW_SCORE:
        return "missing_required_input"
    if status == STATUS_INVALID_RAW_SCORE:
        return "invalid_numeric"
    if status == STATUS_ZERO_SCALE:
        return "zero_dispersion"
    return "unknown"


def to_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def finite_mask(series: pd.Series) -> pd.Series:
    return series.map(lambda value: pd.notna(value) and math.isfinite(float(value)))


def positive_finite(value: float) -> bool:
    return pd.notna(value) and math.isfinite(float(value)) and value > 0


def clip_series_to_bounds(
    series: pd.Series,
    lower: float | None,
    upper: float | None,
) -> pd.Series:
    output = series.copy()
    if lower is not None:
        output = output.clip(lower=lower)
    if upper is not None:
        output = output.clip(upper=upper)
    return output


def clip_value_to_bounds(value: float, lower: float | None, upper: float | None) -> float:
    if lower is not None:
        value = max(value, lower)
    if upper is not None:
        value = min(value, upper)
    return value
