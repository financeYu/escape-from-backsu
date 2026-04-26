from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scores.normalization_timeseries import (  # noqa: E402
    TimeSeriesNormalizationConfig,
    apply_clipping,
    apply_winsorization,
    normalize_timeseries_score,
    normalize_timeseries_scores,
    robust_zscore_expanding,
)
from src.preprocess.schema_validator import GENERIC_EXCHANGE_SYMBOL_POLICY  # noqa: E402


RAW_COLUMN = "example_raw"
VALUE_COLUMN = "example_ts_robust_zscore"
STATUS_COLUMN = "example_ts_status"
QUALITY_COLUMN = "example_ts_data_quality_flag"
SCALE_METHOD_COLUMN = "example_ts_scale_method"
WINSORIZED_VALUE_COLUMN = "example_ts_winsorized_value"
WAS_WINSORIZED_COLUMN = "example_ts_was_winsorized"
WAS_CLIPPED_COLUMN = "example_ts_was_clipped"


def config(
    *,
    min_periods: int = 3,
    window: int | None = None,
    clip_lower: float | None = None,
    clip_upper: float | None = None,
) -> TimeSeriesNormalizationConfig:
    return TimeSeriesNormalizationConfig(
        window=window,
        min_periods=min_periods,
        winsorize_lower_pct=None,
        winsorize_upper_pct=None,
        clip_lower=clip_lower,
        clip_upper=clip_upper,
    )


def raw_frame(
    values: list[object],
    *,
    ticker: str = "005930",
    warmup_state: str = "ready",
    minimum_history_required: int = 1,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": [ticker] * len(values),
            "date": [f"2026-01-{idx:02d}" for idx in range(1, len(values) + 1)],
            RAW_COLUMN: values,
            "score_warmup_state": [warmup_state] * len(values),
            "minimum_history_required": [minimum_history_required] * len(values),
        }
    )


def test_ticker_local_calculation_does_not_mix_tickers() -> None:
    frame = pd.concat(
        [
            raw_frame([1.0, 2.0, 3.0], ticker="005930"),
            raw_frame([100.0, 101.0, 102.0], ticker="000660"),
        ],
        ignore_index=True,
    )

    result = normalize_timeseries_score(frame, RAW_COLUMN, config=config())

    samsung = result[result["ticker"].eq("005930")].iloc[-1]
    hynix = result[result["ticker"].eq("000660")].iloc[-1]
    assert samsung[VALUE_COLUMN] == pytest.approx((3.0 - 2.0) / 1.4826)
    assert hynix[VALUE_COLUMN] == pytest.approx((102.0 - 101.0) / 1.4826)


def test_input_is_sorted_by_ticker_and_date_before_time_series_calculation() -> None:
    frame = raw_frame([1.0, 2.0, 3.0]).iloc[[2, 0, 1]].reset_index(drop=True)

    result = normalize_timeseries_score(frame, RAW_COLUMN, config=config())

    assert result["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
    ]
    assert result.iloc[-1][VALUE_COLUMN] == pytest.approx((3.0 - 2.0) / 1.4826)


def test_no_lookahead_when_future_raw_score_changes() -> None:
    base = raw_frame([1.0, 2.0, 3.0, 4.0])
    changed_future = base.copy()
    changed_future.loc[3, RAW_COLUMN] = 1000.0

    result = normalize_timeseries_score(base, RAW_COLUMN, config=config())
    changed = normalize_timeseries_score(changed_future, RAW_COLUMN, config=config())

    past = result[result["date"].eq(pd.Timestamp("2026-01-03"))].iloc[0]
    changed_past = changed[changed["date"].eq(pd.Timestamp("2026-01-03"))].iloc[0]
    assert past[VALUE_COLUMN] == pytest.approx(changed_past[VALUE_COLUMN])


def test_min_periods_and_upstream_insufficient_history_are_blocked() -> None:
    warmup = normalize_timeseries_score(raw_frame([1.0, 2.0]), RAW_COLUMN, config=config(min_periods=3))

    assert warmup[VALUE_COLUMN].isna().all()
    assert set(warmup[STATUS_COLUMN]) == {"warmup"}
    assert set(warmup[QUALITY_COLUMN]) == {"warmup"}

    insufficient = raw_frame([1.0], warmup_state="insufficient_history")
    result = normalize_timeseries_score(insufficient, RAW_COLUMN, config=config(min_periods=1))

    assert pd.isna(result.loc[0, VALUE_COLUMN])
    assert result.loc[0, STATUS_COLUMN] == "insufficient_history"
    assert result.loc[0, QUALITY_COLUMN] == "insufficient_history"


def test_zero_mad_can_use_iqr_fallback_when_iqr_is_positive() -> None:
    result = robust_zscore_expanding(
        [1.0, 1.0, 1.0, 10.0],
        min_periods=4,
        winsorize_lower_pct=None,
        winsorize_upper_pct=None,
    )

    assert result.loc[3, "status"] == "ok"
    assert result.loc[3, "scale_method"] == "iqr"
    assert result.loc[3, "robust_zscore"] > 0


def test_all_tie_zero_scale_is_missing_and_flagged() -> None:
    result = robust_zscore_expanding(
        [5.0, 5.0, 5.0],
        min_periods=3,
        winsorize_lower_pct=None,
        winsorize_upper_pct=None,
    )

    assert pd.isna(result.loc[2, "robust_zscore"])
    assert result.loc[2, "status"] == "zero_scale"
    assert result.loc[2, "data_quality_flag"] == "zero_dispersion"


def test_nan_raw_score_is_missing_not_filled() -> None:
    result = normalize_timeseries_score(raw_frame([1.0, math.nan, 3.0]), RAW_COLUMN, config=config(min_periods=1))

    assert pd.isna(result.loc[1, VALUE_COLUMN])
    assert result.loc[1, STATUS_COLUMN] == "missing_raw_score"
    assert result.loc[1, QUALITY_COLUMN] == "missing_required_input"


def test_inf_raw_score_is_invalid_not_infinite_output() -> None:
    result = normalize_timeseries_score(raw_frame([1.0, math.inf, 3.0]), RAW_COLUMN, config=config(min_periods=1))

    assert pd.isna(result.loc[1, VALUE_COLUMN])
    assert result.loc[1, STATUS_COLUMN] == "invalid_raw_score"
    assert result.loc[1, QUALITY_COLUMN] == "invalid_numeric"
    finite_or_missing = [pd.isna(value) or math.isfinite(float(value)) for value in result[VALUE_COLUMN]]
    assert all(finite_or_missing)


def test_clipping_boundary_is_applied_and_diagnosed() -> None:
    clipped = apply_clipping([-5.0, 0.0, 5.0], lower=-2.0, upper=2.0)

    assert clipped["value"].tolist() == pytest.approx([-2.0, 0.0, 2.0])
    assert clipped["was_clipped"].tolist() == [True, False, True]

    result = normalize_timeseries_score(
        raw_frame([1.0, 2.0, 100.0]),
        RAW_COLUMN,
        config=config(min_periods=3, clip_upper=1.0),
    )
    assert result.loc[2, VALUE_COLUMN] <= 1.0
    assert bool(result.loc[2, WAS_CLIPPED_COLUMN])


def test_winsorization_boundary_is_applied_and_diagnosed() -> None:
    winsorized = apply_winsorization([0.0, 10.0, 100.0], lower_pct=0.0, upper_pct=0.5)

    assert winsorized["value"].tolist() == pytest.approx([0.0, 10.0, 10.0])
    assert winsorized["was_winsorized"].tolist() == [False, False, True]

    result = normalize_timeseries_score(
        raw_frame([0.0, 10.0, 100.0]),
        RAW_COLUMN,
        config=TimeSeriesNormalizationConfig(
            window=None,
            min_periods=3,
            winsorize_lower_pct=0.0,
            winsorize_upper_pct=0.5,
        ),
    )
    assert result.loc[2, WINSORIZED_VALUE_COLUMN] == pytest.approx(10.0)
    assert bool(result.loc[2, WAS_WINSORIZED_COLUMN])


def test_leading_zero_ticker_is_preserved_as_string() -> None:
    result = normalize_timeseries_score(raw_frame([1.0, 2.0, 3.0], ticker="005930"), RAW_COLUMN, config=config())

    assert result.loc[0, "ticker"] == "005930"
    assert str(result["ticker"].dtype) == "string"


def test_generic_symbol_policy_accepts_exchange_symbol() -> None:
    result = normalize_timeseries_score(
        raw_frame([1.0, 2.0, 3.0], ticker="AAPL"),
        RAW_COLUMN,
        config=config(),
        symbol_policy=GENERIC_EXCHANGE_SYMBOL_POLICY,
    )

    assert result.loc[0, "ticker"] == "AAPL"
    assert str(result["ticker"].dtype) == "string"


def test_duplicate_ticker_date_rows_are_rejected() -> None:
    frame = raw_frame([1.0, 2.0])
    frame.loc[1, "date"] = frame.loc[0, "date"]

    with pytest.raises(ValueError, match="Duplicate ticker/date"):
        normalize_timeseries_score(frame, RAW_COLUMN, config=config(min_periods=1))


def test_output_contains_no_rank_composite_or_backtest_columns() -> None:
    frame = raw_frame([1.0, 2.0, 3.0])
    frame["second_raw"] = [3.0, 2.0, 1.0]

    result = normalize_timeseries_scores(
        frame,
        raw_score_columns=(RAW_COLUMN, "second_raw"),
        config=config(),
    )

    forbidden = {
        "rank",
        "ranking",
        "latest_rank",
        "latest_ranking",
        "technical_composite_score",
        "final_composite_score",
        "forward_return",
        "future_return",
        "backtest_return",
        "valuation_score",
    }
    assert not forbidden.intersection(result.columns)
    assert not [column for column in result.columns if column.endswith("_rank")]
    assert VALUE_COLUMN in result.columns
    assert "second_ts_robust_zscore" in result.columns
