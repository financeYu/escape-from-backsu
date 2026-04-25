from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scores.normalization_cross_sectional import (
    CrossSectionalNormalizationConfig,
    normalize_cross_sectional_scores,
)
from src.scores.normalization_diagnostics import (
    build_normalization_diagnostics,
    summarize_normalization_coverage,
)


RAW = "short_term_overreaction_raw"
CMF = "cmf_confirmation_raw"


def diagnostics_frame() -> pd.DataFrame:
    tickers = ["005930", "000660", "035420", "051910"]
    rows: list[dict[str, object]] = []
    for ticker, short_value, cmf_value in zip(
        tickers,
        [1.0, 2.0, math.nan, math.inf],
        [1.0, 2.0, 3.0, 4.0],
    ):
        rows.append(
            {
                "ticker": ticker,
                "date": "2026-01-01",
                RAW: short_value,
                CMF: cmf_value,
                "score_warmup_state": "ready",
                "score_coverage_status": "adequate",
                "score_data_quality_flag": "valid",
                "minimum_history_required": 2,
            }
        )
    rows[2]["score_warmup_state"] = "insufficient_history"
    rows[2]["score_data_quality_flag"] = "insufficient_history"
    rows[3]["score_coverage_status"] = "blocked"
    rows[3]["score_data_quality_flag"] = "invalid_numeric"

    for ticker, short_value, cmf_value in zip(
        tickers,
        [10.0, 10.0, 10.0, 10.0],
        [0.0, 0.0, 0.0, 100.0],
    ):
        rows.append(
            {
                "ticker": ticker,
                "date": "2026-01-02",
                RAW: short_value,
                CMF: cmf_value,
                "score_warmup_state": "ready",
                "score_coverage_status": "adequate",
                "score_data_quality_flag": "valid",
                "minimum_history_required": 2,
            }
        )
    return pd.DataFrame(rows)


def normalized_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return normalize_cross_sectional_scores(
        frame,
        raw_score_columns=(RAW, CMF),
        config=CrossSectionalNormalizationConfig(
            min_count=2,
            winsorize_lower_pct=0.0,
            winsorize_upper_pct=0.75,
            zscore_clip=1.0,
        ),
    )


def row_for(frame: pd.DataFrame, score_name: str) -> pd.Series:
    return frame[frame["score_name"].eq(score_name)].iloc[0]


def test_score_coverage_counts_match_toy_data() -> None:
    frame = diagnostics_frame()
    normalized = normalized_frame(frame)

    coverage = summarize_normalization_coverage(
        frame,
        raw_score_columns=(RAW, CMF),
        normalized_frame=normalized,
    )

    short = row_for(coverage, "short_term_overreaction")
    assert short["row_count"] == 8
    assert short["valid_observation_count"] == 6
    assert short["missing_count"] == 2
    assert short["insufficient_history_count"] == 1
    assert short["blocked_coverage_count"] == 1
    assert short["zero_dispersion_count"] == 4

    cmf = row_for(coverage, "cmf_confirmation")
    assert cmf["winsorized_count"] >= 1
    assert cmf["clipped_count"] >= 1
    assert cmf["zero_scale_fallback_count"] >= 1


def test_diagnostics_include_date_ticker_event_and_distribution_tables() -> None:
    frame = diagnostics_frame()
    normalized = normalized_frame(frame)

    diagnostics = build_normalization_diagnostics(
        frame,
        raw_score_columns=(RAW, CMF),
        normalized_frame=normalized,
    )

    assert set(diagnostics) == {
        "score_coverage",
        "date_cross_sectional_valid_count",
        "ticker_available_observation_count",
        "normalization_event_counts",
        "warmup_distribution",
        "data_quality_flag_distribution",
        "coverage_status_distribution",
    }

    date_counts = diagnostics["date_cross_sectional_valid_count"]
    short_date1 = date_counts[
        date_counts["score_name"].eq("short_term_overreaction")
        & date_counts["date"].eq(pd.Timestamp("2026-01-01"))
    ].iloc[0]
    short_date2 = date_counts[
        date_counts["score_name"].eq("short_term_overreaction")
        & date_counts["date"].eq(pd.Timestamp("2026-01-02"))
    ].iloc[0]
    assert short_date1["cross_sectional_valid_count"] == 2
    assert short_date1["missing_count"] == 2
    assert short_date2["cross_sectional_valid_count"] == 4

    ticker_counts = diagnostics["ticker_available_observation_count"]
    samsung = ticker_counts[
        ticker_counts["score_name"].eq("short_term_overreaction")
        & ticker_counts["ticker"].eq("005930")
    ].iloc[0]
    assert samsung["available_observation_count"] == 2

    warmup = diagnostics["warmup_distribution"]
    assert warmup.loc[warmup["warmup_status"].eq("insufficient_history"), "row_count"].iloc[0] == 1

    quality = diagnostics["data_quality_flag_distribution"]
    assert set(quality["data_quality_flag"]).issuperset(
        {"valid", "insufficient_history", "invalid_numeric"}
    )

    coverage_status = diagnostics["coverage_status_distribution"]
    assert coverage_status.loc[
        coverage_status["coverage_status"].eq("blocked"), "row_count"
    ].iloc[0] == 1


def test_diagnostics_do_not_emit_rank_composite_or_backtest_columns() -> None:
    diagnostics = build_normalization_diagnostics(
        diagnostics_frame(),
        raw_score_columns=(RAW, CMF),
        normalized_frame=normalized_frame(diagnostics_frame()),
    )

    forbidden_fragments = ("rank", "composite", "backtest", "forward_return", "future_return")
    for table in diagnostics.values():
        lowered = [column.lower() for column in table.columns]
        assert not [
            column
            for column in lowered
            if any(fragment in column for fragment in forbidden_fragments)
        ]


def test_step10_policy_document_names_forbidden_output_boundary() -> None:
    policy = (PROJECT_ROOT / "docs" / "step10_normalization_policy.md").read_text(
        encoding="utf-8"
    )
    lowered = policy.lower()

    assert "forbidden outputs" in lowered
    assert "no ranking" in lowered
    assert "no composite" in lowered
    assert "no backtest" in lowered
    assert "part a" in lowered
    assert "time-series normalization" in lowered
