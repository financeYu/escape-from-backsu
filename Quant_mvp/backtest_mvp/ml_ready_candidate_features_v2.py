"""Build filtered ML-ready candidate feature rows from discrimination audits.

The v2 matrix keeps only audit-approved numeric features in model input
columns. Labels and diagnostic metadata remain separated for review and
trainability checks; this module does not train, score, rank, or change
backtest behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping, Sequence

from Quant_mvp.backtest_mvp.feature_discrimination_contracts import (
    DECISION_KEEP,
    FEATURE_TYPE_STATUS,
    REASON_POST_LABEL_LEAKAGE_RISK,
    SOURCE_TIMING_POST_LABEL,
    validate_feature_discrimination_manifest,
)


FEATURE_SET_VERSION = "ml_ready_candidate_features_v2"
MATRIX_SCHEMA_VERSION = "ml_ready_candidate_features_v2_row_v1_0"
MANIFEST_SCHEMA_VERSION = "ml_ready_candidate_features_v2_manifest_v1_0"
DEFAULT_CREATED_AT = "2026-05-16T00:00:00+00:00"

TRAINABILITY_ML_READY = "ml_ready"
TRAINABILITY_BLOCKED_MISSING_LABEL_MANIFEST = "blocked_missing_label_manifest"
TRAINABILITY_BLOCKED_MISSING_LABELS = "blocked_missing_labels"
TRAINABILITY_BLOCKED_MISSING_LINEAGE = "blocked_missing_lineage"
TRAINABILITY_REVIEW_ONLY_MISSING_LINEAGE = "review_only_missing_lineage"
TRAINABILITY_BLOCKED_NO_INCLUDED_FEATURES = "blocked_no_included_features"
TRAINABILITY_BLOCKED_INSUFFICIENT_COVERAGE = "blocked_insufficient_candidate_label_coverage"
BASELINE_TRAINABILITY_REPORT_VERSION = "baseline_selector_trainability_v2_report_v1_0"
BASELINE_TRAINABLE = "trainable"
BASELINE_BLOCKED_INSUFFICIENT_FEATURES = "blocked_by_insufficient_features"
BASELINE_BLOCKED_INSUFFICIENT_LABELS = "blocked_by_insufficient_labels"
BASELINE_BLOCKED_LEAKAGE_RISK = "blocked_by_leakage_risk"
BASELINE_BLOCKED_LINEAGE_GAP = "blocked_by_lineage_gap"
BASELINE_REVIEW_ONLY = "review_only"

REASON_NOT_AUDIT_KEEP = "audit_decision_not_keep"
REASON_AUDIT_ML_INPUT_NOT_ALLOWED = "audit_ml_input_not_allowed"
REASON_STATUS_DIAGNOSTIC_ONLY = "status_or_readiness_diagnostic_only"
REASON_MISSING_FEATURE_LINEAGE = "missing_feature_lineage"
REASON_SOURCE_TIMING_POST_LABEL = "source_timing_post_label"

FALSE_BOUNDARY_FLAGS = (
    "ml_training_performed",
    "selector_ranking_changed",
    "backtest_behavior_changed",
    "valuation_activation_changed",
    "data_ingestion_changed",
)


@dataclass(frozen=True)
class MLReadyCandidateFeaturesV2Config:
    """Trainability gates for the filtered v2 feature matrix."""

    min_candidate_count: int = 4
    min_positive_labels: int = 2
    min_negative_labels: int = 2


@dataclass(frozen=True)
class BaselineSelectorTrainabilityV2Config:
    """Gates for baseline selector training eligibility review."""

    min_candidate_count: int = 4
    min_positive_labels: int = 2
    min_negative_labels: int = 2
    min_usable_numeric_feature_count: int = 1
    max_constant_or_near_constant_feature_ratio: float = 0.0
    near_constant_dominant_ratio: float = 0.95


def build_ml_ready_candidate_features_v2(
    candidate_rows: Sequence[Mapping[str, Any]],
    audit_manifest: Mapping[str, Any],
    *,
    source_artifacts: Sequence[str],
    label_manifest_id: str | None,
    audit_manifest_id: str,
    feature_lineage: Mapping[str, Mapping[str, Any]],
    label_column: str = "label_review_preferred",
    feature_set_version: str = FEATURE_SET_VERSION,
    created_at: str = DEFAULT_CREATED_AT,
    config: MLReadyCandidateFeaturesV2Config | None = None,
) -> dict[str, Any]:
    """Return a deterministic v2 matrix plus manifest without writing files."""

    cfg = config or MLReadyCandidateFeaturesV2Config()
    validate_feature_discrimination_manifest(audit_manifest)
    audit_rows = [dict(row) for row in audit_manifest["rows"]]
    included_features: list[str] = []
    excluded_features: list[dict[str, Any]] = []
    missing_lineage_features: list[str] = []

    for audit_row in audit_rows:
        feature_name = str(audit_row["feature_name"])
        reasons = list(audit_row.get("reason_codes") or [])
        audit_allows_input = (
            audit_row.get("decision") == DECISION_KEEP
            and audit_row.get("ml_input_allowed") is True
        )
        lineage_status = (
            _lineage_status(feature_name, audit_row, feature_lineage)
            if audit_allows_input
            else "not_required"
        )
        include_allowed = (
            audit_allows_input
            and lineage_status == "covered"
        )
        if include_allowed:
            included_features.append(feature_name)
            continue
        if audit_row.get("decision") != DECISION_KEEP:
            reasons.append(REASON_NOT_AUDIT_KEEP)
        if audit_row.get("ml_input_allowed") is not True:
            reasons.append(REASON_AUDIT_ML_INPUT_NOT_ALLOWED)
        if audit_row.get("feature_type") == FEATURE_TYPE_STATUS:
            reasons.append(REASON_STATUS_DIAGNOSTIC_ONLY)
        if audit_row.get("source_timing") == SOURCE_TIMING_POST_LABEL:
            reasons.extend([REASON_POST_LABEL_LEAKAGE_RISK, REASON_SOURCE_TIMING_POST_LABEL])
        if lineage_status == "missing":
            reasons.append(REASON_MISSING_FEATURE_LINEAGE)
            if audit_row.get("decision") == DECISION_KEEP:
                missing_lineage_features.append(feature_name)
        excluded_features.append(
            {
                "feature_name": feature_name,
                "audit_decision": audit_row.get("decision"),
                "feature_type": audit_row.get("feature_type"),
                "source_timing": audit_row.get("source_timing"),
                "reason_codes": sorted(set(str(reason) for reason in reasons)),
                "diagnostic_available": bool(audit_row.get("diagnostic_available", True)),
            }
        )

    normalized_rows = [dict(row) for row in candidate_rows]
    missing_label_candidate_ids = [
        str(row.get("candidate_id"))
        for row in normalized_rows
        if _label_value(row.get(label_column)) is None
    ]
    matrix_rows = [
        _matrix_row(row, included_features, feature_lineage, label_column=label_column)
        for row in normalized_rows
        if _label_value(row.get(label_column)) is not None
    ]
    matrix_rows.sort(key=lambda row: str(row["candidate_id"]))
    positive_count = sum(row[label_column] == 1 for row in matrix_rows)
    negative_count = sum(row[label_column] == 0 for row in matrix_rows)
    trainability_status = _trainability_status(
        label_manifest_id=label_manifest_id,
        missing_label_candidate_ids=missing_label_candidate_ids,
        included_features=included_features,
        missing_lineage_features=missing_lineage_features,
        matrix_rows=matrix_rows,
        positive_count=positive_count,
        negative_count=negative_count,
        config=cfg,
    )
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "feature_set_version": feature_set_version,
        "created_at": created_at,
        "allowed_use": "manual ML selector input review only",
        "source_artifacts": sorted(str(path) for path in source_artifacts),
        "label_manifest_id": label_manifest_id,
        "audit_manifest_id": audit_manifest_id,
        "audit_schema_version": audit_manifest["schema_version"],
        "label_column": label_column,
        "row_count": len(matrix_rows),
        "input_candidate_count": len(normalized_rows),
        "labeled_candidate_count": len(matrix_rows),
        "missing_label_candidate_ids": sorted(missing_label_candidate_ids),
        "positive_label_count": positive_count,
        "negative_label_count": negative_count,
        "included_features": included_features,
        "included_feature_count": len(included_features),
        "excluded_features": excluded_features,
        "excluded_feature_count": len(excluded_features),
        "exclusion_reasons": _reason_counts(excluded_features),
        "feature_lineage_coverage": {
            "coverage_status": "pass" if not missing_lineage_features else "review_only",
            "covered_features": included_features,
            "covered_feature_count": len(included_features),
            "missing_feature_lineage": sorted(missing_lineage_features),
            "missing_feature_lineage_count": len(missing_lineage_features),
        },
        "trainability_gate_status": trainability_status,
        "ml_ready_gate_passed": trainability_status == TRAINABILITY_ML_READY,
        "minimum_candidate_count": cfg.min_candidate_count,
        "minimum_positive_labels": cfg.min_positive_labels,
        "minimum_negative_labels": cfg.min_negative_labels,
        "matrix_row_schema_version": MATRIX_SCHEMA_VERSION,
        "model_input_columns": included_features,
        "diagnostic_metadata_policy": "excluded_features_remain_in_manifest_not_model_input_columns",
        "no_feedback_check": "ml_ready_candidate_features_v2_must_not_feed_selector_scores_rankings_backtests_or_auto_adoption",
        "ml_training_performed": False,
        "selector_ranking_changed": False,
        "backtest_behavior_changed": False,
        "valuation_activation_changed": False,
        "data_ingestion_changed": False,
    }
    artifact = {"manifest": manifest, "rows": matrix_rows}
    validate_ml_ready_candidate_features_v2(artifact)
    return artifact


def validate_ml_ready_candidate_features_v2(artifact: Mapping[str, Any]) -> None:
    """Validate the v2 matrix/manifest boundary and schema shape."""

    if not isinstance(artifact.get("manifest"), Mapping):
        raise ValueError("ml_ready_candidate_features_v2 artifact requires manifest")
    if not isinstance(artifact.get("rows"), list):
        raise ValueError("ml_ready_candidate_features_v2 artifact requires rows")
    manifest = artifact["manifest"]
    required = {
        "schema_version",
        "feature_set_version",
        "source_artifacts",
        "label_manifest_id",
        "audit_manifest_id",
        "included_features",
        "excluded_features",
        "exclusion_reasons",
        "feature_lineage_coverage",
        "trainability_gate_status",
        "ml_ready_gate_passed",
        "model_input_columns",
        *FALSE_BOUNDARY_FLAGS,
    }
    missing = sorted(required.difference(manifest))
    if missing:
        raise ValueError(f"ml_ready_candidate_features_v2 manifest missing fields: {missing}")
    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise ValueError("unsupported ml_ready_candidate_features_v2 manifest schema_version")
    if manifest["model_input_columns"] != manifest["included_features"]:
        raise ValueError("model_input_columns must match included_features")
    for flag in FALSE_BOUNDARY_FLAGS:
        if manifest.get(flag) is not False:
            raise ValueError(f"ml_ready_candidate_features_v2 must keep {flag}=false")
    included = list(manifest["included_features"])
    for row in artifact["rows"]:
        if not isinstance(row, Mapping):
            raise ValueError("ml_ready_candidate_features_v2 rows must be objects")
        if row.get("schema_version") != MATRIX_SCHEMA_VERSION:
            raise ValueError("unsupported ml_ready_candidate_features_v2 row schema_version")
        feature_values = row.get("feature_values")
        if not isinstance(feature_values, Mapping):
            raise ValueError("ml_ready_candidate_features_v2 row requires feature_values")
        if list(feature_values) != included:
            raise ValueError("row feature_values must match included_features order")
        if manifest["label_column"] in feature_values:
            raise ValueError("label column must not be a model input feature")
        for value in feature_values.values():
            if _as_float(value) is None:
                raise ValueError("model input feature values must be finite numeric values")
    if manifest["ml_ready_gate_passed"] is True and manifest["trainability_gate_status"] != TRAINABILITY_ML_READY:
        raise ValueError("ml_ready gate can pass only with ml_ready trainability status")


def build_baseline_selector_trainability_check_v2(
    ml_ready_artifact: Mapping[str, Any],
    *,
    label_manifest_id: str | None = None,
    feature_lineage_manifest_id: str | None = None,
    leakage_findings: Sequence[Mapping[str, Any]] | None = None,
    created_at: str = DEFAULT_CREATED_AT,
    config: BaselineSelectorTrainabilityV2Config | None = None,
) -> dict[str, Any]:
    """Check whether a v2 feature matrix may be used for baseline training.

    The report is a gate only. It never fits a model, changes ranking behavior,
    or treats a pass as strategy adoption evidence.
    """

    validate_ml_ready_candidate_features_v2(ml_ready_artifact)
    cfg = config or BaselineSelectorTrainabilityV2Config()
    manifest = dict(ml_ready_artifact["manifest"])
    rows = list(ml_ready_artifact["rows"])
    model_input_columns = [str(column) for column in manifest["model_input_columns"]]
    effective_label_manifest_id = label_manifest_id or manifest.get("label_manifest_id")
    leakage_rows = [dict(row) for row in (leakage_findings or [])]
    feature_stats = _feature_trainability_stats(rows, model_input_columns, cfg)
    constant_count = sum(1 for item in feature_stats if item["constant_or_near_constant"])
    feature_count = len(model_input_columns)
    constant_ratio = constant_count / feature_count if feature_count else 0.0
    usable_numeric_feature_count = sum(
        1
        for item in feature_stats
        if item["numeric_value_count"] == len(rows) and not item["constant_or_near_constant"]
    )
    status, blocked_reasons = _baseline_trainability_status(
        manifest=manifest,
        candidate_count=len(rows),
        positive_label_count=int(manifest["positive_label_count"]),
        negative_label_count=int(manifest["negative_label_count"]),
        usable_numeric_feature_count=usable_numeric_feature_count,
        constant_or_near_constant_feature_ratio=constant_ratio,
        label_manifest_id=effective_label_manifest_id,
        feature_lineage_manifest_id=feature_lineage_manifest_id,
        leakage_finding_count=len(leakage_rows),
        config=cfg,
    )
    report = {
        "report_version": BASELINE_TRAINABILITY_REPORT_VERSION,
        "created_at": created_at,
        "feature_set_version": manifest["feature_set_version"],
        "source_feature_manifest_version": manifest["schema_version"],
        "label_manifest_id": effective_label_manifest_id,
        "feature_lineage_manifest_id": feature_lineage_manifest_id,
        "candidate_count": len(rows),
        "positive_label_count": int(manifest["positive_label_count"]),
        "negative_label_count": int(manifest["negative_label_count"]),
        "minimum_candidate_count": cfg.min_candidate_count,
        "minimum_positive_labels": cfg.min_positive_labels,
        "minimum_negative_labels": cfg.min_negative_labels,
        "minimum_usable_numeric_feature_count": cfg.min_usable_numeric_feature_count,
        "usable_numeric_feature_count": usable_numeric_feature_count,
        "model_input_columns": model_input_columns,
        "feature_stats": feature_stats,
        "constant_or_near_constant_feature_count": constant_count,
        "constant_or_near_constant_feature_ratio": round(constant_ratio, 12),
        "maximum_constant_or_near_constant_feature_ratio": cfg.max_constant_or_near_constant_feature_ratio,
        "near_constant_dominant_ratio": cfg.near_constant_dominant_ratio,
        "leakage_finding_count": len(leakage_rows),
        "leakage_findings": leakage_rows,
        "feature_lineage_coverage": dict(manifest["feature_lineage_coverage"]),
        "source_ml_ready_gate_status": manifest["trainability_gate_status"],
        "source_ml_ready_gate_passed": bool(manifest["ml_ready_gate_passed"]),
        "trainability_status": status,
        "training_blocked_reasons": blocked_reasons,
        "model_training_performed": False,
        "ml_training_performed": False,
        "selector_ranking_changed": False,
        "backtest_behavior_changed": False,
        "valuation_activation_changed": False,
        "data_ingestion_changed": False,
        "allowed_use": "baseline selector trainability gate only",
        "adoption_or_performance_support": "none",
        "no_feedback_check": "baseline_trainability_v2_must_not_feed_selector_scores_rankings_backtests_or_auto_adoption",
    }
    validate_baseline_selector_trainability_check_v2(report)
    return report


def validate_baseline_selector_trainability_check_v2(report: Mapping[str, Any]) -> None:
    """Validate baseline selector trainability report shape and boundaries."""

    required = {
        "report_version",
        "feature_set_version",
        "label_manifest_id",
        "feature_lineage_manifest_id",
        "candidate_count",
        "positive_label_count",
        "negative_label_count",
        "minimum_usable_numeric_feature_count",
        "usable_numeric_feature_count",
        "constant_or_near_constant_feature_ratio",
        "maximum_constant_or_near_constant_feature_ratio",
        "leakage_finding_count",
        "feature_lineage_coverage",
        "source_ml_ready_gate_status",
        "trainability_status",
        "training_blocked_reasons",
        "model_training_performed",
        "adoption_or_performance_support",
        *FALSE_BOUNDARY_FLAGS[1:],
    }
    missing = sorted(required.difference(report))
    if missing:
        raise ValueError(f"baseline selector trainability report missing fields: {missing}")
    if report["report_version"] != BASELINE_TRAINABILITY_REPORT_VERSION:
        raise ValueError("unsupported baseline selector trainability report version")
    if report["trainability_status"] not in {
        BASELINE_TRAINABLE,
        BASELINE_BLOCKED_INSUFFICIENT_FEATURES,
        BASELINE_BLOCKED_INSUFFICIENT_LABELS,
        BASELINE_BLOCKED_LEAKAGE_RISK,
        BASELINE_BLOCKED_LINEAGE_GAP,
        BASELINE_REVIEW_ONLY,
    }:
        raise ValueError("unsupported baseline selector trainability_status")
    if report["trainability_status"] == BASELINE_TRAINABLE and report["training_blocked_reasons"]:
        raise ValueError("trainable baseline report must not include blocked reasons")
    for flag in FALSE_BOUNDARY_FLAGS:
        if report.get(flag) is not False:
            raise ValueError(f"baseline selector trainability check must keep {flag}=false")
    if report.get("adoption_or_performance_support") != "none":
        raise ValueError("trainability pass must not claim adoption or performance support")


def _matrix_row(
    row: Mapping[str, Any],
    included_features: Sequence[str],
    feature_lineage: Mapping[str, Mapping[str, Any]],
    *,
    label_column: str,
) -> dict[str, Any]:
    candidate_id = str(row.get("candidate_id"))
    feature_values: dict[str, float] = {}
    feature_lineage_refs: dict[str, str] = {}
    for feature_name in included_features:
        value = _as_float(_feature_value(row, feature_name))
        if value is None:
            raise ValueError(f"candidate {candidate_id} missing numeric feature: {feature_name}")
        feature_values[feature_name] = value
        feature_lineage_refs[feature_name] = str(feature_lineage[feature_name]["source_artifact"])
    return {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "candidate_id": candidate_id,
        label_column: _label_value(row.get(label_column)),
        "feature_values": feature_values,
        "feature_lineage_refs": feature_lineage_refs,
    }


def _feature_trainability_stats(
    rows: Sequence[Mapping[str, Any]],
    feature_names: Sequence[str],
    config: BaselineSelectorTrainabilityV2Config,
) -> list[dict[str, Any]]:
    stats: list[dict[str, Any]] = []
    for feature_name in feature_names:
        values = [
            _as_float(row.get("feature_values", {}).get(feature_name))  # type: ignore[union-attr]
            for row in rows
        ]
        numeric_values = [value for value in values if value is not None]
        unique_values = sorted(set(numeric_values))
        dominant_ratio = _dominant_ratio(numeric_values)
        constant_or_near_constant = (
            len(unique_values) <= 1
            or dominant_ratio >= config.near_constant_dominant_ratio
        )
        stats.append(
            {
                "feature_name": feature_name,
                "numeric_value_count": len(numeric_values),
                "unique_value_count": len(unique_values),
                "dominant_value_ratio": round(dominant_ratio, 12),
                "constant_or_near_constant": constant_or_near_constant,
            }
        )
    return stats


def _baseline_trainability_status(
    *,
    manifest: Mapping[str, Any],
    candidate_count: int,
    positive_label_count: int,
    negative_label_count: int,
    usable_numeric_feature_count: int,
    constant_or_near_constant_feature_ratio: float,
    label_manifest_id: Any,
    feature_lineage_manifest_id: str | None,
    leakage_finding_count: int,
    config: BaselineSelectorTrainabilityV2Config,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if leakage_finding_count:
        reasons.append("leakage_findings_present")
        return BASELINE_BLOCKED_LEAKAGE_RISK, reasons
    if not label_manifest_id:
        reasons.append("label_manifest_missing")
        return BASELINE_BLOCKED_INSUFFICIENT_LABELS, reasons
    if (
        candidate_count < config.min_candidate_count
        or positive_label_count < config.min_positive_labels
        or negative_label_count < config.min_negative_labels
    ):
        reasons.append("candidate_or_label_count_below_minimum")
        return BASELINE_BLOCKED_INSUFFICIENT_LABELS, reasons
    if not feature_lineage_manifest_id:
        reasons.append("feature_lineage_manifest_missing")
        return BASELINE_BLOCKED_LINEAGE_GAP, reasons
    coverage = manifest.get("feature_lineage_coverage")
    if isinstance(coverage, Mapping) and coverage.get("coverage_status") != "pass":
        reasons.append("feature_lineage_coverage_not_pass")
        return BASELINE_REVIEW_ONLY, reasons
    if manifest.get("trainability_gate_status") == TRAINABILITY_REVIEW_ONLY_MISSING_LINEAGE:
        reasons.append("source_feature_matrix_review_only")
        return BASELINE_REVIEW_ONLY, reasons
    if usable_numeric_feature_count < config.min_usable_numeric_feature_count:
        reasons.append("usable_numeric_feature_count_below_minimum")
        return BASELINE_BLOCKED_INSUFFICIENT_FEATURES, reasons
    if constant_or_near_constant_feature_ratio > config.max_constant_or_near_constant_feature_ratio:
        reasons.append("constant_or_near_constant_feature_ratio_above_maximum")
        return BASELINE_BLOCKED_INSUFFICIENT_FEATURES, reasons
    if manifest.get("ml_ready_gate_passed") is not True:
        reasons.append("source_feature_matrix_not_ml_ready")
        return BASELINE_REVIEW_ONLY, reasons
    return BASELINE_TRAINABLE, reasons


def _dominant_ratio(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    counts: dict[float, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return max(counts.values()) / len(values)


def _trainability_status(
    *,
    label_manifest_id: str | None,
    missing_label_candidate_ids: Sequence[str],
    included_features: Sequence[str],
    missing_lineage_features: Sequence[str],
    matrix_rows: Sequence[Mapping[str, Any]],
    positive_count: int,
    negative_count: int,
    config: MLReadyCandidateFeaturesV2Config,
) -> str:
    if not label_manifest_id:
        return TRAINABILITY_BLOCKED_MISSING_LABEL_MANIFEST
    if missing_label_candidate_ids:
        return TRAINABILITY_BLOCKED_MISSING_LABELS
    if not included_features and missing_lineage_features:
        return TRAINABILITY_BLOCKED_MISSING_LINEAGE
    if not included_features:
        return TRAINABILITY_BLOCKED_NO_INCLUDED_FEATURES
    if missing_lineage_features:
        return TRAINABILITY_REVIEW_ONLY_MISSING_LINEAGE
    if (
        len(matrix_rows) < config.min_candidate_count
        or positive_count < config.min_positive_labels
        or negative_count < config.min_negative_labels
    ):
        return TRAINABILITY_BLOCKED_INSUFFICIENT_COVERAGE
    return TRAINABILITY_ML_READY


def _lineage_status(
    feature_name: str,
    audit_row: Mapping[str, Any],
    feature_lineage: Mapping[str, Mapping[str, Any]],
) -> str:
    lineage = feature_lineage.get(feature_name)
    if not lineage:
        return "missing"
    if not lineage.get("source_artifact"):
        return "missing"
    source_timing = str(lineage.get("source_timing") or audit_row.get("source_timing") or "")
    if source_timing == SOURCE_TIMING_POST_LABEL:
        return "missing"
    status = str(lineage.get("lineage_status") or "covered")
    if status not in {"covered", "pass", "available"}:
        return "missing"
    return "covered"


def _feature_value(row: Mapping[str, Any], feature_name: str) -> Any:
    feature_values = row.get("feature_values")
    if isinstance(feature_values, Mapping) and feature_name in feature_values:
        return feature_values[feature_name]
    return row.get(feature_name)


def _reason_counts(excluded_features: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for feature in excluded_features:
        for reason in feature.get("reason_codes") or []:
            counts[str(reason)] = counts.get(str(reason), 0) + 1
    return dict(sorted(counts.items()))


def _label_value(value: Any) -> int | None:
    if value is True:
        return 1
    if value is False:
        return 0
    if value in {0, 1}:
        return int(value)
    if isinstance(value, str) and value.strip() in {"0", "1"}:
        return int(value.strip())
    return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(result):
        return None
    return result


__all__ = [
    "FEATURE_SET_VERSION",
    "MANIFEST_SCHEMA_VERSION",
    "MATRIX_SCHEMA_VERSION",
    "BASELINE_BLOCKED_INSUFFICIENT_FEATURES",
    "BASELINE_BLOCKED_INSUFFICIENT_LABELS",
    "BASELINE_BLOCKED_LEAKAGE_RISK",
    "BASELINE_BLOCKED_LINEAGE_GAP",
    "BASELINE_REVIEW_ONLY",
    "BASELINE_TRAINABILITY_REPORT_VERSION",
    "BASELINE_TRAINABLE",
    "BaselineSelectorTrainabilityV2Config",
    "MLReadyCandidateFeaturesV2Config",
    "TRAINABILITY_BLOCKED_INSUFFICIENT_COVERAGE",
    "TRAINABILITY_BLOCKED_MISSING_LABELS",
    "TRAINABILITY_BLOCKED_MISSING_LINEAGE",
    "TRAINABILITY_BLOCKED_MISSING_LABEL_MANIFEST",
    "TRAINABILITY_BLOCKED_NO_INCLUDED_FEATURES",
    "TRAINABILITY_ML_READY",
    "TRAINABILITY_REVIEW_ONLY_MISSING_LINEAGE",
    "build_baseline_selector_trainability_check_v2",
    "build_ml_ready_candidate_features_v2",
    "validate_baseline_selector_trainability_check_v2",
    "validate_ml_ready_candidate_features_v2",
]
