from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.walk_forward_dataset_v1_6 import (  # noqa: E402
    build_v1_6_walk_forward_backtest_dataset,
)


def test_v1_6_walk_forward_dataset_merges_fold_evidence_and_review_status(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    review_dir = tmp_path / "review_priority"
    output_dir = tmp_path / "walk_forward"
    evidence_root.mkdir()
    review_dir.mkdir()
    _write_evidence_doc(evidence_root / "candidate_a.md", candidate_id="C1")
    _write_csv(
        review_dir / "v1_6_composite_review_priority_manifest_latest.csv",
        [
            {
                "candidate_id": "C1",
                "ticker": "005930",
                "manual_review_priority": "review_preferred",
                "confidence_score": "0.800000",
                "confidence_support_status": "diagnostic_ready",
                "horizon_stability_status": "stable_across_horizons",
                "split_stability_status": "stable_across_splits",
                "redundancy_status_summary": "no_redundant_layer_warning",
            },
            {
                "candidate_id": "C2",
                "ticker": "000660",
                "manual_review_priority": "blocked_manual_review",
                "confidence_score": "0.200000",
                "confidence_support_status": "insufficient_data",
                "horizon_stability_status": "insufficient_horizon_coverage",
                "split_stability_status": "insufficient_split_or_seed_coverage",
                "redundancy_status_summary": "insufficient_data",
            },
        ],
    )
    _write_csv(
        review_dir / "v1_6_confidence_score_manifest_latest.csv",
        [
            {
                "candidate_id": "C1",
                "ticker": "005930",
                "confidence_score": "0.800000",
                "confidence_support_status": "diagnostic_ready",
            },
            {
                "candidate_id": "C2",
                "ticker": "000660",
                "confidence_score": "0.200000",
                "confidence_support_status": "insufficient_data",
            },
        ],
    )
    (review_dir / "v1_6_v2_0_readiness_packet_latest.json").write_text(
        json.dumps(
            {
                "readiness_verdict": "V2_0_LIMITED_REVIEW_PACKET_READY_NOT_FULL_READY",
                "missing_dependencies": ["insufficient_layer_redundancy_evidence"],
            }
        ),
        encoding="utf-8",
    )

    manifest = build_v1_6_walk_forward_backtest_dataset(
        evidence_roots=(evidence_root,),
        v1_6_review_dir=review_dir,
        output_dir=output_dir,
    )

    rows = _read_csv(output_dir / "v1_6_walk_forward_backtest_input_latest.csv")
    assert manifest["walk_forward_fold_row_count"] == 2
    assert manifest["v1_6_candidates_without_walk_forward_folds"] == ["C2"]
    fold_rows = [row for row in rows if row["row_kind"] == "walk_forward_fold"]
    missing_rows = [row for row in rows if row["row_kind"] == "v1_6_candidate_without_walk_forward_folds"]
    assert {row["fold_index"] for row in fold_rows} == {"1", "2"}
    assert {row["backtest_input_status"] for row in fold_rows} == {"walk_forward_fold_ready"}
    assert fold_rows[0]["v1_6_candidate_match_status"] == "matched_v1_6_review_priority"
    assert fold_rows[0]["v1_6_readiness_verdict"] == "V2_0_LIMITED_REVIEW_PACKET_READY_NOT_FULL_READY"
    assert missing_rows[0]["candidate_id"] == "C2"
    assert missing_rows[0]["backtest_input_status"] == "missing_walk_forward_evaluation_evidence"
    assert "order generation" in fold_rows[0]["prohibited_actions_notice"]


def _write_evidence_doc(path: Path, *, candidate_id: str) -> None:
    payload = {
        "candidate_id": candidate_id,
        "evaluation_id": "EE1",
        "evaluation_window": {"start": "2025-01-01", "end": "2025-03-01"},
        "metric_summary": {
            "annualized_return": 0.1,
            "benchmark_comparison": "recorded",
            "oos_stability_status": "recorded_walk_forward_pass",
            "total_return": 0.2,
        },
        "risk_metric_summary": {
            "annualized_volatility": 0.3,
            "coverage_ratio": 0.9,
            "max_drawdown": -0.1,
            "sharpe_ratio": 0.4,
            "turnover_proxy": 0.5,
        },
        "no_feedback_check": "active_boundary_check",
        "no_lookahead_check": "recorded_boundary_check",
        "production_boundary_check": "no_automatic_production_activation_claim",
        "known_limitations": ["candidate_only"],
        "walk_forward_stability_summary": {
            "aggregate_reference_return": 0.05,
            "aggregate_relative_return": 0.15,
            "aggregate_strategy_return": 0.20,
            "fold_count": 2,
            "folds": [
                {
                    "end": "2025-01-31",
                    "fold_index": 1,
                    "period_count": 10,
                    "reference_return": 0.01,
                    "reference_security_count": 20,
                    "relative_return": 0.03,
                    "relative_return_positive": True,
                    "start": "2025-01-01",
                    "strategy_return": 0.04,
                    "valid_security_count": 5,
                },
                {
                    "end": "2025-03-01",
                    "fold_index": 2,
                    "period_count": 10,
                    "reference_return": 0.04,
                    "reference_security_count": 20,
                    "relative_return": 0.12,
                    "relative_return_positive": True,
                    "start": "2025-02-01",
                    "strategy_return": 0.16,
                    "valid_security_count": 5,
                },
            ],
            "method": "chronological_fold_stability",
            "passing_fold_count": 2,
            "passing_fold_ratio": 1.0,
            "status": "recorded_walk_forward_pass",
        },
    }
    path.write_text("# Evidence\n\n```json\n" + json.dumps(payload) + "\n```\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
