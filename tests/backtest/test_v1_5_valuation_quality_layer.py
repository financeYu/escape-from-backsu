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
from Quant_mvp.backtest_mvp.valuation_quality_layer_v1_5 import (  # noqa: E402
    ValuationQualityLayerConfig,
    run_v1_5_valuation_quality_layer,
    validate_v1_5_valuation_quality_artifacts,
)
from src.validation.layer_registry import load_layer_registry  # noqa: E402


def _records() -> list[dict[str, object]]:
    return [
        {
            "candidate_id": "sc_v1_5_supported",
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
            "candidate_id": "sc_v1_5_peer",
            "selector_score": 74.0,
            "gross_return": 0.09,
            "benchmark_return": 0.04,
            "turnover": 0.42,
            "volatility": 0.10,
            "max_drawdown": -0.06,
            "coverage_ratio": 0.94,
            "date_range": {"start": "2025-01-02", "end": "2025-03-31"},
            "leakage_check_status": "pass",
            "no_lookahead_check_status": "pass",
        },
        {
            "candidate_id": "sc_v1_5_missing",
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
        config=NetProfitabilityRunnerConfig(top_k=3, cost_rate=0.003, slippage_rate=0.001),
    )
    return artifacts["evaluation_evidence_v1"]


def _fundamental_record(candidate_id: str, field_name: str, value: float, **overrides: object) -> dict[str, object]:
    evidences = {evidence["candidate_id"]: evidence for evidence in _evidences()}
    record: dict[str, object] = {
        "candidate_id": candidate_id,
        "evidence_id": evidences[candidate_id]["evidence_id"],
        "ticker": "005930" if candidate_id != "sc_v1_5_peer" else "000660",
        "evaluation_date": "2025-03-31",
        "fiscal_period": "FY2024",
        "report_period_end_date": "2024-12-31",
        "filing_date": "2025-03-10",
        "availability_date": "2025-03-15",
        "source_ref": f"fixture_pit_fundamental_{candidate_id}_{field_name}",
        "field_name": field_name,
        "value": value,
        "unit": "ratio",
        "currency": "KRW",
        "sector_id": "technology",
        "industry_id": "semiconductors",
        "reporting_lag_policy": "within_v1_5_policy",
        "stale_data_policy": "within_v1_5_policy",
        "restatement_policy": "no_later_restatement_used",
        "data_quality_flags": ("fixture", "candidate_only"),
    }
    record.update(overrides)
    return record


def _fundamentals() -> list[dict[str, object]]:
    return [
        _fundamental_record("sc_v1_5_supported", "price_to_book", 1.25),
        _fundamental_record("sc_v1_5_supported", "price_to_earnings", 9.5),
        _fundamental_record("sc_v1_5_supported", "roe", 0.13),
        _fundamental_record("sc_v1_5_supported", "asset_growth", 0.04),
        _fundamental_record("sc_v1_5_peer", "price_to_book", 1.50),
        _fundamental_record("sc_v1_5_peer", "price_to_earnings", 11.0),
        _fundamental_record("sc_v1_5_peer", "roe", 0.10),
        _fundamental_record("sc_v1_5_peer", "asset_growth", 0.02),
    ]


def test_v1_5_layer_builds_pending_data_artifacts_without_fundamentals() -> None:
    artifacts = run_v1_5_valuation_quality_layer(_evidences())

    validate_v1_5_valuation_quality_artifacts(artifacts)
    assert artifacts["v1_5_pit_validation_report"]["coverage_status"] == "pending_data"
    assert artifacts["v1_5_valuation_feature_manifest"]["row_count"] == 0
    assert artifacts["v1_5_layer_registry_entry"]["layer_status"] == "diagnostic_only"
    assert artifacts["v1_5_incremental_valuation_evidence_report"]["comparison_status"] == "pending_data"
    assert artifacts["v1_5_completion_report"]["completion_verdict"] == "LIMITED COMPLETE"
    assert "fundamental_record_missing" in artifacts["v1_5_pit_validation_report"]["coverage_gap_summary"]
    assert artifacts["v1_5_completion_report"]["minimum_data_handoff_request"]


def test_v1_5_pit_fundamentals_emit_valuation_quality_and_investment_features() -> None:
    artifacts = run_v1_5_valuation_quality_layer(
        _evidences(),
        fundamental_records=_fundamentals(),
        config=ValuationQualityLayerConfig(min_candidate_coverage_ratio=0.5),
    )

    valuation_rows = {
        row["candidate_id"]: row
        for row in artifacts["v1_5_valuation_feature_manifest"]["rows"]
    }
    quality_rows = {
        row["candidate_id"]: row
        for row in artifacts["v1_5_quality_profitability_feature_manifest"]["rows"]
    }
    investment_rows = {
        row["candidate_id"]: row
        for row in artifacts["v1_5_investment_feature_manifest"]["rows"]
    }

    assert valuation_rows["sc_v1_5_supported"]["raw_features"]["price_to_book"] == 1.25
    assert valuation_rows["sc_v1_5_supported"]["raw_features"]["book_to_price"] == 0.8
    assert valuation_rows["sc_v1_5_supported"]["raw_features"]["earnings_to_price"] == 0.10526316
    assert quality_rows["sc_v1_5_supported"]["raw_features"]["roe"] == 0.13
    assert investment_rows["sc_v1_5_supported"]["raw_features"]["asset_growth"] == 0.04
    assert artifacts["v1_5_layer_registry_entry"]["layer_status"] == "candidate_only"


def test_v1_5_missing_availability_metadata_is_pending_data() -> None:
    records = _fundamentals()
    records[0].pop("availability_date")

    artifacts = run_v1_5_valuation_quality_layer(_evidences(), fundamental_records=records)
    rows = artifacts["v1_5_pit_validation_report"]["candidate_fundamental_rows"]
    pending = [row for row in rows if row["field_name"] == "price_to_book" and row["candidate_id"] == "sc_v1_5_supported"]

    assert pending[0]["pit_status"] == "pending_data"
    assert "availability_date_missing" in pending[0]["reason_codes"]
    assert pending[0]["coverage_status"] == "pending_data"


def test_v1_5_future_available_and_restated_rows_are_excluded() -> None:
    records = [
        _fundamental_record("sc_v1_5_supported", "price_to_book", 1.25, availability_date="2025-04-01"),
        _fundamental_record(
            "sc_v1_5_peer",
            "price_to_book",
            1.50,
            restatement_policy="restated_after_evaluation",
        ),
    ]

    artifacts = run_v1_5_valuation_quality_layer(_evidences(), fundamental_records=records)
    reasons = {
        reason
        for row in artifacts["v1_5_pit_validation_report"]["candidate_fundamental_rows"]
        for reason in row["reason_codes"]
    }

    assert "fundamental_available_after_evaluation_date" in reasons
    assert "restatement_policy_unverified" in reasons
    assert {
        row["pit_status"]
        for row in artifacts["v1_5_pit_validation_report"]["candidate_fundamental_rows"]
    } == {"pending_data"}
    assert artifacts["v1_5_valuation_feature_manifest"]["row_count"] == 0


def test_v1_5_stale_fundamental_rows_are_not_used_as_features() -> None:
    records = [
        _fundamental_record(
            "sc_v1_5_supported",
            "price_to_book",
            1.25,
            filing_date="2023-01-01",
            availability_date="2023-01-15",
        )
    ]

    artifacts = run_v1_5_valuation_quality_layer(_evidences(), fundamental_records=records)

    row = [
        item
        for item in artifacts["v1_5_pit_validation_report"]["candidate_fundamental_rows"]
        if item["candidate_id"] == "sc_v1_5_supported" and item["field_name"] == "price_to_book"
    ][0]
    assert row["pit_status"] == "pending_data"
    assert "stale_data_policy_violation" in row["reason_codes"]
    assert artifacts["v1_5_valuation_feature_manifest"]["row_count"] == 0


def test_v1_5_non_numeric_fundamental_value_is_pending_data() -> None:
    record = _fundamental_record("sc_v1_5_supported", "price_to_book", 1.25)
    record["value"] = "not_numeric"

    artifacts = run_v1_5_valuation_quality_layer(_evidences(), fundamental_records=[record])

    row = [
        item
        for item in artifacts["v1_5_pit_validation_report"]["candidate_fundamental_rows"]
        if item["candidate_id"] == "sc_v1_5_supported" and item["field_name"] == "price_to_book"
    ][0]
    assert row["pit_status"] == "pending_data"
    assert row["coverage_status"] == "pending_data"
    assert "value_not_numeric" in row["reason_codes"]
    assert artifacts["v1_5_valuation_feature_manifest"]["row_count"] == 0


def test_v1_5_sector_relative_report_keeps_raw_and_adjusted_values_separate() -> None:
    artifacts = run_v1_5_valuation_quality_layer(
        _evidences(),
        fundamental_records=_fundamentals(),
        config=ValuationQualityLayerConfig(min_candidate_coverage_ratio=0.5, min_sector_peer_count=2),
    )

    report = artifacts["v1_5_sector_relative_valuation_report"]
    pb_rows = [
        row for row in report["sector_relative_rows"] if row["feature_name"] == "price_to_book"
    ]

    assert report["raw_and_adjusted_separation_status"] == "raw_values_and_sector_adjusted_values_are_separate"
    assert {row["sector_relative_status"] for row in pb_rows} == {"available"}
    supported_pb = [row for row in pb_rows if row["candidate_id"] == "sc_v1_5_supported"][0]
    assert supported_pb["raw_value"] == 1.25
    assert supported_pb["sector_adjusted_value"] == -0.125
    assert supported_pb["peer_count"] == 2


def test_v1_5_sector_relative_report_marks_insufficient_peer_count() -> None:
    artifacts = run_v1_5_valuation_quality_layer(
        _evidences(),
        fundamental_records=[_fundamental_record("sc_v1_5_supported", "price_to_book", 1.25)],
        config=ValuationQualityLayerConfig(min_candidate_coverage_ratio=0.1, min_sector_peer_count=2),
    )

    report = artifacts["v1_5_sector_relative_valuation_report"]
    assert report["pending_sector_data_count"] > 0
    assert report["sector_relative_rows"][0]["sector_relative_status"] == "pending_data"


def test_v1_5_manual_review_section_summarizes_limits_and_checks() -> None:
    artifacts = run_v1_5_valuation_quality_layer(_evidences(), fundamental_records=_fundamentals())
    section = artifacts["v1_5_manual_review_valuation_section"]

    assert section["manual_review_required"] is True
    assert section["valuation_layer_status"] in {"candidate_only", "diagnostic_only"}
    assert section["pit_validation_status"] == "pending_data"
    assert "confirm_source_ref_and_availability_date_before_interpreting_fundamentals" in section["required_human_checks"]
    assert section["incremental_evidence_summary"]["comparison_status"] == "pending_data"


def test_v1_5_layer_registry_config_contains_diagnostic_only_entry() -> None:
    registry = load_layer_registry()
    layer = registry.by_id["v1_5_valuation_quality_profitability_layer"]

    assert layer.layer_category == "valuation"
    assert layer.layer_status == "diagnostic_only"
    assert layer.valuation_fundamental_active_scoring_enabled is False
    assert layer.ranking_role == "none"


def test_v1_5_artifacts_reject_prohibited_language() -> None:
    artifacts = run_v1_5_valuation_quality_layer(_evidences())
    artifacts["v1_5_manual_review_valuation_section"]["bad_text"] = "production ranking replacement"

    with pytest.raises(ValueError, match="prohibited language"):
        validate_v1_5_valuation_quality_artifacts(artifacts)


def test_v1_5_artifacts_are_json_serializable() -> None:
    artifacts = run_v1_5_valuation_quality_layer(_evidences(), fundamental_records=_fundamentals())

    text = json.dumps(artifacts, sort_keys=True)
    assert "v1_5_fundamental_data_contract" in text
    assert "valuation_fundamental_active_scoring_enabled" in text
