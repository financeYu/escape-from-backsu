from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from Quant_mvp.backtest_mvp.feature_discrimination_audit import audit_feature_discrimination
from Quant_mvp.backtest_mvp.feature_discrimination_contracts import (
    DECISION_DIAGNOSTIC_ONLY,
    DECISION_KEEP,
    FEATURE_TYPE_NUMERIC,
    FEATURE_TYPE_STATUS,
    SOURCE_TIMING_POST_LABEL,
    SOURCE_TIMING_PRE_LABEL,
    FeatureDiscriminationAuditConfig,
)
from Quant_mvp.backtest_mvp.ml_ready_candidate_features_v2 import (
    BASELINE_BLOCKED_INSUFFICIENT_FEATURES,
    BASELINE_BLOCKED_INSUFFICIENT_LABELS,
    BASELINE_BLOCKED_LEAKAGE_RISK,
    BASELINE_BLOCKED_LINEAGE_GAP,
    BASELINE_REVIEW_ONLY,
    BASELINE_TRAINABLE,
    TRAINABILITY_BLOCKED_INSUFFICIENT_COVERAGE,
    TRAINABILITY_BLOCKED_MISSING_LABELS,
    TRAINABILITY_BLOCKED_MISSING_LINEAGE,
    TRAINABILITY_ML_READY,
    BaselineSelectorTrainabilityV2Config,
    MLReadyCandidateFeaturesV2Config,
    build_baseline_selector_trainability_check_v2,
    build_ml_ready_candidate_features_v2,
    validate_baseline_selector_trainability_check_v2,
    validate_ml_ready_candidate_features_v2,
)
from Quant_mvp.scripts.build_ml_ready_candidate_features_v2 import (
    DEFAULT_MANIFEST_NAME,
    DEFAULT_ROWS_NAME,
    DEFAULT_TRAINABILITY_NAME,
    build_ml_ready_candidate_features_v2_outputs,
    dry_run_ml_ready_candidate_features_v2,
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


def _audit(rows: list[dict[str, object]] | None = None) -> dict[str, object]:
    return audit_feature_discrimination(
        rows or _rows(),
        _feature_specs(),
        config=FeatureDiscriminationAuditConfig(
            min_non_null_ratio=0.75,
            min_unique_values=2,
            min_label_mean_abs_difference=0.10,
        ),
    )


def _lineage() -> dict[str, dict[str, object]]:
    return {
        "constant_ready_score": {
            "source_artifact": "fixture://candidate_evidence",
            "source_timing": SOURCE_TIMING_PRE_LABEL,
        },
        "sparse_numeric": {
            "source_artifact": "fixture://candidate_evidence",
            "source_timing": SOURCE_TIMING_PRE_LABEL,
        },
        "readiness_status": {
            "source_artifact": "fixture://candidate_diagnostics",
            "source_timing": SOURCE_TIMING_PRE_LABEL,
        },
        "discriminating_quality": {
            "source_artifact": "fixture://candidate_evidence",
            "source_timing": SOURCE_TIMING_PRE_LABEL,
        },
        "weak_numeric": {
            "source_artifact": "fixture://candidate_evidence",
            "source_timing": SOURCE_TIMING_PRE_LABEL,
        },
        "post_label_metric": {
            "source_artifact": "fixture://post_label_diagnostics",
            "source_timing": SOURCE_TIMING_POST_LABEL,
        },
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _runner_inputs(
    tmp_path: Path,
    *,
    leakage_findings: list[dict[str, object]] | None = None,
) -> dict[str, Path]:
    candidate_rows_path = tmp_path / "candidate_rows.jsonl"
    audit_manifest_path = tmp_path / "feature_discrimination_audit_manifest.json"
    label_manifest_path = tmp_path / "label_manifest.json"
    feature_lineage_manifest_path = tmp_path / "feature_lineage_manifest.json"
    leakage_findings_path = tmp_path / "leakage_findings.json"
    candidate_rows_path.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")

    audit_manifest = _audit()
    audit_manifest["audit_manifest_id"] = "fixture_audit_manifest_v2"
    _write_json(audit_manifest_path, audit_manifest)
    _write_json(
        label_manifest_path,
        {
            "label_manifest_id": "fixture_label_manifest_v2",
            "label_column": "label_review_preferred",
        },
    )
    _write_json(
        feature_lineage_manifest_path,
        {
            "feature_lineage_manifest_id": "fixture_lineage_manifest_v2",
            "feature_lineage": _lineage(),
        },
    )
    if leakage_findings is not None:
        _write_json(leakage_findings_path, {"leakage_findings": leakage_findings})
    return {
        "candidate_rows_path": candidate_rows_path,
        "audit_manifest_path": audit_manifest_path,
        "label_manifest_path": label_manifest_path,
        "feature_lineage_manifest_path": feature_lineage_manifest_path,
        "leakage_findings_path": leakage_findings_path,
    }


def _artifact(
    rows: list[dict[str, object]] | None = None,
    *,
    audit_manifest: dict[str, object] | None = None,
    lineage: dict[str, dict[str, object]] | None = None,
    config: MLReadyCandidateFeaturesV2Config | None = None,
) -> dict[str, object]:
    row_values = rows or _rows()
    return build_ml_ready_candidate_features_v2(
        row_values,
        audit_manifest or _audit(row_values),
        source_artifacts=["fixture://candidate_evidence"],
        label_manifest_id="fixture_label_manifest_v1",
        audit_manifest_id="fixture_audit_manifest_v1",
        feature_lineage=lineage or _lineage(),
        config=config,
    )


def _excluded_by_name(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    manifest = artifact["manifest"]  # type: ignore[index]
    return {str(row["feature_name"]): row for row in manifest["excluded_features"]}  # type: ignore[index]


def test_only_audit_passing_features_are_included() -> None:
    artifact = _artifact()
    manifest = artifact["manifest"]

    validate_ml_ready_candidate_features_v2(artifact)
    assert manifest["included_features"] == ["discriminating_quality"]  # type: ignore[index]
    assert manifest["model_input_columns"] == ["discriminating_quality"]  # type: ignore[index]
    assert manifest["trainability_gate_status"] == TRAINABILITY_ML_READY  # type: ignore[index]
    for row in artifact["rows"]:  # type: ignore[index]
        assert list(row["feature_values"]) == ["discriminating_quality"]


def test_excluded_status_readiness_fields_are_recorded_not_model_input() -> None:
    artifact = _artifact()
    excluded = _excluded_by_name(artifact)

    readiness = excluded["readiness_status"]
    assert readiness["audit_decision"] == DECISION_DIAGNOSTIC_ONLY
    assert "status_or_readiness_diagnostic_only" in readiness["reason_codes"]
    assert "readiness_status" not in artifact["manifest"]["model_input_columns"]  # type: ignore[index]
    for row in artifact["rows"]:  # type: ignore[index]
        assert "readiness_status" not in row["feature_values"]


def test_missing_labels_fail_closed() -> None:
    rows = _rows()
    rows[0]["label_review_preferred"] = None
    artifact = _artifact(rows)
    manifest = artifact["manifest"]

    assert manifest["ml_ready_gate_passed"] is False  # type: ignore[index]
    assert manifest["trainability_gate_status"] == TRAINABILITY_BLOCKED_MISSING_LABELS  # type: ignore[index]
    assert manifest["missing_label_candidate_ids"] == ["sc:a"]  # type: ignore[index]


def test_missing_lineage_blocks_ml_ready() -> None:
    lineage = _lineage()
    del lineage["discriminating_quality"]
    artifact = _artifact(lineage=lineage)
    manifest = artifact["manifest"]

    assert manifest["ml_ready_gate_passed"] is False  # type: ignore[index]
    assert manifest["trainability_gate_status"] == TRAINABILITY_BLOCKED_MISSING_LINEAGE  # type: ignore[index]
    assert manifest["included_features"] == []  # type: ignore[index]
    assert manifest["feature_lineage_coverage"]["missing_feature_lineage"] == ["discriminating_quality"]  # type: ignore[index]
    assert "missing_feature_lineage" in _excluded_by_name(artifact)["discriminating_quality"]["reason_codes"]


def test_insufficient_candidate_label_coverage_blocks_ml_ready() -> None:
    artifact = _artifact(
        config=MLReadyCandidateFeaturesV2Config(
            min_candidate_count=8,
            min_positive_labels=2,
            min_negative_labels=2,
        )
    )
    manifest = artifact["manifest"]

    assert manifest["ml_ready_gate_passed"] is False  # type: ignore[index]
    assert manifest["trainability_gate_status"] == TRAINABILITY_BLOCKED_INSUFFICIENT_COVERAGE  # type: ignore[index]
    assert manifest["row_count"] == 6  # type: ignore[index]


def test_deterministic_output_ordering() -> None:
    rows = list(reversed(_rows()))
    artifact = _artifact(rows)

    assert [row["candidate_id"] for row in artifact["rows"]] == [  # type: ignore[index]
        "sc:a",
        "sc:b",
        "sc:c",
        "sc:d",
        "sc:e",
        "sc:f",
    ]
    assert artifact["manifest"]["included_features"] == ["discriminating_quality"]  # type: ignore[index]
    assert artifact["manifest"]["excluded_features"][0]["feature_name"] == "constant_ready_score"  # type: ignore[index]


def test_manifest_records_contract_schema_and_excluded_feature_families() -> None:
    artifact = _artifact()
    manifest = artifact["manifest"]
    excluded = _excluded_by_name(artifact)
    audit_rows = {str(row["feature_name"]): row for row in _audit()["rows"]}  # type: ignore[index]

    assert manifest["schema_version"] == "ml_ready_candidate_features_v2_manifest_v1_0"  # type: ignore[index]
    assert manifest["feature_set_version"] == "ml_ready_candidate_features_v2"  # type: ignore[index]
    assert manifest["label_manifest_id"] == "fixture_label_manifest_v1"  # type: ignore[index]
    assert manifest["audit_manifest_id"] == "fixture_audit_manifest_v1"  # type: ignore[index]
    assert audit_rows["discriminating_quality"]["decision"] == DECISION_KEEP
    assert excluded["post_label_metric"]["source_timing"] == SOURCE_TIMING_POST_LABEL
    assert "source_timing_post_label" in excluded["post_label_metric"]["reason_codes"]
    assert manifest["ml_training_performed"] is False  # type: ignore[index]
    assert manifest["selector_ranking_changed"] is False  # type: ignore[index]
    assert manifest["backtest_behavior_changed"] is False  # type: ignore[index]
    assert manifest["valuation_activation_changed"] is False  # type: ignore[index]
    assert manifest["data_ingestion_changed"] is False  # type: ignore[index]


def _trainability_report(
    artifact: dict[str, object] | None = None,
    *,
    label_manifest_id: str | None = "fixture_label_manifest_v1",
    feature_lineage_manifest_id: str | None = "fixture_lineage_manifest_v1",
    leakage_findings: list[dict[str, object]] | None = None,
    config: BaselineSelectorTrainabilityV2Config | None = None,
) -> dict[str, object]:
    return build_baseline_selector_trainability_check_v2(
        artifact or _artifact(),
        label_manifest_id=label_manifest_id,
        feature_lineage_manifest_id=feature_lineage_manifest_id,
        leakage_findings=leakage_findings,
        config=config,
    )


def test_baseline_trainability_report_allows_clean_v2_fixture() -> None:
    report = _trainability_report()

    validate_baseline_selector_trainability_check_v2(report)
    assert report["trainability_status"] == BASELINE_TRAINABLE
    assert report["training_blocked_reasons"] == []
    assert report["usable_numeric_feature_count"] == 1
    assert report["leakage_finding_count"] == 0
    assert report["model_training_performed"] is False
    assert report["adoption_or_performance_support"] == "none"


def test_baseline_trainability_blocks_when_label_manifest_missing() -> None:
    artifact = _artifact()
    artifact["manifest"]["label_manifest_id"] = None  # type: ignore[index]
    report = _trainability_report(artifact, label_manifest_id=None)

    assert report["trainability_status"] == BASELINE_BLOCKED_INSUFFICIENT_LABELS
    assert "label_manifest_missing" in report["training_blocked_reasons"]
    assert report["model_training_performed"] is False


def test_baseline_trainability_blocks_when_label_counts_are_insufficient() -> None:
    report = _trainability_report(
        config=BaselineSelectorTrainabilityV2Config(
            min_candidate_count=8,
            min_positive_labels=2,
            min_negative_labels=2,
            min_usable_numeric_feature_count=1,
        )
    )

    assert report["trainability_status"] == BASELINE_BLOCKED_INSUFFICIENT_LABELS
    assert "candidate_or_label_count_below_minimum" in report["training_blocked_reasons"]


def test_baseline_trainability_blocks_when_numeric_feature_count_is_insufficient() -> None:
    report = _trainability_report(
        config=BaselineSelectorTrainabilityV2Config(
            min_candidate_count=4,
            min_positive_labels=2,
            min_negative_labels=2,
            min_usable_numeric_feature_count=2,
        )
    )

    assert report["trainability_status"] == BASELINE_BLOCKED_INSUFFICIENT_FEATURES
    assert "usable_numeric_feature_count_below_minimum" in report["training_blocked_reasons"]


def test_baseline_trainability_blocks_when_feature_is_near_constant() -> None:
    artifact = deepcopy(_artifact())
    for row in artifact["rows"]:  # type: ignore[index]
        row["feature_values"]["discriminating_quality"] = 1.0

    report = _trainability_report(artifact)

    assert report["trainability_status"] == BASELINE_BLOCKED_INSUFFICIENT_FEATURES
    assert "usable_numeric_feature_count_below_minimum" in report["training_blocked_reasons"]
    assert report["constant_or_near_constant_feature_ratio"] == 1.0


def test_baseline_trainability_blocks_when_leakage_findings_exist() -> None:
    report = _trainability_report(
        leakage_findings=[
            {
                "feature_name": "post_label_metric",
                "reason": "source_timing_post_label",
            }
        ]
    )

    assert report["trainability_status"] == BASELINE_BLOCKED_LEAKAGE_RISK
    assert "leakage_findings_present" in report["training_blocked_reasons"]
    assert report["leakage_finding_count"] == 1


def test_baseline_trainability_blocks_when_lineage_manifest_missing() -> None:
    report = _trainability_report(feature_lineage_manifest_id=None)

    assert report["trainability_status"] == BASELINE_BLOCKED_LINEAGE_GAP
    assert "feature_lineage_manifest_missing" in report["training_blocked_reasons"]


def test_baseline_trainability_marks_review_only_when_source_matrix_is_review_only() -> None:
    rows = _rows()
    audit_manifest = _audit(rows)
    for audit_row in audit_manifest["rows"]:  # type: ignore[index]
        if audit_row["feature_name"] == "weak_numeric":
            audit_row["decision"] = DECISION_KEEP
            audit_row["ml_input_allowed"] = True
            audit_row["reason_codes"] = ["numeric_label_separation_present"]
    lineage = _lineage()
    del lineage["weak_numeric"]
    artifact = _artifact(rows, audit_manifest=audit_manifest, lineage=lineage)
    report = _trainability_report(artifact)

    assert artifact["manifest"]["trainability_gate_status"] == "review_only_missing_lineage"  # type: ignore[index]
    assert report["trainability_status"] == BASELINE_REVIEW_ONLY
    assert "feature_lineage_coverage_not_pass" in report["training_blocked_reasons"]


def test_runner_dry_run_connects_manifest_ids_without_writing(tmp_path: Path) -> None:
    paths = _runner_inputs(tmp_path)
    result = dry_run_ml_ready_candidate_features_v2(
        candidate_rows_path=paths["candidate_rows_path"],
        audit_manifest_path=paths["audit_manifest_path"],
        label_manifest_path=paths["label_manifest_path"],
        feature_lineage_manifest_path=paths["feature_lineage_manifest_path"],
        created_at="2026-05-16T00:00:00+00:00",
    )

    assert result["output_written"] is False
    assert result["source_summary"]["label_manifest_id"] == "fixture_label_manifest_v2"
    assert result["source_summary"]["audit_manifest_id"] == "fixture_audit_manifest_v2"
    assert result["source_summary"]["feature_lineage_manifest_id"] == "fixture_lineage_manifest_v2"
    assert result["artifact"]["manifest"]["included_features"] == ["discriminating_quality"]
    assert result["baseline_trainability_report"]["trainability_status"] == BASELINE_TRAINABLE
    assert not (tmp_path / DEFAULT_ROWS_NAME).exists()
    assert not (tmp_path / DEFAULT_MANIFEST_NAME).exists()
    assert not (tmp_path / DEFAULT_TRAINABILITY_NAME).exists()


def test_runner_writes_rows_manifest_and_trainability_report(tmp_path: Path) -> None:
    paths = _runner_inputs(tmp_path)
    output_dir = tmp_path / "out"
    result = build_ml_ready_candidate_features_v2_outputs(
        candidate_rows_path=paths["candidate_rows_path"],
        audit_manifest_path=paths["audit_manifest_path"],
        label_manifest_path=paths["label_manifest_path"],
        feature_lineage_manifest_path=paths["feature_lineage_manifest_path"],
        output_dir=output_dir,
        created_at="2026-05-16T00:00:00+00:00",
    )

    rows_path = output_dir / DEFAULT_ROWS_NAME
    manifest_path = output_dir / DEFAULT_MANIFEST_NAME
    trainability_path = output_dir / DEFAULT_TRAINABILITY_NAME
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = json.loads(trainability_path.read_text(encoding="utf-8"))

    validate_ml_ready_candidate_features_v2({"manifest": manifest, "rows": rows})
    validate_baseline_selector_trainability_check_v2(report)
    assert result["output_written"] is True
    assert len(rows) == 6
    assert manifest["label_manifest_id"] == "fixture_label_manifest_v2"
    assert manifest["audit_manifest_id"] == "fixture_audit_manifest_v2"
    assert manifest["model_input_columns"] == ["discriminating_quality"]
    assert report["feature_lineage_manifest_id"] == "fixture_lineage_manifest_v2"
    assert report["trainability_status"] == BASELINE_TRAINABLE


def test_runner_leakage_findings_source_blocks_trainability(tmp_path: Path) -> None:
    paths = _runner_inputs(
        tmp_path,
        leakage_findings=[
            {
                "feature_name": "post_label_metric",
                "reason": "source_timing_post_label",
            }
        ],
    )
    result = dry_run_ml_ready_candidate_features_v2(
        candidate_rows_path=paths["candidate_rows_path"],
        audit_manifest_path=paths["audit_manifest_path"],
        label_manifest_path=paths["label_manifest_path"],
        feature_lineage_manifest_path=paths["feature_lineage_manifest_path"],
        leakage_findings_path=paths["leakage_findings_path"],
        created_at="2026-05-16T00:00:00+00:00",
    )

    assert result["source_summary"]["leakage_finding_count"] == 1
    assert result["baseline_trainability_report"]["trainability_status"] == BASELINE_BLOCKED_LEAKAGE_RISK
    assert "leakage_findings_present" in result["baseline_trainability_report"]["training_blocked_reasons"]
