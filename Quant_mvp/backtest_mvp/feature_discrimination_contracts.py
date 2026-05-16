"""Contracts for evidence-only feature discrimination audits.

The audit contracts describe whether candidate-level fields are suitable for
manual ML-input review. They do not train models, score candidates, update
rankings, or activate production behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


AUDIT_SCHEMA_VERSION = "feature_discrimination_audit_v1_0"
AUDIT_ROW_SCHEMA_VERSION = "feature_discrimination_audit_row_v1_0"
AUDIT_VERSION = "feature_discrimination_audit_contract_v1_0"

FEATURE_TYPE_NUMERIC = "numeric"
FEATURE_TYPE_STATUS = "status"
FEATURE_TYPE_CATEGORICAL = "categorical"
FEATURE_TYPE_DIAGNOSTIC_METADATA = "diagnostic_metadata"

SOURCE_TIMING_PRE_LABEL = "pre_label"
SOURCE_TIMING_AS_OF_LABEL = "as_of_label"
SOURCE_TIMING_POST_LABEL = "post_label"
SOURCE_TIMING_UNKNOWN = "unknown"

DECISION_KEEP = "keep"
DECISION_REVIEW = "review"
DECISION_EXCLUDE = "exclude"
DECISION_DIAGNOSTIC_ONLY = "diagnostic_only"

REASON_CONSTANT_FEATURE = "constant_feature"
REASON_HIGH_NULL_FEATURE = "high_null_feature"
REASON_STATUS_ONLY_DIAGNOSTIC = "status_only_diagnostic"
REASON_DIAGNOSTIC_METADATA_ONLY = "diagnostic_metadata_only"
REASON_NUMERIC_LABEL_SEPARATION_PRESENT = "numeric_label_separation_present"
REASON_NUMERIC_LABEL_SEPARATION_WEAK = "numeric_label_separation_weak"
REASON_NON_NUMERIC_REVIEW = "non_numeric_review_required"
REASON_POST_LABEL_LEAKAGE_RISK = "leakage_risk_post_label_source"
REASON_LABEL_DERIVED_NAME = "leakage_risk_label_derived_name"
REASON_INSUFFICIENT_LABELS = "insufficient_binary_labels"

LABEL_DERIVED_FEATURE_NAMES = frozenset(
    {
        "label",
        "target",
        "outcome",
        "label_review_preferred",
        "label_status",
        "label_reason_code",
        "label_decision",
        "label_null_reason",
        "label_pass_minimum_gate",
        "supervised_label_eligible",
        "adoption_review_eligible",
        "selector_score",
        "selector_rank",
        "actual_oos_stability",
        "prediction_value",
    }
)

MANIFEST_REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "audit_version",
        "allowed_use",
        "input_row_count",
        "labeled_row_count",
        "label_column",
        "feature_count",
        "decision_counts",
        "excluded_feature_count",
        "kept_feature_count",
        "diagnostic_only_feature_count",
        "review_feature_count",
        "thresholds",
        "rows",
        "no_feedback_check",
        "ml_training_changed",
        "selector_ranking_changed",
        "backtest_behavior_changed",
        "valuation_activation_changed",
        "data_ingestion_changed",
    }
)

ROW_REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "feature_name",
        "feature_type",
        "source_timing",
        "decision",
        "reason_codes",
        "row_count",
        "non_null_count",
        "null_count",
        "non_null_ratio",
        "unique_count",
        "label_positive_count",
        "label_negative_count",
        "positive_label_mean",
        "negative_label_mean",
        "label_mean_difference",
        "label_mean_abs_difference",
        "ml_input_allowed",
        "diagnostic_available",
    }
)


@dataclass(frozen=True)
class FeatureDiscriminationAuditConfig:
    """Thresholds for candidate-level feature discrimination review."""

    min_non_null_ratio: float = 0.75
    min_unique_values: int = 2
    min_label_mean_abs_difference: float = 0.10


def validate_feature_discrimination_manifest(manifest: Mapping[str, Any]) -> None:
    """Validate the compact manifest shape and hard-stop boundary flags."""

    missing = MANIFEST_REQUIRED_FIELDS - set(manifest)
    if missing:
        raise ValueError(f"feature discrimination manifest missing fields: {sorted(missing)}")
    if manifest.get("schema_version") != AUDIT_SCHEMA_VERSION:
        raise ValueError("unsupported feature discrimination manifest schema_version")
    rows = manifest.get("rows")
    if not isinstance(rows, list):
        raise ValueError("feature discrimination manifest rows must be a list")
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("feature discrimination row must be an object")
        missing_row = ROW_REQUIRED_FIELDS - set(row)
        if missing_row:
            raise ValueError(f"feature discrimination row missing fields: {sorted(missing_row)}")
        if row.get("schema_version") != AUDIT_ROW_SCHEMA_VERSION:
            raise ValueError("unsupported feature discrimination row schema_version")
        if row.get("decision") not in {
            DECISION_KEEP,
            DECISION_REVIEW,
            DECISION_EXCLUDE,
            DECISION_DIAGNOSTIC_ONLY,
        }:
            raise ValueError(f"unsupported feature audit decision: {row.get('decision')}")
        if not isinstance(row.get("reason_codes"), list) or not row["reason_codes"]:
            raise ValueError("feature discrimination row requires reason_codes")
    for flag in (
        "ml_training_changed",
        "selector_ranking_changed",
        "backtest_behavior_changed",
        "valuation_activation_changed",
        "data_ingestion_changed",
    ):
        if manifest.get(flag) is not False:
            raise ValueError(f"feature discrimination audit must keep {flag}=false")


__all__ = [
    "AUDIT_ROW_SCHEMA_VERSION",
    "AUDIT_SCHEMA_VERSION",
    "AUDIT_VERSION",
    "DECISION_DIAGNOSTIC_ONLY",
    "DECISION_EXCLUDE",
    "DECISION_KEEP",
    "DECISION_REVIEW",
    "FEATURE_TYPE_CATEGORICAL",
    "FEATURE_TYPE_DIAGNOSTIC_METADATA",
    "FEATURE_TYPE_NUMERIC",
    "FEATURE_TYPE_STATUS",
    "FeatureDiscriminationAuditConfig",
    "LABEL_DERIVED_FEATURE_NAMES",
    "REASON_CONSTANT_FEATURE",
    "REASON_DIAGNOSTIC_METADATA_ONLY",
    "REASON_HIGH_NULL_FEATURE",
    "REASON_INSUFFICIENT_LABELS",
    "REASON_LABEL_DERIVED_NAME",
    "REASON_NON_NUMERIC_REVIEW",
    "REASON_NUMERIC_LABEL_SEPARATION_PRESENT",
    "REASON_NUMERIC_LABEL_SEPARATION_WEAK",
    "REASON_POST_LABEL_LEAKAGE_RISK",
    "REASON_STATUS_ONLY_DIAGNOSTIC",
    "SOURCE_TIMING_AS_OF_LABEL",
    "SOURCE_TIMING_POST_LABEL",
    "SOURCE_TIMING_PRE_LABEL",
    "SOURCE_TIMING_UNKNOWN",
    "validate_feature_discrimination_manifest",
]
