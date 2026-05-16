"""Evidence-only feature discrimination audit for selector inputs.

The audit measures missingness, candidate-level variation, and simple label
separation for feature candidates. It returns review metadata only and does not
train or score a selector model.
"""

from __future__ import annotations

from collections import Counter
from math import isfinite
from typing import Any, Mapping, Sequence

from Quant_mvp.backtest_mvp.feature_discrimination_contracts import (
    AUDIT_ROW_SCHEMA_VERSION,
    AUDIT_SCHEMA_VERSION,
    AUDIT_VERSION,
    DECISION_DIAGNOSTIC_ONLY,
    DECISION_EXCLUDE,
    DECISION_KEEP,
    DECISION_REVIEW,
    FEATURE_TYPE_DIAGNOSTIC_METADATA,
    FEATURE_TYPE_NUMERIC,
    FEATURE_TYPE_STATUS,
    FeatureDiscriminationAuditConfig,
    LABEL_DERIVED_FEATURE_NAMES,
    REASON_CONSTANT_FEATURE,
    REASON_DIAGNOSTIC_METADATA_ONLY,
    REASON_HIGH_NULL_FEATURE,
    REASON_INSUFFICIENT_LABELS,
    REASON_LABEL_DERIVED_NAME,
    REASON_NON_NUMERIC_REVIEW,
    REASON_NUMERIC_LABEL_SEPARATION_PRESENT,
    REASON_NUMERIC_LABEL_SEPARATION_WEAK,
    REASON_POST_LABEL_LEAKAGE_RISK,
    REASON_STATUS_ONLY_DIAGNOSTIC,
    SOURCE_TIMING_POST_LABEL,
    SOURCE_TIMING_UNKNOWN,
    validate_feature_discrimination_manifest,
)


def audit_feature_discrimination(
    rows: Sequence[Mapping[str, Any]],
    feature_specs: Sequence[Mapping[str, Any]],
    *,
    label_column: str = "label_review_preferred",
    config: FeatureDiscriminationAuditConfig | None = None,
) -> dict[str, Any]:
    """Build a deterministic discrimination manifest for candidate features."""

    cfg = config or FeatureDiscriminationAuditConfig()
    normalized_rows = [dict(row) for row in rows]
    audit_rows = [
        audit_one_feature(normalized_rows, dict(spec), label_column=label_column, config=cfg)
        for spec in feature_specs
    ]
    decision_counts = Counter(str(row["decision"]) for row in audit_rows)
    labeled_row_count = sum(_label_value(row.get(label_column)) is not None for row in normalized_rows)
    manifest = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "audit_version": AUDIT_VERSION,
        "allowed_use": "manual ML input review only",
        "input_row_count": len(normalized_rows),
        "labeled_row_count": labeled_row_count,
        "label_column": label_column,
        "feature_count": len(audit_rows),
        "decision_counts": dict(sorted(decision_counts.items())),
        "excluded_feature_count": decision_counts.get(DECISION_EXCLUDE, 0),
        "kept_feature_count": decision_counts.get(DECISION_KEEP, 0),
        "diagnostic_only_feature_count": decision_counts.get(DECISION_DIAGNOSTIC_ONLY, 0),
        "review_feature_count": decision_counts.get(DECISION_REVIEW, 0),
        "thresholds": {
            "min_non_null_ratio": cfg.min_non_null_ratio,
            "min_unique_values": cfg.min_unique_values,
            "min_label_mean_abs_difference": cfg.min_label_mean_abs_difference,
        },
        "rows": audit_rows,
        "no_feedback_check": "feature_discrimination_audit_must_not_feed_models_scores_rankings_backtests_or_auto_adoption",
        "ml_training_changed": False,
        "selector_ranking_changed": False,
        "backtest_behavior_changed": False,
        "valuation_activation_changed": False,
        "data_ingestion_changed": False,
    }
    validate_feature_discrimination_manifest(manifest)
    return manifest


def audit_one_feature(
    rows: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any],
    *,
    label_column: str,
    config: FeatureDiscriminationAuditConfig,
) -> dict[str, Any]:
    """Audit one feature using contract-level exclusion rules."""

    feature_name = str(spec["feature_name"])
    feature_type = str(spec.get("feature_type") or FEATURE_TYPE_NUMERIC)
    source_timing = str(spec.get("source_timing") or SOURCE_TIMING_UNKNOWN)
    values = [row.get(feature_name) for row in rows]
    non_null_values = [value for value in values if value is not None]
    row_count = len(rows)
    non_null_count = len(non_null_values)
    null_count = row_count - non_null_count
    non_null_ratio = (non_null_count / row_count) if row_count else 0.0
    unique_count = len({_stable_key(value) for value in non_null_values})

    positive_values = _numeric_values_for_label(rows, feature_name, label_column, 1)
    negative_values = _numeric_values_for_label(rows, feature_name, label_column, 0)
    positive_mean = _mean(positive_values)
    negative_mean = _mean(negative_values)
    label_mean_difference = (
        positive_mean - negative_mean
        if positive_mean is not None and negative_mean is not None
        else None
    )
    label_mean_abs_difference = abs(label_mean_difference) if label_mean_difference is not None else None

    reason_codes: list[str] = []
    decision = DECISION_REVIEW

    if source_timing == SOURCE_TIMING_POST_LABEL:
        decision = DECISION_EXCLUDE
        reason_codes.append(REASON_POST_LABEL_LEAKAGE_RISK)
    elif feature_name in LABEL_DERIVED_FEATURE_NAMES:
        decision = DECISION_EXCLUDE
        reason_codes.append(REASON_LABEL_DERIVED_NAME)
    elif feature_type == FEATURE_TYPE_STATUS:
        decision = DECISION_DIAGNOSTIC_ONLY
        reason_codes.append(REASON_STATUS_ONLY_DIAGNOSTIC)
    elif feature_type == FEATURE_TYPE_DIAGNOSTIC_METADATA:
        decision = DECISION_DIAGNOSTIC_ONLY
        reason_codes.append(REASON_DIAGNOSTIC_METADATA_ONLY)
    elif non_null_ratio < config.min_non_null_ratio:
        decision = DECISION_EXCLUDE
        reason_codes.append(REASON_HIGH_NULL_FEATURE)
    elif unique_count < config.min_unique_values:
        decision = DECISION_EXCLUDE
        reason_codes.append(REASON_CONSTANT_FEATURE)
    elif feature_type != FEATURE_TYPE_NUMERIC:
        decision = DECISION_REVIEW
        reason_codes.append(REASON_NON_NUMERIC_REVIEW)
    elif not positive_values or not negative_values:
        decision = DECISION_REVIEW
        reason_codes.append(REASON_INSUFFICIENT_LABELS)
    elif (
        label_mean_abs_difference is not None
        and label_mean_abs_difference >= config.min_label_mean_abs_difference
    ):
        decision = DECISION_KEEP
        reason_codes.append(REASON_NUMERIC_LABEL_SEPARATION_PRESENT)
    else:
        decision = DECISION_REVIEW
        reason_codes.append(REASON_NUMERIC_LABEL_SEPARATION_WEAK)

    return {
        "schema_version": AUDIT_ROW_SCHEMA_VERSION,
        "feature_name": feature_name,
        "feature_type": feature_type,
        "source_timing": source_timing,
        "decision": decision,
        "reason_codes": reason_codes,
        "row_count": row_count,
        "non_null_count": non_null_count,
        "null_count": null_count,
        "non_null_ratio": round(non_null_ratio, 12),
        "unique_count": unique_count,
        "label_positive_count": len(positive_values),
        "label_negative_count": len(negative_values),
        "positive_label_mean": positive_mean,
        "negative_label_mean": negative_mean,
        "label_mean_difference": label_mean_difference,
        "label_mean_abs_difference": label_mean_abs_difference,
        "ml_input_allowed": decision == DECISION_KEEP,
        "diagnostic_available": decision in {DECISION_DIAGNOSTIC_ONLY, DECISION_REVIEW, DECISION_EXCLUDE},
    }


def _numeric_values_for_label(
    rows: Sequence[Mapping[str, Any]],
    feature_name: str,
    label_column: str,
    label: int,
) -> list[float]:
    values: list[float] = []
    for row in rows:
        if _label_value(row.get(label_column)) != label:
            continue
        value = _as_float(row.get(feature_name))
        if value is not None:
            values.append(value)
    return values


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


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _stable_key(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


__all__ = [
    "audit_feature_discrimination",
    "audit_one_feature",
]
