"""Trainability-first v0.4 selector baseline trainer.

This script consumes the v0.3 selector feature matrix as a read-only input. It
does not create trade signals, order instructions, production activation
artifacts, or new market-data inputs.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback only.
    tomllib = None  # type: ignore[assignment]


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = Path("Quant_mvp/config/v0_4_selector_model.toml")
DEFAULT_TRAINABILITY_MANIFEST = "v0_4_selector_trainability_manifest.json"
DEFAULT_MODEL_MANIFEST = "v0_4_selector_model_manifest.json"
DEFAULT_MODEL_ARTIFACT = "v0_4_selector_baseline_model.pkl"

TRAINED_STATUS = "trained_logistic_regression_baseline"
READY_STATUS = "ready_for_logistic_regression_baseline"
BLOCKED_NO_CLASSES = "blocked_no_positive_negative_classes"
BLOCKED_NO_EVIDENCE = "blocked_no_candidate_level_evidence"
BLOCKED_MISSING_DEPENDENCY = "blocked_missing_ml_dependency"
BLOCKED_NO_TRAINING_ROWS = "blocked_no_training_eligible_rows"
BLOCKED_MISSING_FEATURE = "blocked_missing_required_core_feature"
BLOCKED_LEAKAGE = "blocked_label_leakage_columns_found"
BLOCKED_GENERIC_PROXY_LABEL = "blocked_generic_proxy_used_as_label"

EXPECTED_TRAINING_FEATURE_COLUMNS = [
    "total_return",
    "excess_return_vs_proxy",
    "max_drawdown_abs",
    "sharpe",
    "turnover",
    "volatility",
]

DEFAULT_LEAKAGE_COLUMNS = {
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
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            records.append(payload)
    return records


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def load_config(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("tomllib is unavailable; use Python 3.11+ or provide tomli")
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a TOML object")
    return payload


def sklearn_available() -> bool:
    return importlib.util.find_spec("sklearn") is not None


def _as_label(value: Any) -> int | None:
    if value is True:
        return 1
    if value is False:
        return 0
    if value in {0, 1}:
        return int(value)
    if isinstance(value, str) and value.strip() in {"0", "1"}:
        return int(value.strip())
    return None


def _label_status_blocked(row: dict[str, Any]) -> bool:
    text = " ".join(
        str(row.get(column) or "").lower()
        for column in ("label_status", "label_reason_code", "training_exclusion_reason")
    )
    return "excluded" in text or "blocked" in text


def _candidate_level_metric(row: dict[str, Any]) -> bool:
    return row.get("metric_subject_type") == "strategy_candidate" and row.get("candidate_metric_match") is True


def _generic_proxy_row(row: dict[str, Any]) -> bool:
    return row.get("metric_subject_type") == "generic_proxy" or row.get("metric_role") == "generic_momentum_proxy"


def _feature_values(row: dict[str, Any]) -> dict[str, Any]:
    values = row.get("feature_values")
    if isinstance(values, dict):
        return dict(values)
    return {}


def _row_features(row: dict[str, Any], feature_columns: list[str]) -> list[float] | None:
    values = _feature_values(row)
    features: list[float] = []
    for column in feature_columns:
        value = values.get(column)
        if value is None:
            return None
        try:
            features.append(float(value))
        except (TypeError, ValueError):
            return None
    return features


def _count_bad_max_drawdown_abs(rows: list[dict[str, Any]]) -> int:
    bad_rows = 0
    for row in rows:
        max_drawdown = row.get("max_drawdown")
        max_drawdown_abs = row.get("max_drawdown_abs")
        if max_drawdown is None or max_drawdown_abs is None:
            continue
        try:
            if abs(abs(float(max_drawdown)) - float(max_drawdown_abs)) > 1e-12:
                bad_rows += 1
        except (TypeError, ValueError):
            bad_rows += 1
    return bad_rows


def _training_rows(rows: list[dict[str, Any]], feature_columns: list[str]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        label = _as_label(row.get("label_review_preferred"))
        if row.get("training_eligible") is not True:
            continue
        if not _candidate_level_metric(row):
            continue
        if _label_status_blocked(row):
            continue
        if label is None:
            continue
        if _row_features(row, feature_columns) is None:
            continue
        selected.append(row)
    return selected


def _manifest_int(manifest: dict[str, Any], key: str, default: int) -> int:
    value = manifest.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_trainability_manifest(
    rows: list[dict[str, Any]],
    source_manifest: dict[str, Any],
    config: dict[str, Any],
    *,
    has_ml_dependencies: bool,
    model_artifact_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    feature_columns = list(config["training_feature_columns"])
    leakage_columns = set(source_manifest.get("leakage_excluded_columns") or DEFAULT_LEAKAGE_COLUMNS)
    expected_feature_columns = list(EXPECTED_TRAINING_FEATURE_COLUMNS)
    duplicate_config_features = sorted(
        column
        for column in set(feature_columns)
        if feature_columns.count(column) > 1
    )
    feature_config_leak_columns = sorted(set(feature_columns) & leakage_columns)
    feature_config_unexpected_columns = sorted(set(feature_columns) - set(expected_feature_columns))
    feature_config_missing_columns = sorted(set(expected_feature_columns) - set(feature_columns))
    feature_config_matches_expected = feature_columns == expected_feature_columns
    training_rows = _training_rows(rows, feature_columns)

    feature_value_leak_rows = sum(
        bool(set(_feature_values(row)) & leakage_columns)
        for row in rows
    )
    generic_proxy_bad_rows = sum(
        _generic_proxy_row(row)
        and (
            row.get("training_eligible") is True
            or _candidate_level_metric(row)
            or _as_label(row.get("label_review_preferred")) is not None
        )
        for row in rows
    )
    missing_required_feature_rows = sum(
        row.get("training_eligible") is True
        and _candidate_level_metric(row)
        and _row_features(row, expected_feature_columns) is None
        for row in rows
    )
    labels = [_as_label(row.get("label_review_preferred")) for row in training_rows]
    positive_rows = sum(label == 1 for label in labels)
    negative_rows = sum(label == 0 for label in labels)
    candidate_level_metric_count = _manifest_int(
        source_manifest,
        "candidate_level_metric_count",
        sum(_candidate_level_metric(row) for row in rows),
    )
    warnings: list[str] = []
    threshold = int(config.get("model_defaults", {}).get("limited_training_rows_threshold", 100))
    correlation = source_manifest.get("total_return_excess_return_correlation")
    high_corr_threshold = float(config.get("model_defaults", {}).get("high_feature_correlation_threshold", 0.95))
    if len(training_rows) < threshold:
        warnings.append("limited_insufficient_training_rows")
    if isinstance(correlation, (int, float)) and abs(float(correlation)) >= high_corr_threshold:
        warnings.append("high_feature_correlation_warning")

    train_status = READY_STATUS
    train_blocked_reason: str | None = None
    if candidate_level_metric_count == 0:
        train_status = BLOCKED_NO_EVIDENCE
        train_blocked_reason = BLOCKED_NO_EVIDENCE
    elif feature_config_leak_columns or duplicate_config_features or feature_value_leak_rows:
        train_status = BLOCKED_LEAKAGE
        train_blocked_reason = BLOCKED_LEAKAGE
    elif not feature_config_matches_expected:
        train_status = BLOCKED_MISSING_FEATURE
        train_blocked_reason = BLOCKED_MISSING_FEATURE
    elif missing_required_feature_rows:
        train_status = BLOCKED_MISSING_FEATURE
        train_blocked_reason = BLOCKED_MISSING_FEATURE
    elif len(training_rows) == 0:
        train_status = BLOCKED_NO_TRAINING_ROWS
        train_blocked_reason = BLOCKED_NO_TRAINING_ROWS
    elif positive_rows == 0 or negative_rows == 0:
        train_status = BLOCKED_NO_CLASSES
        train_blocked_reason = BLOCKED_NO_CLASSES
    elif generic_proxy_bad_rows:
        train_status = BLOCKED_GENERIC_PROXY_LABEL
        train_blocked_reason = BLOCKED_GENERIC_PROXY_LABEL
    elif not has_ml_dependencies:
        train_status = BLOCKED_MISSING_DEPENDENCY
        train_blocked_reason = BLOCKED_MISSING_DEPENDENCY

    paths = config.get("paths", {})
    manifest = {
        "schema_version": "v0_4_selector_trainability_manifest_v1_0",
        "selector_model_version": config["selector_model_version"],
        "model_stage": config["model_stage"],
        "baseline_model": config["baseline_model"],
        "generated_at_utc": utc_now(),
        "input_feature_matrix_manifest": paths.get("feature_matrix_manifest"),
        "input_feature_matrix_jsonl": paths.get("feature_matrix_jsonl"),
        "source_feature_matrix_version": source_manifest.get("feature_matrix_version"),
        "matrix_intent": source_manifest.get("matrix_intent"),
        "allowed_use": config.get("boundaries", {}).get("allowed_use"),
        "prediction_claim": config.get("boundaries", {}).get("prediction_claim"),
        "trade_signal_claim": config.get("boundaries", {}).get("trade_signal_claim"),
        "total_rows": _manifest_int(source_manifest, "total_rows", len(rows)),
        "candidate_level_metric_count": candidate_level_metric_count,
        "training_eligible_rows": len(training_rows),
        "positive_rows": positive_rows,
        "negative_rows": negative_rows,
        "null_label_rows": _manifest_int(source_manifest, "null_label_rows", 0),
        "excluded_rows": _manifest_int(source_manifest, "excluded_rows", 0),
        "configured_training_feature_columns": feature_columns,
        "expected_training_feature_columns": expected_feature_columns,
        "required_feature_columns": expected_feature_columns,
        "training_feature_columns": feature_columns,
        "feature_config_matches_expected": feature_config_matches_expected,
        "feature_config_leak_columns": feature_config_leak_columns,
        "feature_config_unexpected_columns": feature_config_unexpected_columns,
        "feature_config_missing_columns": feature_config_missing_columns,
        "duplicate_config_feature_columns": duplicate_config_features,
        "missing_required_feature_rows": missing_required_feature_rows,
        "leakage_excluded_columns": sorted(leakage_columns),
        "feature_value_leak_rows": feature_value_leak_rows,
        "bad_max_drawdown_abs_rows": _count_bad_max_drawdown_abs(rows),
        "generic_proxy_bad_rows": generic_proxy_bad_rows,
        "total_return_excess_return_correlation": correlation,
        "warnings": warnings,
        "has_existing_model_artifact": model_artifact_path.exists(),
        "has_ml_dependencies": has_ml_dependencies,
        "train_status": train_status,
        "train_blocked_reason": train_blocked_reason,
        "model_artifact_created": False,
        "model_artifact_path": str(model_artifact_path.relative_to(PROJECT_ROOT)),
        "prediction_value_row_count": 0,
        "readiness_status": train_status,
    }
    return manifest, training_rows


def _default_model(config: dict[str, Any]) -> Any:
    from sklearn.linear_model import LogisticRegression

    defaults = config.get("model_defaults", {})
    return LogisticRegression(
        class_weight=defaults.get("class_weight", "balanced"),
        max_iter=int(defaults.get("max_iter", 1000)),
    )


def train_selector_baseline(
    *,
    config_path: Path,
    dependency_available: bool | None = None,
    model_factory: Any | None = None,
    write_outputs: bool = True,
) -> dict[str, Any]:
    config = load_config(config_path)
    paths = config["paths"]
    feature_matrix_path = resolve_path(paths["feature_matrix_jsonl"])
    source_manifest_path = resolve_path(paths["feature_matrix_manifest"])
    output_dir = resolve_path(paths["training_output_dir"])
    model_artifact_path = output_dir / DEFAULT_MODEL_ARTIFACT

    rows = read_jsonl(feature_matrix_path)
    source_manifest = read_json(source_manifest_path)
    has_dependency = sklearn_available() if dependency_available is None else dependency_available
    train_manifest, training_rows = build_trainability_manifest(
        rows,
        source_manifest,
        config,
        has_ml_dependencies=has_dependency,
        model_artifact_path=model_artifact_path,
    )

    if train_manifest["train_status"] == READY_STATUS:
        feature_columns = train_manifest["training_feature_columns"]
        x_values = [_row_features(row, feature_columns) for row in training_rows]
        if any(features is None for features in x_values):
            raise RuntimeError("training rows unexpectedly contain missing features")
        y_values = [_as_label(row["label_review_preferred"]) for row in training_rows]
        model = model_factory(config) if model_factory is not None else _default_model(config)
        model.fit(x_values, y_values)
        output_dir.mkdir(parents=True, exist_ok=True)
        if write_outputs:
            with model_artifact_path.open("wb") as handle:
                pickle.dump(model, handle)
        train_manifest["train_status"] = TRAINED_STATUS
        train_manifest["readiness_status"] = TRAINED_STATUS
        train_manifest["train_blocked_reason"] = None
        train_manifest["model_artifact_created"] = bool(write_outputs)
        model_manifest = {
            "schema_version": "v0_4_selector_model_manifest_v1_0",
            "selector_model_version": config["selector_model_version"],
            "model_stage": config["model_stage"],
            "baseline_model": config["baseline_model"],
            "generated_at_utc": utc_now(),
            "training_feature_columns": feature_columns,
            "training_eligible_rows": train_manifest["training_eligible_rows"],
            "positive_rows": train_manifest["positive_rows"],
            "negative_rows": train_manifest["negative_rows"],
            "class_weight": config.get("model_defaults", {}).get("class_weight", "balanced"),
            "max_iter": int(config.get("model_defaults", {}).get("max_iter", 1000)),
            "model_artifact_path": train_manifest["model_artifact_path"],
            "allowed_use": train_manifest["allowed_use"],
            "prediction_claim": train_manifest["prediction_claim"],
            "trade_signal_claim": train_manifest["trade_signal_claim"],
        }
        if write_outputs:
            write_json(output_dir / DEFAULT_MODEL_MANIFEST, model_manifest)

    if write_outputs:
        write_json(output_dir / DEFAULT_TRAINABILITY_MANIFEST, train_manifest)
    return train_manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = train_selector_baseline(config_path=resolve_path(args.config))
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
