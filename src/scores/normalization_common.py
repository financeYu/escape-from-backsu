"""Shared normalization helpers for Step 10 engines.

The helpers in this module are structural support only. They do not define new
scores, ranking behavior, composite behavior, backtest labels, or valuation
logic.
"""

from __future__ import annotations

import math
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd


def load_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def positive_int(value: object, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Config value {name} must be a positive integer.") from exc
    if isinstance(value, bool) or parsed <= 0:
        raise ValueError(f"Config value {name} must be a positive integer.")
    return parsed


def positive_int_or_none(value: object, name: str) -> int | None:
    if value is None:
        return None
    return positive_int(value, name)


def optional_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Config value {name} must be numeric or omitted.") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"Config value {name} must be finite.")
    return parsed


def to_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def finite_mask(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    finite_values = np.isfinite(numeric.to_numpy(dtype=float, na_value=np.nan))
    return pd.Series(finite_values, index=series.index)


def positive_finite(value: float) -> bool:
    return pd.notna(value) and math.isfinite(float(value)) and value > 0


def validate_percentile_bounds(lower: float | None, upper: float | None) -> None:
    if lower is not None and not 0 <= lower <= 1:
        raise ValueError("Winsorization lower percentile must be between 0 and 1.")
    if upper is not None and not 0 <= upper <= 1:
        raise ValueError("Winsorization upper percentile must be between 0 and 1.")
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("Winsorization lower percentile must be <= upper percentile.")


def validate_clip_bounds(lower: float | None, upper: float | None) -> None:
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("Clip lower bound must be <= upper bound.")


def validate_positive_clip(value: float | None, name: str = "zscore_clip") -> None:
    if value is not None and value <= 0:
        raise ValueError(f"{name} must be positive when provided.")


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


def bounded_result(
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


def apply_winsorization(
    values: object,
    *,
    lower_pct: float | None = 0.01,
    upper_pct: float | None = 0.99,
) -> pd.DataFrame:
    validate_percentile_bounds(lower_pct, upper_pct)
    numeric = to_numeric_series(pd.Series(values))
    finite = finite_mask(numeric)
    output = numeric.where(finite)
    if not finite.any() or (lower_pct is None and upper_pct is None):
        changed = pd.Series(False, index=numeric.index)
        return bounded_result(output, changed, None, None, "was_winsorized")

    finite_values = numeric.loc[finite].astype(float)
    lower_bound = float(finite_values.quantile(lower_pct)) if lower_pct is not None else None
    upper_bound = float(finite_values.quantile(upper_pct)) if upper_pct is not None else None
    clipped = clip_series_to_bounds(finite_values, lower_bound, upper_bound)
    output.loc[finite] = clipped
    changed = finite & output.ne(numeric)
    return bounded_result(output, changed, lower_bound, upper_bound, "was_winsorized")


def apply_clipping(
    values: object,
    *,
    lower: float | None = None,
    upper: float | None = None,
) -> pd.DataFrame:
    validate_clip_bounds(lower, upper)
    numeric = to_numeric_series(pd.Series(values))
    finite = finite_mask(numeric)
    output = numeric.where(finite)
    if not finite.any() or (lower is None and upper is None):
        changed = pd.Series(False, index=numeric.index)
        return bounded_result(output, changed, lower, upper, "was_clipped")

    clipped = clip_series_to_bounds(numeric.loc[finite].astype(float), lower, upper)
    output.loc[finite] = clipped
    changed = finite & output.ne(numeric)
    return bounded_result(output, changed, lower, upper, "was_clipped")


def flags_to_series(
    flags: dict[object, set[str]],
    index: pd.Index,
    *,
    flag_order: tuple[str, ...],
) -> pd.Series:
    return pd.Series(
        [format_flags(flags[item], flag_order=flag_order) for item in index],
        index=index,
        dtype="string",
    )


def format_flags(flags: set[str], *, flag_order: tuple[str, ...]) -> str:
    cleaned = {flag for flag in flags if flag and flag != "valid"}
    if not cleaned:
        return "valid"
    ordered = [flag for flag in flag_order if flag in cleaned]
    ordered.extend(sorted(cleaned.difference(ordered)))
    return ";".join(ordered)
