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
)
from Quant_mvp.backtest_mvp.revision_layer_v1_4 import (  # noqa: E402
    REVISION_FEATURE_ALLOWLIST,
    RevisionLayerConfig,
    run_v1_4_revision_layer,
    validate_v1_4_revision_artifacts,
)


def _records() -> list[dict[str, object]]:
    return [
        {
            "candidate_id": "sc_v1_4_revision_supported",
            "selector_score": 88.0,
            "gross_return": 0.12,
            "benchmark_return": 0.04,
            "turnover": 0.35,
            "volatility": 0.11,
            "max_drawdown": -0.05,
            "coverage_ratio": 0.96,
            "date_range": {"start": "2025-01-02", "end": "2025-03-31"},
            "leakage_check_status": "pass",
            "no_lookahead_check_status": "pass",
        },
        {
            "candidate_id": "sc_v1_4_revision_missing",
            "selector_score": 61.0,
            "gross_return": 0.07,
            "benchmark_return": 0.04,
            "turnover": 0.70,
            "volatility": 0.09,
            "max_drawdown": -0.04,
            "coverage_ratio": 0.88,
            "date_range": {"start": "2025-01-02", "end": "2025-03-31"},
            "leakage_check_status": "pass",
            "no_lookahead_check_status": "pass",
        },
    ]


def _evidences() -> list[dict[str, object]]:
    artifacts = run_net_profitability_evidence_v1_1(
        _records(),
        config=NetProfitabilityRunnerConfig(top_k=2, cost_rate=0.003, slippage_rate=0.001),
    )
    return artifacts["evaluation_evidence_v1"]


def _revision_records() -> list[dict[str, object]]:
    evidences = {evidence["candidate_id"]: evidence for evidence in _evidences()}
    return [
        {
            "candidate_id": "sc_v1_4_revision_supported",
            "evidence_id": evidences["sc_v1_4_revision_supported"]["evidence_id"],
            "revision_source_ref": "approved_local_revision_snapshot_20250330_window_3m",
            "estimate_as_of_date": "2025-03-30",
            "available_at": "2025-03-30",
            "fiscal_period": "FY2025",
            "sector_id": "technology",
            "eps_estimate_current": 110.0,
            "eps_estimate_1m_ago": 100.0,
            "eps_estimate_3m_ago": 95.0,
            "analyst_revision_up_count_1m": 7,
            "analyst_revision_down_count_1m": 3,
            "sector_revision_percentile": 0.82,
        }
    ]


def test_v1_4_revision_layer_builds_fail_closed_skeleton_without_data() -> None:
    artifacts = run_v1_4_revision_layer(_evidences())

    validate_v1_4_revision_artifacts(artifacts)
    assert artifacts["v1_4_revision_coverage_report"]["coverage_status"] == "insufficient"
    assert artifacts["v1_4_revision_feature_manifest"]["row_count"] == 0
    assert artifacts["v1_4_revision_layer_registry_entry"]["layer_status"] == "diagnostic_only"
    assert artifacts["v1_4_incremental_revision_evidence_report"]["comparison_status"] == "skipped"
    assert "revision_record_missing" in artifacts["v1_4_revision_coverage_report"]["coverage_gap_summary"]


def test_v1_4_revision_layer_accepts_only_pit_available_revision_rows() -> None:
    artifacts = run_v1_4_revision_layer(
        _evidences(),
        revision_records=_revision_records(),
        config=RevisionLayerConfig(min_candidate_coverage_ratio=0.5),
    )

    rows = {
        row["candidate_id"]: row
        for row in artifacts["v1_4_revision_coverage_report"]["candidate_revision_rows"]
    }
    assert rows["sc_v1_4_revision_supported"]["pit_status"] == "pass"
    assert rows["sc_v1_4_revision_supported"]["eps_revision_change_1m"] == 0.1
    assert rows["sc_v1_4_revision_supported"]["eps_revision_change_3m"] == 0.15789474
    assert rows["sc_v1_4_revision_supported"]["revision_diffusion_1m"] == 0.4
    assert rows["sc_v1_4_revision_missing"]["pit_status"] == "missing"
    assert artifacts["v1_4_revision_layer_registry_entry"]["layer_status"] == "candidate_only"


def test_v1_4_revision_layer_marks_post_evaluation_revision_as_fail() -> None:
    records = _revision_records()
    records[0]["available_at"] = "2025-04-01"

    artifacts = run_v1_4_revision_layer(_evidences(), revision_records=records)
    rows = {
        row["candidate_id"]: row
        for row in artifacts["v1_4_revision_coverage_report"]["candidate_revision_rows"]
    }

    assert rows["sc_v1_4_revision_supported"]["pit_status"] == "fail"
    assert "revision_available_after_evaluation_end" in rows["sc_v1_4_revision_supported"]["reason_codes"]
    assert artifacts["v1_4_revision_feature_manifest"]["row_count"] == 0


def test_v1_4_revision_feature_manifest_uses_allowlist_only() -> None:
    artifacts = run_v1_4_revision_layer(
        _evidences(),
        revision_records=_revision_records(),
        config=RevisionLayerConfig(min_candidate_coverage_ratio=0.5),
    )

    manifest = artifacts["v1_4_revision_feature_manifest"]
    assert tuple(manifest["feature_allowlist"]) == REVISION_FEATURE_ALLOWLIST
    feature_names = set(manifest["rows"][0]["features"])
    assert feature_names == set(REVISION_FEATURE_ALLOWLIST)
    assert manifest["label_separation_status"] == "revision_features_do_not_include_label_or_return_fields"


def test_v1_4_revision_artifacts_reject_prohibited_language() -> None:
    artifacts = run_v1_4_revision_layer(_evidences())
    artifacts["v1_4_revision_manual_review_section"]["bad_text"] = "production ranking replacement"

    with pytest.raises(ValueError, match="prohibited language"):
        validate_v1_4_revision_artifacts(artifacts)


def test_v1_4_revision_artifacts_are_json_serializable() -> None:
    artifacts = run_v1_4_revision_layer(_evidences(), revision_records=_revision_records())

    text = json.dumps(artifacts, sort_keys=True)
    assert "v1_4_revision_data_contract" in text
    assert "valuation_fundamental_active_scoring_enabled" in text
