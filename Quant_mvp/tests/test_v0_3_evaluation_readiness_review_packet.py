from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SCRIPT = PROJECT_ROOT / "Quant_mvp" / "scripts" / "build_v0_3_evaluation_readiness_review_packet.py"
SPEC = importlib.util.spec_from_file_location("build_v0_3_evaluation_readiness_review_packet", SCRIPT)
assert SPEC is not None
review_packet = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(review_packet)

RUN_SCRIPT = PROJECT_ROOT / "Quant_mvp" / "scripts" / "run_v0_3_momentum_evaluation_evidence_cohort.py"
RUN_SPEC = importlib.util.spec_from_file_location("run_v0_3_momentum_evaluation_evidence_cohort", RUN_SCRIPT)
assert RUN_SPEC is not None
evidence_runner = importlib.util.module_from_spec(RUN_SPEC)
assert RUN_SPEC.loader is not None
RUN_SPEC.loader.exec_module(evidence_runner)


def candidate(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "candidate_id": "sc_v0_3_test_momentum",
        "hypothesis_id": "sh_v0_3_test_momentum",
        "version": "0.1.0",
        "status": "evaluable",
        "target_universe": "KOSPI200_candidate_only",
        "data_requirements": ["daily_ohlcv_candidate_review_only"],
        "experiment_scope": {
            "strategy_type": "momentum",
            "benchmark": "equal_weight_kospi200_candidate_proxy",
        },
        "known_constraints": [
            "candidate_only_not_production",
            "evaluation_evidence_required_before_adoption_review",
        ],
        "blocking_issues": [],
        "no_feedback_check": "strategy_candidates_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
    }
    payload.update(overrides)
    return payload


def write_daily_price_csv(
    path: Path,
    dates: pd.DatetimeIndex,
    *,
    excluded_untradable_indices: set[int] | None = None,
) -> None:
    excluded_untradable_indices = excluded_untradable_indices or set()
    path.write_text(
        "date,close,change,open,high,low,volume\n"
        + "\n".join(
            f"{date.date().isoformat()},{100 + index * 2},0,{99 + index * 2},"
            f"{101 + index * 2},{98 + index * 2},"
            f"{0 if index in excluded_untradable_indices else 1000}"
            for index, date in enumerate(dates)
        )
        + "\n",
        encoding="utf-8-sig",
    )


def write_registry(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps({"strategy_candidate": record}, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def read_evidence_markdown(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    payload = text.split("```json\n", 1)[1].split("\n```", 1)[0]
    parsed = json.loads(payload)
    assert isinstance(parsed, dict)
    return parsed


def test_readiness_review_packet_reports_ready_dry_run_without_writing(tmp_path: Path, capsys) -> None:
    registry_path = tmp_path / "registry.jsonl"
    write_registry(registry_path, [candidate(candidate_id="sc_v0_3_ready")])
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    prices_dir.mkdir(parents=True)
    write_daily_price_csv(prices_dir / "005930_daily_prices.csv", pd.bdate_range("2026-01-02", periods=45))

    exit_code = review_packet.main(
        [
            "--registry",
            str(registry_path),
            "--prices-dir",
            str(prices_dir),
            "--project-root",
            str(tmp_path),
            "--cohort-id",
            "test_momentum",
            "--created-at",
            "2026-05-06",
            "--expected-count",
            "1",
            "--max-candidate-examples",
            "1",
        ]
    )

    assert exit_code == 0
    packet = json.loads(capsys.readouterr().out)
    assert packet["schema_version"] == "v0_3_evaluation_readiness_review_packet_0_1"
    assert packet["artifact_type"] == "strategy_candidate_evaluation_readiness_review_packet"
    assert packet["output_written"] is False
    assert packet["candidate_count"] == 1
    assert packet["ready_for_actual_run_count"] == 1
    assert packet["blocked_count"] == 0
    assert packet["price_coverage"]["ticker_count"] == 1
    assert packet["coverage_blocker_counts"] == {"none": 1}
    assert packet["selection_status"] == "selection unavailable / evidence insufficient"
    assert packet["label_readiness"]["selector_label_eligible"] is False
    assert packet["label_readiness"]["contract_only_missing_actual_metrics_are_not_labels"] is True
    assert packet["label_readiness"]["dry_run_metric_summaries_are_not_recorded_labels"] is True
    assert packet["approval_boundary"]["evaluation_evidence_file_write"] is False
    assert packet["approval_boundary"]["auto_adjust_effective_max_date"] is False
    assert packet["candidate_examples"][0]["candidate_id"] == "sc_v0_3_ready"
    assert packet["candidate_examples"][0]["coverage_status"] == "candidate_price_coverage_ready_for_actual_run"
    assert "approved actual EvaluationEvidence run" in packet["recommended_next_action"]
    assert not (tmp_path / "Quant_mvp" / "backtest_mvp").exists()


def test_candidate_level_evaluation_evidence_dry_run_rows_are_candidate_matched(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    write_registry(registry_path, [candidate(candidate_id="sc_v0_3_ready")])
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    prices_dir.mkdir(parents=True)
    write_daily_price_csv(prices_dir / "005930_daily_prices.csv", pd.bdate_range("2026-01-02", periods=45))

    result = evidence_runner.dry_run_momentum_evaluation_evidence_cohort(
        registry=registry_path,
        prices_dir=prices_dir,
        project_root=tmp_path,
        cohort_id="test_momentum",
        created_at="2026-05-06",
        expected_count=1,
    )

    assert result["output_written"] is False
    assert result["candidate_level_evidence_count"] == 1
    assert result["candidate_metric_match_true_count"] == 1
    assert result["excluded_untradable_count"] == 0
    row = result["candidate_level_evidence_rows"][0]
    assert row["candidate_id"] == "sc_v0_3_ready"
    assert row["evidence_id"]
    assert row["evidence_status"] == "evidence_recorded"
    assert row["metric_subject_type"] == "strategy_candidate"
    assert row["metric_subject_id"] == "sc_v0_3_ready"
    assert row["candidate_metric_match"] is True
    assert row["candidate_metric_match_reason"] == "candidate_id_matches_candidate_level_evaluation_evidence"
    assert row["total_return"] is not None
    assert row["benchmark_return"] is not None
    assert row["proxy_return"] is not None
    assert row["excess_return_vs_proxy"] is not None
    assert row["max_drawdown"] is not None
    assert row["sharpe"] is not None
    assert row["turnover"] is not None
    assert row["failure_flags"] == []
    assert row["actual_metric_source"] == "candidate_level_evaluation_evidence_dry_run"
    assert row["actual_metric_role"] == "candidate_level_metric_not_label"
    assert row["label_source"] == "not_generated_dry_run_metric_only"
    assert row["supervised_label_eligible"] is False
    assert result["benchmark_reference_features"][0]["metric_subject_id"] == "generic_momentum_proxy"
    assert result["benchmark_reference_features"][0]["label_source"] == "unlabeled"


def test_candidate_level_dry_run_separates_excluded_untradable_rows(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    write_registry(registry_path, [candidate(candidate_id="sc_v0_3_ready")])
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    prices_dir.mkdir(parents=True)
    write_daily_price_csv(
        prices_dir / "005930_daily_prices.csv",
        pd.bdate_range("2026-01-02", periods=45),
        excluded_untradable_indices={0},
    )

    result = evidence_runner.dry_run_momentum_evaluation_evidence_cohort(
        registry=registry_path,
        prices_dir=prices_dir,
        project_root=tmp_path,
        cohort_id="test_momentum",
        created_at="2026-05-06",
        expected_count=1,
    )

    assert result["candidate_level_evidence_count"] == 1
    assert result["candidate_metric_match_true_count"] == 1
    assert result["excluded_untradable_count"] == 1
    row = result["candidate_level_evidence_rows"][0]
    assert row["excluded_untradable"] is False
    assert row["excluded_untradable_row_count"] == 1
    assert row["failure_flags"] == []


def test_actual_momentum_run_writes_candidate_level_evidence_not_generic_proxy(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    write_registry(
        registry_path,
        [
            candidate(candidate_id="sc_v0_3_ready_one"),
            candidate(candidate_id="sc_v0_3_ready_two"),
        ],
    )
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    output_dir = tmp_path / "Quant_mvp" / "backtest_mvp" / "docs" / "v0_3_evaluation_evidence" / "momentum"
    prices_dir.mkdir(parents=True)
    write_daily_price_csv(prices_dir / "005930_daily_prices.csv", pd.bdate_range("2026-01-02", periods=45))

    result = evidence_runner.run_momentum_evaluation_evidence_cohort(
        registry=registry_path,
        prices_dir=prices_dir,
        output_dir=output_dir,
        project_root=tmp_path,
        cohort_id="test_momentum",
        created_at="2026-05-06",
        expected_count=2,
    )

    assert result["candidate_count"] == 2
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert manifest["label_use_status_counts"] == {"candidate_level_supervised_label_candidate": 2}
    assert manifest["evidence_status_counts"] == {"evidence_recorded": 2}
    for packet_path in result["packet_paths"]:
        evidence = read_evidence_markdown(Path(packet_path))
        assert evidence["status"] == "evidence_recorded"
        assert evidence["metric_subject_type"] == "strategy_candidate"
        assert evidence["metric_subject_id"] == evidence["candidate_id"]
        assert evidence["candidate_metric_match"] is True
        assert evidence["candidate_metric_match_reason"] == "candidate_id_matches_candidate_level_evaluation_evidence"
        assert evidence["label_use_status"] == "candidate_level_supervised_label_candidate"
        assert evidence["metric_summary"]["label_role"] == "candidate_specific"
        assert evidence["metric_summary"]["benchmark_return"] is not None
        assert evidence["metric_summary"]["proxy_return"] is not None
        assert evidence["metric_summary"]["excess_return_vs_proxy"] is not None
        assert evidence["benchmark_reference_summary"]["reference_role"] == "benchmark_reference_feature_not_label"
        assert (
            evidence["required_evaluation_checks"]["benchmark_reference_comparison"]["status"]
            == "recorded"
        )


def test_readiness_review_packet_reports_blocked_coverage_without_writing(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    write_registry(
        registry_path,
        [
            candidate(
                candidate_id="sc_v0_3_blocked",
                test_period="2015-01-01 through 2025-12-31",
            )
        ],
    )
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    prices_dir.mkdir(parents=True)
    write_daily_price_csv(prices_dir / "005930_daily_prices.csv", pd.bdate_range("2025-11-27", periods=24))

    packet = review_packet.build_review_packet(
        registry=registry_path,
        prices_dir=prices_dir,
        cohort_id="test_momentum",
        created_at="2026-05-06",
        expected_count=1,
        max_candidate_examples=3,
        project_root=tmp_path,
    )

    assert packet["output_written"] is False
    assert packet["candidate_count"] == 1
    assert packet["ready_for_actual_run_count"] == 0
    assert packet["blocked_count"] == 1
    assert packet["selection_status"] == "selection unavailable / evidence insufficient"
    assert packet["selection_reason"] == "blocked_candidates_or_missing_recorded_EvaluationEvidence_labels"
    assert packet["label_readiness"]["recorded_evaluation_evidence_label_count"] == 0
    assert packet["coverage_status_counts"] == {
        "blocked_insufficient_rows_per_ticker_for_signal_and_holding_period": 1
    }
    assert packet["coverage_blocker_counts"] == {
        "requires at least 42 rows per ticker, but max available is 24": 1
    }
    assert packet["effective_max_date_summary"]["count_by_effective_max_date"] == {"2025-12-31": 1}
    assert packet["effective_max_date_summary"]["auto_adjustment_counts"] == {
        "not_performed_requires_explicit_approval": 1
    }
    assert packet["candidate_examples"][0]["readiness_status"] == "blocked_for_actual_run"
    assert packet["candidate_examples"][0]["effective_max_date"] == "2025-12-31"
    assert packet["approval_boundary"]["auto_adjust_StrategyCandidate_test_period"] is False
    assert packet["approval_boundary"]["candidate_contract_adjustment_requires_separate_approval"] is True
    assert "keep blocked candidates contract_only" in packet["recommended_next_action"]
    assert not (tmp_path / "Quant_mvp" / "backtest_mvp").exists()


def test_readiness_review_packet_reports_missing_quant_local_price_inputs(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    write_registry(registry_path, [candidate(candidate_id="sc_v0_3_missing_prices")])
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"

    packet = review_packet.build_review_packet(
        registry=registry_path,
        prices_dir=prices_dir,
        cohort_id="test_momentum",
        created_at="2026-05-06",
        expected_count=1,
        project_root=tmp_path,
    )

    assert packet["output_written"] is False
    assert packet["candidate_count"] == 1
    assert packet["ready_for_actual_run_count"] == 0
    assert packet["blocked_count"] == 1
    assert packet["coverage_status_counts"] == {
        "blocked_missing_quant_local_price_inputs": 1,
    }
    assert packet["selection_status"] == "selection unavailable / evidence insufficient"
    assert packet["selection_reason"] == "missing_quant_local_price_inputs_for_recorded_EvaluationEvidence"
    assert "approved Quant-local daily price CSV inputs" in packet["recommended_next_action"]
    assert packet["raw_dry_run_status"]["mode"] == "blocked_before_dry_run"
