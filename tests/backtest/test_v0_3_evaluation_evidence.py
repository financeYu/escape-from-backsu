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

from Quant_mvp.backtest_mvp import (  # noqa: E402
    CandidateRankingSnapshotConfig,
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
    assert evidence["comparison_group"] == [
        "v0_3_candidate_review_cohort",
        "equal_weight_kospi200_candidate_proxy",
    ]
    assert evidence["failure_flags"] == []
    assert "must_not_feed" in evidence["no_feedback_check"]
    assert evidence["production_boundary_check"] == "no_automatic_production_activation_claim"
    assert not result.ranking_snapshot.empty


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
