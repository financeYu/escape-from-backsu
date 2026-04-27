"""Evaluation-only next-horizon up-probability helpers.

This module does not train a model, create rankings, change composite scores,
or generate trading recommendations. It only builds supervised evaluation
labels and converts an already calibrated probability into a 0-100 candidate
score.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

import pandas as pd

from src.scores.schema import assert_no_valuation_fundamental_columns, require_columns


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "Quant_mvp" / "config" / "up_probability.toml"
DEFAULT_HORIZON_TRADING_DAYS = 1
DEFAULT_SCORE_NAME = "next_horizon_up_probability_score"
DEFAULT_PROBABILITY_COLUMN = "next_horizon_up_probability"
DEFAULT_LABEL_COLUMN = "next_horizon_up_label"
DEFAULT_RETURN_COLUMN = "observed_horizon_close_return"
DEFAULT_BUCKET_COLUMN = "next_horizon_probability_bucket"
DEFAULT_INPUT_CUTOFF = "close_t"
DEFAULT_NOTICE = (
    "KOSPI200 technical-only candidate up-probability score; "
    "evaluation-only, no trading recommendation."
)


@dataclass(frozen=True)
class UpProbabilityScoreConfig:
    """Configuration for candidate next-horizon up-probability scoring."""

    horizon_trading_days: int = DEFAULT_HORIZON_TRADING_DAYS
    probability_column: str = DEFAULT_PROBABILITY_COLUMN
    score_column: str = DEFAULT_SCORE_NAME
    label_column: str = DEFAULT_LABEL_COLUMN
    observed_return_column: str = DEFAULT_RETURN_COLUMN
    bucket_column: str = DEFAULT_BUCKET_COLUMN
    input_cutoff: str = DEFAULT_INPUT_CUTOFF
    evaluation_only_notice: str = DEFAULT_NOTICE

    def __post_init__(self) -> None:
        if self.horizon_trading_days < 1:
            raise ValueError("horizon_trading_days must be greater than or equal to 1.")


def load_up_probability_score_config(path: str | Path = DEFAULT_CONFIG_PATH) -> UpProbabilityScoreConfig:
    """Load the candidate score config without activating runtime scoring."""

    config_path = Path(path)
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    section = data.get("up_probability_score", {})
    columns = section.get("columns", {})
    return UpProbabilityScoreConfig(
        horizon_trading_days=int(section.get("horizon_trading_days", DEFAULT_HORIZON_TRADING_DAYS)),
        probability_column=str(columns.get("probability", DEFAULT_PROBABILITY_COLUMN)),
        score_column=str(columns.get("score", DEFAULT_SCORE_NAME)),
        label_column=str(columns.get("label", DEFAULT_LABEL_COLUMN)),
        observed_return_column=str(columns.get("observed_return", DEFAULT_RETURN_COLUMN)),
        bucket_column=str(columns.get("bucket", DEFAULT_BUCKET_COLUMN)),
        input_cutoff=str(section.get("input_cutoff", DEFAULT_INPUT_CUTOFF)),
        evaluation_only_notice=str(section.get("evaluation_only_notice", DEFAULT_NOTICE)),
    )


def add_next_horizon_up_label(
    frame: pd.DataFrame,
    *,
    config: UpProbabilityScoreConfig | None = None,
    ticker_column: str = "ticker",
    date_column: str = "date",
    close_column: str = "close",
) -> pd.DataFrame:
    """Add a supervised evaluation label for close[t+h] / close[t] - 1 > 0."""

    resolved = config or UpProbabilityScoreConfig()
    require_columns(frame, (ticker_column, date_column, close_column), context="up-probability label input")
    assert_no_valuation_fundamental_columns(frame, context="up-probability label input")

    output = _sorted_identity_frame(frame, ticker_column=ticker_column, date_column=date_column)
    close = pd.to_numeric(output[close_column], errors="coerce")
    future_close = close.groupby(output[ticker_column], sort=False).shift(-resolved.horizon_trading_days)
    observed_return = (future_close / close) - 1.0
    label = observed_return.gt(0.0).astype("Int64")
    label = label.mask(observed_return.isna(), pd.NA)

    output[resolved.observed_return_column] = observed_return
    output[resolved.label_column] = label
    output["horizon_trading_days"] = resolved.horizon_trading_days
    output["input_cutoff"] = resolved.input_cutoff
    output["evaluation_only_notice"] = resolved.evaluation_only_notice
    return output.reset_index(drop=True)


def score_next_horizon_up_probability(
    frame: pd.DataFrame,
    *,
    config: UpProbabilityScoreConfig | None = None,
    ticker_column: str = "ticker",
    date_column: str = "date",
) -> pd.DataFrame:
    """Convert calibrated probabilities in [0, 1] into 0-100 candidate scores."""

    resolved = config or UpProbabilityScoreConfig()
    require_columns(
        frame,
        (ticker_column, date_column, resolved.probability_column),
        context="up-probability score input",
    )
    assert_no_valuation_fundamental_columns(frame, context="up-probability score input")

    output = _sorted_identity_frame(frame, ticker_column=ticker_column, date_column=date_column)
    probability = pd.to_numeric(output[resolved.probability_column], errors="coerce")
    _assert_probability_range(probability)

    output[resolved.score_column] = probability * 100.0
    output[resolved.bucket_column] = probability.map(_probability_bucket)
    output["horizon_trading_days"] = resolved.horizon_trading_days
    output["horizon_usage_status"] = _horizon_usage_status(resolved.horizon_trading_days)
    output["input_cutoff"] = resolved.input_cutoff
    output["evaluation_only_notice"] = resolved.evaluation_only_notice
    return output.reset_index(drop=True)


def build_next_horizon_up_probability_candidate_frame(
    frame: pd.DataFrame,
    *,
    config: UpProbabilityScoreConfig | None = None,
    ticker_column: str = "ticker",
    date_column: str = "date",
    close_column: str = "close",
) -> pd.DataFrame:
    """Build a candidate frame with labels when close data is available."""

    resolved = config or UpProbabilityScoreConfig()
    scored = score_next_horizon_up_probability(
        frame,
        config=resolved,
        ticker_column=ticker_column,
        date_column=date_column,
    )
    if close_column not in scored.columns:
        return scored

    labeled = add_next_horizon_up_label(
        scored,
        config=resolved,
        ticker_column=ticker_column,
        date_column=date_column,
        close_column=close_column,
    )
    return labeled


def _sorted_identity_frame(frame: pd.DataFrame, *, ticker_column: str, date_column: str) -> pd.DataFrame:
    output = frame.copy()
    output[ticker_column] = output[ticker_column].astype("string").str.zfill(6)
    output[date_column] = pd.to_datetime(output[date_column])
    return output.sort_values([ticker_column, date_column]).reset_index(drop=True)


def _assert_probability_range(probability: pd.Series) -> None:
    present = probability.dropna()
    invalid = present.lt(0.0) | present.gt(1.0)
    if invalid.any():
        raise ValueError("Calibrated up-probability values must be within [0, 1].")


def _probability_bucket(value: float) -> str:
    if pd.isna(value):
        return "missing_probability"
    if value < 0.4:
        return "low_candidate_probability"
    if value <= 0.6:
        return "neutral_candidate_probability"
    return "high_candidate_probability"


def _horizon_usage_status(horizon_trading_days: int) -> str:
    if horizon_trading_days == DEFAULT_HORIZON_TRADING_DAYS:
        return "evaluation_only_default_horizon"
    return "evaluation_only_non_default_horizon"


__all__ = (
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_HORIZON_TRADING_DAYS",
    "UpProbabilityScoreConfig",
    "add_next_horizon_up_label",
    "build_next_horizon_up_probability_candidate_frame",
    "load_up_probability_score_config",
    "score_next_horizon_up_probability",
)
