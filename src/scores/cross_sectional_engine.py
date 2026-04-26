"""Step 10B cross-sectional normalization primitives.

Input schema:
- identity columns: ``ticker``, ``date``
- Step 9 raw score columns such as ``short_term_overreaction_raw``
- Step 9 metadata columns: ``score_warmup_state``, ``score_coverage_status``,
  ``score_data_quality_flag``, ``minimum_history_required``

Output schema:
- preserves ``ticker``/``date`` alignment and source metadata
- emits per-score ``*_cross_sectional_robust_z`` values and review metadata
- does not emit ranking, composite, backtest, forward-return, or valuation
  columns

This module intentionally contains no ticker-local time-series normalization.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
import numpy as np
import pandas as pd

from .cross_sectional_config import (
    CrossSectionalNormalizationConfig,
    load_cross_sectional_normalization_config,
)
from .normalization_common import finite_mask, flags_to_series
from .schema import (
    IDENTITY_COLUMNS,
    SCORE_METADATA_COLUMNS,
    assert_no_forbidden_output_columns,
    assert_no_valuation_fundamental_columns,
    require_columns,
)


STEP9_RAW_SCORE_COLUMNS: tuple[str, ...] = (
    "short_term_overreaction_raw",
    "atr_adjusted_oversold_distance_raw",
    "donchian_breakout_distance_raw",
    "bollinger_width_squeeze_raw",
    "cmf_confirmation_raw",
    "rsi_price_divergence_raw",
    "realized_vol_percentile_raw",
    "efficiency_ratio_trend_raw",
)

ELIGIBLE_COVERAGE_STATUSES = frozenset({"adequate", "partial", "sparse"})
BLOCKING_QUALITY_FLAGS = frozenset(
    {
        "invalid_ticker",
        "leading_zero_lost",
        "invalid_date",
        "future_date",
        "duplicate_ticker_date",
    }
)
FLAG_ORDER = (
    "missing_required_input",
    "invalid_numeric",
    "warmup",
    "insufficient_history",
    "blocked_by_missing_dependency",
    "coverage_blocked",
    "coverage_unknown",
    "insufficient_cross_section",
    "zero_dispersion",
    "winsorized_outlier",
    "clipped_outlier",
    "invalid_ticker",
    "leading_zero_lost",
    "invalid_date",
    "future_date",
    "duplicate_ticker_date",
    "unknown",
)


def robust_zscore_cross_sectional(
    values: pd.Series,
    *,
    config: CrossSectionalNormalizationConfig | None = None,
    min_count: int | None = None,
    winsorize_lower_pct: float | None = None,
    winsorize_upper_pct: float | None = None,
    zscore_clip: float | None = None,
) -> pd.DataFrame:
    """Return robust z-scores for one same-date cross-section.

    ``values`` must represent a single cross-sectional context. NaN and
    infinite values are excluded from the median/MAD denominator and retain
    missing/invalid flags. Tied finite values receive identical z-scores.
    When the context has too few finite observations or zero dispersion, the
    normalized value is left missing rather than filled optimistically.
    """

    active_config = _merge_config(
        config=config,
        min_count=min_count,
        winsorize_lower_pct=winsorize_lower_pct,
        winsorize_upper_pct=winsorize_upper_pct,
        zscore_clip=zscore_clip,
    )
    numeric = pd.to_numeric(values, errors="coerce")
    finite = finite_mask(numeric)
    valid_count = int(finite.sum())

    result = pd.DataFrame(index=values.index)
    result["cross_sectional_robust_z"] = pd.Series(pd.NA, index=values.index, dtype="Float64")
    result["cross_sectional_valid_count"] = valid_count
    result["cross_sectional_status"] = pd.Series("blocked", index=values.index, dtype="string")
    result["cross_sectional_scale_method"] = pd.Series(
        "insufficient_count", index=values.index, dtype="string"
    )
    result["cross_sectional_winsorized"] = False
    result["cross_sectional_clipped"] = False

    row_flags = _initial_value_flags(values, numeric, finite)
    if valid_count < active_config.min_count:
        for index in values.index:
            row_flags[index].add("insufficient_cross_section")
        result["cross_sectional_quality_flag"] = flags_to_series(row_flags, values.index, flag_order=FLAG_ORDER)
        return result

    finite_values = numeric.loc[finite].astype(float)
    winsorized = _winsorize(finite_values, active_config)
    winsorized_mask = ~np.isclose(
        finite_values.to_numpy(dtype=float),
        winsorized.to_numpy(dtype=float),
        equal_nan=True,
    )
    if winsorized_mask.any():
        changed_index = finite_values.index[winsorized_mask]
        result.loc[changed_index, "cross_sectional_winsorized"] = True
        for index in changed_index:
            row_flags[index].add("winsorized_outlier")

    median = float(winsorized.median())
    mad = float((winsorized - median).abs().median())
    scale_method = "mad"
    scale = mad * active_config.mad_scale_factor

    if not np.isfinite(scale) or scale <= 0:
        q75 = float(winsorized.quantile(0.75))
        q25 = float(winsorized.quantile(0.25))
        iqr_scale = (q75 - q25) / 1.349
        if np.isfinite(iqr_scale) and iqr_scale > 0:
            scale = iqr_scale
            scale_method = "iqr_fallback"
        else:
            result.loc[finite_values.index, "cross_sectional_scale_method"] = "zero_dispersion"
            for index in values.index:
                row_flags[index].add("zero_dispersion")
            result["cross_sectional_quality_flag"] = flags_to_series(row_flags, values.index, flag_order=FLAG_ORDER)
            return result

    z_values = (winsorized - median) / scale
    if active_config.zscore_clip is not None:
        clipped = z_values.clip(-active_config.zscore_clip, active_config.zscore_clip)
        clipped_mask = ~np.isclose(
            z_values.to_numpy(dtype=float),
            clipped.to_numpy(dtype=float),
            equal_nan=True,
        )
        if clipped_mask.any():
            changed_index = z_values.index[clipped_mask]
            result.loc[changed_index, "cross_sectional_clipped"] = True
            for index in changed_index:
                row_flags[index].add("clipped_outlier")
        z_values = clipped

    result.loc[finite_values.index, "cross_sectional_robust_z"] = z_values.astype(float)
    result.loc[finite_values.index, "cross_sectional_status"] = "adequate"
    result.loc[finite_values.index, "cross_sectional_scale_method"] = scale_method
    result["cross_sectional_quality_flag"] = flags_to_series(row_flags, values.index, flag_order=FLAG_ORDER)
    return result


def normalize_cross_sectional_score(
    frame: pd.DataFrame,
    raw_column: str,
    *,
    score_name: str | None = None,
    config: CrossSectionalNormalizationConfig | None = None,
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Normalize one Step 9 raw score within each same-date cross-section.

    Rows with missing/non-finite raw values, non-ready warmup status, blocked
    coverage, or hard data-quality flags are excluded from the same-date
    denominator. The returned frame preserves one row per input ``ticker`` and
    ``date`` and does not create ranking or composite columns.
    """

    prepared = prepare_cross_sectional_input_frame(
        frame,
        raw_score_columns=(raw_column,),
        as_of_date=as_of_date,
    )
    active_config = config or load_cross_sectional_normalization_config()
    normalized_name = score_name or score_name_from_raw_column(raw_column)
    numeric = pd.to_numeric(prepared[raw_column], errors="coerce")
    finite = finite_mask(numeric)
    eligible = eligible_cross_sectional_observations(prepared, raw_column)
    context_values = numeric.where(eligible)

    parts: list[pd.DataFrame] = []
    for _, group in prepared.groupby("date", sort=False):
        parts.append(
            robust_zscore_cross_sectional(
                context_values.loc[group.index],
                config=active_config,
            )
        )
    generic = pd.concat(parts).sort_index()

    quality_flags = _score_quality_flags(
        prepared=prepared,
        raw_column=raw_column,
        numeric=numeric,
        finite=finite,
        eligible=eligible,
        generic=generic,
    )
    result = prepared.loc[
        :,
        [
            *IDENTITY_COLUMNS,
            raw_column,
            *SCORE_METADATA_COLUMNS,
        ],
    ].copy()
    prefix = f"{normalized_name}_cross_sectional"
    result[f"{prefix}_robust_z"] = generic["cross_sectional_robust_z"].astype("Float64")
    result[f"{prefix}_valid_count"] = generic["cross_sectional_valid_count"].astype("Int64")
    result[f"{prefix}_status"] = generic["cross_sectional_status"].astype("string")
    result[f"{prefix}_scale_method"] = generic["cross_sectional_scale_method"].astype("string")
    result[f"{prefix}_quality_flag"] = quality_flags.astype("string")
    result[f"{prefix}_winsorized"] = generic["cross_sectional_winsorized"].astype(bool)
    result[f"{prefix}_clipped"] = generic["cross_sectional_clipped"].astype(bool)
    return result.reset_index(drop=True)


def normalize_cross_sectional_scores(
    frame: pd.DataFrame,
    raw_score_columns: Sequence[str] | None = None,
    *,
    config: CrossSectionalNormalizationConfig | None = None,
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Normalize multiple Step 9 raw score columns by same-date cross-section.

    If ``raw_score_columns`` is omitted, the function uses the known Step 9 raw
    score columns that are present in ``frame``. It does not perform time-series
    normalization and does not create rank, composite, forward-return, backtest,
    or valuation columns.
    """

    selected_columns = tuple(raw_score_columns or _present_step9_raw_columns(frame.columns))
    if not selected_columns:
        raise ValueError("No raw score columns were provided or found.")

    active_config = config or load_cross_sectional_normalization_config()
    prepared = prepare_cross_sectional_input_frame(
        frame,
        raw_score_columns=selected_columns,
        as_of_date=as_of_date,
    )
    combined = prepared.loc[:, [*IDENTITY_COLUMNS, *selected_columns, *SCORE_METADATA_COLUMNS]].copy()
    for raw_column in selected_columns:
        one_score = normalize_cross_sectional_score(
            prepared,
            raw_column,
            config=active_config,
            as_of_date=as_of_date,
        )
        prefix = f"{score_name_from_raw_column(raw_column)}_cross_sectional"
        for suffix in (
            "robust_z",
            "valid_count",
            "status",
            "scale_method",
            "quality_flag",
            "winsorized",
            "clipped",
        ):
            combined[f"{prefix}_{suffix}"] = one_score[f"{prefix}_{suffix}"]
    return combined.reset_index(drop=True)


def prepare_cross_sectional_input_frame(
    frame: pd.DataFrame,
    *,
    raw_score_columns: Sequence[str],
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Validate and coerce Step 9 raw score input for Step 10B normalization."""

    required = (*IDENTITY_COLUMNS, *SCORE_METADATA_COLUMNS, *raw_score_columns)
    require_columns(frame, required, context="Step 10B cross-sectional normalization input")
    assert_no_forbidden_output_columns(
        frame, context="Step 10B cross-sectional normalization input"
    )
    assert_no_valuation_fundamental_columns(
        frame, context="Step 10B cross-sectional normalization input"
    )

    prepared = frame.loc[:, list(dict.fromkeys(required))].copy()
    prepared["ticker"] = _coerce_ticker(prepared["ticker"])
    parsed_dates = pd.to_datetime(prepared["date"], errors="coerce")
    if parsed_dates.isna().any():
        bad_count = int(parsed_dates.isna().sum())
        raise ValueError(f"Step 10B input contains {bad_count} invalid date value(s).")
    prepared["date"] = parsed_dates.dt.normalize()
    if as_of_date is not None:
        parsed_as_of = pd.Timestamp(as_of_date).normalize()
        if prepared["date"].gt(parsed_as_of).any():
            raise ValueError("Step 10B input contains dates after as_of_date.")
    duplicate_mask = prepared.duplicated(list(IDENTITY_COLUMNS), keep=False)
    if duplicate_mask.any():
        duplicates = prepared.loc[duplicate_mask, list(IDENTITY_COLUMNS)]
        preview = duplicates.head(5).to_dict(orient="records")
        raise ValueError(f"Duplicate ticker/date rows are not allowed: {preview}")
    return prepared


def eligible_cross_sectional_observations(frame: pd.DataFrame, raw_column: str) -> pd.Series:
    """Return the rows allowed into a same-date denominator for ``raw_column``."""

    require_columns(
        frame,
        (*IDENTITY_COLUMNS, *SCORE_METADATA_COLUMNS, raw_column),
        context="Step 10B cross-sectional eligibility input",
    )
    numeric = pd.to_numeric(frame[raw_column], errors="coerce")
    finite = finite_mask(numeric)
    warmup_ready = frame["score_warmup_state"].astype("string").fillna("unknown").eq("ready")
    coverage_allowed = (
        frame["score_coverage_status"]
        .astype("string")
        .fillna("unknown")
        .isin(ELIGIBLE_COVERAGE_STATUSES)
    )
    hard_quality_block = frame["score_data_quality_flag"].map(_has_blocking_quality_flag)
    return finite & warmup_ready & coverage_allowed & ~hard_quality_block


def score_name_from_raw_column(raw_column: str) -> str:
    """Convert ``*_raw`` Step 9 column names to canonical score names."""

    if raw_column.endswith("_raw"):
        return raw_column[: -len("_raw")]
    return raw_column


def _merge_config(
    *,
    config: CrossSectionalNormalizationConfig | None,
    min_count: int | None,
    winsorize_lower_pct: float | None,
    winsorize_upper_pct: float | None,
    zscore_clip: float | None,
) -> CrossSectionalNormalizationConfig:
    base = config or CrossSectionalNormalizationConfig()
    return CrossSectionalNormalizationConfig(
        min_count=base.min_count if min_count is None else min_count,
        mad_scale_factor=base.mad_scale_factor,
        winsorize_lower_pct=(
            base.winsorize_lower_pct
            if winsorize_lower_pct is None
            else winsorize_lower_pct
        ),
        winsorize_upper_pct=(
            base.winsorize_upper_pct
            if winsorize_upper_pct is None
            else winsorize_upper_pct
        ),
        zscore_clip=base.zscore_clip if zscore_clip is None else zscore_clip,
    )


def _present_step9_raw_columns(columns: Iterable[str]) -> tuple[str, ...]:
    present = set(columns)
    return tuple(column for column in STEP9_RAW_SCORE_COLUMNS if column in present)


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


def _winsorize(
    values: pd.Series, config: CrossSectionalNormalizationConfig
) -> pd.Series:
    output = values.copy()
    if config.winsorize_lower_pct is not None:
        lower = float(output.quantile(config.winsorize_lower_pct))
        output = output.clip(lower=lower)
    if config.winsorize_upper_pct is not None:
        upper = float(output.quantile(config.winsorize_upper_pct))
        output = output.clip(upper=upper)
    return output


def _initial_value_flags(
    original: pd.Series, numeric: pd.Series, finite: pd.Series
) -> dict[object, set[str]]:
    flags: dict[object, set[str]] = {index: set() for index in original.index}
    for index in original.index:
        if pd.isna(original.loc[index]):
            flags[index].add("missing_required_input")
        elif pd.isna(numeric.loc[index]) or not bool(finite.loc[index]):
            flags[index].add("invalid_numeric")
    return flags


def _score_quality_flags(
    *,
    prepared: pd.DataFrame,
    raw_column: str,
    numeric: pd.Series,
    finite: pd.Series,
    eligible: pd.Series,
    generic: pd.DataFrame,
) -> pd.Series:
    flags = _initial_value_flags(prepared[raw_column], numeric, finite)
    for index in prepared.index:
        for original_flag in _split_flags(prepared.at[index, "score_data_quality_flag"]):
            flags[index].add(original_flag)
        warmup = str(prepared.at[index, "score_warmup_state"])
        if warmup != "ready":
            flags[index].add(warmup if warmup else "unknown")
        coverage = str(prepared.at[index, "score_coverage_status"])
        if coverage not in ELIGIBLE_COVERAGE_STATUSES:
            flags[index].add("coverage_blocked" if coverage == "blocked" else "coverage_unknown")
        for generated_flag in _split_flags(generic.at[index, "cross_sectional_quality_flag"]):
            flags[index].add(generated_flag)
        if not bool(eligible.loc[index]) and "valid" in flags[index]:
            flags[index].remove("valid")
    return flags_to_series(flags, prepared.index, flag_order=FLAG_ORDER)


def _split_flags(value: object) -> tuple[str, ...]:
    if pd.isna(value):
        return ("unknown",)
    flags = tuple(
        part.strip()
        for part in str(value).split(";")
        if part.strip() and part.strip() != "valid"
    )
    return flags


def _has_blocking_quality_flag(value: object) -> bool:
    return bool(BLOCKING_QUALITY_FLAGS.intersection(_split_flags(value)))


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


def _optional_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Config value {name} must be numeric or omitted.") from exc
    if not np.isfinite(parsed):
        raise ValueError(f"Config value {name} must be finite.")
    return parsed
