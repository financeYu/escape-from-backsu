"""Build a v0.3 selector feature matrix scaffold from ML-ready candidate rows.

The scaffold is an input artifact for later ML selector work. It does not train
models, score candidates, rank outputs, or activate any production behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.scripts.artifact_io import read_jsonl, write_jsonl

DEFAULT_INPUT = Path("Quant_mvp/data/v0_3/ml_ready_candidate_inputs/v0_3_ml_ready_candidate_input.jsonl")
DEFAULT_OUTPUT_DIR = Path("Quant_mvp/data/v0_3/selector_feature_matrix")
DEFAULT_JSONL_NAME = "v0_3_selector_feature_matrix.jsonl"
DEFAULT_CSV_NAME = "v0_3_selector_feature_matrix.csv"
DEFAULT_MANIFEST_NAME = "v0_3_selector_feature_matrix_manifest.json"

SCHEMA_VERSION = "v0_3_selector_feature_matrix_v1_0"
MANIFEST_SCHEMA_VERSION = "v0_3_selector_feature_matrix_manifest_v1_0"
FEATURE_MATRIX_VERSION = "v0_3_selector_feature_matrix_v1_0"
MATRIX_INTENT = "post_evaluation_selector_rule_replication_audit"
TRAINABILITY_READY = "ready_for_baseline_training"
TRAINABILITY_BLOCKED_NO_CANDIDATE_LEVEL_EVIDENCE = "blocked_no_candidate_level_evidence"
TRAINABILITY_BLOCKED_NO_CLASSES = "blocked_no_positive_negative_classes"
TRAINABILITY_LIMITED_ROWS = "limited_insufficient_training_rows"
MIN_BASELINE_TRAINING_ROWS = 30
GENERIC_PROXY_ROLE = "generic_momentum_proxy"

TRAINING_FEATURE_COLUMNS = [
    "total_return",
    "excess_return_vs_proxy",
    "max_drawdown_abs",
    "sharpe",
    "turnover",
    "volatility",
]
FEATURE_COLUMNS = TRAINING_FEATURE_COLUMNS
REQUIRED_CORE_FEATURE_COLUMNS = TRAINING_FEATURE_COLUMNS

AUDIT_ONLY_COLUMNS = [
    "candidate_id",
    "evidence_id",
    "metric_subject_type",
    "metric_subject_id",
    "candidate_metric_match",
    "strategy_family",
    "signal_family",
    "max_drawdown",
    "proxy_return",
    "actual_oos_stability",
    "has_oos_evidence",
    "has_benchmark_comparison",
    "failure_flag_count",
    "label_review_preferred",
    "label_status",
    "label_reason_code",
    "evidence_limitations",
]

LABEL_COLUMNS = [
    "label_review_preferred",
    "label_status",
    "label_reason_code",
    "label_decision",
    "label_null_reason",
    "label_pass_minimum_gate",
    "supervised_label_eligible",
    "adoption_review_eligible",
    "adoption_candidate_status",
    "selector_score",
    "selector_rank",
]

EXCLUDED_COLUMNS_WITH_REASONS = {
    "strategy_family": "excluded_from_training_feature_due_to_cohort_memorization_risk; retained_as_audit_column",
    "signal_family": "excluded_from_training_feature_due_to_cohort_memorization_risk; retained_as_audit_column",
    "holding_period": "excluded_from_training_feature_when_missing_or_unavailable",
    "proxy_return": "retained_as_reference_context_only; excess_return_vs_proxy is the training feature",
    "risk_adjusted_delta_vs_proxy": "excluded_from_training_feature_when_missing_or_unavailable",
    "universe_scope": "excluded_from_training_feature_when_constant",
    "has_oos_evidence": "retained_as_audit_check_only_due_to_label_eligibility_or_constant_feature_risk",
    "has_benchmark_comparison": "retained_as_audit_check_only_due_to_label_eligibility_or_constant_feature_risk",
    "failure_flag_count": "retained_as_exclusion_or_gate_audit; excluded_when constant or gate-derived",
    "actual_oos_stability": "excluded_from_training_feature_due_to_direct_label_rule_connection",
    "label_review_preferred": "target_column",
    "label_status": "target_or_target_derived_column",
    "label_reason_code": "target_or_target_derived_column",
    "label_decision": "target_or_target_derived_column",
    "label_null_reason": "target_or_target_derived_column",
    "label_pass_minimum_gate": "target_or_target_derived_column",
    "supervised_label_eligible": "target_or_label_eligibility_column",
    "adoption_review_eligible": "post_label_adoption_gate_column",
    "adoption_candidate_status": "post_selector_or_adoption_output_column",
    "selector_score": "post_selector_output_column",
    "selector_rank": "post_selector_output_column",
}

LEAKAGE_RISK_COLUMNS = [
    *LABEL_COLUMNS,
    "actual_label_source",
    "actual_label_role",
    "actual_label_use_status",
    "actual_label_evidence_id",
    "actual_label_generated_at",
    "actual_label_blocked_reason",
    "ml_training_status",
    "actual_oos_stability",
    "prediction_model_version",
    "prediction_generated_at",
    "prediction_uncertainty",
    "pred_total_return",
    "pred_max_drawdown",
    "pred_volatility",
    "pred_turnover",
    "pred_sharpe",
    "pred_oos_stability",
]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_bool_feature(value: Any) -> int:
    return 1 if value is True else 0


def _pearson_correlation(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 2:
        return None
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
    x_denominator = sum((x - x_mean) ** 2 for x in xs)
    y_denominator = sum((y - y_mean) ** 2 for y in ys)
    denominator = (x_denominator * y_denominator) ** 0.5
    if denominator == 0:
        return None
    return numerator / denominator


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(records[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({key: _csv_value(value) for key, value in record.items()})


def _has_oos_evidence(row: dict[str, Any]) -> bool:
    status = str(row.get("actual_oos_stability") or "").strip().lower()
    return bool(
        status
        and status
        not in {
            "not_available",
            "not_available_single_pass_snapshot",
            "required_before_adoption_review",
            "required_before_approved_run",
            "missing",
            "none",
        }
    )


def _has_benchmark_comparison(row: dict[str, Any], proxy_return: float | None, excess_return: float | None) -> bool:
    if proxy_return is not None or excess_return is not None:
        return True
    return bool(row.get("reference_feature_candidate") is True and row.get("metric_subject_type") == "generic_proxy")


def _feature_values(row: dict[str, Any]) -> dict[str, Any]:
    candidate_metric = (
        row.get("metric_subject_type") == "strategy_candidate"
        and row.get("candidate_metric_match") is True
    )
    generic_proxy = row.get("metric_subject_type") == "generic_proxy" or row.get("metric_role") == GENERIC_PROXY_ROLE

    total_return = _as_float(row.get("actual_total_return")) if candidate_metric else None
    max_drawdown = _as_float(row.get("actual_max_drawdown")) if candidate_metric else None
    sharpe = _as_float(row.get("actual_sharpe")) if candidate_metric else None
    turnover = _as_float(row.get("actual_turnover")) if candidate_metric else None
    volatility = _as_float(row.get("actual_volatility")) if candidate_metric else None
    proxy_return = _as_float(row.get("actual_total_return")) if generic_proxy else None
    explicit_excess_return = _as_float(row.get("actual_excess_return_vs_proxy")) if candidate_metric else None
    excess_return = (
        explicit_excess_return
        if explicit_excess_return is not None
        else None
    )

    return {
        "total_return": total_return,
        "excess_return_vs_proxy": excess_return,
        "max_drawdown_abs": abs(max_drawdown) if max_drawdown is not None else None,
        "sharpe": sharpe,
        "turnover": turnover,
        "volatility": volatility,
    }


def _audit_values(row: dict[str, Any]) -> dict[str, Any]:
    candidate_metric = row.get("metric_subject_type") == "strategy_candidate" and row.get("candidate_metric_match") is True
    generic_proxy = row.get("metric_subject_type") == "generic_proxy" or row.get("metric_role") == GENERIC_PROXY_ROLE
    proxy_return = _as_float(row.get("actual_total_return")) if generic_proxy else None
    excess_return = _as_float(row.get("actual_excess_return_vs_proxy")) if candidate_metric else None
    evidence_limitations = (
        row.get("evidence_limitations")
        or row.get("limitation_summary")
        or row.get("limitations")
        or row.get("actual_label_blocked_reason")
    )
    return {
        "candidate_id": row.get("candidate_id"),
        "evidence_id": row.get("evaluation_id"),
        "metric_subject_type": row.get("metric_subject_type"),
        "metric_subject_id": row.get("metric_subject_id"),
        "candidate_metric_match": row.get("candidate_metric_match"),
        "strategy_family": row.get("strategy_type"),
        "signal_family": row.get("signal_family_candidate"),
        "max_drawdown": _as_float(row.get("actual_max_drawdown")) if candidate_metric else None,
        "proxy_return": proxy_return,
        "actual_oos_stability": row.get("actual_oos_stability"),
        "has_oos_evidence": _as_bool_feature(_has_oos_evidence(row)),
        "has_benchmark_comparison": _as_bool_feature(_has_benchmark_comparison(row, proxy_return, excess_return)),
        "failure_flag_count": len(_as_list(row.get("evaluation_failure_flags"))),
        "label_review_preferred": row.get("label_review_preferred"),
        "label_status": row.get("label_status"),
        "label_reason_code": row.get("label_reason_code"),
        "evidence_limitations": evidence_limitations,
    }


def _candidate_level_metric(row: dict[str, Any]) -> bool:
    return row.get("metric_subject_type") == "strategy_candidate" and row.get("candidate_metric_match") is True


def _missing_required_core_features(feature_values: dict[str, Any]) -> list[str]:
    return [
        column
        for column in REQUIRED_CORE_FEATURE_COLUMNS
        if feature_values.get(column) is None
    ]


def _training_exclusion_reason(row: dict[str, Any], feature_values: dict[str, Any]) -> str | None:
    if row.get("excluded_untradable") is True:
        return "excluded_untradable"
    if row.get("excluded_failure") is True:
        return "excluded_failure"
    if not _candidate_level_metric(row):
        if row.get("metric_subject_type") == "generic_proxy" or row.get("metric_role") == GENERIC_PROXY_ROLE:
            return "blocked_generic_proxy_not_candidate_level"
        return "blocked_not_candidate_level_metric"
    if row.get("supervised_label_eligible") is not True:
        return str(row.get("label_decision") or "null_or_blocked_label")
    if row.get("label_review_preferred") not in {0, 1}:
        return "null_label_review_preferred"
    missing_core_features = _missing_required_core_features(feature_values)
    if missing_core_features:
        return "missing_required_core_feature"
    return None


def build_feature_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        feature_values = _feature_values(record)
        audit_values = _audit_values(record)
        exclusion_reason = _training_exclusion_reason(record, feature_values)
        row = {
            "schema_version": SCHEMA_VERSION,
            "candidate_version": record.get("candidate_version"),
            "metric_role": record.get("metric_role"),
            "reference_feature_candidate": record.get("reference_feature_candidate"),
            "training_eligible": exclusion_reason is None,
            "training_exclusion_reason": exclusion_reason,
            "feature_values": feature_values,
            **audit_values,
            **feature_values,
        }
        validate_feature_row(row)
        rows.append(row)
    return rows


def validate_feature_row(row: dict[str, Any]) -> None:
    feature_values = row.get("feature_values")
    if not isinstance(feature_values, dict):
        raise ValueError("feature row requires feature_values object")
    leaked = sorted(set(feature_values) & set(LEAKAGE_RISK_COLUMNS))
    if leaked:
        raise ValueError(f"feature_values include leakage columns: {leaked}")
    missing = sorted(set(FEATURE_COLUMNS) - set(feature_values))
    if missing:
        raise ValueError(f"feature_values missing feature columns: {missing}")
    if row.get("metric_subject_type") == "generic_proxy":
        if row.get("training_eligible") is True:
            raise ValueError("generic proxy rows may not be training eligible")
        if feature_values.get("total_return") is not None:
            raise ValueError("generic proxy return may not be copied into candidate total_return")
        if row.get("candidate_metric_match") is True:
            raise ValueError("generic proxy rows may not be marked as candidate_metric_match")


def validate_feature_rows(rows: list[dict[str, Any]]) -> None:
    candidate_ids = [str(row.get("candidate_id")) for row in rows]
    duplicates = [candidate_id for candidate_id, count in Counter(candidate_ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate candidate_id rows: {sorted(duplicates)}")
    for row in rows:
        validate_feature_row(row)


def build_manifest(rows: list[dict[str, Any]], *, run_id: str, input_ref: Path) -> dict[str, Any]:
    training_eligible_rows = [row for row in rows if row.get("training_eligible") is True]
    candidate_level_metric_count = sum(_candidate_level_metric(row) for row in rows)
    positive_rows = sum(row.get("label_review_preferred") == 1 for row in training_eligible_rows)
    negative_rows = sum(row.get("label_review_preferred") == 0 for row in training_eligible_rows)
    excluded_rows = sum(
        str(row.get("training_exclusion_reason") or "").startswith("excluded_")
        for row in rows
    )
    null_label_rows = sum(
        row.get("label_review_preferred") is None
        and not str(row.get("training_exclusion_reason") or "").startswith("excluded_")
        for row in rows
    )
    missing_required_core_feature_rows = sum(
        row.get("training_exclusion_reason") == "missing_required_core_feature"
        for row in rows
    )
    all_missing_training_feature_columns = [
        column
        for column in TRAINING_FEATURE_COLUMNS
        if all(row.get(column) is None for row in training_eligible_rows)
    ]
    constant_training_feature_columns = []
    for column in TRAINING_FEATURE_COLUMNS:
        values = [
            row.get(column)
            for row in training_eligible_rows
            if row.get(column) is not None
        ]
        if values and len(set(values)) == 1:
            constant_training_feature_columns.append(column)
    correlation_pairs = [
        (float(row["total_return"]), float(row["excess_return_vs_proxy"]))
        for row in training_eligible_rows
        if row.get("total_return") is not None and row.get("excess_return_vs_proxy") is not None
    ]
    trainability_status = TRAINABILITY_READY
    if candidate_level_metric_count == 0:
        trainability_status = TRAINABILITY_BLOCKED_NO_CANDIDATE_LEVEL_EVIDENCE
    elif positive_rows == 0 or negative_rows == 0:
        trainability_status = TRAINABILITY_BLOCKED_NO_CLASSES
    elif len(training_eligible_rows) < MIN_BASELINE_TRAINING_ROWS:
        trainability_status = TRAINABILITY_LIMITED_ROWS
    elif missing_required_core_feature_rows > 0 or all_missing_training_feature_columns:
        trainability_status = TRAINABILITY_LIMITED_ROWS
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "feature_matrix_version": FEATURE_MATRIX_VERSION,
        "matrix_intent": MATRIX_INTENT,
        "prediction_claim": "none",
        "trade_signal_claim": "none",
        "allowed_use": "AdoptionCandidate review prioritization only",
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "input_ref": str(input_ref),
        "total_rows": len(rows),
        "total_candidates": len(rows),
        "total_feature_rows": len(rows),
        "candidate_level_metric_count": candidate_level_metric_count,
        "training_eligible_rows": len(training_eligible_rows),
        "positive_rows": positive_rows,
        "negative_rows": negative_rows,
        "excluded_rows": excluded_rows,
        "null_label_rows": null_label_rows,
        "missing_required_core_feature_rows": missing_required_core_feature_rows,
        "training_feature_columns": list(TRAINING_FEATURE_COLUMNS),
        "feature_columns": list(TRAINING_FEATURE_COLUMNS),
        "feature_columns_count": len(TRAINING_FEATURE_COLUMNS),
        "audit_only_columns": list(AUDIT_ONLY_COLUMNS),
        "excluded_columns": sorted(EXCLUDED_COLUMNS_WITH_REASONS),
        "excluded_columns_with_reasons": dict(sorted(EXCLUDED_COLUMNS_WITH_REASONS.items())),
        "leakage_risk_columns": list(LEAKAGE_RISK_COLUMNS),
        "leakage_excluded_columns": list(LEAKAGE_RISK_COLUMNS),
        "leakage_excluded_columns_count": len(LEAKAGE_RISK_COLUMNS),
        "constant_training_feature_columns": constant_training_feature_columns,
        "all_missing_training_feature_columns": all_missing_training_feature_columns,
        "total_return_excess_return_correlation": _pearson_correlation(correlation_pairs),
        "leakage_policy": "label_status_reason_adoption_selector_and_prediction_columns_excluded_from_training_feature_values",
        "trainability_status": trainability_status,
        "training_matrix_written": trainability_status == TRAINABILITY_READY,
        "minimum_training_rows_for_ready_status": MIN_BASELINE_TRAINING_ROWS,
        "generic_proxy_policy": "generic_momentum_proxy_is_benchmark_reference_context_only_not_label_or_candidate_level_metric",
        "label_distribution": {
            "positive_rows": positive_rows,
            "negative_rows": negative_rows,
            "null_label_rows": null_label_rows,
            "excluded_rows": excluded_rows,
        },
        "training_exclusion_reason_counts": dict(
            sorted(Counter(str(row.get("training_exclusion_reason")) for row in rows).items())
        ),
        "no_feedback_check": "selector_feature_matrix_v1_must_not_feed_scores_rankings_reports_trading_or_auto_adoption",
        "activation_boundary": "production_activation_requires_later_root_approved_gate",
    }


def build_feature_matrix(
    input_path: Path,
    output_dir: Path,
    *,
    run_id: str,
    write_csv_output: bool = True,
) -> dict[str, Path]:
    records = read_jsonl(input_path)
    rows = build_feature_rows(records)
    validate_feature_rows(rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / DEFAULT_JSONL_NAME
    manifest_path = output_dir / DEFAULT_MANIFEST_NAME
    write_jsonl(jsonl_path, rows)
    manifest = build_manifest(rows, run_id=run_id, input_ref=input_path)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    paths = {"jsonl": jsonl_path, "manifest": manifest_path}
    if write_csv_output:
        csv_path = output_dir / DEFAULT_CSV_NAME
        write_csv(csv_path, rows)
        paths["csv"] = csv_path
    return paths


def dry_run_feature_matrix(input_path: Path, *, run_id: str) -> dict[str, Any]:
    records = read_jsonl(input_path)
    rows = build_feature_rows(records)
    validate_feature_rows(rows)
    manifest = build_manifest(rows, run_id=run_id, input_ref=input_path)
    return {
        "mode": "dry_run",
        "output_written": False,
        "record_count": len(rows),
        "training_feature_columns": list(TRAINING_FEATURE_COLUMNS),
        "feature_columns": list(TRAINING_FEATURE_COLUMNS),
        "audit_only_columns": list(AUDIT_ONLY_COLUMNS),
        "excluded_columns": sorted(EXCLUDED_COLUMNS_WITH_REASONS),
        "excluded_columns_with_reasons": dict(sorted(EXCLUDED_COLUMNS_WITH_REASONS.items())),
        "leakage_risk_columns": list(LEAKAGE_RISK_COLUMNS),
        "manifest": manifest,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("selector_feature_matrix_%Y%m%d_%H%M%S"),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and validate the feature dataframe, then print a manifest without writing outputs.",
    )
    parser.add_argument("--no-csv", action="store_true", help="Do not write the CSV mirror.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run:
        result = dry_run_feature_matrix(args.input, run_id=args.run_id)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    paths = build_feature_matrix(
        args.input,
        args.output_dir,
        run_id=args.run_id,
        write_csv_output=not args.no_csv,
    )
    print(json.dumps({key: str(path) for key, path in paths.items()}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
