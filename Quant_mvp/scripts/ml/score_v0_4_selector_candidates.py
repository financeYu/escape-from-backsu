"""Score v0.4 selector candidates from a trained evidence-only model.

Scores generated here are review-prioritization values for AdoptionCandidate
review only. They are not trade signals, order instructions, or production
activation inputs.
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

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.scripts.artifact_io import write_jsonl

TRAIN_SCRIPT = PROJECT_ROOT / "Quant_mvp" / "scripts" / "ml" / "train_v0_4_selector_baseline.py"
SPEC = importlib.util.spec_from_file_location("train_v0_4_selector_baseline", TRAIN_SCRIPT)
assert SPEC is not None
trainer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(trainer)

DEFAULT_SCORE_MANIFEST = "v0_4_selector_score_manifest.json"
DEFAULT_SCORE_JSONL = "v0_4_selector_scores.jsonl"
DEFAULT_RANDOM_FOREST_SCORE_MANIFEST = "v0_4_selector_random_forest_score_manifest.json"
DEFAULT_RANDOM_FOREST_SCORE_JSONL = "v0_4_selector_random_forest_scores.jsonl"
DEFAULT_COMPARISON_MANIFEST = "v0_4_selector_lr_rf_comparison_manifest.json"
DEFAULT_COMPARISON_JSONL = "v0_4_selector_lr_rf_comparison.jsonl"
DEFAULT_RANKING_MANIFEST = "v0_4_1_selector_ml_score_ranking_manifest.json"
DEFAULT_RANKING_JSONL = "v0_4_1_selector_ml_score_ranking.jsonl"
RANKING_SCHEMA_VERSION = "v0_4_1_selector_ml_score_ranking_row_v1_0"

SCORE_MODEL_REGISTRY = {
    "logistic_regression": {
        "model_id": "logistic_regression",
        "model_type": "logistic_regression",
        "model_role": "frozen_baseline",
        "score_manifest_name": DEFAULT_SCORE_MANIFEST,
        "score_rows_name": DEFAULT_SCORE_JSONL,
        "required_selector_score_source": "ml_model",
        "score_fields": ["selector_score"],
    },
    "random_forest": {
        "model_id": "random_forest",
        "model_type": "random_forest_classifier",
        "model_role": "nonlinear_challenger",
        "score_manifest_name": DEFAULT_RANDOM_FOREST_SCORE_MANIFEST,
        "score_rows_name": DEFAULT_RANDOM_FOREST_SCORE_JSONL,
        "required_selector_score_source": "random_forest_challenger",
        "score_fields": ["random_forest_prediction_value", "prediction_value"],
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _base_manifest(config: dict[str, Any]) -> dict[str, Any]:
    generated_at = utc_now()
    return {
        "schema_version": "v0_4_selector_score_manifest_v1_0",
        "scorer_version": "v0_4_selector_scorer_v1_0",
        "selector_model_version": config["selector_model_version"],
        "model_stage": config["model_stage"],
        "generated_at_utc": generated_at,
        "generated_at": generated_at,
        "selector_score_source": None,
        "scored_candidate_count": 0,
        "prediction_value_row_count": 0,
        "blocked_reason": None,
        "fallback_used": False,
        "fallback_reason": None,
        "warnings": [],
        "performance_claim_allowed": False,
        "evaluation_mode": "baseline_diagnostic_only",
        "allowed_use": config.get("boundaries", {}).get("allowed_use"),
        "trade_signal_claim": config.get("boundaries", {}).get("trade_signal_claim"),
    }


def _positive_class_index(model: Any) -> int:
    classes = getattr(model, "classes_", None)
    if classes is None:
        return 1
    for index, value in enumerate(classes):
        if value == 1:
            return index
    return len(classes) - 1


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _fallback(
    manifest: dict[str, Any],
    reason: str,
    *,
    warning: str | None = None,
    trainability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest["selector_score_source"] = "rule_only"
    manifest["blocked_reason"] = reason
    manifest["fallback_used"] = True
    manifest["fallback_reason"] = reason
    if warning:
        manifest["warnings"] = sorted(set(list(manifest.get("warnings") or []) + [warning]))
    _attach_score_discrimination_diagnostics(
        manifest,
        [],
        trainability=trainability,
        score_field="selector_score",
        selector_score_source="fallback",
    )
    return manifest


def _score_bucket_key(value: Any) -> str:
    try:
        return f"{float(value):.12g}"
    except (TypeError, ValueError):
        return "null"


def _attach_tie_diagnostics(
    score_rows: list[dict[str, Any]],
    *,
    score_field: str,
    tie_break_keys: list[str],
) -> None:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in score_rows:
        buckets.setdefault(_score_bucket_key(row.get(score_field)), []).append(row)
    for bucket_rows in buckets.values():
        ranked = sorted(
            bucket_rows,
            key=lambda row: tuple(str(row.get(key) or "") for key in tie_break_keys[1:]),
        )
        for rank, row in enumerate(ranked, start=1):
            row["tie_group_size"] = len(bucket_rows)
            row["tie_break_keys"] = list(tie_break_keys)
            row["rank_within_score_bucket"] = rank


def _score_source_from_manifest_value(value: Any) -> str:
    if value == "ml_model" or value == "random_forest_challenger":
        return "model_prediction"
    if value == "rule_only":
        return "fallback"
    if value == "blocked_train_status":
        return "unknown"
    return "unknown"


def _attach_score_discrimination_diagnostics(
    manifest: dict[str, Any],
    score_rows: list[dict[str, Any]],
    *,
    trainability: dict[str, Any] | None,
    score_field: str,
    selector_score_source: str | None = None,
    tie_break_keys: list[str] | None = None,
) -> None:
    tie_keys = list(tie_break_keys or [score_field, "candidate_id"])
    scores = [row.get(score_field) for row in score_rows if row.get(score_field) is not None]
    bucket_counts: dict[str, int] = {}
    for score in scores:
        key = _score_bucket_key(score)
        bucket_counts[key] = bucket_counts.get(key, 0) + 1
    train_diagnostics = {}
    if isinstance(trainability, dict):
        train_diagnostics = dict(trainability.get("score_discrimination_diagnostics") or {})
    manifest["score_discrimination_diagnostics"] = {
        "schema_version": "v0_4_selector_score_manifest_discrimination_diagnostics_v1_0",
        "selector_score_source": selector_score_source
        or _score_source_from_manifest_value(manifest.get("selector_score_source")),
        "fallback_used": bool(manifest.get("fallback_used")),
        "fallback_reason": manifest.get("fallback_reason"),
        "trainability_status": trainability.get("train_status") if isinstance(trainability, dict) else None,
        "trainability_failure_reasons": [
            reason
            for reason in [
                trainability.get("train_blocked_reason") if isinstance(trainability, dict) else None,
                manifest.get("blocked_reason"),
            ]
            if reason
        ],
        "target_unique_count": train_diagnostics.get("target_unique_count"),
        "target_bucket_count": train_diagnostics.get("target_bucket_count"),
        "target_value_counts": train_diagnostics.get("target_value_counts"),
        "model_prediction_unique_count": len(set(_score_bucket_key(score) for score in scores)),
        "selector_score_unique_count": len(set(_score_bucket_key(score) for score in scores)),
        "selector_score_bucket_count": len(bucket_counts),
        "selector_score_bucket_counts": dict(sorted(bucket_counts.items())),
        "feature_effective_column_count": train_diagnostics.get("feature_effective_column_count"),
        "low_variance_feature_count": train_diagnostics.get("low_variance_feature_count"),
        "all_null_feature_count": train_diagnostics.get("all_null_feature_count"),
        "neutral_filled_feature_count": train_diagnostics.get("neutral_filled_feature_count"),
        "feature_non_null_summary": train_diagnostics.get("feature_non_null_summary"),
        "feature_unique_count_summary": train_diagnostics.get("feature_unique_count_summary"),
        "feature_matrix_artifact_id": train_diagnostics.get("feature_matrix_artifact_id"),
        "label_manifest_artifact_id": train_diagnostics.get("label_manifest_artifact_id"),
        "feature_label_date_violation_count": train_diagnostics.get("feature_label_date_violation_count"),
        "feature_label_date_check_status": train_diagnostics.get("feature_label_date_check_status"),
        "max_tie_group_size": max(bucket_counts.values()) if bucket_counts else 0,
        "tie_break_keys": tie_keys,
        "deterministic_sort_fields": tie_keys,
        "score_formula_changed": False,
        "production_ranking_changed": False,
        "final_composite_score_changed": False,
        "technical_composite_score_changed": False,
    }


def _manifest_artifact_path_matches(model_manifest: dict[str, Any], expected_path: Path) -> bool:
    recorded = model_manifest.get("model_artifact_path") or model_manifest.get("artifact_path")
    if not recorded:
        return False
    return trainer.resolve_path(recorded).resolve() == expected_path.resolve()


def _model_manifest_mismatch_reasons(
    *,
    model_manifest: dict[str, Any],
    config: dict[str, Any],
    trainability: dict[str, Any],
    model_artifact_path: Path,
    expected_model_type: str = "logistic_regression",
    expected_model_family: str = "logistic_regression",
    expected_model_role: str | None = None,
) -> list[str]:
    reasons: list[str] = []
    if model_manifest.get("selector_model_version") != config["selector_model_version"]:
        reasons.append("selector_model_version_mismatch")
    if model_manifest.get("model_type") != expected_model_type:
        reasons.append("model_type_mismatch")
    if model_manifest.get("model_family") != expected_model_family:
        reasons.append("model_family_mismatch")
    if expected_model_role is not None and model_manifest.get("model_role") != expected_model_role:
        reasons.append("model_role_mismatch")
    if list(model_manifest.get("training_feature_columns") or []) != list(config["training_feature_columns"]):
        reasons.append("training_feature_columns_mismatch")
    if int(model_manifest.get("training_row_count", model_manifest.get("training_eligible_rows", -1))) != int(
        trainability.get("training_eligible_rows", -2)
    ):
        reasons.append("training_row_count_mismatch")
    if not _manifest_artifact_path_matches(model_manifest, model_artifact_path):
        reasons.append("model_artifact_path_mismatch")
    if model_manifest.get("model_artifact_created") is False:
        reasons.append("model_artifact_not_created")
    if model_manifest.get("has_ml_dependencies") is False:
        reasons.append("missing_ml_dependencies_in_model_manifest")
    return reasons


def _scoring_rows(rows: list[dict[str, Any]], feature_columns: list[str]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("training_eligible") is True
        and row.get("metric_subject_type") == "strategy_candidate"
        and row.get("candidate_metric_match") is True
        and trainer._row_features(row, feature_columns) is not None
    ]


def score_candidates(*, config_path: Path, write_outputs: bool = True) -> dict[str, Any]:
    config = trainer.load_config(config_path)
    paths = config["paths"]
    training_output_dir = trainer.resolve_path(paths["training_output_dir"])
    score_output_dir = trainer.resolve_path(paths["score_output_dir"])
    trainability_path = training_output_dir / trainer.DEFAULT_TRAINABILITY_MANIFEST
    model_manifest_path = training_output_dir / trainer.DEFAULT_MODEL_MANIFEST
    model_artifact_path = training_output_dir / trainer.DEFAULT_MODEL_ARTIFACT
    score_rows_path = score_output_dir / DEFAULT_SCORE_JSONL
    manifest = _base_manifest(config)
    manifest["model_artifact_path"] = _relative(model_artifact_path)
    manifest["model_manifest_path"] = _relative(model_manifest_path)
    manifest["trainability_manifest_path"] = _relative(trainability_path)
    manifest["score_rows_path"] = _relative(score_rows_path)

    if not trainability_path.exists():
        manifest["selector_score_source"] = "blocked_train_status"
        manifest["blocked_reason"] = "blocked_missing_trainability_manifest"
        _attach_score_discrimination_diagnostics(
            manifest,
            [],
            trainability=None,
            score_field="selector_score",
            selector_score_source="unknown",
        )
        if write_outputs:
            write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
        return manifest

    trainability = trainer.read_json(trainability_path)
    manifest["warnings"] = list(trainability.get("warnings") or [])
    if trainability.get("train_status") != trainer.TRAINED_STATUS:
        manifest["selector_score_source"] = "blocked_train_status"
        manifest["blocked_reason"] = trainability.get("train_blocked_reason") or trainability.get("train_status")
        _attach_score_discrimination_diagnostics(
            manifest,
            [],
            trainability=trainability,
            score_field="selector_score",
            selector_score_source="unknown",
        )
        if write_outputs:
            write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
        return manifest

    if not model_artifact_path.exists():
        _fallback(
            manifest,
            "rule_only_available_no_model_artifact",
            warning="model_artifact_missing_fallback",
            trainability=trainability,
        )
        if write_outputs:
            write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
        return manifest

    if not model_manifest_path.exists():
        _fallback(
            manifest,
            "rule_only_available_no_model_manifest",
            warning="model_manifest_missing_fallback",
            trainability=trainability,
        )
        if write_outputs:
            write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
        return manifest

    model_manifest = trainer.read_json(model_manifest_path)
    mismatch_reasons = _model_manifest_mismatch_reasons(
        model_manifest=model_manifest,
        config=config,
        trainability=trainability,
        model_artifact_path=model_artifact_path,
    )
    if mismatch_reasons:
        _fallback(
            manifest,
            "model_manifest_mismatch",
            warning="model_manifest_mismatch_fallback",
            trainability=trainability,
        )
        manifest["model_manifest_mismatch_reasons"] = mismatch_reasons
        if write_outputs:
            write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
        return manifest

    try:
        with model_artifact_path.open("rb") as handle:
            model = pickle.load(handle)
    except Exception as exc:  # pragma: no cover - defensive manifest path.
        _fallback(
            manifest,
            f"blocked_model_load_failed:{exc.__class__.__name__}",
            warning="model_artifact_load_failed_fallback",
            trainability=trainability,
        )
        if write_outputs:
            write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
        return manifest

    rows = trainer.read_jsonl(trainer.resolve_path(paths["feature_matrix_jsonl"]))
    feature_columns = list(config["training_feature_columns"])
    scoring_rows = _scoring_rows(rows, feature_columns)
    x_values = [trainer._row_features(row, feature_columns) for row in scoring_rows]
    probabilities = model.predict_proba(x_values)
    positive_index = _positive_class_index(model)
    score_rows: list[dict[str, Any]] = []
    for row, probability in zip(scoring_rows, probabilities):
        score_rows.append(
            {
                "schema_version": "v0_4_selector_score_row_v1_0",
                "selector_model_version": config["selector_model_version"],
                "selector_score_source": "ml_model",
                "candidate_id": row.get("candidate_id"),
                "evidence_id": row.get("evidence_id"),
                "selector_score": float(probability[positive_index]),
                "allowed_use": config.get("boundaries", {}).get("allowed_use"),
                "trade_signal_claim": config.get("boundaries", {}).get("trade_signal_claim"),
            }
        )

    _attach_tie_diagnostics(
        score_rows,
        score_field="selector_score",
        tie_break_keys=["selector_score", "candidate_id"],
    )
    manifest["selector_score_source"] = "ml_model"
    manifest["scored_candidate_count"] = len(score_rows)
    manifest["prediction_value_row_count"] = len(score_rows)
    manifest["fallback_used"] = False
    manifest["fallback_reason"] = None
    _attach_score_discrimination_diagnostics(
        manifest,
        score_rows,
        trainability=trainability,
        score_field="selector_score",
        selector_score_source="model_prediction",
        tie_break_keys=["selector_score", "candidate_id"],
    )
    if write_outputs:
        write_jsonl(score_rows_path, score_rows)
        write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
    return manifest


def _blocked_challenger(
    manifest: dict[str, Any],
    reason: str,
    *,
    warning: str | None = None,
) -> dict[str, Any]:
    manifest["selector_score_source"] = "random_forest_challenger_blocked"
    manifest["blocked_reason"] = reason
    manifest["fallback_used"] = False
    manifest["fallback_reason"] = None
    if warning:
        manifest["warnings"] = sorted(set(list(manifest.get("warnings") or []) + [warning]))
    return manifest


def score_random_forest_candidates(*, config_path: Path, write_outputs: bool = True) -> dict[str, Any]:
    config = trainer.load_config(config_path)
    paths = config["paths"]
    training_output_dir = trainer.resolve_path(paths["training_output_dir"])
    score_output_dir = trainer.resolve_path(paths["score_output_dir"])
    trainability_path = training_output_dir / trainer.DEFAULT_TRAINABILITY_MANIFEST
    model_manifest_path = training_output_dir / trainer.DEFAULT_RANDOM_FOREST_MODEL_MANIFEST
    model_artifact_path = training_output_dir / trainer.DEFAULT_RANDOM_FOREST_MODEL_ARTIFACT
    score_rows_path = score_output_dir / DEFAULT_RANDOM_FOREST_SCORE_JSONL
    manifest = _base_manifest(config)
    manifest.update(
        {
            "schema_version": "v0_4_selector_random_forest_score_manifest_v1_0",
            "selector_score_source": "random_forest_challenger",
            "model_role": "nonlinear_challenger",
            "challenger_only": True,
            "baseline_replacement": False,
            "selector_score_source_default_changed": False,
            "evaluation_mode": "diagnostic_comparison_only",
            "model_artifact_path": _relative(model_artifact_path),
            "model_manifest_path": _relative(model_manifest_path),
            "trainability_manifest_path": _relative(trainability_path),
            "score_rows_path": _relative(score_rows_path),
        }
    )

    if not trainability_path.exists():
        _blocked_challenger(manifest, "blocked_missing_trainability_manifest")
        _attach_score_discrimination_diagnostics(
            manifest,
            [],
            trainability=None,
            score_field="prediction_value",
            selector_score_source="unknown",
            tie_break_keys=["prediction_value", "candidate_id"],
        )
        if write_outputs:
            write_json(score_output_dir / DEFAULT_RANDOM_FOREST_SCORE_MANIFEST, manifest)
        return manifest

    trainability = trainer.read_json(trainability_path)
    manifest["warnings"] = list(trainability.get("warnings") or [])
    if trainability.get("train_status") != trainer.TRAINED_STATUS:
        _blocked_challenger(
            manifest,
            trainability.get("train_blocked_reason") or trainability.get("train_status"),
        )
        _attach_score_discrimination_diagnostics(
            manifest,
            [],
            trainability=trainability,
            score_field="prediction_value",
            selector_score_source="unknown",
            tie_break_keys=["prediction_value", "candidate_id"],
        )
        if write_outputs:
            write_json(score_output_dir / DEFAULT_RANDOM_FOREST_SCORE_MANIFEST, manifest)
        return manifest

    if not model_artifact_path.exists():
        _blocked_challenger(manifest, "random_forest_model_artifact_missing", warning="random_forest_artifact_missing")
        if write_outputs:
            write_json(score_output_dir / DEFAULT_RANDOM_FOREST_SCORE_MANIFEST, manifest)
        return manifest

    if not model_manifest_path.exists():
        _blocked_challenger(manifest, "random_forest_model_manifest_missing", warning="random_forest_manifest_missing")
        if write_outputs:
            write_json(score_output_dir / DEFAULT_RANDOM_FOREST_SCORE_MANIFEST, manifest)
        return manifest

    model_manifest = trainer.read_json(model_manifest_path)
    mismatch_reasons = _model_manifest_mismatch_reasons(
        model_manifest=model_manifest,
        config=config,
        trainability=trainability,
        model_artifact_path=model_artifact_path,
        expected_model_type="random_forest_classifier",
        expected_model_family="random_forest",
        expected_model_role="nonlinear_challenger",
    )
    if mismatch_reasons:
        _blocked_challenger(manifest, "random_forest_model_manifest_mismatch", warning="random_forest_manifest_mismatch")
        manifest["model_manifest_mismatch_reasons"] = mismatch_reasons
        if write_outputs:
            write_json(score_output_dir / DEFAULT_RANDOM_FOREST_SCORE_MANIFEST, manifest)
        return manifest

    try:
        with model_artifact_path.open("rb") as handle:
            model = pickle.load(handle)
    except Exception as exc:  # pragma: no cover - defensive manifest path.
        _blocked_challenger(
            manifest,
            f"blocked_random_forest_model_load_failed:{exc.__class__.__name__}",
            warning="random_forest_model_artifact_load_failed",
        )
        if write_outputs:
            write_json(score_output_dir / DEFAULT_RANDOM_FOREST_SCORE_MANIFEST, manifest)
        return manifest

    rows = trainer.read_jsonl(trainer.resolve_path(paths["feature_matrix_jsonl"]))
    feature_columns = list(config["training_feature_columns"])
    scoring_rows = _scoring_rows(rows, feature_columns)
    x_values = [trainer._row_features(row, feature_columns) for row in scoring_rows]
    probabilities = model.predict_proba(x_values)
    positive_index = _positive_class_index(model)
    score_rows: list[dict[str, Any]] = []
    for row, probability in zip(scoring_rows, probabilities):
        prediction_value = float(probability[positive_index])
        score_rows.append(
            {
                "schema_version": "v0_4_selector_random_forest_score_row_v1_0",
                "selector_model_version": config["selector_model_version"],
                "selector_score_source": "random_forest_challenger",
                "model_role": "nonlinear_challenger",
                "candidate_id": row.get("candidate_id"),
                "evidence_id": row.get("evidence_id"),
                "prediction_value": prediction_value,
                "random_forest_prediction_value": prediction_value,
                "allowed_use": config.get("boundaries", {}).get("allowed_use"),
                "trade_signal_claim": config.get("boundaries", {}).get("trade_signal_claim"),
                "evaluation_mode": "diagnostic_comparison_only",
            }
        )

    _attach_tie_diagnostics(
        score_rows,
        score_field="prediction_value",
        tie_break_keys=["prediction_value", "candidate_id"],
    )
    manifest["selector_score_source"] = "random_forest_challenger"
    manifest["scored_candidate_count"] = len(score_rows)
    manifest["prediction_value_row_count"] = len(score_rows)
    manifest["fallback_used"] = False
    manifest["fallback_reason"] = None
    _attach_score_discrimination_diagnostics(
        manifest,
        score_rows,
        trainability=trainability,
        score_field="prediction_value",
        selector_score_source="model_prediction",
        tie_break_keys=["prediction_value", "candidate_id"],
    )
    if write_outputs:
        write_jsonl(score_rows_path, score_rows)
        write_json(score_output_dir / DEFAULT_RANDOM_FOREST_SCORE_MANIFEST, manifest)
    return manifest


def _rank_map(score_by_candidate: dict[str, float]) -> dict[str, int]:
    ranked = sorted(score_by_candidate.items(), key=lambda item: (-item[1], item[0]))
    return {candidate_id: rank for rank, (candidate_id, _score) in enumerate(ranked, start=1)}


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    x_mean = _mean(xs)
    y_mean = _mean(ys)
    if x_mean is None or y_mean is None:
        return None
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    x_var = sum((x - x_mean) ** 2 for x in xs)
    y_var = sum((y - y_mean) ** 2 for y in ys)
    if x_var == 0 or y_var == 0:
        return None
    return numerator / ((x_var * y_var) ** 0.5)


def _read_jsonl_if_exists(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return trainer.read_jsonl(path)


def _configured_model_ids(config: dict[str, Any]) -> list[str]:
    ranking = config.get("ranking", {})
    configured = ranking.get("compared_model_ids")
    if isinstance(configured, list) and configured:
        return [str(model_id) for model_id in configured]
    return ["logistic_regression", "random_forest"]


def _baseline_model_id(config: dict[str, Any]) -> str:
    ranking = config.get("ranking", {})
    return str(ranking.get("baseline_model_id") or "logistic_regression")


def _top_k_values(config: dict[str, Any], fallback_top_n: int = 5) -> list[int]:
    ranking = config.get("ranking", {})
    configured = ranking.get("top_k_values")
    if isinstance(configured, list) and configured:
        values = sorted({int(value) for value in configured if int(value) > 0})
        if values:
            return values
    return [fallback_top_n]


def _score_value(row: dict[str, Any], score_fields: list[str]) -> float | None:
    for field in score_fields:
        value = row.get(field)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _model_scores_from_manifest(
    *,
    model_id: str,
    spec: dict[str, Any],
    score_output_dir: Path,
) -> tuple[dict[str, Any] | None, dict[str, float]]:
    manifest_path = score_output_dir / str(spec["score_manifest_name"])
    if not manifest_path.exists():
        return None, {}
    manifest = trainer.read_json(manifest_path)
    if manifest.get("selector_score_source") != spec["required_selector_score_source"] or manifest.get("blocked_reason"):
        return manifest, {}
    rows_path = trainer.resolve_path(manifest.get("score_rows_path") or (score_output_dir / str(spec["score_rows_name"])))
    rows = _read_jsonl_if_exists(rows_path)
    scores: dict[str, float] = {}
    for row in rows:
        candidate_id = row.get("candidate_id")
        value = _score_value(row, list(spec["score_fields"]))
        if candidate_id is not None and value is not None:
            scores[str(candidate_id)] = value
    return manifest, scores


def _top_k_overlap_summary(
    *,
    scores_by_model: dict[str, dict[str, float]],
    baseline_model_id: str,
    top_k_values: list[int],
) -> dict[str, Any]:
    baseline_scores = scores_by_model.get(baseline_model_id, {})
    summary: dict[str, Any] = {}
    for top_k in top_k_values:
        effective_top_k = min(top_k, len(baseline_scores))
        baseline_top = {
            candidate_id
            for candidate_id, _score in sorted(
                baseline_scores.items(),
                key=lambda item: (-item[1], item[0]),
            )[:effective_top_k]
        }
        per_model: dict[str, Any] = {}
        for model_id, scores in sorted(scores_by_model.items()):
            if model_id == baseline_model_id:
                continue
            model_effective_top_k = min(top_k, len(scores))
            model_top = {
                candidate_id
                for candidate_id, _score in sorted(
                    scores.items(),
                    key=lambda item: (-item[1], item[0]),
                )[:model_effective_top_k]
            }
            overlap = len(baseline_top & model_top)
            denominator = min(effective_top_k, model_effective_top_k)
            per_model[model_id] = {
                "top_k": top_k,
                "overlap_count": overlap,
                "overlap_ratio": (overlap / denominator) if denominator else None,
            }
        summary[str(top_k)] = per_model
    return summary


def _same_candidate_set(scores_by_model: dict[str, dict[str, float]], model_ids: list[str]) -> set[str]:
    if not model_ids:
        return set()
    candidate_ids = set(scores_by_model.get(model_ids[0], {}))
    for model_id in model_ids[1:]:
        candidate_ids &= set(scores_by_model.get(model_id, {}))
    return candidate_ids


def _filter_scores_to_candidates(
    scores_by_model: dict[str, dict[str, float]],
    candidate_ids: set[str],
) -> dict[str, dict[str, float]]:
    return {
        model_id: {
            candidate_id: score
            for candidate_id, score in scores.items()
            if candidate_id in candidate_ids
        }
        for model_id, scores in scores_by_model.items()
    }


def build_ml_score_ranking(
    *,
    config_path: Path,
    top_k_values: list[int] | None = None,
    write_outputs: bool = True,
) -> dict[str, Any]:
    config = trainer.load_config(config_path)
    paths = config["paths"]
    score_output_dir = trainer.resolve_path(paths["score_output_dir"])
    ranking_rows_path = score_output_dir / DEFAULT_RANKING_JSONL
    manifest_path = score_output_dir / DEFAULT_RANKING_MANIFEST
    model_ids = _configured_model_ids(config)
    baseline_model_id = _baseline_model_id(config)
    if baseline_model_id not in model_ids:
        model_ids = [baseline_model_id] + model_ids
    configured_top_k = top_k_values or _top_k_values(config)

    blocked_reasons: list[str] = []
    source_manifest_paths: dict[str, str] = {}
    scores_by_model: dict[str, dict[str, float]] = {}
    for model_id in model_ids:
        spec = SCORE_MODEL_REGISTRY.get(model_id)
        if spec is None:
            blocked_reasons.append(f"unknown_model_id:{model_id}")
            scores_by_model[model_id] = {}
            continue
        manifest_path_for_model = score_output_dir / str(spec["score_manifest_name"])
        source_manifest_paths[model_id] = _relative(manifest_path_for_model)
        manifest, scores = _model_scores_from_manifest(
            model_id=model_id,
            spec=spec,
            score_output_dir=score_output_dir,
        )
        if manifest is None:
            blocked_reasons.append(f"missing_score_manifest:{model_id}")
        elif not scores:
            blocked_reasons.append(f"scores_unavailable:{model_id}")
        scores_by_model[model_id] = scores

    all_candidate_ids = set().union(*(set(scores) for scores in scores_by_model.values()))
    same_set_candidate_ids = _same_candidate_set(scores_by_model, model_ids)
    candidate_ids = sorted(same_set_candidate_ids)
    ranking_scores_by_model = _filter_scores_to_candidates(scores_by_model, same_set_candidate_ids)
    ranks_by_model = {model_id: _rank_map(scores) for model_id, scores in ranking_scores_by_model.items()}
    rows: list[dict[str, Any]] = []
    for candidate_id in candidate_ids:
        model_scores: dict[str, float | None] = {
            model_id: ranking_scores_by_model[model_id].get(candidate_id)
            for model_id in model_ids
        }
        model_ranks: dict[str, int | None] = {
            model_id: ranks_by_model[model_id].get(candidate_id)
            for model_id in model_ids
        }
        model_available = {
            model_id: model_scores[model_id] is not None
            for model_id in model_ids
        }
        baseline_score = model_scores.get(baseline_model_id)
        baseline_rank = model_ranks.get(baseline_model_id)
        baseline_relative: dict[str, dict[str, float | int | None]] = {}
        for model_id in model_ids:
            if model_id == baseline_model_id:
                continue
            score = model_scores.get(model_id)
            rank = model_ranks.get(model_id)
            baseline_relative[model_id] = {
                "score_delta": (score - baseline_score) if score is not None and baseline_score is not None else None,
                "rank_delta": (rank - baseline_rank) if rank is not None and baseline_rank is not None else None,
            }
        row: dict[str, Any] = {
            "schema_version": RANKING_SCHEMA_VERSION,
            "selector_model_version": config["selector_model_version"],
            "candidate_id": candidate_id,
            "evaluation_mode": "diagnostic_ranking_only",
            "baseline_model_id": baseline_model_id,
            "compared_model_ids": list(model_ids),
            "model_scores": model_scores,
            "model_ranks": model_ranks,
            "model_score_available": model_available,
            "baseline_score": baseline_score,
            "baseline_rank": baseline_rank,
            "baseline_relative": baseline_relative,
            "selector_score_source_unchanged": True,
            "performance_claim_allowed": False,
            "trading_signal_allowed": False,
        }
        for model_id in model_ids:
            row[f"{model_id}_score"] = model_scores.get(model_id)
            row[f"{model_id}_rank"] = model_ranks.get(model_id)
            row[f"{model_id}_available"] = model_available.get(model_id)
            if model_id != baseline_model_id:
                row[f"{model_id}_score_delta_vs_{baseline_model_id}"] = baseline_relative[model_id]["score_delta"]
                row[f"{model_id}_rank_delta_vs_{baseline_model_id}"] = baseline_relative[model_id]["rank_delta"]
        rows.append(row)

    per_model_score_available_count = {
        model_id: len(scores_by_model.get(model_id, {}))
        for model_id in model_ids
    }
    per_model_score_missing_from_same_set_count = {
        model_id: len(all_candidate_ids - set(scores_by_model.get(model_id, {})))
        for model_id in model_ids
    }
    per_model_score_excluded_from_ranking_count = {
        model_id: len(set(scores_by_model.get(model_id, {})) - same_set_candidate_ids)
        for model_id in model_ids
    }
    top_k_overlap = _top_k_overlap_summary(
        scores_by_model=ranking_scores_by_model,
        baseline_model_id=baseline_model_id,
        top_k_values=configured_top_k,
    )
    manifest = {
        "schema_version": "v0_4_1_selector_ml_score_ranking_manifest_v1_0",
        "selector_model_version": config["selector_model_version"],
        "model_stage": config["model_stage"],
        "generated_at_utc": utc_now(),
        "evaluation_mode": "diagnostic_ranking_only",
        "baseline_model_id": baseline_model_id,
        "compared_model_ids": list(model_ids),
        "candidate_count": len(rows),
        "all_scored_candidate_count": len(all_candidate_ids),
        "candidate_set_policy": "same_candidate_set_intersection_of_compared_model_scores",
        "per_model_score_available_count": per_model_score_available_count,
        "per_model_score_missing_from_same_set_count": per_model_score_missing_from_same_set_count,
        "per_model_score_excluded_from_ranking_count": per_model_score_excluded_from_ranking_count,
        "ranking_schema_version": RANKING_SCHEMA_VERSION,
        "ranking_rows_path": _relative(ranking_rows_path),
        "source_score_manifest_paths": source_manifest_paths,
        "selector_score_source_unchanged": True,
        "baseline_relative_score_model_id": baseline_model_id,
        "performance_claim_allowed": False,
        "trading_signal_allowed": False,
        "adoption_auto_decision_allowed": False,
        "diagnostic_reference_only": True,
        "top_k_values": configured_top_k,
        "top_k_overlap": top_k_overlap,
        "blocked_reason": ";".join(blocked_reasons) if blocked_reasons else None,
        "warnings": sorted(blocked_reasons),
    }
    if write_outputs:
        write_jsonl(ranking_rows_path, rows)
        write_json(manifest_path, manifest)
    return manifest


def compare_logistic_regression_random_forest_scores(
    *,
    config_path: Path,
    top_n: int = 5,
    write_outputs: bool = True,
) -> dict[str, Any]:
    config = trainer.load_config(config_path)
    paths = config["paths"]
    score_output_dir = trainer.resolve_path(paths["score_output_dir"])
    lr_manifest_path = score_output_dir / DEFAULT_SCORE_MANIFEST
    rf_manifest_path = score_output_dir / DEFAULT_RANDOM_FOREST_SCORE_MANIFEST
    comparison_rows_path = score_output_dir / DEFAULT_COMPARISON_JSONL
    manifest_path = score_output_dir / DEFAULT_COMPARISON_MANIFEST
    ranking_manifest = build_ml_score_ranking(
        config_path=config_path,
        top_k_values=_top_k_values(config, fallback_top_n=top_n),
        write_outputs=write_outputs,
    )
    manifest = {
        "schema_version": "v0_4_selector_lr_rf_comparison_manifest_v1_0",
        "selector_model_version": config["selector_model_version"],
        "model_stage": config["model_stage"],
        "generated_at_utc": utc_now(),
        "evaluation_mode": "diagnostic_comparison_only",
        "performance_claim_allowed": False,
        "trading_signal_allowed": False,
        "adoption_auto_decision_allowed": False,
        "diagnostic_reference_only": True,
        "baseline_model": "logistic_regression",
        "challenger_model": "random_forest_classifier",
        "baseline_replacement": False,
        "selector_score_source_default_changed": False,
        "ranking_manifest_path": _relative(score_output_dir / DEFAULT_RANKING_MANIFEST),
        "comparison_rows_path": _relative(comparison_rows_path),
        "logistic_regression_score_manifest_path": _relative(lr_manifest_path),
        "random_forest_score_manifest_path": _relative(rf_manifest_path),
        "blocked_reason": None,
        "warnings": [],
        "summary": {
            "compared_candidate_count": 0,
            "lr_score_available_count": 0,
            "rf_score_available_count": 0,
            "mean_abs_score_delta": None,
            "max_abs_score_delta": None,
            "rank_correlation": None,
            "top_n_overlap": 0,
            "top_n": top_n,
            "ranking_top_k_overlap": ranking_manifest.get("top_k_overlap"),
        },
    }

    if not lr_manifest_path.exists():
        manifest["blocked_reason"] = "missing_logistic_regression_score_manifest"
        if write_outputs:
            write_json(manifest_path, manifest)
        return manifest
    if not rf_manifest_path.exists():
        manifest["blocked_reason"] = "missing_random_forest_score_manifest"
        if write_outputs:
            write_json(manifest_path, manifest)
        return manifest

    lr_manifest = trainer.read_json(lr_manifest_path)
    rf_manifest = trainer.read_json(rf_manifest_path)
    manifest["warnings"] = sorted(set(list(lr_manifest.get("warnings") or []) + list(rf_manifest.get("warnings") or [])))
    if lr_manifest.get("selector_score_source") != "ml_model" or lr_manifest.get("blocked_reason"):
        manifest["blocked_reason"] = "logistic_regression_scores_unavailable"
        if write_outputs:
            write_json(manifest_path, manifest)
        return manifest
    if rf_manifest.get("selector_score_source") != "random_forest_challenger" or rf_manifest.get("blocked_reason"):
        manifest["blocked_reason"] = "random_forest_scores_unavailable"
        if write_outputs:
            write_json(manifest_path, manifest)
        return manifest

    lr_rows = _read_jsonl_if_exists(trainer.resolve_path(lr_manifest["score_rows_path"]))
    rf_rows = _read_jsonl_if_exists(trainer.resolve_path(rf_manifest["score_rows_path"]))
    lr_scores = {
        str(row["candidate_id"]): float(row["selector_score"])
        for row in lr_rows
        if row.get("candidate_id") is not None and row.get("selector_score") is not None
    }
    rf_scores = {
        str(row["candidate_id"]): float(row.get("random_forest_prediction_value", row.get("prediction_value")))
        for row in rf_rows
        if row.get("candidate_id") is not None
        and row.get("random_forest_prediction_value", row.get("prediction_value")) is not None
    }
    common_candidate_ids = sorted(set(lr_scores) & set(rf_scores))
    common_candidate_set = set(common_candidate_ids)
    lr_common_scores = {
        candidate_id: score
        for candidate_id, score in lr_scores.items()
        if candidate_id in common_candidate_set
    }
    rf_common_scores = {
        candidate_id: score
        for candidate_id, score in rf_scores.items()
        if candidate_id in common_candidate_set
    }
    lr_ranks = _rank_map(lr_common_scores)
    rf_ranks = _rank_map(rf_common_scores)
    comparison_rows: list[dict[str, Any]] = []
    for candidate_id in common_candidate_ids:
        lr_value = lr_scores[candidate_id]
        rf_value = rf_scores[candidate_id]
        score_rank_lr = lr_ranks[candidate_id]
        score_rank_rf = rf_ranks[candidate_id]
        comparison_rows.append(
            {
                "schema_version": "v0_4_selector_lr_rf_comparison_row_v1_0",
                "selector_model_version": config["selector_model_version"],
                "candidate_id": candidate_id,
                "logistic_regression_prediction_value": lr_value,
                "random_forest_prediction_value": rf_value,
                "score_delta": rf_value - lr_value,
                "score_rank_lr": score_rank_lr,
                "score_rank_rf": score_rank_rf,
                "baseline_model_id": "logistic_regression",
                "challenger_model_id": "random_forest",
                "baseline_score": lr_value,
                "challenger_score": rf_value,
                "baseline_rank": score_rank_lr,
                "challenger_rank": score_rank_rf,
                "rank_delta": score_rank_rf - score_rank_lr,
                "evaluation_mode": "diagnostic_comparison_only",
            }
        )

    abs_deltas = [abs(row["score_delta"]) for row in comparison_rows]
    rank_correlation = _pearson(
        [float(row["score_rank_lr"]) for row in comparison_rows],
        [float(row["score_rank_rf"]) for row in comparison_rows],
    )
    effective_top_n = min(top_n, len(common_candidate_ids))
    lr_top = {
        candidate_id
        for candidate_id, _score in sorted(
            lr_common_scores.items(),
            key=lambda item: (-item[1], item[0]),
        )[:effective_top_n]
    }
    rf_top = {
        candidate_id
        for candidate_id, _score in sorted(
            rf_common_scores.items(),
            key=lambda item: (-item[1], item[0]),
        )[:effective_top_n]
    }
    top_n_overlap = len(lr_top & rf_top)
    manifest["summary"] = {
        "compared_candidate_count": len(comparison_rows),
        "lr_score_available_count": len(lr_scores),
        "rf_score_available_count": len(rf_scores),
        "mean_abs_score_delta": _mean(abs_deltas),
        "max_abs_score_delta": max(abs_deltas) if abs_deltas else None,
        "rank_correlation": rank_correlation,
        "top_n_overlap": top_n_overlap,
        "top_n": top_n,
        "top_n_overlap_ratio": (top_n_overlap / effective_top_n) if effective_top_n else None,
        "ranking_top_k_overlap": ranking_manifest.get("top_k_overlap"),
        "baseline_model_id": "logistic_regression",
        "challenger_model_id": "random_forest",
    }
    if write_outputs:
        write_jsonl(comparison_rows_path, comparison_rows)
        write_json(manifest_path, manifest)
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=trainer.DEFAULT_CONFIG)
    parser.add_argument(
        "--mode",
        choices=["logistic_regression", "random_forest", "comparison", "ranking", "all"],
        default="logistic_regression",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_path = trainer.resolve_path(args.config)
    if args.mode == "random_forest":
        manifest = score_random_forest_candidates(config_path=config_path)
    elif args.mode == "ranking":
        manifest = build_ml_score_ranking(config_path=config_path)
    elif args.mode == "comparison":
        manifest = compare_logistic_regression_random_forest_scores(config_path=config_path)
    elif args.mode == "all":
        score_candidates(config_path=config_path)
        score_random_forest_candidates(config_path=config_path)
        manifest = compare_logistic_regression_random_forest_scores(config_path=config_path)
    else:
        manifest = score_candidates(config_path=config_path)
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
