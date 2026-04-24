from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scores.mean_reversion_scores import PartAScoreConfig
from src.scores.technical_scores import (
    ALL_STEP9_RAW_SCORE_COLUMNS,
    calculate_all_raw_scores,
)
from src.scores.trend_vol_flow_scores import TrendVolFlowScoreWindows


def part_a_config() -> PartAScoreConfig:
    return PartAScoreConfig(
        return_window=1,
        atr_window=14,
        rsi_window=14,
        realized_vol_window=20,
        realized_vol_percentile_window=3,
        minimum_history_by_score={
            "short_term_overreaction": 2,
            "atr_adjusted_oversold_distance": 2,
            "rsi_price_divergence": 2,
            "realized_vol_percentile": 2,
        },
        bollinger_window=3,
    )


def part_b_windows() -> TrendVolFlowScoreWindows:
    return TrendVolFlowScoreWindows(
        donchian=3,
        bollinger=3,
        cmf=3,
        efficiency_ratio=3,
        minimum_history_required=4,
    )


def step9_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["005930", "005930", "005930", "005930", "005930"],
            "date": [
                "2026-01-01",
                "2026-01-02",
                "2026-01-03",
                "2026-01-04",
                "2026-01-05",
            ],
            "close": [10.0, 11.0, 12.0, 14.0, 13.0],
            "history_count": [1, 2, 3, 4, 5],
            "minimum_history_required": [2, 2, 2, 2, 2],
            "warmup_state": ["warmup", "ready", "ready", "ready", "ready"],
            "return_1d": [math.nan, 0.10, 12.0 / 11.0 - 1.0, 14.0 / 12.0 - 1.0, 13.0 / 14.0 - 1.0],
            "atr_14": [math.nan, 1.5, 1.75, 2.0, 2.25],
            "bollinger_mid_3": [math.nan, math.nan, 11.0, 12.5, 13.0],
            "rsi_14": [50.0, 52.0, 55.0, 54.0, 56.0],
            "realized_vol_20": [3.0, 1.0, 2.0, 4.0, 5.0],
            "donchian_high_prior_3": [math.nan, math.nan, math.nan, 12.5, 14.5],
            "bollinger_width_3": [math.nan, math.nan, 0.20, 0.10, 0.12],
            "cmf_3": [math.nan, math.nan, 0.20, -0.25, 0.15],
            "efficiency_ratio_3": [math.nan, math.nan, math.nan, 0.75, 0.25],
            "return_3d": [math.nan, math.nan, math.nan, 0.40, 0.18],
        }
    )


def calculate(frame: pd.DataFrame) -> pd.DataFrame:
    return calculate_all_raw_scores(
        frame,
        part_a_config=part_a_config(),
        part_b_windows=part_b_windows(),
        as_of_date="2026-01-31",
    )


def test_integrated_scores_emit_only_the_eight_step9_raw_columns() -> None:
    result = calculate(step9_frame())

    assert tuple(column for column in result.columns if column.endswith("_raw")) == (
        ALL_STEP9_RAW_SCORE_COLUMNS
    )
    assert set(ALL_STEP9_RAW_SCORE_COLUMNS) == {
        "short_term_overreaction_raw",
        "atr_adjusted_oversold_distance_raw",
        "donchian_breakout_distance_raw",
        "bollinger_width_squeeze_raw",
        "cmf_confirmation_raw",
        "rsi_price_divergence_raw",
        "realized_vol_percentile_raw",
        "efficiency_ratio_trend_raw",
    }
    last_ready = result[result["date"].eq(pd.Timestamp("2026-01-04"))].iloc[0]
    assert last_ready["short_term_overreaction_raw"] == pytest.approx(-(14.0 / 12.0 - 1.0))
    assert last_ready["atr_adjusted_oversold_distance_raw"] == pytest.approx((12.5 - 14.0) / 2.0)
    assert last_ready["rsi_price_divergence_raw"] == pytest.approx(0.0)
    assert last_ready["realized_vol_percentile_raw"] == pytest.approx(1.0)
    assert last_ready["donchian_breakout_distance_raw"] == pytest.approx((14.0 / 12.5) - 1.0)
    assert last_ready["bollinger_width_squeeze_raw"] == pytest.approx(-0.10)
    assert last_ready["cmf_confirmation_raw"] == pytest.approx(-0.25)
    assert last_ready["efficiency_ratio_trend_raw"] == pytest.approx(0.75)
    assert last_ready["score_coverage_status"] == "adequate"


def test_integrated_scores_preserve_alignment_and_leading_zero_ticker() -> None:
    frame = step9_frame().iloc[[3, 1, 0, 4, 2]].reset_index(drop=True)

    result = calculate(frame)

    assert result["ticker"].iloc[0] == "005930"
    assert str(result["ticker"].dtype) == "string"
    assert result["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
        "2026-01-04",
        "2026-01-05",
    ]


def test_integrated_scores_do_not_use_future_rows() -> None:
    base = step9_frame()
    changed_future = base.copy()
    changed_future.loc[4, "realized_vol_20"] = 1000.0
    changed_future.loc[4, "close"] = 9999.0
    changed_future.loc[4, "efficiency_ratio_3"] = 0.01

    result = calculate(base)
    changed_result = calculate(changed_future)

    past = result[result["date"].eq(pd.Timestamp("2026-01-04"))].iloc[0]
    changed_past = changed_result[changed_result["date"].eq(pd.Timestamp("2026-01-04"))].iloc[0]
    for column in ALL_STEP9_RAW_SCORE_COLUMNS:
        left = past[column]
        right = changed_past[column]
        if pd.isna(left):
            assert pd.isna(right)
        else:
            assert left == pytest.approx(right)


def test_integrated_scores_reject_valuation_or_fundamental_inputs() -> None:
    frame = step9_frame()
    frame["PER"] = [10.0, 11.0, 12.0, 13.0, 14.0]

    with pytest.raises(ValueError, match="valuation/fundamental columns"):
        calculate(frame)


def test_integrated_scores_reject_financial_fundamental_valuation_prefixes() -> None:
    for forbidden_column in (
        "financial_revenue",
        "fundamental_quality_score",
        "valuation_discount_flag",
    ):
        frame = step9_frame()
        frame[forbidden_column] = [1, 1, 1, 1, 1]

        with pytest.raises(ValueError, match="valuation/fundamental columns"):
            calculate(frame)


def test_integrated_scores_exclude_forbidden_outputs() -> None:
    result = calculate(step9_frame())

    forbidden = {
        "rank",
        "ranking",
        "latest_rank",
        "normalized_score",
        "technical_composite_score",
        "final_composite_score",
        "forward_return",
        "future_return",
        "backtest_return",
        "alpha",
        "signal",
        "buy",
        "sell",
        "valuation_score",
    }
    assert not forbidden.intersection(result.columns)
    assert not [column for column in result.columns if column.endswith("_normalized")]
