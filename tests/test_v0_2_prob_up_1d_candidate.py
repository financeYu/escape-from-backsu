from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scores.prob_up_1d_candidate import (  # noqa: E402
    CANDIDATE_SIDECAR_RANK_COLUMN,
    DECISION_TIME_COLUMN,
    EXECUTION_TIME_COLUMN,
    FEATURE_STATUS_COLUMN,
    LABEL_AVAILABILITY_TIME_COLUMN,
    LABEL_AVAILABLE_COLUMN,
    LABEL_COLUMN,
    LABEL_TIME_COLUMN,
    PROBABILITY_COLUMN,
    PROBABILITY_SAMPLE_ROLE_COLUMN,
    PROBABILITY_STATUS_COLUMN,
    ProbUp1DConfig,
    build_prob_up_1d_candidate_sidecar_ranking,
    build_prob_up_1d_dataset,
    run_prob_up_1d_candidate_pipeline,
)


FEATURE_COLUMNS = ("old_score_a_raw", "old_score_b_raw")


def probability_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    prices = {
        "005930": [10.0, 11.0, 10.0, 12.0, 13.0, 12.0],
        "000660": [20.0, 19.0, 21.0, 20.0, 22.0, 23.0],
    }
    score_a = {
        "005930": [0.80, 0.20, 0.70, 0.90, 0.10, 0.30],
        "000660": [0.10, 0.70, 0.25, 0.75, 0.85, 0.60],
    }
    score_b = {
        "005930": [0.60, 0.30, 0.65, 0.80, 0.20, 0.40],
        "000660": [0.20, 0.60, 0.35, 0.70, 0.75, 0.65],
    }
    for ticker in ("005930", "000660"):
        for offset, price in enumerate(prices[ticker], start=1):
            rows.append(
                {
                    "ticker": ticker,
                    "date": f"2026-01-{offset:02d}",
                    "adjusted_close": price,
                    "old_score_a_raw": score_a[ticker][offset - 1],
                    "old_score_b_raw": score_b[ticker][offset - 1],
                }
            )
    return pd.DataFrame(rows)


def small_config() -> ProbUp1DConfig:
    return ProbUp1DConfig(
        feature_columns=FEATURE_COLUMNS,
        min_train_rows=6,
        min_eval_rows=2,
        eval_fraction=0.30,
        max_iter=300,
        learning_rate=0.15,
    )


def test_feature_table_and_next_day_labels_are_separated() -> None:
    dataset = build_prob_up_1d_dataset(probability_frame(), config=small_config())

    assert LABEL_COLUMN not in dataset.feature_table.columns
    assert LABEL_AVAILABLE_COLUMN not in dataset.feature_table.columns
    assert "adjusted_close" not in dataset.feature_table.columns
    assert set(dataset.feature_columns) == set(FEATURE_COLUMNS)

    labels = dataset.label_table.sort_values(["ticker", "date"]).reset_index(drop=True)
    samsung_first = labels[
        labels["ticker"].eq("005930") & labels["date"].eq(pd.Timestamp("2026-01-01"))
    ].iloc[0]
    samsung_second = labels[
        labels["ticker"].eq("005930") & labels["date"].eq(pd.Timestamp("2026-01-02"))
    ].iloc[0]
    samsung_last = labels[
        labels["ticker"].eq("005930") & labels["date"].eq(pd.Timestamp("2026-01-06"))
    ].iloc[0]

    assert samsung_first[LABEL_COLUMN] == 1
    assert samsung_second[LABEL_COLUMN] == 0
    assert bool(samsung_last[LABEL_AVAILABLE_COLUMN]) is False
    assert pd.isna(samsung_last[LABEL_COLUMN])
    assert samsung_first[LABEL_TIME_COLUMN] == pd.Timestamp("2026-01-02")
    assert samsung_first[LABEL_AVAILABILITY_TIME_COLUMN] == pd.Timestamp("2026-01-02")
    assert pd.isna(samsung_last[LABEL_TIME_COLUMN])
    assert pd.isna(samsung_last[LABEL_AVAILABILITY_TIME_COLUMN])


def test_feature_table_does_not_change_when_only_future_price_changes() -> None:
    base = probability_frame()
    changed_future = base.copy()
    changed_future.loc[
        changed_future["ticker"].eq("005930") & changed_future["date"].eq("2026-01-06"),
        "adjusted_close",
    ] = 999.0

    dataset = build_prob_up_1d_dataset(base, config=small_config())
    changed_dataset = build_prob_up_1d_dataset(changed_future, config=small_config())

    base_features = dataset.feature_table[
        dataset.feature_table["ticker"].eq("005930")
        & dataset.feature_table["date"].eq(pd.Timestamp("2026-01-05"))
    ].loc[:, list(FEATURE_COLUMNS)]
    changed_features = changed_dataset.feature_table[
        changed_dataset.feature_table["ticker"].eq("005930")
        & changed_dataset.feature_table["date"].eq(pd.Timestamp("2026-01-05"))
    ].loc[:, list(FEATURE_COLUMNS)]

    pd.testing.assert_frame_equal(base_features.reset_index(drop=True), changed_features.reset_index(drop=True))
    base_label = dataset.label_table[
        dataset.label_table["ticker"].eq("005930")
        & dataset.label_table["date"].eq(pd.Timestamp("2026-01-05"))
    ][LABEL_COLUMN].iloc[0]
    changed_label = changed_dataset.label_table[
        changed_dataset.label_table["ticker"].eq("005930")
        & changed_dataset.label_table["date"].eq(pd.Timestamp("2026-01-05"))
    ][LABEL_COLUMN].iloc[0]
    assert base_label == 0
    assert changed_label == 1


def test_pipeline_outputs_candidate_probabilities_without_ranking_or_composites() -> None:
    result = run_prob_up_1d_candidate_pipeline(probability_frame(), config=small_config())
    output = result.candidate_output

    assert PROBABILITY_COLUMN in output.columns
    assert {DECISION_TIME_COLUMN, EXECUTION_TIME_COLUMN, LABEL_TIME_COLUMN, LABEL_AVAILABILITY_TIME_COLUMN}.issubset(
        output.columns
    )
    assert PROBABILITY_STATUS_COLUMN in output.columns
    assert PROBABILITY_SAMPLE_ROLE_COLUMN in output.columns
    ready = output[PROBABILITY_STATUS_COLUMN].eq("candidate_probability")
    assert ready.any()
    assert output.loc[ready, PROBABILITY_COLUMN].between(0.0, 1.0).all()
    assert result.training_result.model.train_count == 7
    assert result.training_result.model.evaluation_count == 3
    assert result.training_result.model.evaluation_metrics["evaluation_count"] == pytest.approx(3.0)
    assert "evaluation_out_of_sample" in set(output[PROBABILITY_SAMPLE_ROLE_COLUMN])
    assert "candidate_unlabeled" in set(output[PROBABILITY_SAMPLE_ROLE_COLUMN])
    latest = output[
        output["ticker"].eq("005930") & output["date"].eq(pd.Timestamp("2026-01-06"))
    ].iloc[0]
    assert latest[DECISION_TIME_COLUMN] == pd.Timestamp("2026-01-06")
    assert latest[EXECUTION_TIME_COLUMN] == pd.Timestamp("2026-01-06")
    assert pd.isna(latest[LABEL_TIME_COLUMN])
    assert pd.isna(latest[LABEL_AVAILABILITY_TIME_COLUMN])

    forbidden = {
        "rank",
        "ranking",
        "latest_rank",
        "technical_composite_score",
        "final_composite_score",
        "backtest_return",
        "buy",
        "sell",
        "recommendation",
        LABEL_COLUMN,
    }
    assert not forbidden.intersection(output.columns)


def test_as_of_date_latest_rows_are_candidate_inference_without_labels() -> None:
    result = run_prob_up_1d_candidate_pipeline(
        probability_frame(),
        config=small_config(),
        as_of_date="2026-01-06",
    )
    latest_rows = result.candidate_output[result.candidate_output["date"].eq(pd.Timestamp("2026-01-06"))]

    assert set(latest_rows[PROBABILITY_SAMPLE_ROLE_COLUMN]) == {"candidate_unlabeled"}
    assert latest_rows[PROBABILITY_COLUMN].notna().all()
    assert latest_rows[LABEL_TIME_COLUMN].isna().all()
    assert latest_rows[LABEL_AVAILABILITY_TIME_COLUMN].isna().all()
    assert result.candidate_sidecar_ranking["date"].eq(pd.Timestamp("2026-01-06")).all()
    assert CANDIDATE_SIDECAR_RANK_COLUMN in result.candidate_sidecar_ranking.columns


def test_candidate_sidecar_ranking_orders_probability_then_ticker_for_ties() -> None:
    candidate_output = pd.DataFrame(
        [
            {"ticker": "005930", "date": "2026-01-06", PROBABILITY_COLUMN: 0.60},
            {"ticker": "000660", "date": "2026-01-06", PROBABILITY_COLUMN: 0.60},
            {"ticker": "035420", "date": "2026-01-06", PROBABILITY_COLUMN: 0.80},
            {"ticker": "051910", "date": "2026-01-05", PROBABILITY_COLUMN: 0.99},
        ]
    )

    sidecar = build_prob_up_1d_candidate_sidecar_ranking(candidate_output, as_of_date="2026-01-06")

    assert sidecar["ticker"].tolist() == ["035420", "000660", "005930"]
    assert sidecar[CANDIDATE_SIDECAR_RANK_COLUMN].tolist() == [1, 2, 3]
    assert "technical_composite_score" not in sidecar.columns
    assert "final_composite_score" not in sidecar.columns


def test_candidate_sidecar_ranking_rejects_production_rank_leakage() -> None:
    candidate_output = pd.DataFrame(
        [
            {
                "ticker": "005930",
                "date": "2026-01-06",
                PROBABILITY_COLUMN: 0.60,
                "production_rank": 1,
            }
        ]
    )

    with pytest.raises(ValueError, match="production_rank"):
        build_prob_up_1d_candidate_sidecar_ranking(candidate_output, as_of_date="2026-01-06")


def test_forbidden_backtest_and_valuation_columns_are_rejected() -> None:
    backtest_frame = probability_frame()
    backtest_frame["sharpe_ratio"] = 1.2
    with pytest.raises(ValueError, match="backtest/evaluation leakage"):
        build_prob_up_1d_dataset(
            backtest_frame,
            config=small_config(),
            feature_columns=("old_score_a_raw", "sharpe_ratio"),
        )

    label_frame = probability_frame()
    label_frame["target_label"] = 1
    with pytest.raises(ValueError, match="leakage columns"):
        build_prob_up_1d_dataset(
            label_frame,
            config=small_config(),
            feature_columns=("old_score_a_raw", "target_label"),
        )

    future_feature_frame = probability_frame()
    future_feature_frame["old_future_return_raw"] = 0.1
    with pytest.raises(ValueError, match="leakage/backtest feature columns"):
        build_prob_up_1d_dataset(
            future_feature_frame,
            config=small_config(),
            feature_columns=("old_score_a_raw", "old_future_return_raw"),
        )

    valuation_frame = probability_frame()
    valuation_frame["PER"] = 10.0
    with pytest.raises(ValueError, match="valuation/fundamental columns"):
        build_prob_up_1d_dataset(valuation_frame, config=small_config())


def test_missing_features_do_not_emit_fabricated_probabilities() -> None:
    frame = probability_frame()
    missing_row = frame["ticker"].eq("000660") & frame["date"].eq("2026-01-01")
    frame.loc[missing_row, "old_score_a_raw"] = pd.NA

    result = run_prob_up_1d_candidate_pipeline(frame, config=small_config())
    first = result.candidate_output[
        result.candidate_output["ticker"].eq("000660")
        & result.candidate_output["date"].eq(pd.Timestamp("2026-01-01"))
    ].iloc[0]

    assert first[PROBABILITY_STATUS_COLUMN] == "missing_features"
    assert pd.isna(first[PROBABILITY_COLUMN])
    assert result.dataset.feature_table.loc[0, FEATURE_STATUS_COLUMN] == "missing_features"
