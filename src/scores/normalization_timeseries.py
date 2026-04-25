"""Step 10A ticker-local time-series normalization primitives.

This module implements only time-series normalization. It does not perform
cross-sectional normalization, ranking, composite scoring, valuation scoring,
forward-return labeling, or backtesting.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
import math
import re
import tomllib

import pandas as pd

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
TICKER_PATTERN = re.compile(r"^[0-9A-Z]{6}$")


@dataclass(frozen=True)
class TimeSeriesNormalizationConfig:
    """Configuration for ticker-local robust z-score normalization.

    `window=None` means expanding context. A positive `window` means each row
    uses at most that many same-ticker rows ending at the current row. The
    context never uses future rows and never crosses ticker boundaries.
    """

    window: int | None = 252
    min_periods: int = 60
    mad_scale: float = 1.4826
    iqr_scale: float = 1.349
    use_iqr_fallback: bool = True
    winsorize_lower_pct: float | None = 0.01
    winsorize_upper_pct: float | None = 0.99
    clip_lower: float | None = None
    clip_upper: float | None = None

    def __post_init__(self) -> None:
        if self.window is not None and self.window <= 0:
            raise ValueError("Time-series normalization window must be positive or None.")
        if self.min_periods <= 0:
            raise ValueError("Time-series normalization min_periods must be positive.")
        if self.mad_scale <= 0:
            raise ValueError("MAD scale must be positive.")
        if self.iqr_scale <= 0:
            raise ValueError("IQR scale must be positive.")
        _validate_percentile_bounds(self.winsorize_lower_pct, self.winsorize_upper_pct)
        _validate_clip_bounds(self.clip_lower, self.clip_upper)


def load_timeseries_normalization_config(
    *,
    windows_config_path: str | Path = "Quant_mvp/config/windows.toml",
    thresholds_config_path: str | Path = "Quant_mvp/config/thresholds.toml",
) -> TimeSeriesNormalizationConfig:
    """Load Step 10A time-series normalization defaults from Quant config.

    Reads:
    - `Quant_mvp/config/windows.toml -> [normalization].time_series_window`
    - `Quant_mvp/config/thresholds.toml -> [quality].min_non_nan_observations`
    - `Quant_mvp/config/thresholds.toml -> [outliers].winsorize_lower_pct`
    - `Quant_mvp/config/thresholds.toml -> [outliers].winsorize_upper_pct`

    Robust z-score clipping bounds are not configured yet, so they default to
    `None` unless explicitly passed in a test or downstream caller config.
    """

    windows_config = _load_toml(Path(windows_config_path))
    thresholds_config = _load_toml(Path(thresholds_config_path))
    normalization = windows_config.get("normalization", {})
    quality = thresholds_config.get("quality", {})
    outliers = thresholds_config.get("outliers", {})
    return TimeSeriesNormalizationConfig(
        window=_positive_int_or_none(
            normalization.get("time_series_window"),
            "normalization.time_series_window",
        ),
        min_periods=_positive_int(
            quality.get("min_non_nan_observations"),
            "quality.min_non_nan_observations",
        ),
        winsorize_lower_pct=_optional_float(
            outliers.get("winsorize_lower_pct"),
            "outliers.winsorize_lower_pct",
        ),
        winsorize_upper_pct=_optional_float(
            outliers.get("winsorize_upper_pct"),
            "outliers.winsorize_upper_pct",
        ),
    )


def normalize_timeseries_scores(
    frame: pd.DataFrame,
    *,
    raw_score_columns: Sequence[str] | None = None,
    config: TimeSeriesNormalizationConfig | None = None,
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

    data = _prepare_timeseries_input(frame, required_columns=selected)
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
) -> pd.DataFrame:
    """Normalize a single raw score column using ticker-local history only.

    The function sorts by `ticker`, `date`, rejects duplicate ticker/date pairs,
    preserves leading-zero tickers as strings, and calculates each row from same
    ticker observations with `date <= current date`.
    """

    data = _prepare_timeseries_input(frame, required_columns=(raw_score_column,))
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
    """Winsorize finite numeric values and return value plus diagnostics.

    Output columns are `value`, `was_winsorized`, `lower_bound`, and
    `upper_bound`. NaN, non-numeric, and infinite inputs remain missing.
    """

    _validate_percentile_bounds(lower_pct, upper_pct)
    numeric = _to_numeric_series(pd.Series(values))
    finite = _finite_mask(numeric)
    output = numeric.where(finite)
    if not finite.any() or (lower_pct is None and upper_pct is None):
        return _bounded_result(output, pd.Series(False, index=numeric.index), None, None, "was_winsorized")

    finite_values = numeric.loc[finite].astype(float)
    lower_bound = float(finite_values.quantile(lower_pct)) if lower_pct is not None else None
    upper_bound = float(finite_values.quantile(upper_pct)) if upper_pct is not None else None
    clipped = _clip_series_to_bounds(finite_values, lower_bound, upper_bound)
    output.loc[finite] = clipped
    changed = finite & output.ne(numeric)
    return _bounded_result(output, changed, lower_bound, upper_bound, "was_winsorized")


def apply_clipping(
    values: Iterable[object],
    *,
    lower: float | None = None,
    upper: float | None = None,
) -> pd.DataFrame:
    """Clip finite numeric values to explicit bounds and return diagnostics.

    Output columns are `value`, `was_clipped`, `lower_bound`, and `upper_bound`.
    If both bounds are `None`, values are returned unchanged except that
    non-finite values remain missing.
    """

    _validate_clip_bounds(lower, upper)
    numeric = _to_numeric_series(pd.Series(values))
    finite = _finite_mask(numeric)
    output = numeric.where(finite)
    if not finite.any() or (lower is None and upper is None):
        return _bounded_result(output, pd.Series(False, index=numeric.index), lower, upper, "was_clipped")

    clipped = _clip_series_to_bounds(numeric.loc[finite].astype(float), lower, upper)
    output.loc[finite] = clipped
    changed = finite & output.ne(numeric)
    return _bounded_result(output, changed, lower, upper, "was_clipped")


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
    numeric = _to_numeric_series(raw)
    finite = _finite_mask(numeric)
    invalid = raw.notna() & (~finite) & numeric.notna()
    invalid = invalid | (raw.notna() & numeric.isna())
    missing = raw.isna()
    finite_values = numeric.where(finite)

    normalized_values: list[float | pd.NA] = []
    statuses: list[str] = []
    coverage_statuses: list[str] = []
    quality_flags: list[str] = []
    observation_counts: list[int] = []
    scales: list[float | pd.NA] = []
    scale_methods: list[str | pd.NA] = []
    winsorized_values: list[float | pd.NA] = []
    was_winsorized: list[bool] = []
    was_clipped: list[bool] = []

    warmup_values = (
        upstream_warmup.reset_index(drop=True).astype("string") if upstream_warmup is not None else None
    )
    minimum_history_values = (
        pd.to_numeric(minimum_history.reset_index(drop=True), errors="coerce")
        if minimum_history is not None
        else None
    )

    for position in range(len(raw)):
        context = _context_values(finite_values, position=position, window=config.window)
        observation_count = int(context.count())
        row_min_periods = _row_min_periods(config.min_periods, minimum_history_values, position)
        upstream_status = _upstream_status(warmup_values, position)

        normalized_value: float | pd.NA = pd.NA
        status = STATUS_OK
        scale: float | pd.NA = pd.NA
        scale_method: str | pd.NA = pd.NA
        current_winsorized: float | pd.NA = pd.NA
        current_was_winsorized = False
        current_was_clipped = False

        if upstream_status is not None:
            status = upstream_status
        elif bool(missing.iloc[position]):
            status = STATUS_MISSING_RAW_SCORE
        elif bool(invalid.iloc[position]):
            status = STATUS_INVALID_RAW_SCORE
        elif observation_count < row_min_periods:
            status = STATUS_WARMUP
        else:
            current_raw = float(numeric.iloc[position])
            context_result = _robust_zscore_for_context(
                context.astype(float),
                current_raw=current_raw,
                config=config,
            )
            status = context_result["status"]
            normalized_value = context_result["value"]
            scale = context_result["scale"]
            scale_method = context_result["scale_method"]
            current_winsorized = context_result["winsorized_value"]
            current_was_winsorized = bool(context_result["was_winsorized"])
            current_was_clipped = bool(context_result["was_clipped"])

        normalized_values.append(normalized_value)
        statuses.append(status)
        coverage_statuses.append("adequate" if status == STATUS_OK else "blocked")
        quality_flags.append(_quality_flag(status, current_was_winsorized, current_was_clipped))
        observation_counts.append(observation_count)
        scales.append(scale)
        scale_methods.append(scale_method)
        winsorized_values.append(current_winsorized)
        was_winsorized.append(current_was_winsorized)
        was_clipped.append(current_was_clipped)

    return pd.DataFrame(
        {
            ROBUST_ZSCORE_COLUMN: normalized_values,
            "status": statuses,
            "coverage_status": coverage_statuses,
            "data_quality_flag": quality_flags,
            "observation_count": observation_counts,
            "scale": scales,
            "scale_method": scale_methods,
            "winsorized_value": winsorized_values,
            "was_winsorized": was_winsorized,
            "was_clipped": was_clipped,
        },
        index=raw.index,
    )


def _robust_zscore_for_context(
    context: pd.Series,
    *,
    current_raw: float,
    config: TimeSeriesNormalizationConfig,
) -> dict[str, object]:
    winsorized_context = context.copy()
    winsorized_current = current_raw
    was_winsorized = False
    if config.winsorize_lower_pct is not None or config.winsorize_upper_pct is not None:
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
        winsorized_context = _clip_series_to_bounds(context, lower, upper)
        winsorized_current = float(_clip_value_to_bounds(current_raw, lower, upper))
        was_winsorized = not math.isclose(winsorized_current, current_raw, rel_tol=0.0, abs_tol=0.0)

    median = float(winsorized_context.median())
    mad = float((winsorized_context - median).abs().median())
    scale = mad * config.mad_scale
    scale_method = "mad"

    if not _positive_finite(scale):
        if config.use_iqr_fallback:
            iqr = float(winsorized_context.quantile(0.75) - winsorized_context.quantile(0.25))
            fallback_scale = iqr / config.iqr_scale
            if _positive_finite(fallback_scale):
                scale = fallback_scale
                scale_method = "iqr"
        if not _positive_finite(scale):
            return {
                "value": pd.NA,
                "status": STATUS_ZERO_SCALE,
                "scale": pd.NA,
                "scale_method": pd.NA,
                "winsorized_value": winsorized_current,
                "was_winsorized": was_winsorized,
                "was_clipped": False,
            }

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


def _prepare_timeseries_input(
    frame: pd.DataFrame,
    *,
    required_columns: Sequence[str],
) -> pd.DataFrame:
    require_columns(frame, (*IDENTITY_COLUMNS, *required_columns), context="Step 10A input")
    assert_no_forbidden_output_columns(frame, context="Step 10A input")
    assert_no_valuation_fundamental_columns(frame, context="Step 10A input")

    data = frame.copy()
    data["ticker"] = data["ticker"].astype("string").str.strip()
    valid_ticker = data["ticker"].map(
        lambda value: isinstance(value, str) and bool(TICKER_PATTERN.fullmatch(value)),
        na_action="ignore",
    ).fillna(False)
    if (~valid_ticker).any():
        raise ValueError("Step 10A input ticker must be six-character string values.")

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


def _to_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _finite_mask(series: pd.Series) -> pd.Series:
    return series.map(lambda value: pd.notna(value) and math.isfinite(float(value)))


def _positive_finite(value: float) -> bool:
    return pd.notna(value) and math.isfinite(float(value)) and value > 0


def _clip_series_to_bounds(
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


def _clip_value_to_bounds(value: float, lower: float | None, upper: float | None) -> float:
    if lower is not None:
        value = max(value, lower)
    if upper is not None:
        value = min(value, upper)
    return value


def _bounded_result(
    values: pd.Series,
    changed: pd.Series,
    lower: float | None,
    upper: float | None,
    changed_column: str,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "value": values.astype("Float64"),
            changed_column: changed.astype("boolean"),
            "lower_bound": pd.Series(lower, index=values.index, dtype="Float64"),
            "upper_bound": pd.Series(upper, index=values.index, dtype="Float64"),
        }
    )


def _validate_percentile_bounds(lower: float | None, upper: float | None) -> None:
    if lower is not None and not 0 <= lower <= 1:
        raise ValueError("Winsorization lower percentile must be between 0 and 1.")
    if upper is not None and not 0 <= upper <= 1:
        raise ValueError("Winsorization upper percentile must be between 0 and 1.")
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("Winsorization lower percentile must be <= upper percentile.")


def _validate_clip_bounds(lower: float | None, upper: float | None) -> None:
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("Clip lower bound must be <= upper bound.")


def _load_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _positive_int(value: object, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Config value {name} must be a positive integer.") from exc
    if isinstance(value, bool) or parsed <= 0:
        raise ValueError(f"Config value {name} must be a positive integer.")
    return parsed


def _positive_int_or_none(value: object, name: str) -> int | None:
    if value is None:
        return None
    return _positive_int(value, name)


def _optional_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Config value {name} must be numeric or omitted.") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"Config value {name} must be finite.")
    return parsed
