from __future__ import annotations

import importlib.util
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "Quant_mvp" / "scripts" / "build_v0_4_2_evaluation_evidence_coverage.py"
SPEC = importlib.util.spec_from_file_location("build_v0_4_2_evaluation_evidence_coverage", SCRIPT_PATH)
assert SPEC is not None
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def candidate(candidate_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "candidate_id": candidate_id,
        "candidate_version": "v0.3.0",
        "linked_strategy_hypothesis_id": candidate_id.replace("sc:", "sh:"),
        "status": "draft",
        "target_universe": "Candidate-only KOSPI200 daily OHLCV review boundary",
        "data_requirements": ["daily_ohlcv"],
        "blocking_issues": ["manual_review_required"],
        "experiment_scope": {"strategy_type": "momentum"},
        "test_period": "2015-01-01 through 2025-12-31",
    }
    payload.update(overrides)
    return {"strategy_candidate": payload}


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def test_v0_4_2_coverage_selects_manual_review_gap_without_labels(tmp_path: Path) -> None:
    registry = tmp_path / "registry.jsonl"
    write_jsonl(
        registry,
        [
            candidate("sc:manual_review_gap"),
            candidate(
                "sc:fundamental_blocked",
                blocking_issues=["manual_review_required", "point_in_time_fundamentals_required"],
                data_requirements=["daily_ohlcv", "point_in_time_fundamentals"],
            ),
            candidate("sc:existing_evidence"),
        ],
    )
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "ee_v0_3_existing.md").write_text(
        "# existing\n\n```json\n"
        + json.dumps({"candidate_id": "sc:existing_evidence", "status": "evidence_recorded"})
        + "\n```\n",
        encoding="utf-8",
    )
    ml_manifest = tmp_path / "ml_manifest.json"
    feature_manifest = tmp_path / "feature_manifest.json"
    trainability_manifest = tmp_path / "trainability_manifest.json"
    write_json(
        ml_manifest,
        {
            "total_rows": 3,
            "candidate_level_metric_count": 1,
            "label_positive": 1,
            "label_negative": 0,
            "evaluation_status_counts": {"missing_evaluation_evidence": 2},
            "strategy_type_counts": {"momentum": 3},
        },
    )
    write_json(feature_manifest, {"training_eligible_rows": 1, "null_label_rows": 2})
    write_json(trainability_manifest, {"warnings": ["limited_insufficient_training_rows"]})

    manifest = builder.build_coverage(
        registry=registry,
        evidence_dir=evidence_dir,
        output_dir=tmp_path / "out",
        coverage_manifest_dir=tmp_path / "coverage",
        coverage_manifest_name="manifest.json",
        ml_ready_manifest_path=ml_manifest,
        feature_manifest_path=feature_manifest,
        trainability_manifest_path=trainability_manifest,
        cohort_id="test_v0_4_2",
        created_at="2026-05-07",
        max_candidates=10,
        dry_run=True,
    )

    assert manifest["selected_candidate_ids"] == ["sc:manual_review_gap"]
    assert manifest["expected_manifest_delta_after_regeneration"]["missing_evaluation_evidence"] == -1
    assert manifest["expected_manifest_delta_after_regeneration"]["positive_rows"] == 0
    assert manifest["label_generation_status"] == "not_generated_no_synthetic_label"
    assert manifest["guardrails"]["trading_signal_allowed"] is False
    assert "excluded_forbidden_blocker_point_in_time_fundamentals_required" in manifest["exclusion_reason_counts"]
