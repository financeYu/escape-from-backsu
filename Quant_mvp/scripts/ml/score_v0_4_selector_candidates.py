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
    return {
        "schema_version": "v0_4_selector_score_manifest_v1_0",
        "selector_model_version": config["selector_model_version"],
        "model_stage": config["model_stage"],
        "generated_at_utc": utc_now(),
        "selector_score_source": None,
        "scored_candidate_count": 0,
        "prediction_value_row_count": 0,
        "blocked_reason": None,
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


def score_candidates(*, config_path: Path, write_outputs: bool = True) -> dict[str, Any]:
    config = trainer.load_config(config_path)
    paths = config["paths"]
    training_output_dir = trainer.resolve_path(paths["training_output_dir"])
    score_output_dir = trainer.resolve_path(paths["score_output_dir"])
    trainability_path = training_output_dir / trainer.DEFAULT_TRAINABILITY_MANIFEST
    model_artifact_path = training_output_dir / trainer.DEFAULT_MODEL_ARTIFACT
    manifest = _base_manifest(config)

    if not trainability_path.exists():
        manifest["selector_score_source"] = "blocked_train_status"
        manifest["blocked_reason"] = "blocked_missing_trainability_manifest"
        if write_outputs:
            write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
        return manifest

    trainability = trainer.read_json(trainability_path)
    if trainability.get("train_status") != trainer.TRAINED_STATUS:
        manifest["selector_score_source"] = "blocked_train_status"
        manifest["blocked_reason"] = trainability.get("train_blocked_reason") or trainability.get("train_status")
        if write_outputs:
            write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
        return manifest

    if not model_artifact_path.exists():
        manifest["selector_score_source"] = "rule_only"
        manifest["blocked_reason"] = "rule_only_available_no_model_artifact"
        if write_outputs:
            write_json(score_output_dir / DEFAULT_SCORE_MANIFEST, manifest)
        return manifest

    try:
        with model_artifact_path.open("rb") as handle:
            model = pickle.load(handle)
    except Exception as exc:  # pragma: no cover - defensive manifest path.
        manifest["selector_score_source"] = "blocked_no_model_artifact"
        manifest["blocked_reason"] = f"blocked_model_load_failed:{exc.__class__.__name__}"
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
    if write_outputs:
        write_jsonl(score_output_dir / DEFAULT_SCORE_JSONL, score_rows)
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
