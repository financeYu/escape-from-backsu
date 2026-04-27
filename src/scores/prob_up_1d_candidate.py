"""Candidate-only 1-day up probability pipeline.

This module implements the post-MVP v0.2 `prob_up_1d_candidate` path. It
builds old-score feature tables, derives the next-day up label in a separated
label table, trains a small transparent logistic model, and emits candidate
probabilities only.

It does not create production rankings, trading recommendations, composite
scores, valuation scores, backtest metrics, or report behavior changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import math
from typing import Mapping

import numpy as np
import pandas as pd

from src.preprocess.schema_validator import KOSPI200_SYMBOL_POLICY, SymbolPolicy

from .schema import (
    IDENTITY_COLUMNS,
    assert_no_forbidden_output_columns,
    assert_no_valuation_fundamental_columns,
    require_columns,
)
from .technical_scores import ALL_STEP9_RAW_SCORE_COLUMNS


DEFAULT_PRICE_COLUMN = "adjusted_close"
LABEL_COLUMN = "up_1d_label"
LABEL_AVAILABLE_COLUMN = "up_1d_label_available"
PROBABILITY_COLUMN = "prob_up_1d_candidate"
PROBABILITY_STATUS_COLUMN = "prob_up_1d_candidate_status"
PROBABILITY_SAMPLE_ROLE_COLUMN = "prob_up_1d_candidate_sample_role"
FEATURE_STATUS_COLUMN = "prob_up_1d_feature_status"
FEATURE_VALID_COUNT_COLUMN = "prob_up_1d_feature_valid_count"

DEFAULT_OLD_SCORE_FEATURE_COLUMNS = ALL_STEP9_RAW_SCORE_COLUMNS

FORBIDDEN_LABEL_OR_OUTPUT_COLUMNS = frozenset(
    {
        LABEL_COLUMN,
        LABEL_AVAILABLE_COLUMN,
        PROBABILITY_COLUMN,
        PROBABILITY_STATUS_COLUMN,
        PROBABILITY_SAMPLE_ROLE_COLUMN,
    }
)
FORBIDDEN_FUTURE_LABEL_PREFIXES = (
    "forward_return",
    "future_return",
    "next_return",
    "next_period_return",
    "next_day_return",
    "next_month_return",
    "label_return",
    "target_return",
    "realized_alpha",
)
FORBIDDEN_BACKTEST_FEATURE_MARKERS = (
    "backtest",
    "sharpe",
    "sortino",
    "calmar",
    "profit_factor",
    "cagr",
    "annualized_return",
    "cumulative_return",
    "max_drawdown",
    "win_rate",
    "hit_rate",
    "expectancy",
    "pnl",
)


@dataclass(frozen=True)
class ProbUp1DConfig:
    """Config for candidate feature selection and logistic training."""

    price_column: str = DEFAULT_PRICE_COLUMN
    feature_columns: tuple[str, ...] | None = None
    min_train_rows: int = 20
    min_eval_rows: int = 5
    eval_fraction: float = 0.25
    max_iter: int = 500
    learning_rate: float = 0.1
    l2: float = 1e-3
    tolerance: float = 1e-8


@dataclass(frozen=True)
class ProbUp1DDataset:
    feature_table: pd.DataFrame
    label_table: pd.DataFrame
    feature_columns: tuple[str, ...]


@dataclass(frozen=True)
class ProbUp1DModel:
    feature_columns: tuple[str, ...]
    coefficients: tuple[float, ...]
    intercept: float
    feature_means: tuple[float, ...]
    feature_scales: tuple[float, ...]
    train_count: int
    evaluation_count: int
    evaluation_metrics: Mapping[str, float]


@dataclass(frozen=True)
class ProbUp1DTrainingResult:
    model: ProbUp1DModel
    train_keys: tuple[tuple[str, pd.Timestamp], ...]
    evaluation_keys: tuple[tuple[str, pd.Timestamp], ...]


@dataclass(frozen=True)
class ProbUp1DPipelineResult:
    dataset: ProbUp1DDataset
    training_result: ProbUp1DTrainingResult
    candidate_output: pd.DataFrame


def build_prob_up_1d_dataset(
    frame: pd.DataFrame,
    *,
    config: ProbUp1DConfig | None = None,
    feature_columns: tuple[str, ...] | None = None,
    price_column: str | None = None,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> ProbUp1DDataset:
    """Return separated feature and label tables for `prob_up_1d_candidate`."""

    active_config = config or ProbUp1DConfig()
    active_price_column = price_column or active_config.price_column
    selected_feature_columns = feature_columns or active_config.feature_columns
    data = _prepare_candidate_input(
        frame,
        price_column=active_price_column,
        as_of_date=as_of_date,
        symbol_policy=symbol_policy,
    )
    resolved_feature_columns = _resolve_feature_columns(data, selected_feature_columns)

    feature_table = _build_feature_table(data, resolved_feature_columns)
    label_table = _build_label_table(data, price_column=active_price_column)
    _assert_label_separated(feature_table)
    return ProbUp1DDataset(
        feature_table=feature_table,
        label_table=label_table,
        feature_columns=resolved_feature_columns,
    )


def fit_prob_up_1d_candidate_model(
    dataset: ProbUp1DDataset,
    *,
    config: ProbUp1DConfig | None = None,
) -> ProbUp1DTrainingResult:
    """Fit the candidate logistic probability model on labeled training rows."""

    active_config = config or ProbUp1DConfig()
    _validate_training_config(active_config)
    modeling_frame = _modeling_frame(dataset)
    train_frame, evaluation_frame = _time_ordered_train_eval_split(modeling_frame, active_config)

    train_x = train_frame.loc[:, list(dataset.feature_columns)].to_numpy(dtype=float)
    train_y = train_frame[LABEL_COLUMN].to_numpy(dtype=float)
    means = train_x.mean(axis=0)
    scales = train_x.std(axis=0)
    scales = np.where(scales > 0, scales, 1.0)
    standardized_train_x = (train_x - means) / scales

    coefficients, intercept = _fit_logistic_regression(
        standardized_train_x,
        train_y,
        config=active_config,
    )
    evaluation_x = evaluation_frame.loc[:, list(dataset.feature_columns)].to_numpy(dtype=float)
    standardized_evaluation_x = (evaluation_x - means) / scales
    evaluation_probabilities = _sigmoid(standardized_evaluation_x @ coefficients + intercept)
    evaluation_metrics = _evaluation_metrics(
        evaluation_frame[LABEL_COLUMN].to_numpy(dtype=float),
        evaluation_probabilities,
    )

    model = ProbUp1DModel(
        feature_columns=dataset.feature_columns,
        coefficients=tuple(float(value) for value in coefficients),
        intercept=float(intercept),
        feature_means=tuple(float(value) for value in means),
        feature_scales=tuple(float(value) for value in scales),
        train_count=int(len(train_frame)),
        evaluation_count=int(len(evaluation_frame)),
        evaluation_metrics=evaluation_metrics,
    )
    return ProbUp1DTrainingResult(
        model=model,
        train_keys=_identity_keys(train_frame),
        evaluation_keys=_identity_keys(evaluation_frame),
    )


def predict_prob_up_1d_candidate(
    feature_table: pd.DataFrame,
    model: ProbUp1DModel,
    *,
    sample_roles: Mapping[tuple[str, pd.Timestamp], str] | None = None,
) -> pd.DataFrame:
    """Emit candidate probability output without ranking or composite columns."""

    require_columns(feature_table, (*IDENTITY_COLUMNS, *model.feature_columns), context="v0.2 probability features")
    _assert_no_probability_leakage_columns(feature_table.columns, context="v0.2 probability feature table")
    _assert_label_separated(feature_table)

    output = feature_table.loc[:, list(IDENTITY_COLUMNS)].copy()
    output[PROBABILITY_COLUMN] = pd.Series(pd.NA, index=output.index, dtype="Float64")
    output[PROBABILITY_STATUS_COLUMN] = pd.Series("missing_features", index=output.index, dtype="string")
    output[PROBABILITY_SAMPLE_ROLE_COLUMN] = pd.Series("candidate_unlabeled", index=output.index, dtype="string")

    numeric_features = _numeric_feature_frame(feature_table, model.feature_columns)
    complete_features = _complete_feature_mask(numeric_features)
    if complete_features.any():
        means = np.asarray(model.feature_means, dtype=float)
        scales = np.asarray(model.feature_scales, dtype=float)
        coefficients = np.asarray(model.coefficients, dtype=float)
        matrix = numeric_features.loc[complete_features, list(model.feature_columns)].to_numpy(dtype=float)
        standardized = (matrix - means) / scales
        probabilities = _sigmoid(standardized @ coefficients + model.intercept)
        output.loc[complete_features, PROBABILITY_COLUMN] = probabilities
        output.loc[complete_features, PROBABILITY_STATUS_COLUMN] = "candidate_probability"

    if sample_roles:
        for index, row in output.iterrows():
            key = (str(row["ticker"]), pd.Timestamp(row["date"]))
            role = sample_roles.get(key)
            if role is not None:
                output.at[index, PROBABILITY_SAMPLE_ROLE_COLUMN] = role

    assert_no_forbidden_output_columns(output, context="v0.2 probability candidate output")
    return output


def run_prob_up_1d_candidate_pipeline(
    frame: pd.DataFrame,
    *,
    config: ProbUp1DConfig | None = None,
    feature_columns: tuple[str, ...] | None = None,
    price_column: str | None = None,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> ProbUp1DPipelineResult:
    """Build, train, evaluate, and emit `prob_up_1d_candidate` probabilities."""

    active_config = config or ProbUp1DConfig()
    dataset = build_prob_up_1d_dataset(
        frame,
        config=active_config,
        feature_columns=feature_columns,
        price_column=price_column,
        as_of_date=as_of_date,
        symbol_policy=symbol_policy,
    )
    training_result = fit_prob_up_1d_candidate_model(dataset, config=active_config)
    sample_roles = _sample_roles(
        dataset,
        train_keys=training_result.train_keys,
        evaluation_keys=training_result.evaluation_keys,
    )
    candidate_output = predict_prob_up_1d_candidate(
        dataset.feature_table,
        training_result.model,
        sample_roles=sample_roles,
    )
    return ProbUp1DPipelineResult(
        dataset=dataset,
        training_result=training_result,
        candidate_output=candidate_output,
    )


def _prepare_candidate_input(
    frame: pd.DataFrame,
    *,
    price_column: str,
    as_of_date: date | datetime | pd.Timestamp | str | None,
    symbol_policy: SymbolPolicy,
) -> pd.DataFrame:
    require_columns(frame, (*IDENTITY_COLUMNS, price_column), context="v0.2 probability input")
    assert_no_forbidden_output_columns(frame, context="v0.2 probability input")
    assert_no_valuation_fundamental_columns(frame, context="v0.2 probability input")
    _assert_no_probability_leakage_columns(frame.columns, context="v0.2 probability input")

    data = frame.copy()
    data["ticker"] = data["ticker"].astype("string").str.strip()
    valid_ticker = data["ticker"].map(
        lambda value: isinstance(value, str) and symbol_policy.is_valid(value),
        na_action="ignore",
    ).fillna(False)
    if (~valid_ticker).any():
        raise ValueError(f"v0.2 probability input ticker must preserve {symbol_policy.display_rule}.")

    data["date"] = pd.to_datetime(data["date"], errors="raise")
    _assert_no_future_dates(data["date"], as_of_date=as_of_date)
    duplicate_rows = data.duplicated(["ticker", "date"], keep=False)
    if duplicate_rows.any():
        raise ValueError("v0.2 probability input contains duplicate ticker/date rows.")

    data[price_column] = _numeric_series(data[price_column], column=price_column)
    return data.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def _resolve_feature_columns(
    frame: pd.DataFrame,
    requested_feature_columns: tuple[str, ...] | None,
) -> tuple[str, ...]:
    if requested_feature_columns is None:
        feature_columns = tuple(column for column in DEFAULT_OLD_SCORE_FEATURE_COLUMNS if column in frame.columns)
    else:
        feature_columns = tuple(requested_feature_columns)
    if not feature_columns:
        raise ValueError("v0.2 probability candidate requires at least one approved old-score feature column.")

    missing = [column for column in feature_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"v0.2 probability feature columns missing from input: {', '.join(missing)}")
    _assert_no_probability_leakage_columns(feature_columns, context="v0.2 probability feature columns")
    return feature_columns


def _build_feature_table(data: pd.DataFrame, feature_columns: tuple[str, ...]) -> pd.DataFrame:
    feature_table = data.loc[:, [*IDENTITY_COLUMNS, *feature_columns]].copy()
    numeric_features = _numeric_feature_frame(feature_table, feature_columns)
    for column in feature_columns:
        feature_table[column] = numeric_features[column].astype("Float64")
    complete_features = _complete_feature_mask(numeric_features)
    valid_counts = numeric_features.notna().sum(axis=1)
    feature_table[FEATURE_VALID_COUNT_COLUMN] = valid_counts.astype("Int64")
    feature_table[FEATURE_STATUS_COLUMN] = pd.Series("missing_features", index=feature_table.index, dtype="string")
    feature_table.loc[complete_features, FEATURE_STATUS_COLUMN] = "ready"
    return feature_table


def _build_label_table(data: pd.DataFrame, *, price_column: str) -> pd.DataFrame:
    label_table = data.loc[:, list(IDENTITY_COLUMNS)].copy()
    current_price = data[price_column]
    next_price = current_price.groupby(data["ticker"], sort=False).shift(-1)
    current_finite = _finite_mask(current_price)
    next_finite = _finite_mask(next_price)
    label_available = current_price.notna() & next_price.notna() & current_finite & next_finite
    labels = (next_price > current_price).astype("Int64").where(label_available)
    label_table[LABEL_AVAILABLE_COLUMN] = label_available.astype("boolean")
    label_table[LABEL_COLUMN] = labels.astype("Int64")
    return label_table


def _modeling_frame(dataset: ProbUp1DDataset) -> pd.DataFrame:
    joined = dataset.feature_table.merge(dataset.label_table, on=list(IDENTITY_COLUMNS), how="inner")
    numeric_features = _numeric_feature_frame(joined, dataset.feature_columns)
    complete_features = _complete_feature_mask(numeric_features)
    eligible = joined[LABEL_AVAILABLE_COLUMN].fillna(False) & complete_features
    modeling = joined.loc[eligible].copy()
    if modeling.empty:
        raise ValueError("v0.2 probability candidate has no labeled rows with complete features.")
    modeling[LABEL_COLUMN] = pd.to_numeric(modeling[LABEL_COLUMN], errors="raise").astype("int64")
    modeling = modeling.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)
    return modeling


def _time_ordered_train_eval_split(
    modeling_frame: pd.DataFrame,
    config: ProbUp1DConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    row_count = len(modeling_frame)
    if row_count < config.min_train_rows + config.min_eval_rows:
        raise ValueError(
            "v0.2 probability candidate needs at least "
            f"{config.min_train_rows + config.min_eval_rows} labeled rows; got {row_count}."
        )

    train_count = int(math.floor(row_count * (1.0 - config.eval_fraction)))
    train_count = max(train_count, config.min_train_rows)
    train_count = min(train_count, row_count - config.min_eval_rows)
    if train_count < config.min_train_rows:
        raise ValueError("v0.2 probability train/evaluation split cannot satisfy minimum train rows.")

    train_frame = modeling_frame.iloc[:train_count].reset_index(drop=True)
    evaluation_frame = modeling_frame.iloc[train_count:].reset_index(drop=True)
    return train_frame, evaluation_frame


def _fit_logistic_regression(
    features: np.ndarray,
    labels: np.ndarray,
    *,
    config: ProbUp1DConfig,
) -> tuple[np.ndarray, float]:
    positive_rate = float(np.clip(labels.mean(), 1e-6, 1.0 - 1e-6))
    intercept = math.log(positive_rate / (1.0 - positive_rate))
    coefficients = np.zeros(features.shape[1], dtype=float)
    if np.unique(labels).size < 2:
        return coefficients, intercept

    for _ in range(config.max_iter):
        probabilities = _sigmoid(features @ coefficients + intercept)
        residual = probabilities - labels
        gradient_coefficients = (features.T @ residual) / len(labels) + config.l2 * coefficients
        gradient_intercept = float(residual.mean())
        next_coefficients = coefficients - (config.learning_rate * gradient_coefficients)
        next_intercept = intercept - (config.learning_rate * gradient_intercept)
        if max(
            float(np.max(np.abs(next_coefficients - coefficients))),
            abs(float(next_intercept - intercept)),
        ) < config.tolerance:
            coefficients = next_coefficients
            intercept = next_intercept
            break
        coefficients = next_coefficients
        intercept = next_intercept
    return coefficients, intercept


def _evaluation_metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    clipped = np.clip(probabilities, 1e-12, 1.0 - 1e-12)
    predictions = (clipped >= 0.5).astype(float)
    return {
        "evaluation_count": float(len(labels)),
        "positive_rate": float(labels.mean()) if len(labels) else float("nan"),
        "brier_score": float(np.mean((clipped - labels) ** 2)),
        "log_loss": float(-np.mean((labels * np.log(clipped)) + ((1.0 - labels) * np.log1p(-clipped)))),
        "classification_accuracy": float(np.mean(predictions == labels)),
    }


def _sample_roles(
    dataset: ProbUp1DDataset,
    *,
    train_keys: tuple[tuple[str, pd.Timestamp], ...],
    evaluation_keys: tuple[tuple[str, pd.Timestamp], ...],
) -> dict[tuple[str, pd.Timestamp], str]:
    labels_by_key = {
        (str(row["ticker"]), pd.Timestamp(row["date"])): bool(row[LABEL_AVAILABLE_COLUMN])
        for _, row in dataset.label_table.iterrows()
    }
    roles = {
        key: ("candidate_unlabeled" if not label_available else "labeled_not_used")
        for key, label_available in labels_by_key.items()
    }
    roles.update({key: "train_in_sample" for key in train_keys})
    roles.update({key: "evaluation_out_of_sample" for key in evaluation_keys})
    return roles


def _identity_keys(frame: pd.DataFrame) -> tuple[tuple[str, pd.Timestamp], ...]:
    return tuple((str(row["ticker"]), pd.Timestamp(row["date"])) for _, row in frame.iterrows())


def _numeric_feature_frame(frame: pd.DataFrame, feature_columns: tuple[str, ...]) -> pd.DataFrame:
    numeric = pd.DataFrame(index=frame.index)
    for column in feature_columns:
        numeric[column] = _numeric_series(frame[column], column=column)
    return numeric


def _numeric_series(values: pd.Series, *, column: str) -> pd.Series:
    bool_values = values.map(lambda value: isinstance(value, (bool, np.bool_)), na_action="ignore").fillna(False)
    if bool_values.any():
        raise ValueError(f"v0.2 probability column {column} contains boolean values.")
    numeric = pd.to_numeric(values, errors="coerce")
    invalid = values.notna() & numeric.isna()
    if invalid.any():
        raise ValueError(f"v0.2 probability column {column} contains non-numeric values.")
    return numeric


def _complete_feature_mask(features: pd.DataFrame) -> pd.Series:
    finite = np.isfinite(features.to_numpy(dtype=float, na_value=np.nan))
    return pd.Series(finite.all(axis=1), index=features.index)


def _finite_mask(values: pd.Series) -> pd.Series:
    finite = np.isfinite(values.to_numpy(dtype=float, na_value=np.nan))
    return pd.Series(finite, index=values.index)


def _assert_label_separated(feature_table: pd.DataFrame) -> None:
    leaked = [column for column in feature_table.columns if column in {LABEL_COLUMN, LABEL_AVAILABLE_COLUMN}]
    if leaked:
        raise ValueError(f"v0.2 probability feature table contains label columns: {', '.join(leaked)}")


def _assert_no_probability_leakage_columns(columns: pd.Index | tuple[str, ...] | list[str], *, context: str) -> None:
    flagged: list[str] = []
    for column in columns:
        normalized = str(column).lower()
        if normalized in FORBIDDEN_LABEL_OR_OUTPUT_COLUMNS:
            flagged.append(str(column))
            continue
        if normalized == "label" or normalized == "target":
            flagged.append(str(column))
            continue
        if normalized.endswith("_label") or normalized.startswith(("label_", "target_")):
            flagged.append(str(column))
            continue
        if normalized.startswith(FORBIDDEN_FUTURE_LABEL_PREFIXES):
            flagged.append(str(column))
            continue
        if any(marker in normalized for marker in FORBIDDEN_BACKTEST_FEATURE_MARKERS):
            flagged.append(str(column))
    if flagged:
        raise ValueError(f"{context} contains label, future-return, or backtest/evaluation leakage columns: {', '.join(flagged)}")


def _validate_training_config(config: ProbUp1DConfig) -> None:
    if config.min_train_rows <= 0 or config.min_eval_rows <= 0:
        raise ValueError("v0.2 probability train/evaluation minimum rows must be positive.")
    if not 0.0 < config.eval_fraction < 1.0:
        raise ValueError("v0.2 probability eval_fraction must be between 0 and 1.")
    if config.max_iter <= 0 or config.learning_rate <= 0:
        raise ValueError("v0.2 probability logistic training parameters must be positive.")
    if config.l2 < 0:
        raise ValueError("v0.2 probability l2 must be non-negative.")


def _sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _assert_no_future_dates(
    dates: pd.Series,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None,
) -> None:
    if as_of_date is None:
        return
    cutoff = pd.Timestamp(as_of_date).normalize()
    future_mask = dates.dt.normalize() > cutoff
    if future_mask.any():
        first_future = dates.loc[future_mask].min().date()
        raise ValueError(f"v0.2 probability input contains future dates after {cutoff.date()}: first={first_future}")


__all__ = (
    "DEFAULT_OLD_SCORE_FEATURE_COLUMNS",
    "DEFAULT_PRICE_COLUMN",
    "FEATURE_STATUS_COLUMN",
    "FEATURE_VALID_COUNT_COLUMN",
    "LABEL_AVAILABLE_COLUMN",
    "LABEL_COLUMN",
    "PROBABILITY_COLUMN",
    "PROBABILITY_SAMPLE_ROLE_COLUMN",
    "PROBABILITY_STATUS_COLUMN",
    "ProbUp1DConfig",
    "ProbUp1DDataset",
    "ProbUp1DModel",
    "ProbUp1DPipelineResult",
    "ProbUp1DTrainingResult",
    "build_prob_up_1d_dataset",
    "fit_prob_up_1d_candidate_model",
    "predict_prob_up_1d_candidate",
    "run_prob_up_1d_candidate_pipeline",
)
