from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.validation.v0_2_candidate_ml_guardrails import (  # noqa: E402
    validate_v0_2_candidate_artifact_columns,
    validate_v0_2_candidate_artifact_frame,
    validate_v0_2_candidate_feature_columns,
    validate_v0_2_candidate_text,
)


def candidate_artifact() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "005930",
                "date": "2026-04-24",
                "decision_time": "2026-04-24",
                "execution_time": "2026-04-24",
                "label_time": "2026-04-27",
                "label_availability_time": "2026-04-27",
                "prob_up_1d_candidate": 0.58,
                "prob_up_1d_candidate_sidecar_rank": 1,
                "status": "candidate_only_sidecar",
            }
        ]
    )


def test_candidate_artifact_accepts_candidate_only_sidecar_shape() -> None:
    validate_v0_2_candidate_artifact_frame(
        candidate_artifact(),
        feature_columns=("old_score_a_raw", "old_score_b_raw"),
    )


def test_candidate_artifact_rejects_final_and_technical_composite_writes() -> None:
    for column in ("final_composite_score", "technical_composite_score"):
        frame = candidate_artifact()
        frame[column] = 50.0

        with pytest.raises(ValueError, match="forbidden production/backtest/trading columns"):
            validate_v0_2_candidate_artifact_frame(frame)


def test_candidate_artifact_rejects_production_ranking_activation_columns() -> None:
    frame = candidate_artifact()
    frame["production_rank"] = 1

    with pytest.raises(ValueError, match="production_rank"):
        validate_v0_2_candidate_artifact_frame(frame)


def test_candidate_artifact_rejects_backtest_feedback_fields() -> None:
    for column in ("sharpe_ratio", "realized_holding_return"):
        frame = candidate_artifact()
        frame[column] = 1.4

        with pytest.raises(ValueError, match=column):
            validate_v0_2_candidate_artifact_frame(frame)


def test_candidate_text_rejects_backtest_feedback_and_production_activation() -> None:
    with pytest.raises(ValueError, match="backtest feedback"):
        validate_v0_2_candidate_text(
            "Backtest feedback tuned the model score and ranking weights."
        )

    with pytest.raises(ValueError, match="production ranking activation"):
        validate_v0_2_candidate_text(
            "The candidate output activates production ranking for the latest report."
        )


def test_candidate_text_rejects_trading_and_performance_language() -> None:
    for text in (
        "This emits a buy signal recommendation.",
        "The score implies expected-return improvement.",
        "The model has proven-alpha.",
    ):
        with pytest.raises(ValueError, match="forbidden v0.2 candidate language"):
            validate_v0_2_candidate_text(text)


def test_feature_columns_reject_future_label_and_backtest_leakage() -> None:
    for feature in (
        "next_day_return",
        "target_label",
        "future_close",
        "realized_return_1d",
        "backtest_hit_rate",
    ):
        with pytest.raises(ValueError, match="leakage/backtest feature columns"):
            validate_v0_2_candidate_feature_columns(("old_score_a_raw", feature))


def test_feature_columns_allow_non_label_y_characters() -> None:
    validate_v0_2_candidate_feature_columns(("volatility_regime_raw", "liquidity_proxy_raw"))


def test_candidate_artifact_requires_timing_fields() -> None:
    frame = candidate_artifact().drop(columns=["decision_time", "label_availability_time"])

    with pytest.raises(ValueError, match="missing required timing fields"):
        validate_v0_2_candidate_artifact_frame(frame)


def test_candidate_artifact_requires_probability_column() -> None:
    frame = candidate_artifact().drop(columns=["prob_up_1d_candidate"])

    with pytest.raises(ValueError, match="missing required candidate probability column"):
        validate_v0_2_candidate_artifact_columns(frame.columns)
