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
import json
import math
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

from src.preprocess.schema_validator import KOSPI200_SYMBOL_POLICY, SymbolPolicy
from src.validation.v0_2_candidate_ml_guardrails import (
    validate_v0_2_candidate_artifact_columns,
    validate_v0_2_candidate_feature_columns,
)

from .schema import (
    IDENTITY_COLUMNS,
    assert_no_forbidden_output_columns,
    assert_no_valuation_fundamental_columns,
    require_columns,
)
from .technical_scores import ALL_STEP9_RAW_SCORE_COLUMNS, calculate_all_raw_scores


DEFAULT_PRICE_COLUMN = "adjusted_close"
DEFAULT_PRICE_ALIAS_COLUMNS = ("adj_close",)
LABEL_COLUMN = "up_1d_label"
LABEL_AVAILABLE_COLUMN = "up_1d_label_available"
PROBABILITY_COLUMN = "prob_up_1d_candidate"
PROBABILITY_STATUS_COLUMN = "prob_up_1d_candidate_status"
PROBABILITY_SAMPLE_ROLE_COLUMN = "prob_up_1d_candidate_sample_role"
FEATURE_STATUS_COLUMN = "prob_up_1d_feature_status"
FEATURE_VALID_COUNT_COLUMN = "prob_up_1d_feature_valid_count"
DECISION_TIME_COLUMN = "decision_time"
EXECUTION_TIME_COLUMN = "execution_time"
LABEL_TIME_COLUMN = "label_time"
LABEL_AVAILABILITY_TIME_COLUMN = "label_availability_time"
CANDIDATE_SIDECAR_RANK_COLUMN = "prob_up_1d_candidate_sidecar_rank"
FEATURE_SET_VERSION_COLUMN = "feature_set_version"
LABEL_CONTRACT_VERSION_COLUMN = "label_contract_version"
DEFAULT_FEATURE_SET_VERSION = "v0_2_candidate_ml_score"
DEFAULT_LABEL_CONTRACT_VERSION = "adjusted_close_up_1d_v0_2"
DEFAULT_SIDECAR_FILENAME_TEMPLATE = "prob_up_1d_candidate_candidate_only_sidecar_{as_of_date}.csv"
DEFAULT_SIDECAR_MANIFEST_TEMPLATE = "prob_up_1d_candidate_candidate_only_sidecar_{as_of_date}.manifest.json"
DEFAULT_SELECTION_PACKET_ROOT = "reports/v0_2_predictive_probability/candidate_sidecar/selection_packet"
DEFAULT_SELECTION_PACKET_FILENAME_TEMPLATE = "prob_up_1d_candidate_selection_packet_{as_of_date}.csv"
DEFAULT_SELECTION_PACKET_MANIFEST_TEMPLATE = "prob_up_1d_candidate_selection_packet_{as_of_date}.manifest.json"
SELECTION_PACKET_PATH = "src.scores.prob_up_1d_candidate.build_prob_up_1d_candidate_selection_packet"
SELECTION_PACKET_EXPORT_PATH = "src.scores.prob_up_1d_candidate.export_prob_up_1d_candidate_selection_packet"
SELECTION_PACKET_TYPE = "candidate_sidecar_selection_packet"
MODEL_VERSION = "candidate_logistic_v0_2"
MODEL_TYPE = "transparent_logistic_regression"
FEATURE_INPUT_SOURCE = "step9_raw_technical_old_scores"
FEATURE_INPUT_PATH = "src.scores.prob_up_1d_candidate.build_prob_up_1d_feature_input_frame"
WALK_FORWARD_EVALUATION_SOURCE = "time_ordered_walk_forward_candidate_quality"
WALK_FORWARD_EVALUATION_PATH = "src.scores.prob_up_1d_candidate.evaluate_prob_up_1d_candidate_walk_forward"
DEFAULT_WALK_FORWARD_EVALUATION_ROOT = "reports/v0_2_predictive_probability/evaluation"
DEFAULT_WALK_FORWARD_SUMMARY_TEMPLATE = "prob_up_1d_candidate_walk_forward_metric_summary_{as_of_date}.csv"
DEFAULT_WALK_FORWARD_FOLD_TEMPLATE = "prob_up_1d_candidate_walk_forward_fold_metrics_{as_of_date}.csv"
DEFAULT_WALK_FORWARD_CALIBRATION_TEMPLATE = "prob_up_1d_candidate_walk_forward_calibration_{as_of_date}.csv"
DEFAULT_WALK_FORWARD_STABILITY_TEMPLATE = "prob_up_1d_candidate_walk_forward_feature_stability_{as_of_date}.csv"
DEFAULT_WALK_FORWARD_MANIFEST_TEMPLATE = "prob_up_1d_candidate_walk_forward_evaluation_{as_of_date}.manifest.json"
DEFAULT_EVALUATION_BACKTEST_ROOT = "reports/v0_2_predictive_probability/evaluation_only_backtest"
DEFAULT_EVALUATION_BACKTEST_DIAGNOSTIC_TEMPLATE = (
    "prob_up_1d_candidate_evaluation_only_backtest_diagnostic_{as_of_date}.csv"
)
DEFAULT_EVALUATION_BACKTEST_MANIFEST_TEMPLATE = (
    "prob_up_1d_candidate_evaluation_only_backtest_{as_of_date}.manifest.json"
)
EVALUATION_BACKTEST_PATH = "src.scores.prob_up_1d_candidate.run_prob_up_1d_evaluation_only_backtest"
EVALUATION_BACKTEST_EXPORT_PATH = "src.scores.prob_up_1d_candidate.export_prob_up_1d_evaluation_only_backtest"
EVALUATION_BACKTEST_SOURCE = "candidate_probability_artifact_evaluation_only"
EVALUATION_BACKTEST_ARTIFACT_TYPE = "candidate_only_evaluation_backtest_diagnostic"
WALK_FORWARD_INTERPRETATION_LIMITS = (
    "candidate_only_model_quality_diagnostic",
    "not_production_ranking_activation",
    "not_final_or_technical_composite_replacement",
    "not_report_behavior_change",
    "not_model_selection_feedback_from_return_performance",
)
EVALUATION_BACKTEST_INTERPRETATION_LIMITS = (
    "candidate_probability_artifact_evaluation_only",
    "not_production_ranking_activation",
    "not_final_or_technical_composite_replacement",
    "not_report_behavior_change",
    "not_model_selection_feedback",
    "not_feature_selection_feedback",
    "not_cutoff_selection_feedback",
)

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
    "holding_return",
    "realized_return",
    "forward_return",
    "future_return",
    "paper_return",
    "generated_report",
    "report_output",
    "ranking_output",
    "candidate_sidecar",
    "cache",
)


@dataclass(frozen=True)
class ProbUp1DConfig:
    """Config for candidate feature selection and logistic training."""

    price_column: str = DEFAULT_PRICE_COLUMN
    price_alias_columns: tuple[str, ...] = DEFAULT_PRICE_ALIAS_COLUMNS
    feature_columns: tuple[str, ...] | None = None
    min_train_rows: int = 20
    min_eval_rows: int = 5
    eval_fraction: float = 0.25
    max_iter: int = 500
    learning_rate: float = 0.1
    l2: float = 1e-3
    tolerance: float = 1e-8
    feature_set_version: str = DEFAULT_FEATURE_SET_VERSION
    label_contract_version: str = DEFAULT_LABEL_CONTRACT_VERSION
    walk_forward_initial_train_periods: int = 20
    walk_forward_eval_periods: int = 5
    walk_forward_step_periods: int = 5
    walk_forward_min_folds: int = 2
    calibration_bins: int = 5
    sidecar_output_root: str | Path | None = None
    sidecar_filename_template: str = DEFAULT_SIDECAR_FILENAME_TEMPLATE
    sidecar_manifest_template: str = DEFAULT_SIDECAR_MANIFEST_TEMPLATE
    evaluation_output_root: str | Path | None = None
    walk_forward_summary_template: str = DEFAULT_WALK_FORWARD_SUMMARY_TEMPLATE
    walk_forward_fold_template: str = DEFAULT_WALK_FORWARD_FOLD_TEMPLATE
    walk_forward_calibration_template: str = DEFAULT_WALK_FORWARD_CALIBRATION_TEMPLATE
    walk_forward_stability_template: str = DEFAULT_WALK_FORWARD_STABILITY_TEMPLATE
    walk_forward_manifest_template: str = DEFAULT_WALK_FORWARD_MANIFEST_TEMPLATE


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
class ProbUp1DSidecarExportResult:
    sidecar_path: Path
    manifest_path: Path
    as_of_date: str
    row_count: int


@dataclass(frozen=True)
class ProbUp1DSelectionPacketExportResult:
    packet_path: Path
    manifest_path: Path
    as_of_date: str
    row_count: int


@dataclass(frozen=True)
class ProbUp1DWalkForwardEvaluationResult:
    fold_metrics: pd.DataFrame
    metric_summary: pd.DataFrame
    calibration_table: pd.DataFrame
    feature_stability_table: pd.DataFrame
    interpretation_limits: tuple[str, ...] = WALK_FORWARD_INTERPRETATION_LIMITS


@dataclass(frozen=True)
class ProbUp1DWalkForwardExportResult:
    summary_path: Path
    fold_metrics_path: Path
    calibration_path: Path
    feature_stability_path: Path
    manifest_path: Path
    as_of_date: str
    fold_count: int


@dataclass(frozen=True)
class ProbUp1DEvaluationOnlyBacktestConfig:
    """Config for diagnostic-only candidate artifact evaluation."""

    output_root: str | Path | None = None
    diagnostic_template: str = DEFAULT_EVALUATION_BACKTEST_DIAGNOSTIC_TEMPLATE
    manifest_template: str = DEFAULT_EVALUATION_BACKTEST_MANIFEST_TEMPLATE
    updates_model_parameters: bool = False
    updates_feature_allowlist: bool = False
    updates_score_weights: bool = False
    updates_ranking_rules: bool = False
    updates_composite_definitions: bool = False
    feeds_production_ranking: bool = False
    feeds_reports: bool = False


@dataclass(frozen=True)
class ProbUp1DEvaluationOnlyBacktestExportResult:
    diagnostic_path: Path
    manifest_path: Path
    as_of_date: str
    row_count: int


@dataclass(frozen=True)
class ProbUp1DPipelineResult:
    dataset: ProbUp1DDataset
    training_result: ProbUp1DTrainingResult
    candidate_output: pd.DataFrame
    candidate_sidecar_ranking: pd.DataFrame
    sidecar_export: ProbUp1DSidecarExportResult | None = None


def build_prob_up_1d_feature_input_frame(
    price_frame: pd.DataFrame,
    *,
    technical_feature_frame: pd.DataFrame | None = None,
    config: ProbUp1DConfig | None = None,
    feature_columns: tuple[str, ...] | None = None,
    price_column: str | None = None,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> pd.DataFrame:
    """Connect approved old-score technical features to the candidate input.

    The returned frame is the narrow input expected by
    :func:`build_prob_up_1d_dataset`: identity columns, canonical
    ``adjusted_close``, and allowlisted Step 9 raw technical old-score columns.
    Missing feature values remain missing so train/eval exclude them and
    inference emits ``missing_features`` instead of fabricated probabilities.
    """

    active_config = config or ProbUp1DConfig()
    active_price_column = price_column or active_config.price_column
    selected_feature_columns = feature_columns or active_config.feature_columns
    price_data = _prepare_candidate_input(
        price_frame,
        price_column=active_price_column,
        price_alias_columns=active_config.price_alias_columns,
        as_of_date=as_of_date,
        symbol_policy=symbol_policy,
    )
    if technical_feature_frame is None:
        technical_feature_frame = calculate_all_raw_scores(price_data, as_of_date=as_of_date)
    technical_features = _prepare_old_score_feature_input(
        technical_feature_frame,
        as_of_date=as_of_date,
        symbol_policy=symbol_policy,
    )
    resolved_feature_columns = _resolve_feature_columns(technical_features, selected_feature_columns)
    feature_input = price_data.loc[:, [*IDENTITY_COLUMNS, active_price_column]].merge(
        technical_features.loc[:, [*IDENTITY_COLUMNS, *resolved_feature_columns]],
        on=list(IDENTITY_COLUMNS),
        how="left",
        validate="one_to_one",
    )
    feature_input = feature_input.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    return feature_input


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
        price_alias_columns=active_config.price_alias_columns,
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
    label_table: pd.DataFrame | None = None,
    feature_set_version: str = DEFAULT_FEATURE_SET_VERSION,
    label_contract_version: str = DEFAULT_LABEL_CONTRACT_VERSION,
) -> pd.DataFrame:
    """Emit candidate probability output without ranking or composite columns."""

    require_columns(feature_table, (*IDENTITY_COLUMNS, *model.feature_columns), context="v0.2 probability features")
    _assert_no_probability_leakage_columns(feature_table.columns, context="v0.2 probability feature table")
    _assert_label_separated(feature_table)

    output = feature_table.loc[:, list(IDENTITY_COLUMNS)].copy()
    output = _attach_candidate_timing_fields(output, label_table=label_table)
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

    output[FEATURE_SET_VERSION_COLUMN] = pd.Series(feature_set_version, index=output.index, dtype="string")
    output[LABEL_CONTRACT_VERSION_COLUMN] = pd.Series(label_contract_version, index=output.index, dtype="string")

    assert_no_forbidden_output_columns(output, context="v0.2 probability candidate output")
    validate_v0_2_candidate_artifact_columns(
        output.columns,
        context="v0.2 probability candidate output",
    )
    return output


def build_prob_up_1d_candidate_sidecar_ranking(
    candidate_output: pd.DataFrame,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """Return candidate-only sidecar ordering by probability, never production rank."""

    require_columns(
        candidate_output,
        (*IDENTITY_COLUMNS, PROBABILITY_COLUMN),
        context="v0.2 probability candidate sidecar ranking",
    )
    assert_no_forbidden_output_columns(candidate_output, context="v0.2 probability candidate sidecar ranking input")
    validate_v0_2_candidate_artifact_columns(
        candidate_output.columns,
        context="v0.2 probability candidate sidecar ranking input",
        require_timing_fields=False,
    )

    data = candidate_output.copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data[PROBABILITY_COLUMN] = _numeric_series(data[PROBABILITY_COLUMN], column=PROBABILITY_COLUMN)
    data = data.loc[data[PROBABILITY_COLUMN].notna()].copy()
    if data.empty:
        sidecar = data.copy()
        sidecar[CANDIDATE_SIDECAR_RANK_COLUMN] = pd.Series(dtype="Int64")
        return sidecar

    target_date = pd.Timestamp(as_of_date).normalize() if as_of_date is not None else data["date"].dt.normalize().max()
    sidecar = data.loc[data["date"].dt.normalize().eq(target_date)].copy()
    sidecar = sidecar.sort_values(
        [PROBABILITY_COLUMN, "ticker"],
        ascending=[False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    sidecar[CANDIDATE_SIDECAR_RANK_COLUMN] = pd.Series(range(1, len(sidecar) + 1), dtype="Int64")
    return sidecar


def export_prob_up_1d_candidate_sidecar(
    sidecar: pd.DataFrame,
    *,
    output_root: str | Path,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
    filename_template: str = DEFAULT_SIDECAR_FILENAME_TEMPLATE,
    manifest_template: str = DEFAULT_SIDECAR_MANIFEST_TEMPLATE,
) -> ProbUp1DSidecarExportResult:
    """Persist a candidate-only sidecar CSV and manifest without production outputs."""

    required_columns = (
        *IDENTITY_COLUMNS,
        DECISION_TIME_COLUMN,
        EXECUTION_TIME_COLUMN,
        LABEL_TIME_COLUMN,
        LABEL_AVAILABILITY_TIME_COLUMN,
        PROBABILITY_COLUMN,
        PROBABILITY_STATUS_COLUMN,
        PROBABILITY_SAMPLE_ROLE_COLUMN,
        FEATURE_SET_VERSION_COLUMN,
        LABEL_CONTRACT_VERSION_COLUMN,
        CANDIDATE_SIDECAR_RANK_COLUMN,
    )
    require_columns(sidecar, required_columns, context="v0.2 probability sidecar export")
    assert_no_forbidden_output_columns(sidecar, context="v0.2 probability sidecar export")
    validate_v0_2_candidate_artifact_columns(
        sidecar.columns,
        context="v0.2 probability sidecar export",
    )

    data = sidecar.copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    target_date = _resolve_sidecar_export_date(data, as_of_date=as_of_date)
    if not data.empty:
        mismatched = data["date"].dt.normalize().ne(target_date)
        if mismatched.any():
            raise ValueError("v0.2 probability sidecar export contains rows outside the requested as_of_date.")

    output_dir = Path(output_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_token = target_date.strftime("%Y%m%d")
    sidecar_path = output_dir / filename_template.format(as_of_date=date_token)
    manifest_path = output_dir / manifest_template.format(as_of_date=date_token)
    data.to_csv(sidecar_path, index=False)

    manifest = {
        "artifact_type": "sidecar_candidate_only",
        "candidate_output": PROBABILITY_COLUMN,
        "as_of_date": date_token,
        "row_count": int(len(data)),
        "schema": list(data.columns),
        "feature_set_versions": _unique_string_values(data, FEATURE_SET_VERSION_COLUMN),
        "label_contract_versions": _unique_string_values(data, LABEL_CONTRACT_VERSION_COLUMN),
        "production_rank_activation": False,
        "feeds_production_ranking": False,
        "feeds_reports": False,
        "feeds_composite_scores": False,
        "replace_technical_composite_score": False,
        "replace_final_composite_score": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return ProbUp1DSidecarExportResult(
        sidecar_path=sidecar_path,
        manifest_path=manifest_path,
        as_of_date=date_token,
        row_count=int(len(data)),
    )


def build_prob_up_1d_candidate_selection_packet(
    result: ProbUp1DPipelineResult,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
    model_version: str = MODEL_VERSION,
    model_type: str = MODEL_TYPE,
    adjusted_close_source_field: str = DEFAULT_PRICE_COLUMN,
    adjusted_close_alias_columns: tuple[str, ...] = DEFAULT_PRICE_ALIAS_COLUMNS,
) -> pd.DataFrame:
    """Return a candidate-only sorted selection packet without production rank."""

    validate_prob_up_1d_schema_consistency(result)
    candidate_output = result.candidate_output.copy()
    require_columns(
        candidate_output,
        (
            *IDENTITY_COLUMNS,
            DECISION_TIME_COLUMN,
            PROBABILITY_COLUMN,
            PROBABILITY_STATUS_COLUMN,
            PROBABILITY_SAMPLE_ROLE_COLUMN,
            FEATURE_SET_VERSION_COLUMN,
            LABEL_CONTRACT_VERSION_COLUMN,
        ),
        context="v0.2 probability selection packet input",
    )
    assert_no_forbidden_output_columns(candidate_output, context="v0.2 probability selection packet input")
    validate_v0_2_candidate_artifact_columns(
        candidate_output.columns,
        context="v0.2 probability selection packet input",
    )

    feature_quality = result.dataset.feature_table.loc[
        :, [*IDENTITY_COLUMNS, FEATURE_VALID_COUNT_COLUMN, FEATURE_STATUS_COLUMN]
    ].copy()
    data = candidate_output.merge(feature_quality, on=list(IDENTITY_COLUMNS), how="left", validate="one_to_one")
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data[DECISION_TIME_COLUMN] = pd.to_datetime(data[DECISION_TIME_COLUMN], errors="raise")
    data[PROBABILITY_COLUMN] = _numeric_series(data[PROBABILITY_COLUMN], column=PROBABILITY_COLUMN)
    target_date = _resolve_selection_packet_date(data, as_of_date=as_of_date)
    data = data.loc[
        data["date"].dt.normalize().eq(target_date) & data[PROBABILITY_COLUMN].notna()
    ].copy()

    feature_count = len(result.dataset.feature_columns)
    data["as_of_date"] = target_date.strftime("%Y-%m-%d")
    data["candidate_packet_type"] = SELECTION_PACKET_TYPE
    data["model_version"] = model_version
    data["model_type"] = model_type
    data["model_train_count"] = result.training_result.model.train_count
    data["model_evaluation_count"] = result.training_result.model.evaluation_count
    data["model_feature_count"] = feature_count
    data["feature_schema_version"] = data[FEATURE_SET_VERSION_COLUMN].astype("string")
    data["feature_schema_columns"] = "|".join(result.dataset.feature_columns)
    data["adjusted_close_source_field"] = adjusted_close_source_field
    data["adjusted_close_approved_aliases"] = "|".join(adjusted_close_alias_columns)
    data["adjusted_close_canonical_source_status"] = "canonical_or_approved_alias"
    data["feature_expected_count"] = feature_count
    data["feature_coverage_ratio"] = (
        pd.to_numeric(data[FEATURE_VALID_COUNT_COLUMN], errors="coerce") / feature_count
        if feature_count
        else pd.NA
    )
    data["data_quality_flag"] = data[FEATURE_STATUS_COLUMN].astype("string")

    packet_columns = [
        "ticker",
        "as_of_date",
        DECISION_TIME_COLUMN,
        PROBABILITY_COLUMN,
        PROBABILITY_STATUS_COLUMN,
        PROBABILITY_SAMPLE_ROLE_COLUMN,
        "model_version",
        "model_type",
        "model_train_count",
        "model_evaluation_count",
        "model_feature_count",
        FEATURE_SET_VERSION_COLUMN,
        "feature_schema_version",
        "feature_schema_columns",
        LABEL_CONTRACT_VERSION_COLUMN,
        "adjusted_close_source_field",
        "adjusted_close_approved_aliases",
        "adjusted_close_canonical_source_status",
        FEATURE_STATUS_COLUMN,
        FEATURE_VALID_COUNT_COLUMN,
        "feature_expected_count",
        "feature_coverage_ratio",
        "data_quality_flag",
        "candidate_packet_type",
    ]
    packet = data.loc[:, packet_columns].sort_values(
        [PROBABILITY_COLUMN, "ticker"],
        ascending=[False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    validate_prob_up_1d_selection_packet_schema(packet)
    return packet


def validate_prob_up_1d_selection_packet_schema(packet: pd.DataFrame) -> None:
    """Validate candidate selection packet schema, ordering, and boundaries."""

    required_columns = (
        "ticker",
        "as_of_date",
        DECISION_TIME_COLUMN,
        PROBABILITY_COLUMN,
        "model_version",
        "model_type",
        FEATURE_SET_VERSION_COLUMN,
        "feature_schema_version",
        "feature_schema_columns",
        LABEL_CONTRACT_VERSION_COLUMN,
        "adjusted_close_source_field",
        "adjusted_close_canonical_source_status",
        FEATURE_STATUS_COLUMN,
        FEATURE_VALID_COUNT_COLUMN,
        "feature_expected_count",
        "feature_coverage_ratio",
        "data_quality_flag",
        "candidate_packet_type",
    )
    require_columns(packet, required_columns, context="v0.2 probability candidate selection packet")
    assert_no_forbidden_output_columns(packet, context="v0.2 probability candidate selection packet")
    validate_v0_2_candidate_artifact_columns(
        [*packet.columns, "date", EXECUTION_TIME_COLUMN, LABEL_TIME_COLUMN, LABEL_AVAILABILITY_TIME_COLUMN],
        context="v0.2 probability candidate selection packet",
    )
    forbidden_columns = {
        CANDIDATE_SIDECAR_RANK_COLUMN,
        "rank",
        "ranking",
        "production_rank",
        "final_composite_score",
        "technical_composite_score",
        "recommendation",
    }
    leaked = sorted(forbidden_columns.intersection(packet.columns))
    if leaked:
        raise ValueError(
            "v0.2 probability candidate selection packet contains forbidden production fields: "
            f"{', '.join(leaked)}"
        )
    as_of_dates = _parse_required_datetime_column(packet["as_of_date"], column="as_of_date")
    decision_times = _parse_required_datetime_column(packet[DECISION_TIME_COLUMN], column=DECISION_TIME_COLUMN)
    probabilities = _numeric_series(packet[PROBABILITY_COLUMN], column=PROBABILITY_COLUMN)
    if as_of_dates.isna().any():
        raise ValueError("v0.2 probability candidate selection packet has missing as_of_date.")
    if decision_times.isna().any():
        raise ValueError("v0.2 probability candidate selection packet has missing decision_time.")
    if probabilities.isna().any():
        raise ValueError("v0.2 probability candidate selection packet has missing prob_up_1d_candidate.")
    if not probabilities.between(0.0, 1.0).all():
        raise ValueError("v0.2 probability candidate selection packet has probabilities outside [0, 1].")
    if not packet["candidate_packet_type"].eq(SELECTION_PACKET_TYPE).all():
        raise ValueError("v0.2 probability candidate selection packet has invalid packet type.")
    _assert_selection_packet_sort(packet)


def export_prob_up_1d_candidate_selection_packet(
    packet: pd.DataFrame,
    *,
    output_root: str | Path,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
    filename_template: str = DEFAULT_SELECTION_PACKET_FILENAME_TEMPLATE,
    manifest_template: str = DEFAULT_SELECTION_PACKET_MANIFEST_TEMPLATE,
) -> ProbUp1DSelectionPacketExportResult:
    """Persist a candidate-only selection packet and manifest."""

    validate_prob_up_1d_selection_packet_schema(packet)
    data = packet.copy()
    target_date = _resolve_selection_packet_export_date(data, as_of_date=as_of_date)
    if not data.empty:
        mismatched = pd.to_datetime(data["as_of_date"], errors="raise").dt.normalize().ne(target_date)
        if mismatched.any():
            raise ValueError("v0.2 probability selection packet export contains rows outside as_of_date.")

    output_dir = Path(output_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_token = target_date.strftime("%Y%m%d")
    packet_path = output_dir / filename_template.format(as_of_date=date_token)
    manifest_path = output_dir / manifest_template.format(as_of_date=date_token)
    data.to_csv(packet_path, index=False)

    manifest = {
        "artifact_type": SELECTION_PACKET_TYPE,
        "candidate_output": PROBABILITY_COLUMN,
        "as_of_date": date_token,
        "row_count": int(len(data)),
        "sort_fields": [PROBABILITY_COLUMN, "ticker"],
        "sort_directions": ["desc", "asc"],
        "schema": list(data.columns),
        "selection_packet_path": SELECTION_PACKET_PATH,
        "production_rank_activation": False,
        "feeds_production_ranking": False,
        "feeds_reports": False,
        "feeds_composite_scores": False,
        "replace_final_composite_score": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return ProbUp1DSelectionPacketExportResult(
        packet_path=packet_path,
        manifest_path=manifest_path,
        as_of_date=date_token,
        row_count=int(len(data)),
    )


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
        label_table=dataset.label_table,
        feature_set_version=active_config.feature_set_version,
        label_contract_version=active_config.label_contract_version,
    )
    candidate_sidecar_ranking = build_prob_up_1d_candidate_sidecar_ranking(
        candidate_output,
        as_of_date=as_of_date,
    )
    sidecar_export = None
    if active_config.sidecar_output_root is not None:
        sidecar_export = export_prob_up_1d_candidate_sidecar(
            candidate_sidecar_ranking,
            output_root=active_config.sidecar_output_root,
            as_of_date=as_of_date,
            filename_template=active_config.sidecar_filename_template,
            manifest_template=active_config.sidecar_manifest_template,
        )
    return ProbUp1DPipelineResult(
        dataset=dataset,
        training_result=training_result,
        candidate_output=candidate_output,
        candidate_sidecar_ranking=candidate_sidecar_ranking,
        sidecar_export=sidecar_export,
    )


def evaluate_prob_up_1d_candidate_walk_forward(
    dataset: ProbUp1DDataset,
    *,
    config: ProbUp1DConfig | None = None,
) -> ProbUp1DWalkForwardEvaluationResult:
    """Run expanding-window, time-ordered candidate model quality diagnostics."""

    active_config = config or ProbUp1DConfig()
    _validate_walk_forward_config(active_config)
    evaluation_base = _walk_forward_base_frame(dataset)
    labeled_dates = tuple(
        pd.Timestamp(value).normalize()
        for value in evaluation_base.loc[evaluation_base[LABEL_AVAILABLE_COLUMN], "date"].drop_duplicates().sort_values()
    )
    fold_records: list[dict[str, object]] = []
    calibration_tables: list[pd.DataFrame] = []
    stability_tables: list[pd.DataFrame] = []

    train_periods = active_config.walk_forward_initial_train_periods
    fold_index = 1
    while train_periods + active_config.walk_forward_eval_periods <= len(labeled_dates):
        train_dates = labeled_dates[:train_periods]
        eval_dates = labeled_dates[
            train_periods : train_periods + active_config.walk_forward_eval_periods
        ]
        train_full = evaluation_base.loc[
            evaluation_base["date"].dt.normalize().isin(train_dates)
            & evaluation_base[LABEL_AVAILABLE_COLUMN]
        ].copy()
        eval_full = evaluation_base.loc[
            evaluation_base["date"].dt.normalize().isin(eval_dates)
            & evaluation_base[LABEL_AVAILABLE_COLUMN]
        ].copy()
        train_frame = train_full.loc[train_full["_prob_up_1d_complete_features"]].copy()
        eval_frame = eval_full.loc[eval_full["_prob_up_1d_complete_features"]].copy()

        if len(train_frame) >= active_config.min_train_rows and len(eval_frame) >= active_config.min_eval_rows:
            probabilities = _walk_forward_fold_probabilities(
                dataset.feature_columns,
                train_frame,
                eval_frame,
                config=active_config,
            )
            labels = eval_frame[LABEL_COLUMN].to_numpy(dtype=float)
            metrics = _evaluation_metrics(labels, probabilities)
            calibration_error = abs(float(probabilities.mean()) - float(labels.mean()))
            stability = _feature_stability_table(
                fold_index,
                dataset.feature_columns,
                train_frame,
                eval_full,
            )
            stability_tables.append(stability)
            stability_shift = pd.to_numeric(
                stability["standardized_mean_shift"],
                errors="coerce",
            )
            eval_feature_values = _finite_feature_frame(eval_full, dataset.feature_columns)
            total_feature_values = int(len(eval_full) * len(dataset.feature_columns))
            finite_feature_values = int(eval_feature_values.notna().sum().sum())
            nan_missing_rate = (
                1.0 - (finite_feature_values / total_feature_values)
                if total_feature_values
                else float("nan")
            )
            coverage = len(eval_frame) / len(eval_full) if len(eval_full) else float("nan")
            fold_records.append(
                {
                    "fold_index": fold_index,
                    "train_start_date": train_dates[0].date().isoformat(),
                    "train_end_date": train_dates[-1].date().isoformat(),
                    "eval_start_date": eval_dates[0].date().isoformat(),
                    "eval_end_date": eval_dates[-1].date().isoformat(),
                    "train_count": int(len(train_frame)),
                    "evaluation_count": int(len(eval_frame)),
                    "eval_label_available_count": int(len(eval_full)),
                    "brier_score": metrics["brier_score"],
                    "log_loss": metrics["log_loss"],
                    "calibration_error": calibration_error,
                    "calibration_mean_probability": float(probabilities.mean()),
                    "calibration_observed_rate": float(labels.mean()),
                    "coverage": float(coverage),
                    "nan_missing_rate": float(nan_missing_rate),
                    "missing_row_rate": float(1.0 - coverage),
                    "feature_stability_mean_abs_shift": float(stability_shift.abs().mean()),
                    "feature_stability_max_abs_shift": float(stability_shift.abs().max()),
                    "split_mode": "time_ordered_expanding_window",
                    "candidate_only_diagnostic": True,
                }
            )
            calibration_tables.append(
                _calibration_table(
                    fold_index,
                    probabilities,
                    labels,
                    bins=active_config.calibration_bins,
                )
            )
            fold_index += 1

        train_periods += active_config.walk_forward_step_periods

    if len(fold_records) < active_config.walk_forward_min_folds:
        raise ValueError(
            "v0.2 probability walk-forward evaluation could not build the required "
            f"{active_config.walk_forward_min_folds} valid folds; got {len(fold_records)}."
        )

    fold_metrics = pd.DataFrame(fold_records)
    metric_summary = _walk_forward_metric_summary(fold_metrics)
    calibration_table = pd.concat(calibration_tables, ignore_index=True) if calibration_tables else pd.DataFrame()
    feature_stability_table = (
        pd.concat(stability_tables, ignore_index=True) if stability_tables else pd.DataFrame()
    )
    return ProbUp1DWalkForwardEvaluationResult(
        fold_metrics=fold_metrics,
        metric_summary=metric_summary,
        calibration_table=calibration_table,
        feature_stability_table=feature_stability_table,
    )


def export_prob_up_1d_walk_forward_evaluation(
    evaluation: ProbUp1DWalkForwardEvaluationResult,
    *,
    output_root: str | Path,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
    summary_template: str = DEFAULT_WALK_FORWARD_SUMMARY_TEMPLATE,
    fold_template: str = DEFAULT_WALK_FORWARD_FOLD_TEMPLATE,
    calibration_template: str = DEFAULT_WALK_FORWARD_CALIBRATION_TEMPLATE,
    stability_template: str = DEFAULT_WALK_FORWARD_STABILITY_TEMPLATE,
    manifest_template: str = DEFAULT_WALK_FORWARD_MANIFEST_TEMPLATE,
) -> ProbUp1DWalkForwardExportResult:
    """Persist candidate-only walk-forward diagnostic artifacts."""

    if evaluation.fold_metrics.empty:
        raise ValueError("v0.2 probability walk-forward export requires at least one fold.")

    output_dir = Path(output_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    target_date = _resolve_evaluation_export_date(evaluation.fold_metrics, as_of_date=as_of_date)
    date_token = target_date.strftime("%Y%m%d")
    summary_path = output_dir / summary_template.format(as_of_date=date_token)
    fold_path = output_dir / fold_template.format(as_of_date=date_token)
    calibration_path = output_dir / calibration_template.format(as_of_date=date_token)
    stability_path = output_dir / stability_template.format(as_of_date=date_token)
    manifest_path = output_dir / manifest_template.format(as_of_date=date_token)

    evaluation.metric_summary.to_csv(summary_path, index=False)
    evaluation.fold_metrics.to_csv(fold_path, index=False)
    evaluation.calibration_table.to_csv(calibration_path, index=False)
    evaluation.feature_stability_table.to_csv(stability_path, index=False)

    manifest = {
        "artifact_type": "candidate_only_walk_forward_evaluation",
        "candidate_output": PROBABILITY_COLUMN,
        "evaluation_source": WALK_FORWARD_EVALUATION_SOURCE,
        "split_mode": "time_ordered_expanding_window",
        "as_of_date": date_token,
        "fold_count": int(len(evaluation.fold_metrics)),
        "required_metrics": [
            "brier_score",
            "log_loss",
            "calibration_error",
            "coverage",
            "nan_missing_rate",
            "feature_stability_mean_abs_shift",
        ],
        "interpretation_limits": list(evaluation.interpretation_limits),
        "production_rank_activation": False,
        "feeds_production_ranking": False,
        "feeds_reports": False,
        "feeds_composite_scores": False,
        "replace_technical_composite_score": False,
        "replace_final_composite_score": False,
        "feeds_model_selection_from_return_performance": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return ProbUp1DWalkForwardExportResult(
        summary_path=summary_path,
        fold_metrics_path=fold_path,
        calibration_path=calibration_path,
        feature_stability_path=stability_path,
        manifest_path=manifest_path,
        as_of_date=date_token,
        fold_count=int(len(evaluation.fold_metrics)),
    )


def load_candidate_probability_artifact(
    artifact_path: str | Path,
    *,
    expected_artifact_type: str = SELECTION_PACKET_TYPE,
    required_schema: tuple[str, ...] = (),
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """Load a candidate probability artifact for diagnostic-only evaluation."""

    path = Path(artifact_path)
    data = pd.read_csv(path)
    for column in ("date", "as_of_date", DECISION_TIME_COLUMN, EXECUTION_TIME_COLUMN, LABEL_TIME_COLUMN, LABEL_AVAILABILITY_TIME_COLUMN):
        if column in data.columns:
            data[column] = _parse_required_datetime_column(data[column], column=column)
    for column in required_schema:
        if column not in data.columns:
            raise ValueError(f"v0.2 probability evaluation artifact missing required column: {column}")

    validate_prob_up_1d_evaluation_only_backtest_input(
        data,
        expected_artifact_type=expected_artifact_type,
        as_of_date=as_of_date,
    )
    return data


def validate_prob_up_1d_evaluation_only_backtest_input(
    candidate_probability_frame: pd.DataFrame,
    *,
    expected_artifact_type: str = SELECTION_PACKET_TYPE,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
) -> None:
    """Validate candidate artifact boundaries before diagnostic evaluation."""

    if expected_artifact_type == SELECTION_PACKET_TYPE:
        validate_prob_up_1d_selection_packet_schema(candidate_probability_frame)
    else:
        require_columns(
            candidate_probability_frame,
            ("ticker", DECISION_TIME_COLUMN, PROBABILITY_COLUMN),
            context="v0.2 probability evaluation artifact",
        )
        if "date" not in candidate_probability_frame.columns and "as_of_date" not in candidate_probability_frame.columns:
            raise ValueError("v0.2 probability evaluation artifact requires date or as_of_date.")
        assert_no_forbidden_output_columns(
            candidate_probability_frame,
            context="v0.2 probability evaluation artifact",
        )
        validate_v0_2_candidate_artifact_columns(
            candidate_probability_frame.columns,
            context="v0.2 probability evaluation artifact",
            require_timing_fields=False,
        )

    _assert_no_evaluation_forbidden_columns(candidate_probability_frame.columns)
    _validate_evaluation_candidate_timing(candidate_probability_frame)
    if as_of_date is not None:
        _filter_evaluation_backtest_rows(candidate_probability_frame, as_of_date=as_of_date)


def run_prob_up_1d_evaluation_only_backtest(
    candidate_probability_frame: pd.DataFrame,
    *,
    config: ProbUp1DEvaluationOnlyBacktestConfig | None = None,
    expected_artifact_type: str = SELECTION_PACKET_TYPE,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """Return downstream diagnostics for candidate artifacts only."""

    active_config = config or ProbUp1DEvaluationOnlyBacktestConfig()
    _validate_evaluation_only_backtest_config(active_config)
    validate_prob_up_1d_evaluation_only_backtest_input(
        candidate_probability_frame,
        expected_artifact_type=expected_artifact_type,
        as_of_date=as_of_date,
    )
    data = _filter_evaluation_backtest_rows(candidate_probability_frame, as_of_date=as_of_date)
    probabilities = _numeric_series(data[PROBABILITY_COLUMN], column=PROBABILITY_COLUMN)
    valid_probabilities = probabilities.dropna()
    if not valid_probabilities.between(0.0, 1.0).all():
        raise ValueError("v0.2 probability evaluation artifact contains probabilities outside [0, 1].")

    target_date = _resolve_evaluation_backtest_date(data, as_of_date=as_of_date)
    row_count = int(len(data))
    probability_count = int(valid_probabilities.count())
    diagnostic = pd.DataFrame(
        [
            {
                "artifact_type": EVALUATION_BACKTEST_ARTIFACT_TYPE,
                "evaluation_source": EVALUATION_BACKTEST_SOURCE,
                "input_artifact_type": expected_artifact_type,
                "candidate_output": PROBABILITY_COLUMN,
                "as_of_date": target_date.strftime("%Y-%m-%d"),
                "input_row_count": row_count,
                "probability_row_count": probability_count,
                "probability_coverage": float(probability_count / row_count) if row_count else float("nan"),
                "mean_probability": float(valid_probabilities.mean()) if probability_count else float("nan"),
                "min_probability": float(valid_probabilities.min()) if probability_count else float("nan"),
                "max_probability": float(valid_probabilities.max()) if probability_count else float("nan"),
                "candidate_only_diagnostic": True,
                "production_rank_activation": False,
                "feeds_production_ranking": False,
                "feeds_reports": False,
                "feeds_composite_scores": False,
                "replace_technical_composite_score": False,
                "replace_final_composite_score": False,
                "backtest_feedback_into_features": False,
                "backtest_feedback_into_model": False,
                "backtest_feedback_into_scoring": False,
                "backtest_feedback_into_ranking": False,
                "backtest_feedback_into_reports": False,
                "model_selection_from_backtest": False,
                "feature_selection_from_backtest": False,
                "cutoff_selection_from_backtest": False,
                "interpretation_limits": "|".join(EVALUATION_BACKTEST_INTERPRETATION_LIMITS),
            }
        ]
    )
    return diagnostic


def export_prob_up_1d_evaluation_only_backtest(
    diagnostic: pd.DataFrame,
    *,
    output_root: str | Path,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
    diagnostic_template: str = DEFAULT_EVALUATION_BACKTEST_DIAGNOSTIC_TEMPLATE,
    manifest_template: str = DEFAULT_EVALUATION_BACKTEST_MANIFEST_TEMPLATE,
) -> ProbUp1DEvaluationOnlyBacktestExportResult:
    """Persist evaluation-only diagnostics without production outputs."""

    validate_prob_up_1d_evaluation_only_backtest_diagnostic(diagnostic)
    _validate_evaluation_output_root(output_root)
    data = diagnostic.copy()
    target_date = _resolve_evaluation_backtest_date(data, as_of_date=as_of_date)
    if not data.empty:
        mismatched = pd.to_datetime(data["as_of_date"], errors="raise").dt.normalize().ne(target_date)
        if mismatched.any():
            raise ValueError("v0.2 probability evaluation-only diagnostic export contains rows outside as_of_date.")

    output_dir = Path(output_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_token = target_date.strftime("%Y%m%d")
    diagnostic_path = output_dir / diagnostic_template.format(as_of_date=date_token)
    manifest_path = output_dir / manifest_template.format(as_of_date=date_token)
    data.to_csv(diagnostic_path, index=False)

    manifest = {
        "artifact_type": EVALUATION_BACKTEST_ARTIFACT_TYPE,
        "candidate_output": PROBABILITY_COLUMN,
        "evaluation_source": EVALUATION_BACKTEST_SOURCE,
        "as_of_date": date_token,
        "row_count": int(len(data)),
        "schema": list(data.columns),
        "interpretation_limits": list(EVALUATION_BACKTEST_INTERPRETATION_LIMITS),
        "production_rank_activation": False,
        "feeds_production_ranking": False,
        "feeds_reports": False,
        "feeds_composite_scores": False,
        "replace_technical_composite_score": False,
        "replace_final_composite_score": False,
        "backtest_feedback_into_features": False,
        "backtest_feedback_into_model": False,
        "backtest_feedback_into_scoring": False,
        "backtest_feedback_into_ranking": False,
        "backtest_feedback_into_reports": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return ProbUp1DEvaluationOnlyBacktestExportResult(
        diagnostic_path=diagnostic_path,
        manifest_path=manifest_path,
        as_of_date=date_token,
        row_count=int(len(data)),
    )


def validate_prob_up_1d_evaluation_only_backtest_diagnostic(diagnostic: pd.DataFrame) -> None:
    """Validate diagnostic-only evaluation output boundaries."""

    required_columns = (
        "artifact_type",
        "evaluation_source",
        "input_artifact_type",
        "candidate_output",
        "as_of_date",
        "input_row_count",
        "probability_row_count",
        "probability_coverage",
        "candidate_only_diagnostic",
        "production_rank_activation",
        "feeds_production_ranking",
        "feeds_reports",
        "feeds_composite_scores",
        "replace_technical_composite_score",
        "replace_final_composite_score",
        "backtest_feedback_into_features",
        "backtest_feedback_into_model",
        "backtest_feedback_into_scoring",
        "backtest_feedback_into_ranking",
        "backtest_feedback_into_reports",
        "model_selection_from_backtest",
        "feature_selection_from_backtest",
        "cutoff_selection_from_backtest",
    )
    require_columns(diagnostic, required_columns, context="v0.2 probability evaluation-only diagnostic")
    if not diagnostic["artifact_type"].eq(EVALUATION_BACKTEST_ARTIFACT_TYPE).all():
        raise ValueError("v0.2 probability evaluation-only diagnostic has invalid artifact type.")
    true_forbidden = (
        "production_rank_activation",
        "feeds_production_ranking",
        "feeds_reports",
        "feeds_composite_scores",
        "replace_technical_composite_score",
        "replace_final_composite_score",
        "backtest_feedback_into_features",
        "backtest_feedback_into_model",
        "backtest_feedback_into_scoring",
        "backtest_feedback_into_ranking",
        "backtest_feedback_into_reports",
        "model_selection_from_backtest",
        "feature_selection_from_backtest",
        "cutoff_selection_from_backtest",
    )
    for column in true_forbidden:
        if _truthy_flag_present(diagnostic[column]):
            raise ValueError(f"v0.2 probability evaluation-only diagnostic has forbidden true flag: {column}")


def validate_prob_up_1d_schema_consistency(result: ProbUp1DPipelineResult) -> None:
    """Validate train/eval/inference use the same candidate feature schema."""

    dataset_features = tuple(result.dataset.feature_columns)
    model_features = tuple(result.training_result.model.feature_columns)
    if dataset_features != model_features:
        raise ValueError(
            "v0.2 probability schema mismatch between dataset and model: "
            f"dataset={dataset_features}, model={model_features}"
        )

    require_columns(
        result.dataset.feature_table,
        (*IDENTITY_COLUMNS, *dataset_features, FEATURE_VALID_COUNT_COLUMN, FEATURE_STATUS_COLUMN),
        context="v0.2 probability feature schema consistency",
    )
    require_columns(
        result.candidate_output,
        (
            *IDENTITY_COLUMNS,
            DECISION_TIME_COLUMN,
            EXECUTION_TIME_COLUMN,
            LABEL_TIME_COLUMN,
            LABEL_AVAILABILITY_TIME_COLUMN,
            PROBABILITY_COLUMN,
            PROBABILITY_STATUS_COLUMN,
            PROBABILITY_SAMPLE_ROLE_COLUMN,
        ),
        context="v0.2 probability inference schema consistency",
    )

    leaked_features = [column for column in dataset_features if column in result.candidate_output.columns]
    if leaked_features:
        raise ValueError(
            "v0.2 probability candidate output must not expose training feature columns: "
            f"{', '.join(leaked_features)}"
        )

    feature_keys = set(_identity_keys(result.dataset.feature_table))
    output_keys = set(_identity_keys(result.candidate_output))
    if feature_keys != output_keys:
        raise ValueError("v0.2 probability inference output keys do not match feature table keys.")


def _walk_forward_base_frame(dataset: ProbUp1DDataset) -> pd.DataFrame:
    joined = dataset.feature_table.merge(dataset.label_table, on=list(IDENTITY_COLUMNS), how="inner")
    joined["date"] = pd.to_datetime(joined["date"], errors="raise")
    joined[LABEL_AVAILABLE_COLUMN] = joined[LABEL_AVAILABLE_COLUMN].fillna(False).astype(bool)
    numeric_features = _numeric_feature_frame(joined, dataset.feature_columns)
    joined["_prob_up_1d_complete_features"] = _complete_feature_mask(numeric_features)
    if not joined[LABEL_AVAILABLE_COLUMN].any():
        raise ValueError("v0.2 probability walk-forward evaluation has no label-available rows.")
    return joined.sort_values(["date", "ticker"], kind="mergesort").reset_index(drop=True)


def _walk_forward_fold_probabilities(
    feature_columns: tuple[str, ...],
    train_frame: pd.DataFrame,
    evaluation_frame: pd.DataFrame,
    *,
    config: ProbUp1DConfig,
) -> np.ndarray:
    train_x = train_frame.loc[:, list(feature_columns)].to_numpy(dtype=float)
    train_y = train_frame[LABEL_COLUMN].to_numpy(dtype=float)
    means = train_x.mean(axis=0)
    scales = train_x.std(axis=0)
    scales = np.where(scales > 0, scales, 1.0)
    standardized_train_x = (train_x - means) / scales
    coefficients, intercept = _fit_logistic_regression(
        standardized_train_x,
        train_y,
        config=config,
    )
    evaluation_x = evaluation_frame.loc[:, list(feature_columns)].to_numpy(dtype=float)
    standardized_evaluation_x = (evaluation_x - means) / scales
    return _sigmoid(standardized_evaluation_x @ coefficients + intercept)


def _feature_stability_table(
    fold_index: int,
    feature_columns: tuple[str, ...],
    train_frame: pd.DataFrame,
    evaluation_full_frame: pd.DataFrame,
) -> pd.DataFrame:
    train_numeric = _finite_feature_frame(train_frame, feature_columns)
    evaluation_numeric = _finite_feature_frame(evaluation_full_frame, feature_columns)
    records: list[dict[str, object]] = []
    for column in feature_columns:
        train_mean = float(train_numeric[column].mean())
        train_std = float(train_numeric[column].std(ddof=0))
        train_std = train_std if train_std > 0 else 1.0
        evaluation_mean = float(evaluation_numeric[column].mean())
        shift = (evaluation_mean - train_mean) / train_std
        records.append(
            {
                "fold_index": fold_index,
                "feature": column,
                "train_mean": train_mean,
                "evaluation_mean": evaluation_mean,
                "train_std": train_std,
                "standardized_mean_shift": float(shift),
                "evaluation_feature_missing_rate": float(evaluation_numeric[column].isna().mean()),
            }
        )
    return pd.DataFrame(records)


def _finite_feature_frame(frame: pd.DataFrame, feature_columns: tuple[str, ...]) -> pd.DataFrame:
    numeric = _numeric_feature_frame(frame, feature_columns)
    return numeric.replace([np.inf, -np.inf], np.nan)


def _calibration_table(
    fold_index: int,
    probabilities: np.ndarray,
    labels: np.ndarray,
    *,
    bins: int,
) -> pd.DataFrame:
    if len(probabilities) == 0:
        return pd.DataFrame()
    bin_index = np.minimum(np.floor(np.clip(probabilities, 0.0, 1.0) * bins).astype(int), bins - 1)
    records: list[dict[str, object]] = []
    for index in range(bins):
        mask = bin_index == index
        if not mask.any():
            continue
        mean_probability = float(probabilities[mask].mean())
        observed_rate = float(labels[mask].mean())
        records.append(
            {
                "fold_index": fold_index,
                "calibration_bin": int(index + 1),
                "bin_lower": float(index / bins),
                "bin_upper": float((index + 1) / bins),
                "count": int(mask.sum()),
                "mean_probability": mean_probability,
                "observed_positive_rate": observed_rate,
                "absolute_calibration_error": abs(mean_probability - observed_rate),
            }
        )
    return pd.DataFrame(records)


def _walk_forward_metric_summary(fold_metrics: pd.DataFrame) -> pd.DataFrame:
    weight = "evaluation_count"
    summary = {
        "fold_count": float(len(fold_metrics)),
        "evaluation_count": float(fold_metrics["evaluation_count"].sum()),
        "brier_score": _weighted_mean(fold_metrics, "brier_score", weight),
        "log_loss": _weighted_mean(fold_metrics, "log_loss", weight),
        "calibration_error": _weighted_mean(fold_metrics, "calibration_error", weight),
        "coverage": _weighted_mean(fold_metrics, "coverage", "eval_label_available_count"),
        "nan_missing_rate": _weighted_mean(fold_metrics, "nan_missing_rate", "eval_label_available_count"),
        "missing_row_rate": _weighted_mean(fold_metrics, "missing_row_rate", "eval_label_available_count"),
        "feature_stability_mean_abs_shift": float(
            pd.to_numeric(fold_metrics["feature_stability_mean_abs_shift"], errors="coerce").mean()
        ),
        "feature_stability_max_abs_shift": float(
            pd.to_numeric(fold_metrics["feature_stability_max_abs_shift"], errors="coerce").max()
        ),
        "split_mode": "time_ordered_expanding_window",
        "candidate_only_diagnostic": True,
    }
    return pd.DataFrame([summary])


def _weighted_mean(frame: pd.DataFrame, value_column: str, weight_column: str) -> float:
    values = pd.to_numeric(frame[value_column], errors="coerce")
    weights = pd.to_numeric(frame[weight_column], errors="coerce")
    valid = values.notna() & weights.notna() & weights.gt(0)
    if not valid.any():
        return float("nan")
    return float(np.average(values.loc[valid], weights=weights.loc[valid]))


def _resolve_evaluation_export_date(
    fold_metrics: pd.DataFrame,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None,
) -> pd.Timestamp:
    if as_of_date is not None:
        return pd.Timestamp(as_of_date).normalize()
    end_dates = pd.to_datetime(fold_metrics["eval_end_date"], errors="raise")
    return end_dates.max().normalize()


def _prepare_candidate_input(
    frame: pd.DataFrame,
    *,
    price_column: str,
    price_alias_columns: tuple[str, ...],
    as_of_date: date | datetime | pd.Timestamp | str | None,
    symbol_policy: SymbolPolicy,
) -> pd.DataFrame:
    require_columns(frame, IDENTITY_COLUMNS, context="v0.2 probability input")
    assert_no_forbidden_output_columns(frame, context="v0.2 probability input")
    assert_no_valuation_fundamental_columns(frame, context="v0.2 probability input")
    _assert_no_probability_leakage_columns(frame.columns, context="v0.2 probability input")

    data = _normalize_adjusted_close_source(
        frame,
        price_column=price_column,
        price_alias_columns=price_alias_columns,
    )
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


def _prepare_old_score_feature_input(
    frame: pd.DataFrame,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None,
    symbol_policy: SymbolPolicy,
) -> pd.DataFrame:
    require_columns(frame, IDENTITY_COLUMNS, context="v0.2 probability old-score feature input")
    assert_no_forbidden_output_columns(frame, context="v0.2 probability old-score feature input")
    assert_no_valuation_fundamental_columns(frame, context="v0.2 probability old-score feature input")
    _assert_no_probability_leakage_columns(
        frame.columns,
        context="v0.2 probability old-score feature input",
    )

    data = frame.copy()
    data["ticker"] = data["ticker"].astype("string").str.strip()
    valid_ticker = data["ticker"].map(
        lambda value: isinstance(value, str) and symbol_policy.is_valid(value),
        na_action="ignore",
    ).fillna(False)
    if (~valid_ticker).any():
        raise ValueError(f"v0.2 probability old-score feature input ticker must preserve {symbol_policy.display_rule}.")

    data["date"] = pd.to_datetime(data["date"], errors="raise")
    _assert_no_future_dates(data["date"], as_of_date=as_of_date)
    duplicate_rows = data.duplicated(["ticker", "date"], keep=False)
    if duplicate_rows.any():
        raise ValueError("v0.2 probability old-score feature input contains duplicate ticker/date rows.")
    return data.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def _normalize_adjusted_close_source(
    frame: pd.DataFrame,
    *,
    price_column: str,
    price_alias_columns: tuple[str, ...],
) -> pd.DataFrame:
    data = frame.copy()
    aliases_present = tuple(alias for alias in price_alias_columns if alias in data.columns)

    if price_column not in data.columns:
        if not aliases_present:
            if "close" in data.columns:
                raise ValueError(
                    "v0.2 probability input missing adjusted_close; "
                    "close is not an approved adjusted_close alias."
                )
            aliases = ", ".join(price_alias_columns) if price_alias_columns else "none"
            raise ValueError(
                "v0.2 probability input missing adjusted_close or approved "
                f"adjusted-close alias: {aliases}."
            )
        data[price_column] = _numeric_series(data[aliases_present[0]], column=aliases_present[0])
    else:
        data[price_column] = _numeric_series(data[price_column], column=price_column)

    for alias in aliases_present:
        alias_values = _numeric_series(data[alias], column=alias)
        comparable = data[price_column].notna() & alias_values.notna()
        conflicts = comparable & ~np.isclose(
            data[price_column].astype(float),
            alias_values.astype(float),
            rtol=1e-12,
            atol=1e-12,
        )
        if conflicts.any():
            raise ValueError(
                "v0.2 probability input contains conflicting adjusted_close "
                f"and approved alias values: {alias}."
            )
    return data


def _resolve_feature_columns(
    frame: pd.DataFrame,
    requested_feature_columns: tuple[str, ...] | None,
) -> tuple[str, ...]:
    if requested_feature_columns is None:
        feature_columns = DEFAULT_OLD_SCORE_FEATURE_COLUMNS
    else:
        feature_columns = tuple(requested_feature_columns)
    if not feature_columns:
        raise ValueError("v0.2 probability candidate requires at least one approved old-score feature column.")

    not_allowed = [column for column in feature_columns if column not in DEFAULT_OLD_SCORE_FEATURE_COLUMNS]
    if not_allowed:
        raise ValueError(
            "v0.2 probability feature columns are not in the old-score feature allowlist: "
            f"{', '.join(not_allowed)}"
        )

    missing = [column for column in feature_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"v0.2 probability feature columns missing from input: {', '.join(missing)}")
    _assert_no_probability_leakage_columns(feature_columns, context="v0.2 probability feature columns")
    validate_v0_2_candidate_feature_columns(
        feature_columns,
        context="v0.2 probability feature columns",
    )
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
    next_date = data["date"].groupby(data["ticker"], sort=False).shift(-1)
    current_finite = _finite_mask(current_price)
    next_finite = _finite_mask(next_price)
    label_available = current_price.notna() & next_price.notna() & current_finite & next_finite
    labels = (next_price > current_price).astype("Int64").where(label_available)
    label_table[LABEL_TIME_COLUMN] = pd.to_datetime(next_date)
    label_table[LABEL_AVAILABILITY_TIME_COLUMN] = pd.to_datetime(next_date).where(label_available)
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


def _attach_candidate_timing_fields(
    output: pd.DataFrame,
    *,
    label_table: pd.DataFrame | None,
) -> pd.DataFrame:
    timed = output.copy()
    timed[DECISION_TIME_COLUMN] = pd.to_datetime(timed["date"], errors="raise")
    timed[EXECUTION_TIME_COLUMN] = timed[DECISION_TIME_COLUMN] + pd.Timedelta(days=1)
    timed[LABEL_TIME_COLUMN] = pd.NaT
    timed[LABEL_AVAILABILITY_TIME_COLUMN] = pd.NaT
    if label_table is None:
        return timed

    require_columns(
        label_table,
        (*IDENTITY_COLUMNS, LABEL_TIME_COLUMN, LABEL_AVAILABILITY_TIME_COLUMN),
        context="v0.2 probability label timing table",
    )
    timing = label_table.loc[:, [*IDENTITY_COLUMNS, LABEL_TIME_COLUMN, LABEL_AVAILABILITY_TIME_COLUMN]].copy()
    timing["date"] = pd.to_datetime(timing["date"], errors="raise")
    timing[LABEL_TIME_COLUMN] = pd.to_datetime(timing[LABEL_TIME_COLUMN])
    timing[LABEL_AVAILABILITY_TIME_COLUMN] = pd.to_datetime(timing[LABEL_AVAILABILITY_TIME_COLUMN])
    timed = timed.drop(columns=[LABEL_TIME_COLUMN, LABEL_AVAILABILITY_TIME_COLUMN]).merge(
        timing,
        on=list(IDENTITY_COLUMNS),
        how="left",
        validate="one_to_one",
    )
    return timed


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


def _resolve_sidecar_export_date(
    data: pd.DataFrame,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None,
) -> pd.Timestamp:
    if as_of_date is not None:
        return pd.Timestamp(as_of_date).normalize()
    if data.empty:
        raise ValueError("v0.2 probability sidecar export requires as_of_date when the sidecar has no rows.")
    return data["date"].dt.normalize().max()


def _resolve_selection_packet_date(
    data: pd.DataFrame,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None,
) -> pd.Timestamp:
    if as_of_date is not None:
        return pd.Timestamp(as_of_date).normalize()
    probability_rows = data.loc[data[PROBABILITY_COLUMN].notna()]
    if probability_rows.empty:
        raise ValueError("v0.2 probability selection packet requires as_of_date when no probabilities are available.")
    return probability_rows["date"].dt.normalize().max()


def _resolve_selection_packet_export_date(
    data: pd.DataFrame,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None,
) -> pd.Timestamp:
    if as_of_date is not None:
        return pd.Timestamp(as_of_date).normalize()
    if data.empty:
        raise ValueError("v0.2 probability selection packet export requires as_of_date when packet has no rows.")
    return pd.to_datetime(data["as_of_date"], errors="raise").dt.normalize().max()


def _assert_selection_packet_sort(packet: pd.DataFrame) -> None:
    if packet.empty:
        return
    ordered = packet.sort_values(
        [PROBABILITY_COLUMN, "ticker"],
        ascending=[False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    comparable = packet.reset_index(drop=True).loc[:, ["ticker", PROBABILITY_COLUMN]]
    expected = ordered.loc[:, ["ticker", PROBABILITY_COLUMN]]
    if not comparable.equals(expected):
        raise ValueError(
            "v0.2 probability candidate selection packet must be sorted by "
            "prob_up_1d_candidate desc, ticker asc."
        )


def _unique_string_values(data: pd.DataFrame, column: str) -> list[str]:
    if column not in data.columns or data.empty:
        return []
    return sorted(str(value) for value in data[column].dropna().unique())


def _assert_no_evaluation_forbidden_columns(columns: pd.Index | tuple[str, ...] | list[str]) -> None:
    forbidden_exact = {
        LABEL_COLUMN,
        LABEL_AVAILABLE_COLUMN,
        "technical_composite_score",
        "final_composite_score",
        "rank",
        "ranking",
        "production_rank",
        "production_ranking",
        "report_output",
        "generated_report",
        "expected_return",
        "proven_alpha",
        "label",
        "target",
        "target_label",
    }
    forbidden_markers = (
        "up_1d_label",
        "target_",
        "forward_return",
        "future_return",
        "realized_return",
        "label_derived",
        "target_return",
    )
    leaked: list[str] = []
    for column in columns:
        normalized = str(column).lower()
        label_like = (
            normalized.endswith("_label")
            or (normalized.startswith("label_") and normalized != LABEL_CONTRACT_VERSION_COLUMN)
        )
        if normalized in forbidden_exact or label_like or any(marker in normalized for marker in forbidden_markers):
            leaked.append(str(column))
    if leaked:
        raise ValueError(
            "v0.2 probability evaluation-only input contains forbidden feedback or production fields: "
            f"{', '.join(sorted(leaked))}"
        )


def _parse_required_datetime_column(values: pd.Series, *, column: str) -> pd.Series:
    try:
        parsed = pd.to_datetime(values, errors="raise", format="mixed")
    except (TypeError, ValueError):
        raise ValueError(f"v0.2 probability evaluation artifact contains invalid {column} values.")
    return parsed


def _validate_evaluation_candidate_timing(frame: pd.DataFrame) -> None:
    if DECISION_TIME_COLUMN not in frame.columns:
        raise ValueError("v0.2 probability evaluation-only input requires decision_time.")
    decision_time = pd.to_datetime(frame[DECISION_TIME_COLUMN], errors="raise")
    if decision_time.isna().any():
        raise ValueError("v0.2 probability evaluation-only input has missing decision_time.")
    if EXECUTION_TIME_COLUMN in frame.columns:
        execution_time = pd.to_datetime(frame[EXECUTION_TIME_COLUMN], errors="coerce")
        comparable = execution_time.notna()
        if (execution_time.loc[comparable] <= decision_time.loc[comparable]).any():
            raise ValueError("v0.2 probability evaluation-only input has execution_time not after decision_time.")
    for column in (LABEL_TIME_COLUMN, LABEL_AVAILABILITY_TIME_COLUMN):
        if column in frame.columns:
            label_time = pd.to_datetime(frame[column], errors="coerce")
            comparable = label_time.notna()
            if (label_time.loc[comparable] <= decision_time.loc[comparable]).any():
                raise ValueError(f"v0.2 probability evaluation-only input has {column} not after decision_time.")


def _validate_evaluation_only_backtest_config(config: ProbUp1DEvaluationOnlyBacktestConfig) -> None:
    forbidden_true_flags = {
        "updates_model_parameters": config.updates_model_parameters,
        "updates_feature_allowlist": config.updates_feature_allowlist,
        "updates_score_weights": config.updates_score_weights,
        "updates_ranking_rules": config.updates_ranking_rules,
        "updates_composite_definitions": config.updates_composite_definitions,
        "feeds_production_ranking": config.feeds_production_ranking,
        "feeds_reports": config.feeds_reports,
    }
    enabled = [name for name, value in forbidden_true_flags.items() if value]
    if enabled:
        raise ValueError(
            "v0.2 probability evaluation-only config enables forbidden feedback properties: "
            f"{', '.join(enabled)}"
        )
    if config.output_root is not None:
        _validate_evaluation_output_root(config.output_root)


def _validate_evaluation_output_root(output_root: str | Path) -> None:
    normalized = Path(output_root).as_posix().lower()
    forbidden_fragments = (
        "reports/selection",
        "reports/latest",
        "latest_ranking",
        "production_ranking",
        "production_rank",
        "runtime_report",
        "report_output",
        "final_composite",
        "technical_composite",
    )
    blocked = [fragment for fragment in forbidden_fragments if fragment in normalized]
    if blocked:
        raise ValueError(
            "v0.2 probability evaluation-only output root points at forbidden production surface: "
            f"{', '.join(blocked)}"
        )


def _filter_evaluation_backtest_rows(
    data: pd.DataFrame,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None,
) -> pd.DataFrame:
    filtered = data.copy()
    if as_of_date is None:
        return filtered
    target_date = pd.Timestamp(as_of_date).normalize()
    if "as_of_date" in filtered.columns:
        dates = pd.to_datetime(filtered["as_of_date"], errors="raise").dt.normalize()
    else:
        dates = pd.to_datetime(filtered["date"], errors="raise").dt.normalize()
    filtered = filtered.loc[dates.eq(target_date)].copy()
    if filtered.empty:
        raise ValueError(f"v0.2 probability evaluation-only input has no rows for {target_date.date()}.")
    return filtered


def _resolve_evaluation_backtest_date(
    data: pd.DataFrame,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None,
) -> pd.Timestamp:
    if as_of_date is not None:
        return pd.Timestamp(as_of_date).normalize()
    if data.empty:
        raise ValueError("v0.2 probability evaluation-only artifact requires as_of_date when there are no rows.")
    if "as_of_date" in data.columns:
        return pd.to_datetime(data["as_of_date"], errors="raise").dt.normalize().max()
    if "date" in data.columns:
        return pd.to_datetime(data["date"], errors="raise").dt.normalize().max()
    raise ValueError("v0.2 probability evaluation-only artifact requires date or as_of_date.")


def _truthy_flag_present(values: pd.Series) -> bool:
    def is_truthy(value: object) -> bool:
        if pd.isna(value):
            return False
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes"}
        return bool(value)

    return bool(values.map(is_truthy).any())


def _validate_training_config(config: ProbUp1DConfig) -> None:
    if config.min_train_rows <= 0 or config.min_eval_rows <= 0:
        raise ValueError("v0.2 probability train/evaluation minimum rows must be positive.")
    if not 0.0 < config.eval_fraction < 1.0:
        raise ValueError("v0.2 probability eval_fraction must be between 0 and 1.")
    if config.max_iter <= 0 or config.learning_rate <= 0:
        raise ValueError("v0.2 probability logistic training parameters must be positive.")
    if config.l2 < 0:
        raise ValueError("v0.2 probability l2 must be non-negative.")


def _validate_walk_forward_config(config: ProbUp1DConfig) -> None:
    _validate_training_config(config)
    if config.walk_forward_initial_train_periods <= 0:
        raise ValueError("v0.2 probability walk-forward initial train periods must be positive.")
    if config.walk_forward_eval_periods <= 0:
        raise ValueError("v0.2 probability walk-forward evaluation periods must be positive.")
    if config.walk_forward_step_periods <= 0:
        raise ValueError("v0.2 probability walk-forward step periods must be positive.")
    if config.walk_forward_min_folds <= 0:
        raise ValueError("v0.2 probability walk-forward minimum folds must be positive.")
    if config.calibration_bins <= 0:
        raise ValueError("v0.2 probability calibration bins must be positive.")


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
    "CANDIDATE_SIDECAR_RANK_COLUMN",
    "DECISION_TIME_COLUMN",
    "DEFAULT_FEATURE_SET_VERSION",
    "DEFAULT_LABEL_CONTRACT_VERSION",
    "DEFAULT_OLD_SCORE_FEATURE_COLUMNS",
    "DEFAULT_PRICE_ALIAS_COLUMNS",
    "DEFAULT_PRICE_COLUMN",
    "DEFAULT_SELECTION_PACKET_FILENAME_TEMPLATE",
    "DEFAULT_SELECTION_PACKET_MANIFEST_TEMPLATE",
    "DEFAULT_SELECTION_PACKET_ROOT",
    "DEFAULT_EVALUATION_BACKTEST_DIAGNOSTIC_TEMPLATE",
    "DEFAULT_EVALUATION_BACKTEST_MANIFEST_TEMPLATE",
    "DEFAULT_EVALUATION_BACKTEST_ROOT",
    "DEFAULT_SIDECAR_FILENAME_TEMPLATE",
    "DEFAULT_SIDECAR_MANIFEST_TEMPLATE",
    "DEFAULT_WALK_FORWARD_CALIBRATION_TEMPLATE",
    "DEFAULT_WALK_FORWARD_EVALUATION_ROOT",
    "DEFAULT_WALK_FORWARD_FOLD_TEMPLATE",
    "DEFAULT_WALK_FORWARD_MANIFEST_TEMPLATE",
    "DEFAULT_WALK_FORWARD_STABILITY_TEMPLATE",
    "DEFAULT_WALK_FORWARD_SUMMARY_TEMPLATE",
    "EXECUTION_TIME_COLUMN",
    "EVALUATION_BACKTEST_ARTIFACT_TYPE",
    "EVALUATION_BACKTEST_EXPORT_PATH",
    "EVALUATION_BACKTEST_INTERPRETATION_LIMITS",
    "EVALUATION_BACKTEST_PATH",
    "EVALUATION_BACKTEST_SOURCE",
    "FEATURE_INPUT_PATH",
    "FEATURE_INPUT_SOURCE",
    "FEATURE_SET_VERSION_COLUMN",
    "FEATURE_STATUS_COLUMN",
    "FEATURE_VALID_COUNT_COLUMN",
    "LABEL_AVAILABLE_COLUMN",
    "LABEL_AVAILABILITY_TIME_COLUMN",
    "LABEL_COLUMN",
    "LABEL_CONTRACT_VERSION_COLUMN",
    "LABEL_TIME_COLUMN",
    "MODEL_TYPE",
    "MODEL_VERSION",
    "PROBABILITY_COLUMN",
    "PROBABILITY_SAMPLE_ROLE_COLUMN",
    "PROBABILITY_STATUS_COLUMN",
    "ProbUp1DConfig",
    "ProbUp1DDataset",
    "ProbUp1DEvaluationOnlyBacktestConfig",
    "ProbUp1DEvaluationOnlyBacktestExportResult",
    "ProbUp1DModel",
    "ProbUp1DPipelineResult",
    "ProbUp1DSelectionPacketExportResult",
    "ProbUp1DSidecarExportResult",
    "ProbUp1DTrainingResult",
    "ProbUp1DWalkForwardEvaluationResult",
    "ProbUp1DWalkForwardExportResult",
    "WALK_FORWARD_EVALUATION_PATH",
    "WALK_FORWARD_EVALUATION_SOURCE",
    "WALK_FORWARD_INTERPRETATION_LIMITS",
    "SELECTION_PACKET_EXPORT_PATH",
    "SELECTION_PACKET_PATH",
    "SELECTION_PACKET_TYPE",
    "build_prob_up_1d_candidate_sidecar_ranking",
    "build_prob_up_1d_candidate_selection_packet",
    "build_prob_up_1d_dataset",
    "build_prob_up_1d_feature_input_frame",
    "evaluate_prob_up_1d_candidate_walk_forward",
    "export_prob_up_1d_evaluation_only_backtest",
    "export_prob_up_1d_candidate_sidecar",
    "export_prob_up_1d_candidate_selection_packet",
    "export_prob_up_1d_walk_forward_evaluation",
    "fit_prob_up_1d_candidate_model",
    "load_candidate_probability_artifact",
    "predict_prob_up_1d_candidate",
    "run_prob_up_1d_evaluation_only_backtest",
    "run_prob_up_1d_candidate_pipeline",
    "validate_prob_up_1d_evaluation_only_backtest_diagnostic",
    "validate_prob_up_1d_evaluation_only_backtest_input",
    "validate_prob_up_1d_schema_consistency",
    "validate_prob_up_1d_selection_packet_schema",
)
