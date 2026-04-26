from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scores.trend_vol_flow_scores import (
    PART_B_RAW_SCORE_COLUMNS,
    TrendVolFlowScoreWindows,
    calculate_trend_vol_flow_raw_scores,
    load_part_b_score_windows,
)
from src.preprocess.schema_validator import GENERIC_EXCHANGE_SYMBOL_POLICY


def part_b_windows(window: int = 3, minimum_history: int = 4) -> TrendVolFlowScoreWindows:
    return TrendVolFlowScoreWindows(
        donchian=window,
        bollinger=window,
        cmf=window,
        efficiency_ratio=window,
        minimum_history_required=minimum_history,
    )


def part_b_frame(*, ticker: str = "005930") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [ticker, ticker, ticker, ticker],
            "date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
            "close": [10.0, 11.0, 12.0, 14.0],
            "history_count": [1, 2, 3, 4],
            "warmup_state": ["warmup", "warmup", "warmup", "ready"],
            "donchian_high_prior_3": [math.nan, math.nan, math.nan, 12.5],
            "bollinger_width_3": [math.nan, math.nan, 0.20, 0.10],
            "cmf_3": [math.nan, math.nan, 0.20, -0.25],
            "efficiency_ratio_3": [math.nan, math.nan, math.nan, 0.75],
            "return_3d": [math.nan, math.nan, math.nan, 0.40],
        }
    )


def default_config_part_b_frame(*, rows: int = 60) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    close = [100.0 + idx for idx in range(rows)]
    return pd.DataFrame(
        {
            "ticker": ["005930"] * rows,
            "date": dates,
            "close": close,
            "history_count": list(range(1, rows + 1)),
            "warmup_state": ["ready"] * rows,
            "donchian_high_prior_20": [math.nan] * (rows - 1) + [158.0],
            "bollinger_width_20": [0.10] * rows,
            "cmf_20": [0.20] * rows,
            "efficiency_ratio_20": [0.80] * rows,
            "return_20d": [math.nan] * (rows - 1) + [0.20],
        }
    )


def test_part_b_deterministic_raw_formulas() -> None:
    result = calculate_trend_vol_flow_raw_scores(
        part_b_frame(), windows=part_b_windows()
    )

    last = result[result["date"].eq(pd.Timestamp("2026-01-04"))].iloc[0]
    assert last["donchian_breakout_distance_raw"] == pytest.approx((14.0 / 12.5) - 1.0)
    assert last["bollinger_width_squeeze_raw"] == pytest.approx(-0.10)
    assert last["cmf_confirmation_raw"] == pytest.approx(-0.25)
    assert last["efficiency_ratio_trend_raw"] == pytest.approx(0.75)
    assert last["score_warmup_state"] == "ready"
    assert last["score_coverage_status"] == "adequate"
    assert last["score_data_quality_flag"] == "valid"


def test_part_b_scores_do_not_cross_ticker_boundaries() -> None:
    up = part_b_frame(ticker="005930")
    down = part_b_frame(ticker="000660")
    down["close"] = [100.0, 99.0, 98.0, 96.0]
    down["return_3d"] = math.nan
    up["return_3d"] = math.nan
    down["efficiency_ratio_3"] = [math.nan, math.nan, math.nan, 0.60]
    frame = pd.concat([up.iloc[[0, 2, 1, 3]], down.iloc[[1, 0, 3, 2]]], ignore_index=True)

    result = calculate_trend_vol_flow_raw_scores(frame, windows=part_b_windows())

    samsung = result[
        result["ticker"].eq("005930") & result["date"].eq(pd.Timestamp("2026-01-04"))
    ].iloc[0]
    hynix = result[
        result["ticker"].eq("000660") & result["date"].eq(pd.Timestamp("2026-01-04"))
    ].iloc[0]
    assert samsung["efficiency_ratio_trend_raw"] == pytest.approx(0.75)
    assert hynix["efficiency_ratio_trend_raw"] == pytest.approx(-0.60)


def test_part_b_sorts_by_ticker_and_date_before_calculation() -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["005930", "005930", "005930", "005930"],
            "date": ["2026-01-03", "2026-01-01", "2026-01-04", "2026-01-02"],
            "close": [15.0, 10.0, 18.0, 12.0],
            "donchian_high_prior_2": [12.0, math.nan, 15.0, math.nan],
            "bollinger_width_2": [0.15, math.nan, 0.12, 0.20],
            "cmf_2": [0.10, math.nan, 0.30, -0.10],
            "efficiency_ratio_2": [0.70, math.nan, 0.90, math.nan],
        }
    )

    result = calculate_trend_vol_flow_raw_scores(
        frame, windows=part_b_windows(window=2, minimum_history=3)
    )

    assert result["date"].tolist() == [
        pd.Timestamp("2026-01-01"),
        pd.Timestamp("2026-01-02"),
        pd.Timestamp("2026-01-03"),
        pd.Timestamp("2026-01-04"),
    ]
    last = result.iloc[-1]
    assert last["efficiency_ratio_trend_raw"] == pytest.approx(0.90)


def test_part_b_preserves_ticker_leading_zero_string() -> None:
    result = calculate_trend_vol_flow_raw_scores(
        part_b_frame(ticker="005930"), windows=part_b_windows()
    )

    assert result["ticker"].iloc[0] == "005930"
    assert str(result["ticker"].dtype) == "string"


def test_part_b_accepts_kospi200_alphanumeric_code() -> None:
    result = calculate_trend_vol_flow_raw_scores(
        part_b_frame(ticker="0126Z0"), windows=part_b_windows()
    )

    assert result["ticker"].iloc[0] == "0126Z0"
    assert str(result["ticker"].dtype) == "string"


def test_part_b_generic_symbol_policy_accepts_exchange_symbol() -> None:
    result = calculate_trend_vol_flow_raw_scores(
        part_b_frame(ticker="AAPL"),
        windows=part_b_windows(),
        symbol_policy=GENERIC_EXCHANGE_SYMBOL_POLICY,
    )

    assert result["ticker"].iloc[0] == "AAPL"
    assert str(result["ticker"].dtype) == "string"


def test_part_b_rejects_invalid_or_leading_zero_lost_ticker() -> None:
    with pytest.raises(ValueError, match="six-character uppercase alphanumeric string format"):
        calculate_trend_vol_flow_raw_scores(
            part_b_frame(ticker="5930"), windows=part_b_windows()
        )


def test_part_b_rejects_future_dates_when_as_of_date_is_supplied() -> None:
    frame = part_b_frame()
    frame.loc[3, "date"] = "2026-02-01"

    with pytest.raises(ValueError, match="future dates"):
        calculate_trend_vol_flow_raw_scores(
            frame,
            windows=part_b_windows(),
            as_of_date="2026-01-31",
        )


def test_part_b_marks_insufficient_history_without_optimistic_fill() -> None:
    short = part_b_frame().iloc[:3].copy()
    result = calculate_trend_vol_flow_raw_scores(short, windows=part_b_windows())

    assert set(result["score_warmup_state"]) == {"insufficient_history"}
    assert result.loc[:, list(PART_B_RAW_SCORE_COLUMNS)].isna().all().all()
    assert set(result["score_coverage_status"]) == {"blocked"}
    assert result["score_data_quality_flag"].str.contains("insufficient_history").all()
    assert set(result["donchian_breakout_distance_missing_reason"]) == {
        "insufficient_history"
    }


def test_part_b_is_nan_aware_and_does_not_create_infinite_values() -> None:
    frame = part_b_frame()
    frame.loc[3, "donchian_high_prior_3"] = 0.0
    frame.loc[3, "cmf_3"] = math.nan

    result = calculate_trend_vol_flow_raw_scores(frame, windows=part_b_windows())
    last = result.iloc[-1]

    raw_values = result.loc[:, list(PART_B_RAW_SCORE_COLUMNS)].to_numpy().ravel()
    finite_or_nan = [pd.isna(value) or math.isfinite(float(value)) for value in raw_values]
    assert all(finite_or_nan)
    assert pd.isna(last["donchian_breakout_distance_raw"])
    assert last["donchian_breakout_distance_missing_reason"] == "zero_denominator"
    assert pd.isna(last["cmf_confirmation_raw"])
    assert last["cmf_confirmation_missing_reason"] == "missing_required_input"
    assert "invalid_numeric" in last["score_data_quality_flag"]
    assert "missing_required_input" in last["score_data_quality_flag"]


def test_part_b_no_lookahead_when_future_row_changes() -> None:
    base = pd.concat(
        [
            part_b_frame(),
            pd.DataFrame(
                {
                    "ticker": ["005930"],
                    "date": ["2026-01-05"],
                    "close": [15.0],
                    "history_count": [5],
                    "warmup_state": ["ready"],
                    "donchian_high_prior_3": [14.0],
                    "bollinger_width_3": [0.08],
                    "cmf_3": [0.35],
                    "efficiency_ratio_3": [0.65],
                    "return_3d": [math.nan],
                }
            ),
        ],
        ignore_index=True,
    )
    changed_future = base.copy()
    changed_future.loc[4, "close"] = 9999.0
    changed_future.loc[4, "efficiency_ratio_3"] = 0.01

    first = calculate_trend_vol_flow_raw_scores(base, windows=part_b_windows())
    second = calculate_trend_vol_flow_raw_scores(changed_future, windows=part_b_windows())

    first_past = first[first["date"].eq(pd.Timestamp("2026-01-04"))].iloc[0]
    second_past = second[second["date"].eq(pd.Timestamp("2026-01-04"))].iloc[0]
    for column in PART_B_RAW_SCORE_COLUMNS:
        assert first_past[column] == pytest.approx(second_past[column])


def test_part_b_output_excludes_forbidden_columns_and_part_a_scores() -> None:
    result = calculate_trend_vol_flow_raw_scores(
        part_b_frame(), windows=part_b_windows()
    )

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
    assert "short_term_overreaction_raw" not in result.columns
    assert "atr_adjusted_oversold_distance_raw" not in result.columns
    assert "rsi_price_divergence_raw" not in result.columns


def test_part_b_rejects_valuation_or_fundamental_input_columns() -> None:
    frame = part_b_frame()
    frame["PER"] = [9.0, 9.1, 9.2, 9.3]

    with pytest.raises(ValueError, match="valuation/fundamental columns"):
        calculate_trend_vol_flow_raw_scores(frame, windows=part_b_windows())


def test_part_b_rejects_forbidden_output_like_input_columns() -> None:
    frame = part_b_frame()
    frame["normalized_score"] = [1.0, 2.0, 3.0, 4.0]

    with pytest.raises(ValueError, match="forbidden output columns"):
        calculate_trend_vol_flow_raw_scores(frame, windows=part_b_windows())


def test_part_b_blocks_missing_indicator_dependency_without_part_a_requirements() -> None:
    frame = part_b_frame().drop(columns=["cmf_3"])

    result = calculate_trend_vol_flow_raw_scores(frame, windows=part_b_windows())
    last = result.iloc[-1]

    assert pd.isna(last["cmf_confirmation_raw"])
    assert last["cmf_confirmation_missing_reason"] == "missing_dependency"
    assert "cmf_confirmation_raw" in result.columns
    assert "rsi_price_divergence_raw" not in result.columns


def test_default_part_b_config_loads_quant_registry_values() -> None:
    config = load_part_b_score_windows(
        windows_config_path=PROJECT_ROOT / "Quant_mvp" / "config" / "windows.toml",
        scores_config_path=PROJECT_ROOT / "Quant_mvp" / "config" / "scores.toml",
    )

    assert config.donchian == 20
    assert config.bollinger == 20
    assert config.cmf == 20
    assert config.efficiency_ratio == 20
    assert config.minimum_history_required == 60


def test_part_b_default_call_uses_quant_config_windows() -> None:
    result = calculate_trend_vol_flow_raw_scores(default_config_part_b_frame())

    last = result.iloc[-1]
    assert last["minimum_history_required"] == 60
    assert last["donchian_breakout_distance_raw"] == pytest.approx((159.0 / 158.0) - 1.0)
    assert last["bollinger_width_squeeze_raw"] == pytest.approx(-0.10)
    assert last["cmf_confirmation_raw"] == pytest.approx(0.20)
    assert last["efficiency_ratio_trend_raw"] == pytest.approx(0.80)
    assert last["score_coverage_status"] == "adequate"
