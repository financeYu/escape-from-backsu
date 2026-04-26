from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scores.normalization_cross_sectional import (
    CrossSectionalNormalizationConfig,
    normalize_cross_sectional_score,
    normalize_cross_sectional_scores,
    robust_zscore_cross_sectional,
)
from src.preprocess.schema_validator import GENERIC_EXCHANGE_SYMBOL_POLICY


RAW = "short_term_overreaction_raw"
PREFIX = "short_term_overreaction_cross_sectional"


def raw_frame(values_by_date: dict[str, list[float | None]]) -> pd.DataFrame:
    tickers = ["005930", "000660", "035420", "051910", "068270"]
    rows: list[dict[str, object]] = []
    for date_value, values in values_by_date.items():
        for ticker, value in zip(tickers, values):
            rows.append(
                {
                    "ticker": ticker,
                    "date": date_value,
                    RAW: value,
                    "score_warmup_state": "ready",
                    "score_coverage_status": "adequate",
                    "score_data_quality_flag": "valid",
                    "minimum_history_required": 2,
                }
            )
    return pd.DataFrame(rows)


def config(**overrides: object) -> CrossSectionalNormalizationConfig:
    defaults = {"min_count": 3}
    defaults.update(overrides)
    return CrossSectionalNormalizationConfig(**defaults)


def test_cross_sectional_normalization_uses_only_same_date_context() -> None:
    frame = raw_frame(
        {
            "2026-01-01": [1.0, 2.0, 3.0],
            "2026-01-02": [100.0, 200.0, 300.0],
        }
    )
    changed_future = frame.copy()
    changed_future.loc[changed_future["date"].eq("2026-01-02"), RAW] = [999.0, -999.0, 0.0]

    result = normalize_cross_sectional_score(frame, RAW, config=config())
    changed = normalize_cross_sectional_score(changed_future, RAW, config=config())

    past = result[result["date"].eq(pd.Timestamp("2026-01-01"))].sort_values("ticker")
    changed_past = changed[changed["date"].eq(pd.Timestamp("2026-01-01"))].sort_values("ticker")
    assert past[f"{PREFIX}_robust_z"].tolist() == pytest.approx(
        changed_past[f"{PREFIX}_robust_z"].tolist()
    )
    assert past[f"{PREFIX}_valid_count"].tolist() == [3, 3, 3]


def test_insufficient_cross_section_count_blocks_normalized_value() -> None:
    frame = raw_frame({"2026-01-01": [1.0, 2.0]})

    result = normalize_cross_sectional_score(frame, RAW, config=config(min_count=3))

    assert result[f"{PREFIX}_robust_z"].isna().all()
    assert set(result[f"{PREFIX}_status"]) == {"blocked"}
    assert result[f"{PREFIX}_quality_flag"].str.contains("insufficient_cross_section").all()


def test_zero_mad_iqr_fallback_and_all_tie_zero_scale_are_explicit() -> None:
    fallback = robust_zscore_cross_sectional(
        pd.Series([1.0, 1.0, 1.0, 2.0, 3.0]),
        config=CrossSectionalNormalizationConfig(min_count=5),
    )
    assert set(fallback["cross_sectional_scale_method"]) == {"iqr_fallback"}
    assert fallback["cross_sectional_robust_z"].notna().all()

    all_tie = robust_zscore_cross_sectional(
        pd.Series([5.0, 5.0, 5.0]),
        config=CrossSectionalNormalizationConfig(min_count=3),
    )
    assert all_tie["cross_sectional_robust_z"].isna().all()
    assert set(all_tie["cross_sectional_scale_method"]) == {"zero_dispersion"}
    assert all_tie["cross_sectional_quality_flag"].str.contains("zero_dispersion").all()


def test_nan_and_inf_raw_scores_are_not_used_as_valid_observations() -> None:
    frame = raw_frame({"2026-01-01": [1.0, math.nan, math.inf, 4.0]})

    result = normalize_cross_sectional_score(frame, RAW, config=config(min_count=2))

    assert result[f"{PREFIX}_valid_count"].tolist() == [2, 2, 2, 2]
    nan_row = result[result["ticker"].eq("000660")].iloc[0]
    inf_row = result[result["ticker"].eq("035420")].iloc[0]
    assert pd.isna(nan_row[f"{PREFIX}_robust_z"])
    assert "missing_required_input" in nan_row[f"{PREFIX}_quality_flag"]
    assert pd.isna(inf_row[f"{PREFIX}_robust_z"])
    assert "invalid_numeric" in inf_row[f"{PREFIX}_quality_flag"]


def test_warmup_and_blocked_coverage_rows_are_excluded_from_denominator() -> None:
    frame = raw_frame({"2026-01-01": [1.0, 2.0, 3.0, 4.0]})
    frame.loc[frame["ticker"].eq("035420"), "score_warmup_state"] = "warmup"
    frame.loc[frame["ticker"].eq("051910"), "score_coverage_status"] = "blocked"

    result = normalize_cross_sectional_score(frame, RAW, config=config(min_count=3))

    assert result[f"{PREFIX}_valid_count"].tolist() == [2, 2, 2, 2]
    assert result[f"{PREFIX}_robust_z"].isna().all()
    warmup_row = result[result["ticker"].eq("035420")].iloc[0]
    blocked_row = result[result["ticker"].eq("051910")].iloc[0]
    assert "warmup" in warmup_row[f"{PREFIX}_quality_flag"]
    assert "coverage_blocked" in blocked_row[f"{PREFIX}_quality_flag"]


def test_leading_zero_ticker_is_preserved_and_numeric_ticker_is_rejected() -> None:
    frame = raw_frame({"2026-01-01": [1.0, 2.0, 3.0]})

    result = normalize_cross_sectional_score(frame, RAW, config=config())

    assert result["ticker"].iloc[0] == "005930"
    assert str(result["ticker"].dtype) == "string"

    bad = frame.astype({"ticker": object}).copy()
    bad.loc[0, "ticker"] = 5930
    with pytest.raises(ValueError, match="six-character uppercase alphanumeric string format"):
        normalize_cross_sectional_score(bad, RAW, config=config())


def test_kospi200_alphanumeric_ticker_is_allowed_by_default_policy() -> None:
    frame = raw_frame({"2026-01-01": [1.0, 2.0, 3.0]})
    frame.loc[frame["ticker"].eq("005930"), "ticker"] = "0126Z0"

    result = normalize_cross_sectional_score(frame, RAW, config=config())

    assert "0126Z0" in result["ticker"].tolist()


def test_generic_symbol_policy_accepts_exchange_symbols() -> None:
    frame = raw_frame({"2026-01-01": [1.0, 2.0, 3.0, 4.0, 5.0]})
    frame["ticker"] = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL"]

    result = normalize_cross_sectional_score(
        frame,
        RAW,
        config=config(),
        symbol_policy=GENERIC_EXCHANGE_SYMBOL_POLICY,
    )

    assert result["ticker"].tolist() == ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL"]
    assert str(result["ticker"].dtype) == "string"


def test_duplicate_ticker_date_rows_are_rejected() -> None:
    frame = raw_frame({"2026-01-01": [1.0, 2.0, 3.0]})
    duplicate = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="Duplicate ticker/date"):
        normalize_cross_sectional_score(duplicate, RAW, config=config())


def test_tied_values_receive_identical_values_without_rank_output() -> None:
    frame = raw_frame({"2026-01-01": [1.0, 1.0, 3.0, 3.0]})

    result = normalize_cross_sectional_score(frame, RAW, config=config(min_count=4))

    first_pair = result[result[RAW].eq(1.0)][f"{PREFIX}_robust_z"].tolist()
    second_pair = result[result[RAW].eq(3.0)][f"{PREFIX}_robust_z"].tolist()
    assert first_pair[0] == pytest.approx(first_pair[1])
    assert second_pair[0] == pytest.approx(second_pair[1])
    forbidden = {
        "rank",
        "ranking",
        "latest_rank",
        "technical_composite_score",
        "final_composite_score",
        "forward_return",
        "future_return",
        "backtest_return",
    }
    assert not forbidden.intersection({column.lower() for column in result.columns})


def test_multi_score_output_excludes_rank_composite_and_backtest_columns() -> None:
    frame = raw_frame({"2026-01-01": [1.0, 2.0, 3.0]})
    frame["cmf_confirmation_raw"] = [0.1, 0.2, 0.3]

    result = normalize_cross_sectional_scores(
        frame,
        raw_score_columns=(RAW, "cmf_confirmation_raw"),
        config=config(),
    )

    assert "short_term_overreaction_cross_sectional_robust_z" in result.columns
    assert "cmf_confirmation_cross_sectional_robust_z" in result.columns
    assert not [column for column in result.columns if "rank" in column.lower()]
    assert not [column for column in result.columns if "composite" in column.lower()]
    assert not [column for column in result.columns if "backtest" in column.lower()]
