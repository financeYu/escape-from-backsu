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
TRAIN_SCRIPT = PROJECT_ROOT / "Quant_mvp" / "scripts" / "ml" / "train_v0_4_selector_baseline.py"
SPEC = importlib.util.spec_from_file_location("train_v0_4_selector_baseline", TRAIN_SCRIPT)
assert SPEC is not None
trainer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(trainer)

DEFAULT_SCORE_MANIFEST = "v0_4_selector_score_manifest.json"
DEFAULT_SCORE_JSONL = "v0_4_selector_scores.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
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


def _fallback(manifest: dict[str, Any], reason: str, *, warning: str | None = None) -> dict[str, Any]:
    manifest["selector_score_source"] = "rule_only"
    manifest["blocked_reason"] = reason
    manifest["fallback_used"] = True
    manifest["fallback_reason"] = reason
    if warning:
        manifest["warnings"] = sorted(set(list(manifest.get("warnings") or []) + [warning]))
    return manifest


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
) -> list[str]:
    reasons: list[str] = []
    if model_manifest.get("selector_model_version") != config["selector_model_version"]:
        reasons.append("selector_model_version_mismatch")
    if model_manifest.get("model_type") not in {None, "logistic_regression"}:
        reasons.append("model_type_mismatch")
    if model_manifest.get("model_family") not in {None, "logistic_regression"}:
        reasons.append("model_family_mismatch")
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
        if write_outputs:
            write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
        return manifest

    trainability = trainer.read_json(trainability_path)
    manifest["warnings"] = list(trainability.get("warnings") or [])
    if trainability.get("train_status") != trainer.TRAINED_STATUS:
        manifest["selector_score_source"] = "blocked_train_status"
        manifest["blocked_reason"] = trainability.get("train_blocked_reason") or trainability.get("train_status")
        if write_outputs:
            write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
        return manifest

    if not model_artifact_path.exists():
        _fallback(manifest, "rule_only_available_no_model_artifact", warning="model_artifact_missing_fallback")
        if write_outputs:
            write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
        return manifest

    if not model_manifest_path.exists():
        _fallback(manifest, "rule_only_available_no_model_manifest", warning="model_manifest_missing_fallback")
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
        _fallback(manifest, "model_manifest_mismatch", warning="model_manifest_mismatch_fallback")
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
        )
        if write_outputs:
            write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
        return manifest

    rows = trainer.read_jsonl(trainer.resolve_path(paths["feature_matrix_jsonl"]))
    feature_columns = list(config["training_feature_columns"])
    scoring_rows = [
        row
        for row in rows
        if row.get("training_eligible") is True
        and row.get("metric_subject_type") == "strategy_candidate"
        and row.get("candidate_metric_match") is True
        and trainer._row_features(row, feature_columns) is not None
    ]
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

    manifest["selector_score_source"] = "ml_model"
    manifest["scored_candidate_count"] = len(score_rows)
    manifest["prediction_value_row_count"] = len(score_rows)
    manifest["fallback_used"] = False
    manifest["fallback_reason"] = None
    if write_outputs:
        write_jsonl(score_rows_path, score_rows)
        write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=trainer.DEFAULT_CONFIG)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = score_candidates(config_path=trainer.resolve_path(args.config))
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
