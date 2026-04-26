from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.features.up_probability import (
    DEFAULT_HORIZON_TRADING_DAYS,
    UpProbabilityScoreConfig,
    add_next_horizon_up_label,
    build_next_horizon_up_probability_candidate_frame,
    load_up_probability_score_config,
    score_next_horizon_up_probability,
)


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["005930", "005930", "005930", "000660", "000660", "000660"],
            "date": [
                "2026-01-01",
                "2026-01-02",
                "2026-01-03",
                "2026-01-01",
                "2026-01-02",
                "2026-01-03",
            ],
            "close": [100.0, 101.0, 99.0, 50.0, 49.0, 52.0],
            "next_horizon_up_probability": [0.61, 0.55, 0.40, 0.39, 0.70, None],
        }
    )


def test_default_config_uses_one_trading_day_horizon() -> None:
    config = load_up_probability_score_config()

    assert config.horizon_trading_days == DEFAULT_HORIZON_TRADING_DAYS == 1
    assert config.score_column == "next_horizon_up_probability_score"
    assert config.label_column == "next_horizon_up_label"


def test_add_next_horizon_up_label_uses_next_trading_row_per_ticker() -> None:
    result = add_next_horizon_up_label(sample_frame())

    samsung = result[result["ticker"].eq("005930")]
    hynix = result[result["ticker"].eq("000660")]

    assert samsung["next_horizon_up_label"].tolist() == [1, 0, pd.NA]
    assert hynix["next_horizon_up_label"].tolist() == [0, 1, pd.NA]
    assert samsung["observed_horizon_close_return"].iloc[0] == pytest.approx(0.01)
    assert result["horizon_trading_days"].eq(1).all()
    assert result["input_cutoff"].eq("close_t").all()


def test_score_next_horizon_up_probability_maps_calibrated_probability_to_0_100() -> None:
    result = score_next_horizon_up_probability(sample_frame())

    samsung = result[result["ticker"].eq("005930")]

    assert samsung["next_horizon_up_probability_score"].iloc[0] == pytest.approx(61.0)
    assert samsung["next_horizon_probability_bucket"].tolist() == [
        "high_candidate_probability",
        "neutral_candidate_probability",
        "neutral_candidate_probability",
    ]
    assert result["horizon_usage_status"].eq("evaluation_only_default_horizon").all()
    assert "rank" not in result.columns
    assert "technical_composite_score" not in result.columns
    assert "final_composite_score" not in result.columns


def test_build_candidate_frame_combines_score_and_label_without_ranking_outputs() -> None:
    result = build_next_horizon_up_probability_candidate_frame(sample_frame())

    assert "next_horizon_up_probability_score" in result.columns
    assert "next_horizon_up_label" in result.columns
    assert "observed_horizon_close_return" in result.columns
    forbidden = {
        "rank",
        "ranking",
        "technical_composite_score",
        "final_composite_score",
        "buy",
        "sell",
        "recommendation",
    }
    assert not forbidden.intersection(result.columns)


def test_probability_score_rejects_out_of_range_values() -> None:
    frame = sample_frame()
    frame.loc[0, "next_horizon_up_probability"] = 1.01

    with pytest.raises(ValueError, match=r"within \[0, 1\]"):
        score_next_horizon_up_probability(frame)


def test_candidate_helpers_reject_valuation_inputs() -> None:
    frame = sample_frame()
    frame["PER"] = 10.0

    with pytest.raises(ValueError, match="valuation/fundamental columns"):
        score_next_horizon_up_probability(frame)


def test_non_default_horizon_is_marked_non_default_without_new_score_name() -> None:
    config = UpProbabilityScoreConfig(horizon_trading_days=3)

    result = score_next_horizon_up_probability(sample_frame(), config=config)

    assert result["horizon_trading_days"].eq(3).all()
    assert result["horizon_usage_status"].eq("evaluation_only_non_default_horizon").all()
    assert "next_3d_up_probability_score" not in result.columns
