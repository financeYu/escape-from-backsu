from __future__ import annotations

import json
import math
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
    FEATURE_INPUT_PATH,
    FEATURE_INPUT_SOURCE,
    FEATURE_SET_VERSION_COLUMN,
    FEATURE_STATUS_COLUMN,
    FEATURE_VALID_COUNT_COLUMN,
    LABEL_AVAILABILITY_TIME_COLUMN,
    LABEL_AVAILABLE_COLUMN,
    LABEL_COLUMN,
    LABEL_CONTRACT_VERSION_COLUMN,
    LABEL_TIME_COLUMN,
    MODEL_TYPE,
    MODEL_VERSION,
    PROBABILITY_COLUMN,
    PROBABILITY_SAMPLE_ROLE_COLUMN,
    PROBABILITY_STATUS_COLUMN,
    ProbUp1DEvaluationOnlyBacktestConfig,
    ProbUp1DConfig,
    SELECTION_PACKET_PATH,
    SELECTION_PACKET_TYPE,
    WALK_FORWARD_EVALUATION_PATH,
    WALK_FORWARD_EVALUATION_SOURCE,
    build_prob_up_1d_candidate_selection_packet,
    build_prob_up_1d_candidate_sidecar_ranking,
    build_prob_up_1d_dataset,
    build_prob_up_1d_feature_input_frame,
    evaluate_prob_up_1d_candidate_walk_forward,
    export_prob_up_1d_candidate_selection_packet,
    export_prob_up_1d_evaluation_only_backtest,
    export_prob_up_1d_walk_forward_evaluation,
    load_candidate_probability_artifact,
    run_prob_up_1d_candidate_pipeline,
    run_prob_up_1d_evaluation_only_backtest,
    validate_prob_up_1d_evaluation_only_backtest_diagnostic,
    validate_prob_up_1d_evaluation_only_backtest_input,
    validate_prob_up_1d_schema_consistency,
    validate_prob_up_1d_selection_packet_schema,
)
from src.scores.technical_scores import ALL_STEP9_RAW_SCORE_COLUMNS  # noqa: E402


FEATURE_COLUMNS = ALL_STEP9_RAW_SCORE_COLUMNS


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
            row: dict[str, object] = {
                "ticker": ticker,
                "date": f"2026-01-{offset:02d}",
                "adjusted_close": price,
            }
            for feature_index, column in enumerate(FEATURE_COLUMNS, start=1):
                source_values = score_a if feature_index % 2 else score_b
                row[column] = source_values[ticker][offset - 1] + (feature_index * 0.01)
            rows.append(row)
    return pd.DataFrame(rows)


def walk_forward_probability_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    prices = {
        "005930": [10.0, 11.0, 10.5, 12.0, 11.8, 12.4, 13.1, 12.7, 13.4, 13.0],
        "000660": [20.0, 19.4, 20.2, 19.8, 20.7, 21.1, 20.8, 21.6, 22.0, 21.7],
    }
    for ticker, series in prices.items():
        for offset, price in enumerate(series, start=1):
            row: dict[str, object] = {
                "ticker": ticker,
                "date": f"2026-02-{offset:02d}",
                "adjusted_close": price,
            }
            for feature_index, column in enumerate(FEATURE_COLUMNS, start=1):
                row[column] = ((offset * 0.07) + (feature_index * 0.03) + (0.11 if ticker == "005930" else 0.02))
            rows.append(row)
    return pd.DataFrame(rows)


def price_frame() -> pd.DataFrame:
    return probability_frame().loc[:, ["ticker", "date", "adjusted_close"]]


def technical_old_score_frame() -> pd.DataFrame:
    return probability_frame().loc[:, ["ticker", "date", *FEATURE_COLUMNS]]


def ohlcv_derived_source_frame() -> pd.DataFrame:
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
            "adjusted_close": [10.0, 11.0, 12.0, 14.0, 13.0],
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


def small_config() -> ProbUp1DConfig:
    return ProbUp1DConfig(
        feature_columns=FEATURE_COLUMNS,
        min_train_rows=6,
        min_eval_rows=2,
        eval_fraction=0.30,
        max_iter=300,
        learning_rate=0.15,
    )


def walk_forward_config(*, min_eval_rows: int = 2) -> ProbUp1DConfig:
    return ProbUp1DConfig(
        feature_columns=FEATURE_COLUMNS,
        min_train_rows=6,
        min_eval_rows=min_eval_rows,
        eval_fraction=0.30,
        max_iter=300,
        learning_rate=0.15,
        walk_forward_initial_train_periods=3,
        walk_forward_eval_periods=1,
        walk_forward_step_periods=1,
        walk_forward_min_folds=2,
        calibration_bins=4,
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


def test_adj_close_alias_is_approved_canonical_adjusted_close_source() -> None:
    frame = probability_frame().rename(columns={"adjusted_close": "adj_close"})

    dataset = build_prob_up_1d_dataset(frame, config=small_config())

    labels = dataset.label_table.sort_values(["ticker", "date"]).reset_index(drop=True)
    samsung_first = labels[
        labels["ticker"].eq("005930") & labels["date"].eq(pd.Timestamp("2026-01-01"))
    ].iloc[0]
    assert samsung_first[LABEL_COLUMN] == 1
    assert "adjusted_close" not in dataset.feature_table.columns
    assert "adj_close" not in dataset.feature_table.columns


def test_close_is_not_silent_adjusted_close_fallback() -> None:
    frame = probability_frame().rename(columns={"adjusted_close": "close"})

    with pytest.raises(ValueError, match="close is not an approved adjusted_close alias"):
        build_prob_up_1d_dataset(frame, config=small_config())


def test_conflicting_adjusted_close_alias_values_are_rejected() -> None:
    frame = probability_frame()
    frame["adj_close"] = frame["adjusted_close"]
    frame.loc[0, "adj_close"] = frame.loc[0, "adjusted_close"] + 1.0

    with pytest.raises(ValueError, match="conflicting adjusted_close"):
        build_prob_up_1d_dataset(frame, config=small_config())


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
    assert latest[EXECUTION_TIME_COLUMN] == pd.Timestamp("2026-01-07")
    assert pd.isna(latest[LABEL_TIME_COLUMN])
    assert pd.isna(latest[LABEL_AVAILABILITY_TIME_COLUMN])
    assert latest[FEATURE_SET_VERSION_COLUMN] == "v0_2_candidate_ml_score"
    assert latest[LABEL_CONTRACT_VERSION_COLUMN] == "adjusted_close_up_1d_v0_2"
    validate_prob_up_1d_schema_consistency(result)

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


def test_pipeline_can_export_candidate_only_sidecar_and_manifest(tmp_path: Path) -> None:
    config = ProbUp1DConfig(
        feature_columns=FEATURE_COLUMNS,
        min_train_rows=6,
        min_eval_rows=2,
        eval_fraction=0.30,
        max_iter=300,
        learning_rate=0.15,
        sidecar_output_root=tmp_path,
    )

    result = run_prob_up_1d_candidate_pipeline(
        probability_frame(),
        config=config,
        as_of_date="2026-01-06",
    )

    assert result.sidecar_export is not None
    assert result.sidecar_export.sidecar_path.exists()
    assert result.sidecar_export.manifest_path.exists()
    exported = pd.read_csv(result.sidecar_export.sidecar_path)
    manifest = json.loads(result.sidecar_export.manifest_path.read_text(encoding="utf-8"))

    assert exported["date"].eq("2026-01-06").all()
    assert CANDIDATE_SIDECAR_RANK_COLUMN in exported.columns
    assert "technical_composite_score" not in exported.columns
    assert "final_composite_score" not in exported.columns
    assert manifest["artifact_type"] == "sidecar_candidate_only"
    assert manifest["candidate_output"] == PROBABILITY_COLUMN
    assert manifest["production_rank_activation"] is False
    assert manifest["feeds_composite_scores"] is False
    assert manifest["row_count"] == len(exported)


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


def test_candidate_selection_packet_contains_required_metadata_and_no_rank() -> None:
    result = run_prob_up_1d_candidate_pipeline(
        probability_frame(),
        config=small_config(),
        as_of_date="2026-01-06",
    )

    packet = build_prob_up_1d_candidate_selection_packet(result, as_of_date="2026-01-06")

    assert SELECTION_PACKET_PATH.endswith("build_prob_up_1d_candidate_selection_packet")
    assert set(packet["candidate_packet_type"]) == {SELECTION_PACKET_TYPE}
    assert set(packet["as_of_date"]) == {"2026-01-06"}
    assert {
        "ticker",
        "as_of_date",
        DECISION_TIME_COLUMN,
        PROBABILITY_COLUMN,
        "model_version",
        "model_type",
        FEATURE_SET_VERSION_COLUMN,
        "feature_schema_version",
        "feature_schema_columns",
        LABEL_CONTRACT_VERSION_COLUMN,
        "adjusted_close_source_field",
        "adjusted_close_canonical_source_status",
        FEATURE_STATUS_COLUMN,
        FEATURE_VALID_COUNT_COLUMN,
        "feature_expected_count",
        "feature_coverage_ratio",
        "data_quality_flag",
    }.issubset(packet.columns)
    assert packet["model_version"].eq(MODEL_VERSION).all()
    assert packet["model_type"].eq(MODEL_TYPE).all()
    assert packet["adjusted_close_source_field"].eq("adjusted_close").all()
    assert packet["feature_schema_columns"].eq("|".join(FEATURE_COLUMNS)).all()
    assert packet["feature_coverage_ratio"].between(0.0, 1.0).all()
    assert CANDIDATE_SIDECAR_RANK_COLUMN not in packet.columns
    assert "rank" not in packet.columns
    assert "final_composite_score" not in packet.columns
    validate_prob_up_1d_selection_packet_schema(packet)


def test_candidate_selection_packet_sort_order_is_probability_desc_then_ticker() -> None:
    result = run_prob_up_1d_candidate_pipeline(
        probability_frame(),
        config=small_config(),
        as_of_date="2026-01-06",
    )
    packet = build_prob_up_1d_candidate_selection_packet(result, as_of_date="2026-01-06")

    expected = packet.sort_values(
        [PROBABILITY_COLUMN, "ticker"],
        ascending=[False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    pd.testing.assert_frame_equal(packet.reset_index(drop=True), expected)

    unsorted = packet.sort_values("ticker", ascending=False).reset_index(drop=True)
    if len(unsorted) > 1 and not unsorted[["ticker", PROBABILITY_COLUMN]].equals(packet[["ticker", PROBABILITY_COLUMN]]):
        with pytest.raises(ValueError, match="prob_up_1d_candidate desc, ticker asc"):
            validate_prob_up_1d_selection_packet_schema(unsorted)


def test_candidate_selection_packet_rejects_production_boundary_fields() -> None:
    result = run_prob_up_1d_candidate_pipeline(
        probability_frame(),
        config=small_config(),
        as_of_date="2026-01-06",
    )
    packet = build_prob_up_1d_candidate_selection_packet(result, as_of_date="2026-01-06")

    for forbidden_column in (
        CANDIDATE_SIDECAR_RANK_COLUMN,
        "rank",
        "production_rank",
        "final_composite_score",
        "technical_composite_score",
        "recommendation",
    ):
        leaked = packet.copy()
        leaked[forbidden_column] = 1

        with pytest.raises(ValueError, match=forbidden_column):
            validate_prob_up_1d_selection_packet_schema(leaked)


def test_candidate_selection_packet_export_writes_candidate_only_manifest(tmp_path: Path) -> None:
    result = run_prob_up_1d_candidate_pipeline(
        probability_frame(),
        config=small_config(),
        as_of_date="2026-01-06",
    )
    packet = build_prob_up_1d_candidate_selection_packet(result, as_of_date="2026-01-06")

    exported = export_prob_up_1d_candidate_selection_packet(
        packet,
        output_root=tmp_path,
        as_of_date="2026-01-06",
    )

    assert exported.packet_path.exists()
    assert exported.manifest_path.exists()
    saved = pd.read_csv(exported.packet_path)
    manifest = json.loads(exported.manifest_path.read_text(encoding="utf-8"))
    assert len(saved) == exported.row_count
    assert CANDIDATE_SIDECAR_RANK_COLUMN not in saved.columns
    assert "rank" not in saved.columns
    assert manifest["artifact_type"] == SELECTION_PACKET_TYPE
    assert manifest["sort_fields"] == [PROBABILITY_COLUMN, "ticker"]
    assert manifest["sort_directions"] == ["desc", "asc"]
    assert manifest["production_rank_activation"] is False
    assert manifest["feeds_production_ranking"] is False
    assert manifest["feeds_reports"] is False
    assert manifest["feeds_composite_scores"] is False
    assert manifest["replace_final_composite_score"] is False


def test_evaluation_only_backtest_loads_selection_packet_and_exports_diagnostics(tmp_path: Path) -> None:
    result = run_prob_up_1d_candidate_pipeline(
        probability_frame(),
        config=small_config(),
        as_of_date="2026-01-06",
    )
    packet = build_prob_up_1d_candidate_selection_packet(result, as_of_date="2026-01-06")
    exported_packet = export_prob_up_1d_candidate_selection_packet(
        packet,
        output_root=tmp_path / "selection_packet",
        as_of_date="2026-01-06",
    )

    loaded = load_candidate_probability_artifact(
        exported_packet.packet_path,
        expected_artifact_type=SELECTION_PACKET_TYPE,
        required_schema=("ticker", PROBABILITY_COLUMN, DECISION_TIME_COLUMN),
        as_of_date="2026-01-06",
    )
    diagnostic = run_prob_up_1d_evaluation_only_backtest(
        loaded,
        expected_artifact_type=SELECTION_PACKET_TYPE,
        as_of_date="2026-01-06",
    )
    validate_prob_up_1d_evaluation_only_backtest_diagnostic(diagnostic)
    exported_diagnostic = export_prob_up_1d_evaluation_only_backtest(
        diagnostic,
        output_root=tmp_path / "evaluation_only_backtest",
        as_of_date="2026-01-06",
    )

    assert exported_diagnostic.diagnostic_path.exists()
    assert exported_diagnostic.manifest_path.exists()
    saved = pd.read_csv(exported_diagnostic.diagnostic_path)
    manifest = json.loads(exported_diagnostic.manifest_path.read_text(encoding="utf-8"))

    assert saved["artifact_type"].eq("candidate_only_evaluation_backtest_diagnostic").all()
    assert saved["candidate_output"].eq(PROBABILITY_COLUMN).all()
    assert saved["input_row_count"].iloc[0] == len(packet)
    assert saved["probability_coverage"].iloc[0] == pytest.approx(1.0)
    assert bool(saved["production_rank_activation"].iloc[0]) is False
    assert bool(saved["feeds_production_ranking"].iloc[0]) is False
    assert bool(saved["feeds_reports"].iloc[0]) is False
    assert bool(saved["replace_final_composite_score"].iloc[0]) is False
    assert manifest["artifact_type"] == "candidate_only_evaluation_backtest_diagnostic"
    assert manifest["production_rank_activation"] is False
    assert manifest["feeds_production_ranking"] is False
    assert manifest["feeds_reports"] is False
    assert manifest["replace_final_composite_score"] is False


def test_evaluation_only_backtest_rejects_forbidden_artifact_fields() -> None:
    result = run_prob_up_1d_candidate_pipeline(
        probability_frame(),
        config=small_config(),
        as_of_date="2026-01-06",
    )
    packet = build_prob_up_1d_candidate_selection_packet(result, as_of_date="2026-01-06")

    for forbidden_column in (
        LABEL_COLUMN,
        "up_1d_label",
        "target_label",
        "technical_composite_score",
        "final_composite_score",
        "production_rank",
        "realized_return_1d",
        "forward_return_1d",
        "generated_report",
    ):
        leaked = packet.copy()
        leaked[forbidden_column] = 1
        with pytest.raises(ValueError, match=forbidden_column):
            validate_prob_up_1d_evaluation_only_backtest_input(leaked, expected_artifact_type=SELECTION_PACKET_TYPE)


def test_evaluation_only_backtest_loader_rejects_invalid_timing_values(tmp_path: Path) -> None:
    result = run_prob_up_1d_candidate_pipeline(
        probability_frame(),
        config=small_config(),
        as_of_date="2026-01-06",
    )
    packet = build_prob_up_1d_candidate_selection_packet(result, as_of_date="2026-01-06")
    packet[DECISION_TIME_COLUMN] = "not-a-date"
    packet_path = tmp_path / "bad_timing_packet.csv"
    packet.to_csv(packet_path, index=False)

    with pytest.raises(ValueError, match="invalid decision_time"):
        load_candidate_probability_artifact(
            packet_path,
            expected_artifact_type=SELECTION_PACKET_TYPE,
            as_of_date="2026-01-06",
        )


def test_evaluation_only_backtest_rejects_timing_and_feedback_config() -> None:
    result = run_prob_up_1d_candidate_pipeline(
        probability_frame(),
        config=small_config(),
        as_of_date="2026-01-06",
    )
    packet = build_prob_up_1d_candidate_selection_packet(result, as_of_date="2026-01-06")

    missing_decision_time = packet.drop(columns=[DECISION_TIME_COLUMN])
    with pytest.raises(ValueError, match="decision_time"):
        validate_prob_up_1d_evaluation_only_backtest_input(
            missing_decision_time,
            expected_artifact_type="candidate_probability_artifact",
        )

    bad_config = ProbUp1DEvaluationOnlyBacktestConfig(updates_model_parameters=True)
    with pytest.raises(ValueError, match="updates_model_parameters"):
        run_prob_up_1d_evaluation_only_backtest(
            packet,
            config=bad_config,
            expected_artifact_type=SELECTION_PACKET_TYPE,
        )

    diagnostic = run_prob_up_1d_evaluation_only_backtest(packet, expected_artifact_type=SELECTION_PACKET_TYPE)
    for forbidden_flag in (
        "model_selection_from_backtest",
        "feature_selection_from_backtest",
        "cutoff_selection_from_backtest",
    ):
        forged_diagnostic = diagnostic.copy()
        forged_diagnostic[forbidden_flag] = True
        with pytest.raises(ValueError, match=forbidden_flag):
            validate_prob_up_1d_evaluation_only_backtest_diagnostic(forged_diagnostic)

    with pytest.raises(ValueError, match="forbidden production surface"):
        export_prob_up_1d_evaluation_only_backtest(
            diagnostic,
            output_root="reports/selection/latest_ranking.csv",
        )


def test_forbidden_backtest_and_valuation_columns_are_rejected() -> None:
    backtest_frame = probability_frame()
    backtest_frame["sharpe_ratio"] = 1.2
    with pytest.raises(ValueError, match="backtest/evaluation leakage"):
        build_prob_up_1d_dataset(
            backtest_frame,
            config=small_config(),
            feature_columns=(FEATURE_COLUMNS[0], "sharpe_ratio"),
        )

    label_frame = probability_frame()
    label_frame["target_label"] = 1
    with pytest.raises(ValueError, match="leakage columns"):
        build_prob_up_1d_dataset(
            label_frame,
            config=small_config(),
            feature_columns=(FEATURE_COLUMNS[0], "target_label"),
        )

    future_feature_frame = probability_frame()
    future_feature_frame["old_future_return_raw"] = 0.1
    with pytest.raises(ValueError, match="future-return"):
        build_prob_up_1d_dataset(
            future_feature_frame,
            config=small_config(),
            feature_columns=(FEATURE_COLUMNS[0], "old_future_return_raw"),
        )

    valuation_frame = probability_frame()
    valuation_frame["PER"] = 10.0
    with pytest.raises(ValueError, match="valuation/fundamental columns"):
        build_prob_up_1d_dataset(valuation_frame, config=small_config())


def test_missing_features_do_not_emit_fabricated_probabilities() -> None:
    frame = probability_frame()
    missing_row = frame["ticker"].eq("000660") & frame["date"].eq("2026-01-01")
    frame.loc[missing_row, FEATURE_COLUMNS[0]] = pd.NA

    result = run_prob_up_1d_candidate_pipeline(frame, config=small_config())
    first = result.candidate_output[
        result.candidate_output["ticker"].eq("000660")
        & result.candidate_output["date"].eq(pd.Timestamp("2026-01-01"))
    ].iloc[0]

    assert first[PROBABILITY_STATUS_COLUMN] == "missing_features"
    assert pd.isna(first[PROBABILITY_COLUMN])
    assert result.dataset.feature_table.loc[0, FEATURE_STATUS_COLUMN] == "missing_features"


def test_feature_input_path_connects_step9_old_score_allowlist() -> None:
    feature_input = build_prob_up_1d_feature_input_frame(
        price_frame(),
        technical_feature_frame=technical_old_score_frame(),
        config=small_config(),
    )

    assert FEATURE_INPUT_SOURCE == "step9_raw_technical_old_scores"
    assert FEATURE_INPUT_PATH.endswith("build_prob_up_1d_feature_input_frame")
    assert list(feature_input.columns) == ["ticker", "date", "adjusted_close", *FEATURE_COLUMNS]
    assert set(FEATURE_COLUMNS) == set(ALL_STEP9_RAW_SCORE_COLUMNS)
    assert "technical_composite_score" not in feature_input.columns
    assert "final_composite_score" not in feature_input.columns
    assert "rank" not in feature_input.columns


def test_feature_input_path_can_derive_step9_old_scores_from_ohlcv_inputs() -> None:
    feature_input = build_prob_up_1d_feature_input_frame(
        ohlcv_derived_source_frame(),
        config=small_config(),
        as_of_date="2026-01-31",
    )

    assert list(feature_input.columns) == ["ticker", "date", "adjusted_close", *FEATURE_COLUMNS]
    assert feature_input["ticker"].tolist() == ["005930"] * 5
    assert feature_input["adjusted_close"].tolist() == [10.0, 11.0, 12.0, 14.0, 13.0]
    assert set(FEATURE_COLUMNS).issubset(feature_input.columns)


def test_feature_input_rejects_forbidden_and_non_allowlisted_features() -> None:
    for forbidden_column in (
        "technical_composite_score",
        "final_composite_score",
        "rank",
        "generated_report_score",
        "backtest_hit_rate",
        "realized_return_1d",
        "future_return_1d",
        "target_label",
    ):
        features = technical_old_score_frame()
        features[forbidden_column] = 1.0

        with pytest.raises(ValueError, match=forbidden_column):
            build_prob_up_1d_feature_input_frame(
                price_frame(),
                technical_feature_frame=features,
                config=small_config(),
            )

    features = technical_old_score_frame()
    features["custom_ohlcv_feature_raw"] = 1.0
    with pytest.raises(ValueError, match="not in the old-score feature allowlist"):
        build_prob_up_1d_feature_input_frame(
            price_frame(),
            technical_feature_frame=features,
            config=small_config(),
            feature_columns=(FEATURE_COLUMNS[0], "custom_ohlcv_feature_raw"),
        )


def test_train_eval_inference_schema_consistency_with_old_score_input_path() -> None:
    feature_input = build_prob_up_1d_feature_input_frame(
        price_frame(),
        technical_feature_frame=technical_old_score_frame(),
        config=small_config(),
    )

    result = run_prob_up_1d_candidate_pipeline(feature_input, config=small_config())

    validate_prob_up_1d_schema_consistency(result)
    assert result.dataset.feature_columns == FEATURE_COLUMNS
    assert result.training_result.model.feature_columns == FEATURE_COLUMNS
    assert set(FEATURE_COLUMNS).issubset(result.dataset.feature_table.columns)
    assert not set(FEATURE_COLUMNS).intersection(result.candidate_output.columns)


def test_walk_forward_evaluation_uses_time_ordered_folds_and_required_metrics() -> None:
    config = walk_forward_config()
    dataset = build_prob_up_1d_dataset(walk_forward_probability_frame(), config=config)

    evaluation = evaluate_prob_up_1d_candidate_walk_forward(dataset, config=config)

    assert WALK_FORWARD_EVALUATION_SOURCE == "time_ordered_walk_forward_candidate_quality"
    assert WALK_FORWARD_EVALUATION_PATH.endswith("evaluate_prob_up_1d_candidate_walk_forward")
    assert len(evaluation.fold_metrics) >= 2
    required_metrics = {
        "brier_score",
        "log_loss",
        "calibration_error",
        "coverage",
        "nan_missing_rate",
        "feature_stability_mean_abs_shift",
    }
    assert required_metrics.issubset(evaluation.fold_metrics.columns)
    assert required_metrics.issubset(evaluation.metric_summary.columns)
    assert evaluation.fold_metrics["split_mode"].eq("time_ordered_expanding_window").all()
    for _, row in evaluation.fold_metrics.iterrows():
        assert pd.Timestamp(row["train_end_date"]) < pd.Timestamp(row["eval_start_date"])
    assert evaluation.fold_metrics["brier_score"].notna().all()
    assert evaluation.fold_metrics["log_loss"].notna().all()
    assert evaluation.fold_metrics["coverage"].between(0.0, 1.0).all()
    assert evaluation.fold_metrics["nan_missing_rate"].between(0.0, 1.0).all()
    assert not evaluation.calibration_table.empty
    assert set(evaluation.feature_stability_table["feature"]) == set(FEATURE_COLUMNS)
    assert "not_production_ranking_activation" in evaluation.interpretation_limits


def test_walk_forward_evaluation_reports_missing_coverage_without_fabricating_rows() -> None:
    config = walk_forward_config(min_eval_rows=1)
    frame = walk_forward_probability_frame()
    missing = frame["ticker"].eq("000660") & frame["date"].eq("2026-02-04")
    frame.loc[missing, FEATURE_COLUMNS[0]] = pd.NA
    dataset = build_prob_up_1d_dataset(frame, config=config)

    evaluation = evaluate_prob_up_1d_candidate_walk_forward(dataset, config=config)

    affected = evaluation.fold_metrics[evaluation.fold_metrics["eval_start_date"].eq("2026-02-04")].iloc[0]
    assert affected["eval_label_available_count"] == 2
    assert affected["evaluation_count"] == 1
    assert affected["coverage"] == pytest.approx(0.5)
    assert affected["missing_row_rate"] == pytest.approx(0.5)
    assert affected["nan_missing_rate"] > 0.0


def test_walk_forward_evaluation_export_writes_candidate_only_artifacts(tmp_path: Path) -> None:
    config = walk_forward_config()
    dataset = build_prob_up_1d_dataset(walk_forward_probability_frame(), config=config)
    evaluation = evaluate_prob_up_1d_candidate_walk_forward(dataset, config=config)

    exported = export_prob_up_1d_walk_forward_evaluation(
        evaluation,
        output_root=tmp_path,
        as_of_date="2026-02-09",
    )

    assert exported.summary_path.exists()
    assert exported.fold_metrics_path.exists()
    assert exported.calibration_path.exists()
    assert exported.feature_stability_path.exists()
    assert exported.manifest_path.exists()
    summary = pd.read_csv(exported.summary_path)
    folds = pd.read_csv(exported.fold_metrics_path)
    manifest = json.loads(exported.manifest_path.read_text(encoding="utf-8"))

    assert summary["fold_count"].iloc[0] == exported.fold_count
    assert len(folds) == exported.fold_count
    assert manifest["artifact_type"] == "candidate_only_walk_forward_evaluation"
    assert manifest["production_rank_activation"] is False
    assert manifest["feeds_production_ranking"] is False
    assert manifest["feeds_reports"] is False
    assert manifest["feeds_composite_scores"] is False
    assert manifest["replace_final_composite_score"] is False
