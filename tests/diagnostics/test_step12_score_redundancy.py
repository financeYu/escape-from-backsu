from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.diagnostics.score_redundancy import (  # noqa: E402
    RedundancyScoreInput,
    ScoreRedundancyConfig,
    build_score_redundancy_diagnostics,
    calculate_score_pair_correlations,
    load_score_redundancy_config,
    prepare_redundancy_input_frame,
    score_inputs_from_columns,
    summarize_score_redundancy,
)
from src.diagnostics.diagnostic_contracts import (  # noqa: E402
    validate_step12_coverage_summary,
    validate_step12_pair_diagnostics,
)


SCORE_A = "score_a_cross_sectional_robust_z"
SCORE_POS = "score_pos_cross_sectional_robust_z"
SCORE_NEG = "score_neg_cross_sectional_robust_z"
SCORE_LOW = "score_low_cross_sectional_robust_z"
SCORE_NAN = "score_nan_cross_sectional_robust_z"
SCORE_CONST = "score_const_cross_sectional_robust_z"


def config(min_count: int = 4) -> ScoreRedundancyConfig:
    return ScoreRedundancyConfig(
        min_cross_section_count=min_count,
        min_non_nan_observations=min_count,
        spearman_warn=0.8,
        spearman_block=0.9,
    )


def score_inputs(*columns: str) -> tuple[RedundancyScoreInput, ...]:
    return score_inputs_from_columns(columns)


def toy_frame(rows_by_date: dict[str, dict[str, list[float | None]]]) -> pd.DataFrame:
    tickers = ["005930", "000660", "035420", "051910", "068270"]
    rows: list[dict[str, object]] = []
    for date_value, columns in rows_by_date.items():
        row_count = len(next(iter(columns.values())))
        for index in range(row_count):
            row = {
                "ticker": tickers[index],
                "date": date_value,
            }
            for column, values in columns.items():
                row[column] = values[index]
            rows.append(row)
    return pd.DataFrame(rows)


def summary_row(frame: pd.DataFrame, score_a: str, score_b: str) -> pd.Series:
    return frame[
        frame["score_a"].eq(score_a)
        & frame["score_b"].eq(score_b)
    ].iloc[0]


def test_positive_negative_and_low_same_date_spearman_are_summarized() -> None:
    frame = toy_frame(
        {
            "2026-01-01": {
                SCORE_A: [1.0, 2.0, 3.0, 4.0, 5.0],
                SCORE_POS: [10.0, 20.0, 30.0, 40.0, 50.0],
                SCORE_NEG: [50.0, 40.0, 30.0, 20.0, 10.0],
                SCORE_LOW: [1.0, 3.0, 5.0, 2.0, 4.0],
            }
        }
    )

    summary = summarize_score_redundancy(
        frame,
        score_inputs=score_inputs(SCORE_A, SCORE_POS, SCORE_NEG, SCORE_LOW),
        config=config(),
    )

    pos = summary_row(summary, "score_a", "score_pos")
    assert pos["dates_evaluated"] == 1
    assert pos["median_spearman"] == pytest.approx(1.0)
    assert pos["redundancy_status"] == "block_candidate"

    neg = summary_row(summary, "score_a", "score_neg")
    assert neg["mean_spearman"] == pytest.approx(-1.0)
    assert neg["max_abs_spearman"] == pytest.approx(1.0)
    assert neg["redundancy_status"] == "block_candidate"

    low = summary_row(summary, "score_a", "score_low")
    assert abs(low["median_spearman"]) < 0.8
    assert low["redundancy_status"] == "ok"


def test_nan_pairwise_exclusion_and_insufficient_cross_section_are_explicit() -> None:
    frame = toy_frame(
        {
            "2026-01-01": {
                SCORE_A: [1.0, 2.0, 3.0, 4.0, 5.0],
                SCORE_NAN: [1.0, None, 3.0, 4.0, 5.0],
            },
            "2026-01-02": {
                SCORE_A: [1.0, 2.0, math.nan, 4.0, math.nan],
                SCORE_NAN: [5.0, 4.0, 3.0, math.nan, math.nan],
            },
        }
    )

    details = calculate_score_pair_correlations(
        frame,
        score_inputs=score_inputs(SCORE_A, SCORE_NAN),
        config=config(min_count=4),
    )
    summary = summarize_score_redundancy(
        frame,
        score_inputs=score_inputs(SCORE_A, SCORE_NAN),
        config=config(min_count=4),
    )

    date1 = details[details["date"].eq(pd.Timestamp("2026-01-01"))].iloc[0]
    date2 = details[details["date"].eq(pd.Timestamp("2026-01-02"))].iloc[0]
    assert date1["pair_observations"] == 4
    assert date1["diagnostic_status"] == "ok"
    assert date2["pair_observations"] == 2
    assert date2["diagnostic_status"] == "insufficient_data"

    row = summary.iloc[0]
    assert row["dates_evaluated"] == 1
    assert row["dates_insufficient"] == 1
    assert row["min_pair_observations"] == 2


def test_constant_column_marks_undefined_correlation_without_zero_fill() -> None:
    frame = toy_frame(
        {
            "2026-01-01": {
                SCORE_A: [1.0, 2.0, 3.0, 4.0],
                SCORE_CONST: [7.0, 7.0, 7.0, 7.0],
            }
        }
    )

    details = calculate_score_pair_correlations(
        frame,
        score_inputs=score_inputs(SCORE_A, SCORE_CONST),
        config=config(min_count=4),
    )
    summary = summarize_score_redundancy(
        frame,
        score_inputs=score_inputs(SCORE_A, SCORE_CONST),
        config=config(min_count=4),
    )

    assert details.iloc[0]["diagnostic_status"] == "undefined_correlation"
    assert pd.isna(details.iloc[0]["spearman"])
    assert summary.iloc[0]["redundancy_status"] == "undefined_correlation"
    assert pd.isna(summary.iloc[0]["median_spearman"])


def test_leading_zero_ticker_is_preserved_and_numeric_ticker_is_rejected() -> None:
    frame = toy_frame(
        {
            "2026-01-01": {
                SCORE_A: [1.0, 2.0, 3.0, 4.0],
                SCORE_POS: [1.0, 2.0, 3.0, 4.0],
            }
        }
    )

    prepared = prepare_redundancy_input_frame(
        frame,
        score_inputs=score_inputs(SCORE_A, SCORE_POS),
    )

    assert prepared["ticker"].iloc[0] == "000660"
    assert str(prepared["ticker"].dtype) == "string"

    bad = frame.astype({"ticker": object}).copy()
    bad.loc[0, "ticker"] = 5930
    with pytest.raises(ValueError, match="six-character string"):
        prepare_redundancy_input_frame(
            bad,
            score_inputs=score_inputs(SCORE_A, SCORE_POS),
        )


def test_missing_normalized_column_does_not_fallback_to_raw_score() -> None:
    frame = pd.DataFrame(
        {
            "ticker": ["005930", "000660", "035420", "051910"],
            "date": ["2026-01-01"] * 4,
            "score_a_raw": [1.0, 2.0, 3.0, 4.0],
            SCORE_POS: [1.0, 2.0, 3.0, 4.0],
        }
    )
    missing_input = RedundancyScoreInput(
        score_name="score_a",
        normalized_column=SCORE_A,
    )

    summary = summarize_score_redundancy(
        frame,
        score_inputs=(missing_input, *score_inputs(SCORE_POS)),
        config=config(min_count=4),
    )

    assert summary.iloc[0]["redundancy_status"] == "insufficient_input"
    assert "upstream_missing_normalized_score_column" in summary.iloc[0]["redundancy_reason"]

    with pytest.raises(ValueError, match="not raw score columns"):
        score_inputs_from_columns(("score_a_raw", SCORE_POS))


def test_same_date_cross_section_only_future_date_change_does_not_alter_past_detail() -> None:
    frame = toy_frame(
        {
            "2026-01-01": {
                SCORE_A: [1.0, 2.0, 3.0, 4.0],
                SCORE_POS: [4.0, 3.0, 2.0, 1.0],
            },
            "2026-01-02": {
                SCORE_A: [10.0, 20.0, 30.0, 40.0],
                SCORE_POS: [40.0, 30.0, 20.0, 10.0],
            },
        }
    )
    changed_future = frame.copy()
    changed_future.loc[changed_future["date"].eq("2026-01-02"), SCORE_POS] = [
        999.0,
        -999.0,
        0.0,
        100.0,
    ]

    original_detail = calculate_score_pair_correlations(
        frame,
        score_inputs=score_inputs(SCORE_A, SCORE_POS),
        config=config(min_count=4),
    )
    changed_detail = calculate_score_pair_correlations(
        changed_future,
        score_inputs=score_inputs(SCORE_A, SCORE_POS),
        config=config(min_count=4),
    )

    original_past = original_detail[original_detail["date"].eq(pd.Timestamp("2026-01-01"))]
    changed_past = changed_detail[changed_detail["date"].eq(pd.Timestamp("2026-01-01"))]
    assert original_past.iloc[0]["spearman"] == pytest.approx(changed_past.iloc[0]["spearman"])


def test_forward_return_and_valuation_columns_are_rejected() -> None:
    frame = toy_frame(
        {
            "2026-01-01": {
                SCORE_A: [1.0, 2.0, 3.0, 4.0],
                SCORE_POS: [1.0, 2.0, 3.0, 4.0],
            }
        }
    )
    for column in ("forward_return", "future_return", "backtest_return", "PER"):
        blocked = frame.copy()
        blocked[column] = 1.0
        with pytest.raises(ValueError):
            summarize_score_redundancy(
                blocked,
                score_inputs=score_inputs(SCORE_A, SCORE_POS),
                config=config(min_count=4),
            )


def test_missing_threshold_keys_report_config_missing_without_defaults() -> None:
    missing = PROJECT_ROOT / "tests" / "diagnostics" / "_tmp_missing_thresholds.toml"
    frame = toy_frame(
        {
            "2026-01-01": {
                SCORE_A: [1.0, 2.0, 3.0, 4.0],
                SCORE_POS: [1.0, 2.0, 3.0, 4.0],
            }
        }
    )

    try:
        missing.write_text(
            "[quality]\nmin_cross_section_count = 4\n",
            encoding="utf-8",
        )
        diagnostics = build_score_redundancy_diagnostics(
            frame,
            score_inputs=score_inputs(SCORE_A, SCORE_POS),
            thresholds_config_path=missing,
        )

        summary = diagnostics["pair_summary"]
        assert summary.iloc[0]["redundancy_status"] == "config_missing"
        assert "redundancy.spearman_warn" in summary.iloc[0]["redundancy_reason"]
        with pytest.raises(ValueError, match="config_missing"):
            load_score_redundancy_config(thresholds_config_path=missing)
    finally:
        if missing.exists():
            missing.unlink()


def test_diagnostic_outputs_do_not_include_forbidden_columns_or_terms() -> None:
    frame = toy_frame(
        {
            "2026-01-01": {
                SCORE_A: [1.0, 2.0, 3.0, 4.0],
                SCORE_LOW: [1.0, 3.0, 2.0, 4.0],
            }
        }
    )
    diagnostics = build_score_redundancy_diagnostics(
        frame,
        score_inputs=score_inputs(SCORE_A, SCORE_LOW),
        config=config(min_count=4),
    )

    validate_step12_pair_diagnostics(diagnostics["pair_diagnostics"])
    validate_step12_coverage_summary(diagnostics["coverage_summary"])
    assert "score_a" in diagnostics["pair_summary"].columns
    assert "score_left" in diagnostics["pair_diagnostics"].columns
    assert "coverage_summary" in diagnostics

    forbidden = {
        "rank",
        "ranking",
        "latest_rank",
        "technical_composite_score",
        "final_composite_score",
        "forward_return",
        "future_return",
        "backtest_return",
        "alpha",
        "signal",
        "buy",
        "sell",
        "valuation",
    }
    for table in diagnostics.values():
        lowered_columns = {column.lower() for column in table.columns}
        assert not lowered_columns.intersection(forbidden)
        text_values = " ".join(
            str(value).lower()
            for value in table.select_dtypes(include=["object", "string"]).stack().tolist()
        )
        assert not [term for term in forbidden if term in text_values]
