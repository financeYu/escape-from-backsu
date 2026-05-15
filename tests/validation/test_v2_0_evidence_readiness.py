from __future__ import annotations

import json

import pandas as pd

from src.validation.v2_0_evidence_readiness import (
    NOT_READY,
    READY_FOR_LIMITED_SELECTOR_REVIEW,
    READY_WITH_LIMITATIONS,
    build_readiness_gap_report,
    validate_readiness_rows,
    write_readiness_gap_report,
)


def _base_row(**overrides):
    row = {
        "candidate_id": "strategy_candidate_001",
        "ticker": "005930",
        "evaluation_date": "2026-05-15",
        "strategy_candidate_ref": "docs/extension/v0_3/adoption_candidates/strategy_candidate_001.md",
        "evaluation_evidence_ref": "Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/001.md",
        "adoption_candidate_ref": "docs/extension/v0_3/adoption_candidates/adoption_001.md",
        "pit_status": "pass",
        "lineage_status": "pass",
        "coverage_status": "pass",
        "feature_label_separation_status": "pass",
        "leakage_check_status": "pass",
        "no_lookahead_check_status": "pass",
        "cost_liquidity_status": "pass",
        "robustness_status": "pass",
        "manual_review_priority_status": "pass",
        "source_artifact": "v1_6_composite_review_priority_manifest_latest.csv",
        "lineage_ref": "v1.1->v1.2->v1.3->v1.4->v1.5->v1.6",
        "manual_review_only": True,
        "feature_columns": "coverage,data_quality,stability",
        "label_columns": "review_bucket",
        "notes": "evidence-only manual review support",
    }
    row.update(overrides)
    return row


def test_v2_0_readiness_passes_clean_evidence_rows():
    report = build_readiness_gap_report([_base_row()])

    assert report["readiness_verdict"] == READY_FOR_LIMITED_SELECTOR_REVIEW
    assert report["manual_review_only"] is True
    assert report["valuation_fundamental_scoring_activation_allowed"] is False
    assert report["production_activation_allowed"] is False
    assert report["summary"]["pass_count"] == 1
    assert validate_readiness_rows([_base_row()]) is True


def test_v2_0_readiness_warns_on_limited_but_present_evidence():
    report = build_readiness_gap_report(
        [
            _base_row(
                coverage_status="partial_diagnostic_ready",
                robustness_status="warn",
                cost_liquidity_status="diagnostic_ready",
            )
        ]
    )

    assert report["readiness_verdict"] == READY_WITH_LIMITATIONS
    row = report["candidate_rows"][0]
    assert row["readiness_status"] == "warn"
    assert "limited_coverage_status:partial_diagnostic_ready" in row["warnings"]
    assert "limited_robustness_status:warn" in row["warnings"]


def test_v2_0_readiness_blocks_missing_pit_lineage_and_coverage():
    report = build_readiness_gap_report(
        [
            _base_row(
                pit_status="",
                lineage_ref="",
                coverage_status="missing_artifact",
            )
        ]
    )

    assert report["readiness_verdict"] == NOT_READY
    row = report["candidate_rows"][0]
    assert row["readiness_status"] == "block"
    assert "missing_required_value:lineage_ref" in row["blockers"]
    assert "missing_status:pit_status" in row["blockers"]
    assert "blocked_coverage_status:missing_artifact" in row["blockers"]


def test_v2_0_readiness_blocks_forbidden_columns_and_language():
    frame = pd.DataFrame(
        [
            {
                **_base_row(notes="contains trading recommendation language"),
                "valuation_score": 0.7,
            }
        ]
    )

    report = build_readiness_gap_report(frame)

    assert report["readiness_verdict"] == NOT_READY
    assert "forbidden_column:valuation_score" in report["global_blockers"]
    assert "forbidden_language:trading recommendation" in report["global_blockers"]


def test_v2_0_readiness_blocks_feature_label_overlap_and_metric_features():
    report = build_readiness_gap_report(
        [
            _base_row(
                feature_columns="coverage,net_return,review_bucket",
                label_columns="review_bucket",
            )
        ]
    )

    row = report["candidate_rows"][0]
    assert report["readiness_verdict"] == NOT_READY
    assert row["readiness_status"] == "block"
    assert "feature_label_overlap:review_bucket" in row["blockers"]
    assert "forbidden_feature_column:net_return" in row["blockers"]


def test_v2_0_readiness_writer_creates_json_report(tmp_path):
    output = tmp_path / "v2_0_evidence_readiness_gap_report_latest.json"

    report = write_readiness_gap_report([_base_row()], output)

    assert output.exists()
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["report_version"] == report["report_version"]
    assert written["readiness_verdict"] == READY_FOR_LIMITED_SELECTOR_REVIEW
