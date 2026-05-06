from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RUNNER_SCRIPT = PROJECT_ROOT / "Quant_mvp" / "scripts" / "run_v0_3_evaluation_evidence.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("run_v0_3_evaluation_evidence", RUNNER_SCRIPT)
assert RUNNER_SPEC is not None
runner = importlib.util.module_from_spec(RUNNER_SPEC)
assert RUNNER_SPEC.loader is not None
RUNNER_SPEC.loader.exec_module(runner)

COHORT_SCRIPT = PROJECT_ROOT / "Quant_mvp" / "scripts" / "build_v0_3_momentum_evaluation_evidence_packets.py"
COHORT_SPEC = importlib.util.spec_from_file_location("build_v0_3_momentum_evaluation_evidence_packets", COHORT_SCRIPT)
assert COHORT_SPEC is not None
cohort_builder = importlib.util.module_from_spec(COHORT_SPEC)
assert COHORT_SPEC.loader is not None
COHORT_SPEC.loader.exec_module(cohort_builder)

RUN_COHORT_SCRIPT = PROJECT_ROOT / "Quant_mvp" / "scripts" / "run_v0_3_momentum_evaluation_evidence_cohort.py"
RUN_COHORT_SPEC = importlib.util.spec_from_file_location(
    "run_v0_3_momentum_evaluation_evidence_cohort",
    RUN_COHORT_SCRIPT,
)
assert RUN_COHORT_SPEC is not None
run_cohort = importlib.util.module_from_spec(RUN_COHORT_SPEC)
assert RUN_COHORT_SPEC.loader is not None
RUN_COHORT_SPEC.loader.exec_module(run_cohort)

from Quant_mvp.backtest_mvp import (  # noqa: E402
    CandidateRankingSnapshotConfig,
    build_contract_only_evaluation_evidence_packet,
    run_v0_3_evaluation_evidence,
    validate_evaluation_evidence_record,
    write_evaluation_evidence_markdown,
)


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


def prices() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    price_paths = {
        "005930": lambda day: 100.0 + day * 2.0,
        "000660": lambda day: 100.0 + day * 1.0,
        "035420": lambda day: 120.0 - day * 0.5,
        "051910": lambda day: 100.0 + ((-1) ** day) * 2.0 + day * 0.1,
    }
    for ticker, price_fn in price_paths.items():
        for day, date in enumerate(pd.bdate_range("2026-01-02", periods=50)):
            close = price_fn(day)
            rows.append(
                {
                    "ticker": ticker,
                    "date": date.date().isoformat(),
                    "open": close - 0.25,
                    "high": close + 0.5,
                    "low": close - 0.5,
                    "close": close,
                    "volume": 1000 + day,
                }
            )
    return pd.DataFrame(rows)


def write_daily_price_csv(path: Path, dates: pd.DatetimeIndex) -> None:
    path.write_text(
        "date,close,change,open,high,low,volume\n"
        + "\n".join(
            f"{date.date().isoformat()},{100 + index * 2},0,{99 + index * 2},"
            f"{101 + index * 2},{98 + index * 2},1000"
            for index, date in enumerate(dates)
        )
        + "\n",
        encoding="utf-8-sig",
    )


def write_daily_price_csv_with_zero_ohlcv_row(path: Path) -> None:
    dates = pd.bdate_range("2026-01-02", periods=46)
    rows = ["2026-01-02,100,0,0,0,0,0"]
    rows.extend(
        f"{date.date().isoformat()},{100 + index * 2},0,{99 + index * 2},"
        f"{101 + index * 2},{98 + index * 2},1000"
        for index, date in enumerate(dates[1:])
    )
    path.write_text(
        "date,close,change,open,high,low,volume\n" + "\n".join(rows) + "\n",
        encoding="utf-8-sig",
    )


def write_daily_price_csv_with_duplicate_row(path: Path) -> None:
    dates = pd.bdate_range("2026-01-02", periods=45)
    rows = [
        f"{date.date().isoformat()},{100 + index * 2},0,{99 + index * 2},"
        f"{101 + index * 2},{98 + index * 2},1000"
        for index, date in enumerate(dates)
    ]
    rows.insert(1, rows[0])
    path.write_text(
        "date,close,change,open,high,low,volume\n" + "\n".join(rows) + "\n",
        encoding="utf-8-sig",
    )


def read_evidence_payload(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    payload = text.split("```json", 1)[1].split("```", 1)[0]
    return json.loads(payload)


def test_v0_3_candidate_runs_to_evaluation_evidence_record() -> None:
    result = run_v0_3_evaluation_evidence(
        {"strategy_candidate": candidate()},
        prices(),
        ranking_config=CandidateRankingSnapshotConfig(
            rebalance_step_days=5,
            entry_percentile_threshold=0.50,
        ),
        backtest_config={
            "defaults": {
                "top_n": 2,
                "holding_period_days": 1,
                "execution_lag_days": 1,
                "transaction_cost_bps": 10.0,
                "slippage_bps": 5.0,
            }
        },
        evaluation_id="ee_v0_3_test_momentum",
        created_at="2026-04-29",
    )

    evidence = result.to_dict()
    validate_evaluation_evidence_record(evidence)

    assert evidence["status"] == "evidence_recorded"
    assert evidence["candidate_id"] == "sc_v0_3_test_momentum"
    assert evidence["hypothesis_id"] == "sh_v0_3_test_momentum"
    assert evidence["performance_metric_summary"]["total_return"] is not None
    assert evidence["risk_metric_summary"]["max_drawdown"] is not None
    assert "sharpe_ratio" in evidence["risk_metric_summary"]
    assert "sortino_ratio" in evidence["risk_metric_summary"]
    assert "exposure_stability" in evidence["risk_metric_summary"]
    assert "warmup_period_count" in evidence["risk_metric_summary"]
    assert "benchmark_relative_return" in evidence["performance_metric_summary"]
    assert evidence["metric_summary"]["benchmark_comparison"] == "not_available_without_approved_benchmark_series"
    assert evidence["metric_summary"]["oos_stability_status"] == "not_available_single_pass_snapshot"
    assert set(evidence["required_evaluation_checks"]) == {
        "cost",
        "drawdown",
        "volatility",
        "turnover",
        "oos_walk_forward_stability",
        "no_lookahead",
        "no_feedback",
    }
    assert evidence["required_evaluation_checks"]["oos_walk_forward_stability"]["status"] == (
        "not_available_single_pass_snapshot"
    )
    assert evidence["comparison_group"] == [
        "v0_3_candidate_review_cohort",
        "equal_weight_kospi200_candidate_proxy",
    ]
    assert evidence["failure_flags"] == []
    assert "must_not_feed" in evidence["no_feedback_check"]
    assert evidence["production_boundary_check"] == "no_automatic_production_activation_claim"
    assert not result.ranking_snapshot.empty


def test_contract_only_evaluation_evidence_packet_is_minimal_and_valid() -> None:
    evidence = build_contract_only_evaluation_evidence_packet(
        candidate(test_period="2015-01-01 through 2025-12-31"),
        cohort_id="momentum_evaluable_cohort_1",
        created_at="2026-04-29",
    )

    validate_evaluation_evidence_record(evidence)

    assert evidence["status"] == "contract_only"
    assert evidence["failure_flags"] == ["not_yet_run"]
    assert evidence["transaction_cost_assumption"] == "not_applicable_for_contract_only"
    assert evidence["comparison_group"] == [
        "momentum_evaluable_cohort_1",
        "equal_weight_kospi200_candidate_proxy",
    ]
    assert evidence["evaluation_window"] == {
        "start": "2015-01-01",
        "end": "2025-12-31",
        "rationale": "predeclared_candidate_contract_window_pending_approved_run",
    }
    checks = evidence["required_evaluation_checks"]
    assert set(checks) == {
        "cost",
        "drawdown",
        "volatility",
        "turnover",
        "oos_walk_forward_stability",
        "no_lookahead",
        "no_feedback",
    }
    assert checks["cost"]["status"] == "required_before_approved_run"
    assert checks["drawdown"]["metric_refs"] == ["risk_metrics.max_drawdown"]
    assert checks["volatility"]["metric_refs"] == ["risk_metrics.annualized_volatility"]
    assert checks["turnover"]["metric_refs"] == ["risk_metrics.turnover_proxy"]
    assert checks["oos_walk_forward_stability"]["status"] == "required_before_adoption_review"
    assert checks["no_lookahead"]["status"] == "required_before_approved_run"
    assert checks["no_feedback"]["status"] == "active_boundary_check"
    assert "metric_summary" not in evidence


def test_v0_3_evaluation_evidence_materializes_generator_prices_once() -> None:
    price_rows = (row for row in prices().to_dict("records"))

    result = run_v0_3_evaluation_evidence(
        candidate(),
        price_rows,
        ranking_config=CandidateRankingSnapshotConfig(
            rebalance_step_days=5,
            entry_percentile_threshold=0.50,
        ),
        backtest_config={"defaults": {"top_n": 1, "holding_period_days": 1, "execution_lag_days": 1}},
        evaluation_id="ee_v0_3_generator_prices",
        created_at="2026-04-29",
    )

    evidence = result.to_dict()
    assert evidence["status"] == "evidence_recorded"
    assert evidence["metric_summary"]["valid_security_count"] > 0
    assert not result.ranking_snapshot.empty


def test_evaluation_evidence_writer_stays_inside_evidence_only_paths(tmp_path: Path) -> None:
    result = run_v0_3_evaluation_evidence(
        candidate(),
        prices(),
        ranking_config=CandidateRankingSnapshotConfig(rebalance_step_days=5),
        backtest_config={"defaults": {"top_n": 1, "holding_period_days": 1, "execution_lag_days": 1}},
        evaluation_id="ee_v0_3_writer_test",
        created_at="2026-04-29",
    )

    allowed_path = (
        tmp_path
        / "Quant_mvp"
        / "backtest_mvp"
        / "docs"
        / "v0_3_evaluation_evidence"
        / "ee_v0_3_writer_test.md"
    )
    written = write_evaluation_evidence_markdown(
        result,
        allowed_path,
        project_root=tmp_path,
    )

    assert written == allowed_path.resolve()
    assert "not automatic production activation" in written.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="evidence-only"):
        write_evaluation_evidence_markdown(
            result,
            tmp_path / "Quant_mvp" / "backtest_mvp" / "engine.md",
            project_root=tmp_path,
        )


def test_evaluation_evidence_rejects_non_evaluable_candidate() -> None:
    with pytest.raises(ValueError, match="evaluable StrategyCandidate"):
        run_v0_3_evaluation_evidence(
            candidate(status="draft"),
            prices(),
        )


def test_evaluation_evidence_rejects_unresolved_blockers() -> None:
    with pytest.raises(ValueError, match="unresolved blockers"):
        run_v0_3_evaluation_evidence(
            candidate(blocking_issues=["manual_review_required"]),
            prices(),
        )


def test_cli_writes_evidence_only_packet(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    price_path = tmp_path / "prices.csv"
    output_path = (
        tmp_path
        / "Quant_mvp"
        / "backtest_mvp"
        / "reports"
        / "v0_3"
        / "evidence_only"
        / "ee_v0_3_cli_test.md"
    )
    ranking_config_path = tmp_path / "ranking_config.json"
    backtest_config_path = tmp_path / "backtest_config.json"

    candidate_path.write_text(json.dumps(candidate(), ensure_ascii=False), encoding="utf-8")
    prices().to_csv(price_path, index=False)
    ranking_config_path.write_text(
        json.dumps({"rebalance_step_days": 5, "entry_percentile_threshold": 0.50}),
        encoding="utf-8",
    )
    backtest_config_path.write_text(
        json.dumps({"defaults": {"top_n": 1, "holding_period_days": 1, "execution_lag_days": 1}}),
        encoding="utf-8",
    )

    exit_code = runner.main(
        [
            "--candidate",
            str(candidate_path),
            "--prices",
            str(price_path),
            "--ranking-config",
            str(ranking_config_path),
            "--backtest-config",
            str(backtest_config_path),
            "--evaluation-id",
            "ee_v0_3_cli_test",
            "--created-at",
            "2026-04-29",
            "--output",
            str(output_path),
            "--project-root",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    text = output_path.read_text(encoding="utf-8")
    assert "ee_v0_3_cli_test" in text
    assert "not automatic production activation" in text


def test_momentum_cohort_builder_writes_expected_contract_only_packets(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    records = [
        {"strategy_candidate": candidate(candidate_id="sc_v0_3_a", strategy_type="ignored")},
        {
            "strategy_candidate": candidate(
                candidate_id="sc_v0_3_b",
                hypothesis_id="sh_v0_3_b",
                status="draft",
            )
        },
        {
            "strategy_candidate": candidate(
                candidate_id="sc_v0_3_c",
                hypothesis_id="sh_v0_3_c",
                experiment_scope={
                    "strategy_type": "reversal",
                    "benchmark": "equal_weight_kospi200_candidate_proxy",
                },
            )
        },
    ]
    registry_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )

    output_dir = Path("Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/test_momentum")
    exit_code = cohort_builder.main(
        [
            "--registry",
            str(registry_path),
            "--output-dir",
            str(output_dir),
            "--project-root",
            str(tmp_path),
            "--created-at",
            "2026-04-29",
        ]
    )

    assert exit_code == 0
    manifest = tmp_path / output_dir / "manifest.json"
    packet_paths = list((tmp_path / output_dir).glob("ee_v0_3_*.md"))
    assert len(packet_paths) == 1
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_payload["candidate_count"] == 1
    assert manifest_payload["required_evaluation_check_ids"] == [
        "cost",
        "drawdown",
        "no_feedback",
        "no_lookahead",
        "oos_walk_forward_stability",
        "turnover",
        "volatility",
    ]
    assert "contract_only" in packet_paths[0].read_text(encoding="utf-8")

    first_packet = packet_paths[0]
    exit_code = cohort_builder.main(
        [
            "--registry",
            str(registry_path),
            "--output-dir",
            str(output_dir),
            "--project-root",
            str(tmp_path),
            "--expected-count",
            "1",
            "--created-at",
            "2026-04-30",
        ]
    )

    assert exit_code == 0
    packet_paths = list((tmp_path / output_dir).glob("ee_v0_3_*.md"))
    assert len(packet_paths) == 1
    assert packet_paths[0].name.endswith("sc_v0_3_a.md")
    assert "20260430" in packet_paths[0].name
    assert not first_packet.exists()


def test_momentum_cohort_runner_writes_actual_evidence_packets(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    registry_path.write_text(
        json.dumps({"strategy_candidate": candidate(candidate_id="sc_v0_3_a")}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    prices_dir.mkdir(parents=True)
    price_path = prices_dir / "005930_daily_prices.csv"
    price_path.write_text(
        "날짜,종가,전일비,시가,고가,저가,거래량\n"
        + "\n".join(
            f"{date.date().isoformat()},{100 + index * 2},0,{99 + index * 2},"
            f"{101 + index * 2},{98 + index * 2},1000"
            for index, date in enumerate(pd.bdate_range("2026-01-02", periods=45))
        )
        + "\n",
        encoding="utf-8-sig",
    )
    output_dir = Path("Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/test_actual_momentum")

    result = run_cohort.run_momentum_evaluation_evidence_cohort(
        registry=registry_path,
        prices_dir=prices_dir,
        output_dir=output_dir,
        project_root=tmp_path,
        cohort_id="test_momentum",
        created_at="2026-05-06",
        expected_count=1,
    )

    assert result["candidate_count"] == 1
    assert result["status_counts"] == {"evidence_recorded": 1}
    manifest = json.loads((tmp_path / output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "evidence_recorded"
    assert manifest["price_row_count"] == 45
    packet_text = next((tmp_path / output_dir).glob("ee_v0_3_*.md")).read_text(encoding="utf-8")
    assert '"status": "evidence_recorded"' in packet_text
    assert '"metric_summary"' in packet_text


def test_momentum_cohort_runner_dry_run_reports_actual_evidence_without_writing(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    registry_path.write_text(
        json.dumps({"strategy_candidate": candidate(candidate_id="sc_v0_3_dry_run")}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    prices_dir.mkdir(parents=True)
    write_daily_price_csv(prices_dir / "005930_daily_prices.csv", pd.bdate_range("2026-01-02", periods=45))

    result = run_cohort.dry_run_momentum_evaluation_evidence_cohort(
        registry=registry_path,
        prices_dir=prices_dir,
        cohort_id="test_momentum",
        created_at="2026-05-06",
        expected_count=1,
        project_root=tmp_path,
    )

    assert result["mode"] == "dry_run"
    assert result["output_written"] is False
    assert "does_not_auto_adjust" in result["adjustment_boundary"]
    assert "approved owner-lane execution" in result["next_evaluation_condition"]
    assert result["advisory"] == "dry_run_only_no_evidence_file_written"
    assert result["candidate_count"] == 1
    assert result["recorded_count"] == 1
    assert result["blocked_count"] == 0
    assert result["evidence_status_counts"] == {"evidence_recorded": 1}
    assert result["candidate_summaries"][0]["valid_security_count"] > 0
    preflight = result["candidate_summaries"][0]["preflight"]
    assert preflight["effective_max_date_inputs"]["test_period_end"] is None
    assert preflight["effective_max_date_inputs"]["auto_adjustment"] == "not_performed_requires_explicit_approval"
    assert preflight["next_evaluation_condition"] == "ready_for_approved_actual_run_with_existing_candidate_period"
    assert preflight["advisory"] == "dry_run_only_no_evidence_file_written"
    assert preflight["coverage_status"] == "candidate_price_coverage_ready_for_actual_run"
    assert preflight["required_rows_per_ticker"] == 42
    assert preflight["tickers_meeting_required_rows"] == 1
    assert result["price_coverage"]["ticker_count"] == 1
    assert not (tmp_path / "Quant_mvp" / "backtest_mvp").exists()


def test_momentum_cohort_runner_dry_run_excludes_zero_ohlcv_rows_without_writing(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    registry_path.write_text(
        json.dumps({"strategy_candidate": candidate(candidate_id="sc_v0_3_zero_ohlcv")}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    prices_dir.mkdir(parents=True)
    write_daily_price_csv_with_zero_ohlcv_row(prices_dir / "005930_daily_prices.csv")

    result = run_cohort.dry_run_momentum_evaluation_evidence_cohort(
        registry=registry_path,
        prices_dir=prices_dir,
        cohort_id="test_momentum",
        created_at="2026-05-06",
        expected_count=1,
        project_root=tmp_path,
    )

    assert result["recorded_count"] == 1
    assert result["blocked_count"] == 0
    assert result["raw_price_row_count"] == 46
    assert result["price_row_count"] == 45
    exception_summary = result["zero_ohlcv_exception_summary"]
    assert exception_summary["excluded_row_count"] == 1
    assert exception_summary["retained_row_count"] == 45
    assert exception_summary["affected_ticker_count"] == 1
    assert exception_summary["field_counts"] == {
        "open": 1,
        "high": 1,
        "low": 1,
        "volume": 1,
    }
    assert "suspended_or_delisted_like_price_rows" in exception_summary["policy"]
    assert (
        result["candidate_summaries"][0]["preflight"]["zero_ohlcv_exception_summary"]["excluded_row_count"]
        == 1
    )
    assert not (tmp_path / "Quant_mvp" / "backtest_mvp").exists()


def test_momentum_cohort_runner_dry_run_collapses_identical_duplicate_rows(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    registry_path.write_text(
        json.dumps({"strategy_candidate": candidate(candidate_id="sc_v0_3_duplicate_price")}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    prices_dir.mkdir(parents=True)
    write_daily_price_csv_with_duplicate_row(prices_dir / "005930_daily_prices.csv")

    result = run_cohort.dry_run_momentum_evaluation_evidence_cohort(
        registry=registry_path,
        prices_dir=prices_dir,
        cohort_id="test_momentum",
        created_at="2026-05-06",
        expected_count=1,
        project_root=tmp_path,
    )

    assert result["recorded_count"] == 1
    assert result["blocked_count"] == 0
    assert result["zero_ohlcv_retained_row_count"] == 46
    assert result["price_row_count"] == 45
    duplicate_summary = result["duplicate_ticker_date_exception_summary"]
    assert duplicate_summary["duplicate_row_count"] == 2
    assert duplicate_summary["duplicate_pair_count"] == 1
    assert duplicate_summary["redundant_row_count"] == 1
    assert duplicate_summary["conflicting_duplicate_pair_count"] == 0
    assert (
        result["candidate_summaries"][0]["preflight"]["duplicate_ticker_date_exception_summary"][
            "redundant_row_count"
        ]
        == 1
    )
    assert not (tmp_path / "Quant_mvp" / "backtest_mvp").exists()


def test_momentum_cohort_runner_writes_zero_ohlcv_exception_summary(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    registry_path.write_text(
        json.dumps({"strategy_candidate": candidate(candidate_id="sc_v0_3_zero_ohlcv_actual")}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    prices_dir.mkdir(parents=True)
    write_daily_price_csv_with_zero_ohlcv_row(prices_dir / "005930_daily_prices.csv")
    output_dir = Path("Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/test_zero_ohlcv")

    result = run_cohort.run_momentum_evaluation_evidence_cohort(
        registry=registry_path,
        prices_dir=prices_dir,
        output_dir=output_dir,
        project_root=tmp_path,
        cohort_id="test_momentum",
        created_at="2026-05-06",
        expected_count=1,
    )

    assert result["candidate_count"] == 1
    assert result["raw_price_row_count"] == 46
    assert result["price_row_count"] == 45
    manifest = json.loads((tmp_path / output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["zero_ohlcv_exception_summary"]["excluded_row_count"] == 1
    payload = read_evidence_payload(next((tmp_path / output_dir).glob("ee_v0_3_*.md")))
    assert payload["zero_ohlcv_exception_summary"]["excluded_row_count"] == 1
    assert "suspended_or_delisted_like_price_rows_excluded" in payload["known_limitations"]


def test_momentum_cohort_runner_dry_run_reports_missing_price_inputs_without_writing(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    registry_path.write_text(
        json.dumps({"strategy_candidate": candidate(candidate_id="sc_v0_3_missing_prices")}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"

    result = run_cohort.dry_run_momentum_evaluation_evidence_cohort(
        registry=registry_path,
        prices_dir=prices_dir,
        cohort_id="test_momentum",
        created_at="2026-05-06",
        expected_count=1,
        project_root=tmp_path,
    )

    assert result["mode"] == "dry_run"
    assert result["output_written"] is False
    assert result["candidate_count"] == 1
    assert result["recorded_count"] == 0
    assert result["blocked_count"] == 1
    assert result["price_input_status"] == "blocked_no_local_price_rows"
    assert "no daily price rows found" in result["price_input_blocker"]
    assert result["price_coverage"] == {
        "row_count": 0,
        "ticker_count": 0,
        "date_start": None,
        "date_end": None,
    }
    assert result["blocked_candidates"][0]["candidate_id"] == "sc_v0_3_missing_prices"
    assert result["blocked_candidates"][0]["status"] == "blocked_for_actual_label"
    assert result["blocked_candidates"][0]["preflight"]["coverage_status"] == "blocked_no_candidate_price_rows"
    assert not (tmp_path / "Quant_mvp" / "backtest_mvp").exists()


def test_momentum_cohort_runner_rejects_non_quant_price_dir(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    registry_path.write_text(
        json.dumps({"strategy_candidate": candidate(candidate_id="sc_v0_3_external_prices")}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    prices_dir = tmp_path / "chart_mvp" / "data"
    prices_dir.mkdir(parents=True)
    write_daily_price_csv(prices_dir / "005930_daily_prices.csv", pd.bdate_range("2026-01-02", periods=45))

    with pytest.raises(ValueError, match="price inputs must stay under Quant_mvp"):
        run_cohort.dry_run_momentum_evaluation_evidence_cohort(
            registry=registry_path,
            prices_dir=prices_dir,
            cohort_id="test_momentum",
            created_at="2026-05-06",
            expected_count=1,
            project_root=tmp_path,
        )


def test_momentum_cohort_runner_caps_actual_run_to_candidate_test_period(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    registry_path.write_text(
        json.dumps(
            {
                "strategy_candidate": candidate(
                    candidate_id="sc_v0_3_window_capped",
                    test_period="2015-01-01 through 2025-12-31",
                )
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    prices_dir.mkdir(parents=True)
    write_daily_price_csv(prices_dir / "005930_daily_prices.csv", pd.bdate_range("2025-09-01", periods=130))
    output_dir = Path("Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/test_window_capped")

    result = run_cohort.run_momentum_evaluation_evidence_cohort(
        registry=registry_path,
        prices_dir=prices_dir,
        output_dir=output_dir,
        project_root=tmp_path,
        cohort_id="test_momentum",
        created_at="2026-05-06",
        expected_count=1,
    )

    assert result["candidate_count"] == 1
    payload = read_evidence_payload(next((tmp_path / output_dir).glob("ee_v0_3_*.md")))
    assert payload["evaluation_window"]["end"] <= "2025-12-31"
    manifest = json.loads((tmp_path / output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["price_row_count"] > 0


def test_momentum_cohort_runner_marks_shared_rule_proxy_not_supervised(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    records = [
        {"strategy_candidate": candidate(candidate_id="sc_v0_3_shared_a", hypothesis_id="sh_v0_3_shared_a")},
        {"strategy_candidate": candidate(candidate_id="sc_v0_3_shared_b", hypothesis_id="sh_v0_3_shared_b")},
    ]
    registry_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    prices_dir.mkdir(parents=True)
    write_daily_price_csv(prices_dir / "005930_daily_prices.csv", pd.bdate_range("2026-01-02", periods=60))
    output_dir = Path("Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/test_shared_proxy")

    result = run_cohort.run_momentum_evaluation_evidence_cohort(
        registry=registry_path,
        prices_dir=prices_dir,
        output_dir=output_dir,
        project_root=tmp_path,
        cohort_id="test_momentum",
        created_at="2026-05-06",
        expected_count=2,
    )

    assert result["candidate_count"] == 2
    payloads = [read_evidence_payload(path) for path in sorted((tmp_path / output_dir).glob("ee_v0_3_*.md"))]
    assert {payload["label_use_status"] for payload in payloads} == {"generic_momentum_proxy_not_supervised"}
    assert all(payload["metric_summary"]["label_role"] == "generic_momentum_proxy" for payload in payloads)
    manifest = json.loads((tmp_path / output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["label_use_status_counts"] == {"generic_momentum_proxy_not_supervised": 2}


def test_momentum_cohort_runner_rejects_invalidated_actual_label_packets(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    registry_path.write_text(
        json.dumps(
            {
                "strategy_candidate": candidate(
                    candidate_id="sc_v0_3_insufficient_window",
                    test_period="2015-01-01 through 2025-12-31",
                )
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    prices_dir.mkdir(parents=True)
    write_daily_price_csv(prices_dir / "005930_daily_prices.csv", pd.bdate_range("2025-11-27", periods=24))
    output_dir = Path("Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/test_invalidated_guard")

    with pytest.raises(ValueError, match="did not produce candidate-level metric_summary labels"):
        run_cohort.run_momentum_evaluation_evidence_cohort(
            registry=registry_path,
            prices_dir=prices_dir,
            output_dir=output_dir,
            project_root=tmp_path,
            cohort_id="test_momentum",
            created_at="2026-05-06",
            expected_count=1,
        )

    assert not (tmp_path / output_dir).exists()


def test_momentum_cohort_runner_dry_run_reports_invalidated_without_writing(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.jsonl"
    registry_path.write_text(
        json.dumps(
            {
                "strategy_candidate": candidate(
                    candidate_id="sc_v0_3_dry_run_invalidated",
                    test_period="2015-01-01 through 2025-12-31",
                )
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    prices_dir = tmp_path / "Quant_mvp" / "data" / "v0_3" / "local_price_inputs"
    prices_dir.mkdir(parents=True)
    write_daily_price_csv(prices_dir / "005930_daily_prices.csv", pd.bdate_range("2025-11-27", periods=24))

    result = run_cohort.dry_run_momentum_evaluation_evidence_cohort(
        registry=registry_path,
        prices_dir=prices_dir,
        cohort_id="test_momentum",
        created_at="2026-05-06",
        expected_count=1,
        project_root=tmp_path,
    )

    assert result["mode"] == "dry_run"
    assert result["output_written"] is False
    assert "does_not_auto_adjust" in result["adjustment_boundary"]
    assert "existing StrategyCandidate test_period/effective_max_date" in result["next_evaluation_condition"]
    assert "Keep blocked candidates contract_only" in result["advisory"]
    assert result["candidate_count"] == 1
    assert result["recorded_count"] == 0
    assert result["blocked_count"] == 1
    assert result["blocked_candidates"][0]["candidate_id"] == "sc_v0_3_dry_run_invalidated"
    assert "Keep this candidate contract_only" in result["blocked_candidates"][0]["blocked_reason"]
    preflight = result["blocked_candidates"][0]["preflight"]
    assert preflight["effective_max_date"] == "2025-12-31"
    assert preflight["effective_max_date_inputs"]["test_period_end"] == "2025-12-31"
    assert preflight["effective_max_date_inputs"]["auto_adjustment"] == "not_performed_requires_explicit_approval"
    assert preflight["next_evaluation_condition"] == (
        "existing local prices must provide required rows per ticker before effective_max_date"
    )
    assert "Keep blocked candidates contract_only" in preflight["advisory"]
    assert preflight["coverage_status"] == "blocked_insufficient_rows_per_ticker_for_signal_and_holding_period"
    assert preflight["required_rows_per_ticker"] == 42
    assert preflight["max_rows_per_ticker"] == 24
    assert preflight["tickers_meeting_required_rows"] == 0
    assert not (tmp_path / "Quant_mvp" / "backtest_mvp").exists()
