from __future__ import annotations

import json
from pathlib import Path

import pytest

from Quant_mvp.backtest_mvp.feature_discrimination_audit import audit_feature_discrimination
from Quant_mvp.backtest_mvp.feature_discrimination_contracts import (
    DECISION_DIAGNOSTIC_ONLY,
    DECISION_EXCLUDE,
    DECISION_KEEP,
    DECISION_REVIEW,
    FEATURE_TYPE_NUMERIC,
    FEATURE_TYPE_STATUS,
    REASON_CONSTANT_FEATURE,
    REASON_HIGH_NULL_FEATURE,
    REASON_NUMERIC_LABEL_SEPARATION_PRESENT,
    REASON_NUMERIC_LABEL_SEPARATION_WEAK,
    REASON_POST_LABEL_LEAKAGE_RISK,
    REASON_STATUS_ONLY_DIAGNOSTIC,
    SOURCE_TIMING_POST_LABEL,
    SOURCE_TIMING_PRE_LABEL,
    FeatureDiscriminationAuditConfig,
    validate_feature_discrimination_manifest,
)


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "feature_discrimination_candidates.jsonl"


def _rows() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in FIXTURE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _feature_specs() -> list[dict[str, object]]:
    return [
        {
            "feature_name": "constant_ready_score",
            "feature_type": FEATURE_TYPE_NUMERIC,
            "source_timing": SOURCE_TIMING_PRE_LABEL,
        },
        {
            "feature_name": "sparse_numeric",
            "feature_type": FEATURE_TYPE_NUMERIC,
            "source_timing": SOURCE_TIMING_PRE_LABEL,
        },
        {
            "feature_name": "readiness_status",
            "feature_type": FEATURE_TYPE_STATUS,
            "source_timing": SOURCE_TIMING_PRE_LABEL,
        },
        {
            "feature_name": "discriminating_quality",
            "feature_type": FEATURE_TYPE_NUMERIC,
            "source_timing": SOURCE_TIMING_PRE_LABEL,
        },
        {
            "feature_name": "weak_numeric",
            "feature_type": FEATURE_TYPE_NUMERIC,
            "source_timing": SOURCE_TIMING_PRE_LABEL,
        },
        {
            "feature_name": "post_label_metric",
            "feature_type": FEATURE_TYPE_NUMERIC,
            "source_timing": SOURCE_TIMING_POST_LABEL,
        },
    ]


def _audit() -> dict[str, object]:
    return audit_feature_discrimination(
        _rows(),
        _feature_specs(),
        config=FeatureDiscriminationAuditConfig(
            min_non_null_ratio=0.75,
            min_unique_values=2,
            min_label_mean_abs_difference=0.10,
        ),
    )


def _by_name(manifest: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(row["feature_name"]): row for row in manifest["rows"]}  # type: ignore[index]


def test_constant_feature_exclusion() -> None:
    row = _by_name(_audit())["constant_ready_score"]

    assert row["decision"] == DECISION_EXCLUDE
    assert REASON_CONSTANT_FEATURE in row["reason_codes"]
    assert row["unique_count"] == 1
    assert row["ml_input_allowed"] is False


def test_high_null_feature_exclusion() -> None:
    row = _by_name(_audit())["sparse_numeric"]

    assert row["decision"] == DECISION_EXCLUDE
    assert REASON_HIGH_NULL_FEATURE in row["reason_codes"]
    assert row["non_null_count"] == 2
    assert row["null_count"] == 4
    assert row["non_null_ratio"] < 0.75


def test_status_only_feature_is_diagnostic_only() -> None:
    row = _by_name(_audit())["readiness_status"]

    assert row["decision"] == DECISION_DIAGNOSTIC_ONLY
    assert REASON_STATUS_ONLY_DIAGNOSTIC in row["reason_codes"]
    assert row["diagnostic_available"] is True
    assert row["ml_input_allowed"] is False


def test_numeric_feature_keep_and_review_decisions() -> None:
    rows = _by_name(_audit())

    kept = rows["discriminating_quality"]
    reviewed = rows["weak_numeric"]
    assert kept["decision"] == DECISION_KEEP
    assert REASON_NUMERIC_LABEL_SEPARATION_PRESENT in kept["reason_codes"]
    assert kept["ml_input_allowed"] is True
    assert reviewed["decision"] == DECISION_REVIEW
    assert REASON_NUMERIC_LABEL_SEPARATION_WEAK in reviewed["reason_codes"]
    assert reviewed["ml_input_allowed"] is False


def test_label_mean_difference_calculation() -> None:
    row = _by_name(_audit())["discriminating_quality"]

    assert row["label_positive_count"] == 3
    assert row["label_negative_count"] == 3
    assert row["positive_label_mean"] == pytest.approx(0.9)
    assert row["negative_label_mean"] == pytest.approx(0.2)
    assert row["label_mean_difference"] == pytest.approx(0.7)
    assert row["label_mean_abs_difference"] == pytest.approx(0.7)


def test_leakage_risk_feature_exclusion_if_source_timing_is_post_label() -> None:
    row = _by_name(_audit())["post_label_metric"]

    assert row["decision"] == DECISION_EXCLUDE
    assert REASON_POST_LABEL_LEAKAGE_RISK in row["reason_codes"]
    assert row["ml_input_allowed"] is False
    assert row["diagnostic_available"] is True


def test_manifest_report_shape() -> None:
    manifest = _audit()

    validate_feature_discrimination_manifest(manifest)
    assert manifest["schema_version"] == "feature_discrimination_audit_v1_0"
    assert manifest["allowed_use"] == "manual ML input review only"
    assert manifest["input_row_count"] == 6
    assert manifest["labeled_row_count"] == 6
    assert manifest["feature_count"] == 6
    assert manifest["kept_feature_count"] == 1
    assert manifest["review_feature_count"] == 1
    assert manifest["diagnostic_only_feature_count"] == 1
    assert manifest["excluded_feature_count"] == 3
    assert manifest["ml_training_changed"] is False
    assert manifest["selector_ranking_changed"] is False
    assert manifest["backtest_behavior_changed"] is False
    assert manifest["valuation_activation_changed"] is False
    assert manifest["data_ingestion_changed"] is False
