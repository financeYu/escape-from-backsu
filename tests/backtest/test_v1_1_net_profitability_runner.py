from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.net_profitability_runner_v1 import (  # noqa: E402
    NetProfitabilityRunnerConfig,
    run_net_profitability_evidence_v1_1,
    validate_net_profitability_artifacts_v1_1,
)


def _records() -> list[dict[str, object]]:
    return [
        {
            "candidate_id": "sc_v1_1_a",
            "selector_score": 91.0,
            "gross_return": 0.14,
            "benchmark_return": 0.05,
            "turnover": 0.8,
            "volatility": 0.10,
            "max_drawdown": -0.06,
            "coverage_ratio": 0.95,
            "date_range": {"start": "2025-01-02", "end": "2025-12-30"},
            "leakage_check_status": "pass",
            "no_lookahead_check_status": "pass",
            "rebalance_frequency": "monthly",
            "rebalancing_role": "material_effect_on_candidate_evidence",
            "rebalance_disclosure": "historical simulated monthly rebalancing materially affects candidate evidence context only",
        },
        {
            "candidate_id": "sc_v1_1_b",
            "selector_score": 76.0,
            "gross_return": 0.08,
            "benchmark_return": 0.05,
            "turnover": 0.4,
            "volatility": 0.12,
            "max_drawdown": -0.09,
            "coverage_ratio": 0.90,
            "date_range": {"start": "2025-01-02", "end": "2025-12-30"},
            "leakage_check_status": "pass",
            "no_lookahead_check_status": "pass",
        },
        {
            "candidate_id": "sc_v1_1_c",
            "selector_score": 48.0,
            "gross_return": 0.03,
            "benchmark_return": 0.05,
            "turnover": 0.2,
            "volatility": 0.08,
            "max_drawdown": -0.04,
            "coverage_ratio": 0.80,
            "date_range": {"start": "2025-01-02", "end": "2025-12-30"},
            "leakage_check_status": "pass",
            "no_lookahead_check_status": "pass",
        },
    ]


def test_net_profitability_runner_builds_required_v1_1_artifacts() -> None:
    artifacts = run_net_profitability_evidence_v1_1(
        _records(),
        config=NetProfitabilityRunnerConfig(top_k=2, random_seed=42),
    )

    validate_net_profitability_artifacts_v1_1(artifacts)
    assert artifacts["v1_1_net_profitability_evidence_runner"]["runner_version"].startswith("v1_1")
    assert len(artifacts["evaluation_evidence_v1"]) == 3
    assert artifacts["v1_1_top_k_profitability_report"]["candidate_count"] == 2
    assert artifacts["v1_1_top_decile_profitability_report"]["candidate_count"] == 1
    assert artifacts["v1_1_manual_review_profitability_packet"]["manual_review_required"] is True
    assert artifacts["v1_1_validation_manifest"]["manifest_lineage"] == (
        "HorizonPolicy -> SimulationRunManifest -> EvaluationEvidenceV1"
    )


def test_net_profitability_runner_outputs_net_and_benchmark_relative_metrics() -> None:
    artifacts = run_net_profitability_evidence_v1_1(
        _records(),
        config=NetProfitabilityRunnerConfig(top_k=2, cost_rate=0.01, slippage_rate=0.005),
    )
    first_summary = artifacts["v1_1_top_k_profitability_report"]["candidate_summaries"][0]

    assert first_summary["candidate_id"] == "sc_v1_1_a"
    assert first_summary["cost_drag"] == pytest.approx(0.012)
    assert first_summary["net_return"] == pytest.approx(0.128)
    assert first_summary["benchmark_relative_net_return"] == pytest.approx(0.078)
    evidence_metric = artifacts["evaluation_evidence_v1"][0]["metric_values"]["realized_return_summary"]
    assert evidence_metric["net_return"] == pytest.approx(first_summary["net_return"])


def test_net_profitability_runner_is_reproducible_for_same_config_and_inputs() -> None:
    config = NetProfitabilityRunnerConfig(top_k=2, random_seed=7)

    first = run_net_profitability_evidence_v1_1(_records(), config=config)
    second = run_net_profitability_evidence_v1_1(list(reversed(_records())), config=config)

    assert first["v1_1_net_profitability_evidence_runner"]["run_id"] == second["v1_1_net_profitability_evidence_runner"]["run_id"]
    assert first["v1_1_top_k_profitability_report"] == second["v1_1_top_k_profitability_report"]


def test_net_profitability_run_id_changes_when_per_record_cost_changes() -> None:
    base_records = _records()
    changed_records = _records()
    changed_records[0]["cost_rate"] = 0.02

    base = run_net_profitability_evidence_v1_1(base_records)
    changed = run_net_profitability_evidence_v1_1(changed_records)

    assert base["v1_1_net_profitability_evidence_runner"]["run_id"] != changed["v1_1_net_profitability_evidence_runner"]["run_id"]


def test_net_profitability_runner_rejects_missing_guardrail_status() -> None:
    records = _records()
    del records[0]["no_lookahead_check_status"]

    with pytest.raises(ValueError, match="no_lookahead_check_status"):
        run_net_profitability_evidence_v1_1(records)


def test_net_profitability_runner_rejects_missing_date_range() -> None:
    records = _records()
    records[0]["date_range"] = {"start": "unknown", "end": "2025-12-30"}

    with pytest.raises(ValueError, match="date_range"):
        run_net_profitability_evidence_v1_1(records)


def test_net_profitability_runner_rejects_guardrail_language_outside_notices() -> None:
    artifacts = run_net_profitability_evidence_v1_1(_records())
    artifacts["v1_1_top_k_profitability_report"]["candidate_summaries"][0]["bad_text"] = "future return"

    with pytest.raises(ValueError, match="prohibited language"):
        validate_net_profitability_artifacts_v1_1(artifacts)


def test_net_profitability_runner_rejects_hyphenated_guardrail_language() -> None:
    artifacts = run_net_profitability_evidence_v1_1(_records())
    artifacts["v1_1_cost_turnover_summary"]["bad_text"] = "proven-alpha"

    with pytest.raises(ValueError, match="prohibited language"):
        validate_net_profitability_artifacts_v1_1(artifacts)


def test_net_profitability_runner_keeps_blocked_flags_false() -> None:
    artifacts = run_net_profitability_evidence_v1_1(_records())
    validation = artifacts["v1_1_validation_manifest"]

    assert validation["live_execution_enabled"] is False
    assert validation["order_generation_enabled"] is False
    assert validation["production_ranking_update_enabled"] is False


def test_net_profitability_runner_fixture_artifacts_are_json_serializable() -> None:
    artifacts = run_net_profitability_evidence_v1_1(_records())

    text = json.dumps(artifacts, sort_keys=True)
    assert "v1_1_net_profitability_evidence_runner" in text
    assert "EvaluationEvidenceV1" not in text or "future return" not in text.lower()
