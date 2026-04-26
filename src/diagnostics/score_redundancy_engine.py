"""Step 12 score redundancy and correlation diagnostics.

This module computes same-date cross-sectional Spearman correlations between
normalized/component score columns. It is diagnostic review material only: it
does not create rankings, composite scores, signals, valuation fields,
forward-return labels, or backtest outputs.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from .score_redundancy_config import (
    ScoreRedundancyConfig,
    ScoreRedundancyConfigError,
    load_score_redundancy_config,
)
from .score_redundancy_inputs import (
    RedundancyScoreInput,
    _finite_mask,
    _missing_score_columns,
    _numeric_score_values,
    _resolve_score_inputs,
    prepare_redundancy_input_frame,
)


PAIR_SUMMARY_COLUMNS = (
    "score_a",
    "score_b",
    "dates_evaluated",
    "dates_insufficient",
    "min_pair_observations",
    "median_pair_observations",
    "median_spearman",
    "mean_spearman",
    "max_abs_spearman",
    "redundancy_status",
    "redundancy_reason",
)
PAIR_DATE_COLUMNS = (
    "score_a",
    "score_b",
    "date",
    "pair_observations",
    "spearman",
    "diagnostic_status",
    "diagnostic_reason",
)


def calculate_score_pair_correlations(
    frame: pd.DataFrame,
    *,
    score_inputs: Sequence[RedundancyScoreInput] | None = None,
    score_columns: Sequence[str] | None = None,
    config: ScoreRedundancyConfig | None = None,
    thresholds_config_path: str | Path = "Quant_mvp/config/thresholds.toml",
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Return per-date same-cross-section Spearman diagnostics by score pair."""

    active_inputs = _resolve_score_inputs(score_inputs, score_columns)
    prepared = prepare_redundancy_input_frame(
        frame,
        score_inputs=active_inputs,
        as_of_date=as_of_date,
    )
    if len(active_inputs) < 2:
        return pd.DataFrame(columns=PAIR_DATE_COLUMNS)

    active_config = config or load_score_redundancy_config(
        thresholds_config_path=thresholds_config_path
    )

    rows: list[dict[str, object]] = []
    for left, right in combinations(active_inputs, 2):
        missing = _missing_score_columns(prepared, (left, right))
        if missing:
            rows.append(_missing_pair_detail(left, right, missing))
            continue
        rows.extend(
            _date_pair_correlation_row(group, left, right, active_config, date_value)
            for date_value, group in prepared.groupby("date", sort=True)
        )
    return pd.DataFrame(rows, columns=PAIR_DATE_COLUMNS)


def summarize_score_redundancy(
    frame: pd.DataFrame,
    *,
    score_inputs: Sequence[RedundancyScoreInput] | None = None,
    score_columns: Sequence[str] | None = None,
    config: ScoreRedundancyConfig | None = None,
    thresholds_config_path: str | Path = "Quant_mvp/config/thresholds.toml",
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Return pair-level Step 12 redundancy summary diagnostics."""

    active_inputs = _resolve_score_inputs(score_inputs, score_columns)
    prepared = prepare_redundancy_input_frame(
        frame,
        score_inputs=active_inputs,
        as_of_date=as_of_date,
    )
    if len(active_inputs) < 2:
        return pd.DataFrame(columns=PAIR_SUMMARY_COLUMNS)

    try:
        active_config = config or load_score_redundancy_config(
            thresholds_config_path=thresholds_config_path
        )
    except ScoreRedundancyConfigError as exc:
        return _config_missing_summary(active_inputs, str(exc))

    details = calculate_score_pair_correlations(
        prepared,
        score_inputs=active_inputs,
        config=active_config,
    )
    if details.empty:
        return pd.DataFrame(columns=PAIR_SUMMARY_COLUMNS)

    rows = [
        _summarize_pair(group, active_config)
        for _, group in details.groupby(["score_a", "score_b"], sort=False)
    ]
    return pd.DataFrame(rows, columns=PAIR_SUMMARY_COLUMNS)


def _date_pair_correlation_row(
    group: pd.DataFrame,
    left: RedundancyScoreInput,
    right: RedundancyScoreInput,
    config: ScoreRedundancyConfig,
    date_value: pd.Timestamp,
) -> dict[str, object]:
    pair = _valid_pair_values(group, left, right)
    observations = int(len(pair))
    if observations < config.min_cross_section_count:
        return _pair_detail_row(
            left,
            right,
            date_value,
            observations=observations,
            spearman=pd.NA,
            status="insufficient_data",
            reason="pair_observations_below_min_cross_section_count",
        )
    if pair["left"].nunique(dropna=True) < 2 or pair["right"].nunique(dropna=True) < 2:
        return _pair_detail_row(
            left,
            right,
            date_value,
            observations=observations,
            spearman=pd.NA,
            status="undefined_correlation",
            reason="constant_score_column",
        )
    spearman = _spearman_correlation(pair["left"], pair["right"])
    if pd.isna(spearman) or not np.isfinite(float(spearman)):
        return _pair_detail_row(
            left,
            right,
            date_value,
            observations=observations,
            spearman=pd.NA,
            status="undefined_correlation",
            reason="spearman_not_defined",
        )
    return _pair_detail_row(
        left,
        right,
        date_value,
        observations=observations,
        spearman=float(spearman),
        status="ok",
        reason="same_date_cross_section_spearman",
    )


def _valid_pair_values(
    group: pd.DataFrame,
    left: RedundancyScoreInput,
    right: RedundancyScoreInput,
) -> pd.DataFrame:
    left_values = _numeric_score_values(group, left)
    right_values = _numeric_score_values(group, right)
    pair_valid = _finite_mask(left_values) & _finite_mask(right_values)
    return pd.DataFrame(
        {
            "left": left_values.loc[pair_valid],
            "right": right_values.loc[pair_valid],
        }
    )


def _pair_detail_row(
    left: RedundancyScoreInput,
    right: RedundancyScoreInput,
    date_value: pd.Timestamp,
    *,
    observations: int | object,
    spearman: float | object,
    status: str,
    reason: str,
) -> dict[str, object]:
    return {
        "score_a": left.score_name,
        "score_b": right.score_name,
        "date": date_value,
        "pair_observations": observations,
        "spearman": spearman,
        "diagnostic_status": status,
        "diagnostic_reason": reason,
    }


def _summarize_pair(group: pd.DataFrame, config: ScoreRedundancyConfig) -> dict[str, object]:
    first = group.iloc[0]
    if "insufficient_input" in set(group["diagnostic_status"]):
        return _pair_summary_row(
            first,
            dates_evaluated=0,
            dates_insufficient=0,
            min_pair_observations=pd.NA,
            median_pair_observations=pd.NA,
            median_spearman=pd.NA,
            mean_spearman=pd.NA,
            max_abs_spearman=pd.NA,
            status="insufficient_input",
            reason=str(first["diagnostic_reason"]),
        )

    ok = group[group["diagnostic_status"].eq("ok")]
    observations = pd.to_numeric(group["pair_observations"], errors="coerce")
    spearman = pd.to_numeric(ok["spearman"], errors="coerce").dropna()
    dates_evaluated = int(len(ok))
    dates_insufficient = int(len(group) - dates_evaluated)

    if dates_evaluated == 0:
        return _no_defined_spearman_summary(first, group, observations, dates_insufficient)

    max_abs = float(spearman.abs().max())
    status = _redundancy_status(max_abs, config)
    reason = _redundancy_reason(status, max_abs, config)
    return _pair_summary_row(
        first,
        dates_evaluated=dates_evaluated,
        dates_insufficient=dates_insufficient,
        min_pair_observations=_safe_min(observations),
        median_pair_observations=_safe_median(observations),
        median_spearman=float(spearman.median()),
        mean_spearman=float(spearman.mean()),
        max_abs_spearman=max_abs,
        status=status,
        reason=reason,
    )


def _no_defined_spearman_summary(
    first: pd.Series,
    group: pd.DataFrame,
    observations: pd.Series,
    dates_insufficient: int,
) -> dict[str, object]:
    status = (
        "undefined_correlation"
        if group["diagnostic_status"].eq("undefined_correlation").any()
        else "insufficient_data"
    )
    reason = (
        "no_same_date_pair_had_defined_spearman"
        if status == "undefined_correlation"
        else "no_same_date_pair_met_min_cross_section_count"
    )
    return _pair_summary_row(
        first,
        dates_evaluated=0,
        dates_insufficient=dates_insufficient,
        min_pair_observations=_safe_min(observations),
        median_pair_observations=_safe_median(observations),
        median_spearman=pd.NA,
        mean_spearman=pd.NA,
        max_abs_spearman=pd.NA,
        status=status,
        reason=reason,
    )


def _pair_summary_row(
    first: pd.Series,
    *,
    dates_evaluated: int,
    dates_insufficient: int,
    min_pair_observations: object,
    median_pair_observations: object,
    median_spearman: object,
    mean_spearman: object,
    max_abs_spearman: object,
    status: str,
    reason: str,
) -> dict[str, object]:
    return {
        "score_a": first["score_a"],
        "score_b": first["score_b"],
        "dates_evaluated": dates_evaluated,
        "dates_insufficient": dates_insufficient,
        "min_pair_observations": min_pair_observations,
        "median_pair_observations": median_pair_observations,
        "median_spearman": median_spearman,
        "mean_spearman": mean_spearman,
        "max_abs_spearman": max_abs_spearman,
        "redundancy_status": status,
        "redundancy_reason": reason,
    }


def _missing_pair_detail(
    left: RedundancyScoreInput,
    right: RedundancyScoreInput,
    missing: Sequence[str],
) -> dict[str, object]:
    return {
        "score_a": left.score_name,
        "score_b": right.score_name,
        "date": pd.NaT,
        "pair_observations": pd.NA,
        "spearman": pd.NA,
        "diagnostic_status": "insufficient_input",
        "diagnostic_reason": "upstream_missing_normalized_score_column:" + ",".join(missing),
    }


def _config_missing_summary(
    score_inputs: Sequence[RedundancyScoreInput], reason: str
) -> pd.DataFrame:
    rows = [
        {
            "score_a": left.score_name,
            "score_b": right.score_name,
            "dates_evaluated": 0,
            "dates_insufficient": 0,
            "min_pair_observations": pd.NA,
            "median_pair_observations": pd.NA,
            "median_spearman": pd.NA,
            "mean_spearman": pd.NA,
            "max_abs_spearman": pd.NA,
            "redundancy_status": "config_missing",
            "redundancy_reason": reason,
        }
        for left, right in combinations(score_inputs, 2)
    ]
    return pd.DataFrame(rows, columns=PAIR_SUMMARY_COLUMNS)


def _spearman_correlation(left: pd.Series, right: pd.Series) -> float:
    left_ranks = left.rank(method="average")
    right_ranks = right.rank(method="average")
    return float(left_ranks.corr(right_ranks))


def _safe_min(values: pd.Series) -> object:
    clean = values.dropna()
    if clean.empty:
        return pd.NA
    return int(clean.min())


def _safe_median(values: pd.Series) -> object:
    clean = values.dropna()
    if clean.empty:
        return pd.NA
    return float(clean.median())


def _redundancy_status(max_abs_spearman: float, config: ScoreRedundancyConfig) -> str:
    if max_abs_spearman >= config.spearman_block:
        return "block_candidate"
    if max_abs_spearman >= config.spearman_warn:
        return "warn"
    return "ok"


def _redundancy_reason(
    status: str, max_abs_spearman: float, config: ScoreRedundancyConfig
) -> str:
    if status == "block_candidate":
        return (
            "max_abs_spearman_meets_redundancy.spearman_block;"
            "diagnostic_flag_only_for_step13_review"
        )
    if status == "warn":
        return (
            "max_abs_spearman_meets_redundancy.spearman_warn;"
            "diagnostic_flag_only_for_step13_review"
        )
    return "max_abs_spearman_below_warn_threshold"

__all__ = (
    "PAIR_DATE_COLUMNS",
    "PAIR_SUMMARY_COLUMNS",
    "calculate_score_pair_correlations",
    "summarize_score_redundancy",
)
