"""Step 12 score redundancy and correlation diagnostics.

This module computes same-date cross-sectional Spearman correlations between
normalized/component score columns. It is diagnostic review material only: it
does not create rankings, composite scores, signals, valuation fields,
forward-return labels, or backtest outputs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
import tomllib

import numpy as np
import pandas as pd

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY, CompositeInputSpec
from src.composite.schema import find_forbidden_step11_output_columns
from src.scores.schema import IDENTITY_COLUMNS, find_valuation_fundamental_columns, require_columns

from .diagnostic_contracts import (
    STEP12_COVERAGE_SUMMARY_COLUMNS,
    STEP12_PAIR_DIAGNOSTIC_COLUMNS,
    Step12DiagnosticStatus,
    assert_no_forbidden_diagnostic_output_columns,
    threshold_flag_for_status,
    validate_step12_coverage_summary,
    validate_step12_pair_diagnostics,
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
FORBIDDEN_INPUT_FRAGMENTS = (
    "rank",
    "ranking",
    "latest_rank",
    "technical_composite_score",
    "final_composite_score",
    "forward_return",
    "future_return",
    "backtest_return",
    "alpha",
    "signal",
    "buy",
    "sell",
)
VALID_NORMALIZED_STATUSES = frozenset({"adequate", "ok"})
BLOCKING_QUALITY_FLAGS = frozenset(
    {
        "invalid_ticker",
        "leading_zero_lost",
        "invalid_date",
        "future_date",
        "duplicate_ticker_date",
        "invalid_numeric",
    }
)


class ScoreRedundancyConfigError(ValueError):
    """Raised when Step 12 threshold config is missing or invalid."""


@dataclass(frozen=True)
class ScoreRedundancyConfig:
    """Config values required for Step 12 redundancy diagnostics."""

    min_cross_section_count: int
    min_non_nan_observations: int
    spearman_warn: float
    spearman_block: float

    def __post_init__(self) -> None:
        if self.min_cross_section_count < 1:
            raise ValueError("min_cross_section_count must be at least 1.")
        if self.min_non_nan_observations < 1:
            raise ValueError("min_non_nan_observations must be at least 1.")
        _validate_threshold(self.spearman_warn, "spearman_warn")
        _validate_threshold(self.spearman_block, "spearman_block")
        if self.spearman_warn > self.spearman_block:
            raise ValueError("spearman_warn cannot exceed spearman_block.")


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


def load_score_redundancy_config(
    *,
    thresholds_config_path: str | Path = "Quant_mvp/config/thresholds.toml",
) -> ScoreRedundancyConfig:
    """Load Step 12 thresholds from Quant config without hardcoded fallback."""

    config = _load_toml(Path(thresholds_config_path))
    quality = _mapping(config.get("quality", {}))
    redundancy = _mapping(config.get("redundancy", {}))
    missing = [
        key
        for key, value in (
            ("quality.min_cross_section_count", quality.get("min_cross_section_count")),
            ("quality.min_non_nan_observations", quality.get("min_non_nan_observations")),
            ("redundancy.spearman_warn", redundancy.get("spearman_warn")),
            ("redundancy.spearman_block", redundancy.get("spearman_block")),
        )
        if value is None
    ]
    if missing:
        raise ScoreRedundancyConfigError(
            "config_missing: " + ", ".join(missing)
        )
    return ScoreRedundancyConfig(
        min_cross_section_count=_positive_int(
            quality.get("min_cross_section_count"),
            "quality.min_cross_section_count",
        ),
        min_non_nan_observations=_positive_int(
            quality.get("min_non_nan_observations"),
            "quality.min_non_nan_observations",
        ),
        spearman_warn=_threshold_float(
            redundancy.get("spearman_warn"),
            "redundancy.spearman_warn",
        ),
        spearman_block=_threshold_float(
            redundancy.get("spearman_block"),
            "redundancy.spearman_block",
        ),
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
        for date_value, group in prepared.groupby("date", sort=True):
            rows.append(_date_pair_correlation_row(group, left, right, active_config, date_value))
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


def build_score_redundancy_diagnostics(
    frame: pd.DataFrame,
    *,
    score_inputs: Sequence[RedundancyScoreInput] | None = None,
    score_columns: Sequence[str] | None = None,
    config: ScoreRedundancyConfig | None = None,
    thresholds_config_path: str | Path = "Quant_mvp/config/thresholds.toml",
    as_of_date: str | pd.Timestamp | None = None,
) -> dict[str, pd.DataFrame]:
    """Build Step 12 engine and contract-facing diagnostic tables."""

    active_inputs = _resolve_score_inputs(score_inputs, score_columns)
    prepared = prepare_redundancy_input_frame(
        frame,
        score_inputs=active_inputs,
        as_of_date=as_of_date,
    )
    try:
        active_config = config or load_score_redundancy_config(
            thresholds_config_path=thresholds_config_path
        )
    except ScoreRedundancyConfigError as exc:
        pair_summary = _config_missing_summary(active_inputs, str(exc))
        pair_diagnostics = _pair_summary_to_contract(
            pair_summary=pair_summary,
            pair_date_diagnostics=pd.DataFrame(columns=PAIR_DATE_COLUMNS),
            score_inputs=active_inputs,
        )
        return {
            "pair_summary": pair_summary,
            "pair_date_diagnostics": pd.DataFrame(columns=PAIR_DATE_COLUMNS),
            "pair_diagnostics": pair_diagnostics,
            "coverage_summary": _config_missing_coverage_summary(active_inputs, str(exc)),
        }

    pair_date = calculate_score_pair_correlations(
        prepared,
        score_inputs=active_inputs,
        config=active_config,
    )
    pair_summary = summarize_score_redundancy(
        prepared,
        score_inputs=active_inputs,
        config=active_config,
    )
    pair_diagnostics = _pair_summary_to_contract(
        pair_summary=pair_summary,
        pair_date_diagnostics=pair_date,
        score_inputs=active_inputs,
    )
    coverage_summary = _build_coverage_summary(
        prepared,
        score_inputs=active_inputs,
        config=active_config,
    )
    validate_step12_pair_diagnostics(pair_diagnostics)
    validate_step12_coverage_summary(coverage_summary)
    return {
        "pair_summary": pair_summary,
        "pair_date_diagnostics": pair_date,
        "pair_diagnostics": pair_diagnostics,
        "coverage_summary": coverage_summary,
    }


def _date_pair_correlation_row(
    group: pd.DataFrame,
    left: RedundancyScoreInput,
    right: RedundancyScoreInput,
    config: ScoreRedundancyConfig,
    date_value: pd.Timestamp,
) -> dict[str, object]:
    left_values = _numeric_score_values(group, left)
    right_values = _numeric_score_values(group, right)
    pair_valid = _finite_mask(left_values) & _finite_mask(right_values)
    pair = pd.DataFrame(
        {
            "left": left_values.loc[pair_valid],
            "right": right_values.loc[pair_valid],
        }
    )
    observations = int(len(pair))
    if observations < config.min_cross_section_count:
        return {
            "score_a": left.score_name,
            "score_b": right.score_name,
            "date": date_value,
            "pair_observations": observations,
            "spearman": pd.NA,
            "diagnostic_status": "insufficient_data",
            "diagnostic_reason": "pair_observations_below_min_cross_section_count",
        }
    if pair["left"].nunique(dropna=True) < 2 or pair["right"].nunique(dropna=True) < 2:
        return {
            "score_a": left.score_name,
            "score_b": right.score_name,
            "date": date_value,
            "pair_observations": observations,
            "spearman": pd.NA,
            "diagnostic_status": "undefined_correlation",
            "diagnostic_reason": "constant_score_column",
        }
    spearman = _spearman_correlation(pair["left"], pair["right"])
    if pd.isna(spearman) or not np.isfinite(float(spearman)):
        return {
            "score_a": left.score_name,
            "score_b": right.score_name,
            "date": date_value,
            "pair_observations": observations,
            "spearman": pd.NA,
            "diagnostic_status": "undefined_correlation",
            "diagnostic_reason": "spearman_not_defined",
        }
    return {
        "score_a": left.score_name,
        "score_b": right.score_name,
        "date": date_value,
        "pair_observations": observations,
        "spearman": float(spearman),
        "diagnostic_status": "ok",
        "diagnostic_reason": "same_date_cross_section_spearman",
    }


def _summarize_pair(group: pd.DataFrame, config: ScoreRedundancyConfig) -> dict[str, object]:
    first = group.iloc[0]
    if "insufficient_input" in set(group["diagnostic_status"]):
        return {
            "score_a": first["score_a"],
            "score_b": first["score_b"],
            "dates_evaluated": 0,
            "dates_insufficient": 0,
            "min_pair_observations": pd.NA,
            "median_pair_observations": pd.NA,
            "median_spearman": pd.NA,
            "mean_spearman": pd.NA,
            "max_abs_spearman": pd.NA,
            "redundancy_status": "insufficient_input",
            "redundancy_reason": str(first["diagnostic_reason"]),
        }

    ok = group[group["diagnostic_status"].eq("ok")]
    observations = pd.to_numeric(group["pair_observations"], errors="coerce")
    spearman = pd.to_numeric(ok["spearman"], errors="coerce").dropna()
    dates_evaluated = int(len(ok))
    dates_insufficient = int(len(group) - dates_evaluated)

    if dates_evaluated == 0:
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
        return {
            "score_a": first["score_a"],
            "score_b": first["score_b"],
            "dates_evaluated": 0,
            "dates_insufficient": dates_insufficient,
            "min_pair_observations": _safe_min(observations),
            "median_pair_observations": _safe_median(observations),
            "median_spearman": pd.NA,
            "mean_spearman": pd.NA,
            "max_abs_spearman": pd.NA,
            "redundancy_status": status,
            "redundancy_reason": reason,
        }

    max_abs = float(spearman.abs().max())
    status = _redundancy_status(max_abs, config)
    reason = _redundancy_reason(status, max_abs, config)
    return {
        "score_a": first["score_a"],
        "score_b": first["score_b"],
        "dates_evaluated": dates_evaluated,
        "dates_insufficient": dates_insufficient,
        "min_pair_observations": _safe_min(observations),
        "median_pair_observations": _safe_median(observations),
        "median_spearman": float(spearman.median()),
        "mean_spearman": float(spearman.mean()),
        "max_abs_spearman": max_abs,
        "redundancy_status": status,
        "redundancy_reason": reason,
    }


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
    rows = []
    for left, right in combinations(score_inputs, 2):
        rows.append(
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
        )
    return pd.DataFrame(rows, columns=PAIR_SUMMARY_COLUMNS)


def _pair_summary_to_contract(
    *,
    pair_summary: pd.DataFrame,
    pair_date_diagnostics: pd.DataFrame,
    score_inputs: Sequence[RedundancyScoreInput],
) -> pd.DataFrame:
    lookup = {score_input.score_name: score_input for score_input in score_inputs}
    rows: list[dict[str, object]] = []
    for _, summary in pair_summary.iterrows():
        left_name = str(summary["score_a"])
        right_name = str(summary["score_b"])
        pair_dates = _pair_date_rows(pair_date_diagnostics, left_name, right_name)
        status = str(summary["redundancy_status"])
        contract_spearman = _contract_spearman_value(summary, pair_dates)
        rows.append(
            {
                "diagnostic_name": "score_pair_correlation",
                "score_left": left_name,
                "score_right": right_name,
                "normalization_scope": _pair_normalization_scope(
                    lookup.get(left_name),
                    lookup.get(right_name),
                ),
                "start_date": _date_bound(pair_dates, "min"),
                "end_date": _date_bound(pair_dates, "max"),
                "observation_count": _pair_observation_count(pair_dates),
                "cross_section_count": int(summary["dates_evaluated"]),
                "spearman_correlation": contract_spearman,
                "abs_spearman_correlation": _absolute_or_na(contract_spearman),
                "threshold_flag": threshold_flag_for_status(status),
                "diagnostic_status": status,
                "insufficient_data_reason": _insufficient_reason(status, summary),
                "score_left_family": _score_family(lookup.get(left_name)),
                "score_right_family": _score_family(lookup.get(right_name)),
                "score_left_role": _score_role(lookup.get(left_name)),
                "score_right_role": _score_role(lookup.get(right_name)),
                "implementation_deviation_id": "",
                "notes": "diagnostic_only_review_material",
            }
        )
    output = pd.DataFrame(rows, columns=STEP12_PAIR_DIAGNOSTIC_COLUMNS)
    assert_no_forbidden_diagnostic_output_columns(output)
    return output


def _build_coverage_summary(
    frame: pd.DataFrame,
    *,
    score_inputs: Sequence[RedundancyScoreInput],
    config: ScoreRedundancyConfig,
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    prepared = prepare_redundancy_input_frame(
        frame,
        score_inputs=score_inputs,
        as_of_date=as_of_date,
    )
    rows: list[dict[str, object]] = []
    ticker_count = int(prepared["ticker"].nunique())
    observation_count = int(len(prepared))
    for score_input in score_inputs:
        if score_input.normalized_column not in prepared.columns:
            rows.append(
                _coverage_row(
                    score_input,
                    ticker_count=ticker_count,
                    observation_count=observation_count,
                    non_nan_observation_count=0,
                    coverage_ratio=0.0,
                    config=config,
                    status=Step12DiagnosticStatus.INSUFFICIENT_INPUT.value,
                    reason="upstream_missing_normalized_score_column:"
                    + score_input.normalized_column,
                )
            )
            continue
        values = _numeric_score_values(prepared, score_input)
        non_nan_observation_count = int(_finite_mask(values).sum())
        coverage_ratio = (
            non_nan_observation_count / observation_count if observation_count else 0.0
        )
        same_date_usable_cross_sections = _same_date_usable_cross_section_count(
            prepared,
            score_input,
            config,
        )
        status, reason = _coverage_status_and_reason(
            non_nan_observation_count,
            same_date_usable_cross_sections,
            config,
        )
        rows.append(
            _coverage_row(
                score_input,
                ticker_count=ticker_count,
                observation_count=observation_count,
                non_nan_observation_count=non_nan_observation_count,
                coverage_ratio=coverage_ratio,
                config=config,
                status=status,
                reason=reason,
                same_date_usable_cross_sections=same_date_usable_cross_sections,
            )
        )
    output = pd.DataFrame(rows, columns=STEP12_COVERAGE_SUMMARY_COLUMNS)
    assert_no_forbidden_diagnostic_output_columns(output)
    return output


def _config_missing_coverage_summary(
    score_inputs: Sequence[RedundancyScoreInput], reason: str
) -> pd.DataFrame:
    rows = [
        {
            "diagnostic_name": "coverage_summary",
            "score_name": score_input.score_name,
            "score_family": score_input.score_family,
            "normalization_scope": score_input.normalization_scope,
            "date": "",
            "ticker_count": 0,
            "observation_count": 0,
            "non_nan_observation_count": 0,
            "coverage_ratio": 0.0,
            "min_required_observations": 0,
            "min_cross_section_count": 0,
            "diagnostic_status": Step12DiagnosticStatus.CONFIG_MISSING.value,
            "insufficient_data_reason": reason,
            "implementation_deviation_id": "",
            "notes": "diagnostic_only_review_material",
        }
        for score_input in score_inputs
    ]
    output = pd.DataFrame(rows, columns=STEP12_COVERAGE_SUMMARY_COLUMNS)
    validate_step12_coverage_summary(output)
    return output


def _coverage_row(
    score_input: RedundancyScoreInput,
    *,
    ticker_count: int,
    observation_count: int,
    non_nan_observation_count: int,
    coverage_ratio: float,
    config: ScoreRedundancyConfig,
    status: str,
    reason: str,
    same_date_usable_cross_sections: int = 0,
) -> dict[str, object]:
    return {
        "diagnostic_name": "coverage_summary",
        "score_name": score_input.score_name,
        "score_family": score_input.score_family,
        "normalization_scope": score_input.normalization_scope,
        "date": "",
        "ticker_count": ticker_count,
        "observation_count": observation_count,
        "non_nan_observation_count": non_nan_observation_count,
        "coverage_ratio": coverage_ratio,
        "min_required_observations": config.min_non_nan_observations,
        "min_cross_section_count": config.min_cross_section_count,
        "diagnostic_status": status,
        "insufficient_data_reason": reason,
        "implementation_deviation_id": "",
        "notes": (
            "diagnostic_only_review_material;"
            f"same_date_usable_cross_sections={same_date_usable_cross_sections}"
        ),
    }


def _pair_date_rows(
    pair_date_diagnostics: pd.DataFrame,
    left_name: str,
    right_name: str,
) -> pd.DataFrame:
    if pair_date_diagnostics.empty:
        return pair_date_diagnostics
    return pair_date_diagnostics[
        pair_date_diagnostics["score_a"].eq(left_name)
        & pair_date_diagnostics["score_b"].eq(right_name)
    ]


def _contract_spearman_value(summary: pd.Series, pair_dates: pd.DataFrame) -> object:
    """Return the signed Spearman value whose absolute value drives the contract row."""

    if pair_dates.empty or "spearman" not in pair_dates:
        return summary["median_spearman"]
    ok_spearman = pd.to_numeric(
        pair_dates.loc[pair_dates["diagnostic_status"].eq("ok"), "spearman"],
        errors="coerce",
    ).dropna()
    if ok_spearman.empty:
        return summary["median_spearman"]
    max_abs_index = ok_spearman.abs().idxmax()
    return float(ok_spearman.loc[max_abs_index])


def _absolute_or_na(value: object) -> object:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return pd.NA
    if not np.isfinite(numeric):
        return pd.NA
    return abs(numeric)


def _date_bound(pair_dates: pd.DataFrame, method: str) -> object:
    if pair_dates.empty or "date" not in pair_dates:
        return ""
    dates = pd.to_datetime(pair_dates["date"], errors="coerce").dropna()
    if dates.empty:
        return ""
    return dates.min() if method == "min" else dates.max()


def _pair_observation_count(pair_dates: pd.DataFrame) -> int:
    if pair_dates.empty or "pair_observations" not in pair_dates:
        return 0
    observations = pd.to_numeric(pair_dates["pair_observations"], errors="coerce")
    return int(observations.dropna().sum())


def _same_date_usable_cross_section_count(
    prepared: pd.DataFrame,
    score_input: RedundancyScoreInput,
    config: ScoreRedundancyConfig,
) -> int:
    values = _numeric_score_values(prepared, score_input)
    finite = _finite_mask(values)
    finite_by_date = finite.groupby(prepared["date"]).sum()
    return int(finite_by_date.ge(config.min_cross_section_count).sum())


def _coverage_status_and_reason(
    non_nan_observation_count: int,
    same_date_usable_cross_sections: int,
    config: ScoreRedundancyConfig,
) -> tuple[str, str]:
    reasons: list[str] = []
    if non_nan_observation_count < config.min_non_nan_observations:
        reasons.append("non_nan_observation_count_below_min_required_observations")
    if same_date_usable_cross_sections < 1:
        reasons.append("no_same_date_cross_section_met_min_cross_section_count")
    if reasons:
        return Step12DiagnosticStatus.INSUFFICIENT_DATA.value, ";".join(reasons)
    return Step12DiagnosticStatus.OK.value, ""


def _pair_normalization_scope(
    left: RedundancyScoreInput | None,
    right: RedundancyScoreInput | None,
) -> str:
    scopes = {
        score_input.normalization_scope
        for score_input in (left, right)
        if score_input is not None and score_input.normalization_scope != "unknown"
    }
    if len(scopes) == 1:
        return next(iter(scopes))
    if len(scopes) > 1:
        return "mixed"
    return "unknown"


def _score_family(score_input: RedundancyScoreInput | None) -> str:
    return score_input.score_family if score_input is not None else "unknown"


def _score_role(score_input: RedundancyScoreInput | None) -> str:
    return score_input.score_role if score_input is not None else "unknown"


def _insufficient_reason(status: str, summary: pd.Series) -> str:
    if status in {
        Step12DiagnosticStatus.OK.value,
        Step12DiagnosticStatus.WARN.value,
        Step12DiagnosticStatus.BLOCK_CANDIDATE.value,
        Step12DiagnosticStatus.SEVERE_REDUNDANCY.value,
    }:
        return ""
    return str(summary["redundancy_reason"])


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


def _assert_no_forbidden_step12_input_columns(frame: pd.DataFrame) -> None:
    forbidden = set(find_forbidden_step11_output_columns(frame.columns))
    for column in frame.columns:
        normalized = column.lower()
        if any(fragment == normalized for fragment in FORBIDDEN_INPUT_FRAGMENTS):
            forbidden.add(column)
    if forbidden:
        raise ValueError(
            "Step 12 redundancy input contains forbidden columns: "
            + ", ".join(sorted(forbidden))
        )


def _assert_no_valuation_fundamental_columns(frame: pd.DataFrame) -> None:
    flagged = find_valuation_fundamental_columns(frame.columns)
    if flagged:
        raise ValueError(
            "Step 12 redundancy input contains valuation/fundamental columns: "
            + ", ".join(flagged)
        )


def _has_blocking_quality_flag(value: object) -> bool:
    if pd.isna(value):
        return False
    flags = {part.strip() for part in str(value).split(";") if part.strip()}
    return bool(flags.intersection(BLOCKING_QUALITY_FLAGS))


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


def _load_toml(path: Path) -> Mapping[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _positive_int(value: object, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ScoreRedundancyConfigError(
            f"config_invalid: {name} must be a positive integer"
        ) from exc
    if isinstance(value, bool) or parsed <= 0:
        raise ScoreRedundancyConfigError(
            f"config_invalid: {name} must be a positive integer"
        )
    return parsed


def _threshold_float(value: object, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ScoreRedundancyConfigError(
            f"config_invalid: {name} must be numeric"
        ) from exc
    try:
        _validate_threshold(parsed, name)
    except ValueError as exc:
        raise ScoreRedundancyConfigError(f"config_invalid: {exc}") from exc
    return parsed


def _validate_threshold(value: float, name: str) -> None:
    if not np.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError(f"{name} must be between 0 and 1.")


__all__ = (
    "PAIR_DATE_COLUMNS",
    "PAIR_SUMMARY_COLUMNS",
    "RedundancyScoreInput",
    "ScoreRedundancyConfig",
    "ScoreRedundancyConfigError",
    "build_score_redundancy_diagnostics",
    "calculate_score_pair_correlations",
    "load_score_redundancy_config",
    "prepare_redundancy_input_frame",
    "score_inputs_from_columns",
    "score_inputs_from_registry",
    "summarize_score_redundancy",
)
