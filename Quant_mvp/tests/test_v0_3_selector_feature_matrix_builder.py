from __future__ import annotations

import importlib.util
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "Quant_mvp" / "scripts" / "build_v0_3_selector_feature_matrix.py"
SPEC = importlib.util.spec_from_file_location("build_v0_3_selector_feature_matrix", SCRIPT_PATH)
assert SPEC is not None
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def ml_ready_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "candidate_id": "sc:test",
        "candidate_version": "v0.3.0",
        "evaluation_id": "ee:test",
        "metric_subject_type": "strategy_candidate",
        "metric_subject_id": "sc:test",
        "candidate_metric_match": True,
        "metric_role": "candidate_specific",
        "reference_feature_candidate": False,
        "strategy_type": "momentum",
        "signal_family_candidate": "momentum",
        "actual_total_return": 0.15,
        "actual_excess_return_vs_proxy": 0.03,
        "actual_max_drawdown": -0.08,
        "actual_sharpe": 1.2,
        "actual_turnover": 0.4,
        "actual_volatility": 0.2,
        "actual_oos_stability": "walk_forward_pass",
        "evaluation_failure_flags": [],
        "excluded_untradable": False,
        "excluded_failure": False,
        "supervised_label_eligible": True,
        "label_review_preferred": 1,
        "label_decision": "positive",
        "label_null_reason": None,
        "label_pass_minimum_gate": 1,
        "actual_label_source": "candidate_level_evaluation_evidence",
        "actual_label_role": "candidate_specific",
        "actual_label_use_status": "candidate_level_supervised_label_candidate",
        "actual_label_evidence_id": "ee:test",
        "actual_label_generated_at": "2026-05-06",
        "ml_training_status": "eligible_candidate_level_label",
    }
    row.update(overrides)
    return row


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def test_feature_rows_exclude_label_and_leakage_columns() -> None:
    rows = builder.build_feature_rows([ml_ready_row()])

    assert len(rows) == 1
    row = rows[0]
    assert row["training_eligible"] is True
    assert row["label_review_preferred"] == 1
    assert row["strategy_family"] == "momentum"
    assert "strategy_family" not in row["feature_values"]
    assert row["feature_values"]["total_return"] == 0.15
    assert row["feature_values"]["excess_return_vs_proxy"] == 0.03
    assert row["feature_values"]["max_drawdown_abs"] == 0.08
    assert row["max_drawdown"] == -0.08
    assert row["has_oos_evidence"] == 1
    assert "actual_oos_stability" not in row["feature_values"]
    for leaked in builder.LEAKAGE_RISK_COLUMNS:
        assert leaked not in row["feature_values"]
    assert "label_review_preferred" not in builder.FEATURE_COLUMNS
    assert builder.TRAINING_FEATURE_COLUMNS == [
        "total_return",
        "excess_return_vs_proxy",
        "max_drawdown_abs",
        "sharpe",
        "turnover",
        "volatility",
    ]


def test_generic_proxy_stays_reference_feature_not_candidate_return() -> None:
    rows = builder.build_feature_rows(
        [
            ml_ready_row(
                metric_subject_type="generic_proxy",
                metric_subject_id="generic_momentum_proxy",
                metric_role="generic_momentum_proxy",
                candidate_metric_match=False,
                reference_feature_candidate=True,
                supervised_label_eligible=False,
                label_review_preferred=None,
                label_decision="blocked_generic_proxy_not_candidate_level",
                label_null_reason="blocked_generic_proxy_not_candidate_level",
                actual_label_source=None,
                actual_label_role=None,
                actual_label_use_status=None,
            )
        ]
    )

    row = rows[0]
    assert row["training_eligible"] is False
    assert row["training_exclusion_reason"] == "blocked_generic_proxy_not_candidate_level"
    assert row["feature_values"]["total_return"] is None
    assert row["proxy_return"] == 0.15
    assert row["has_benchmark_comparison"] == 1


def test_missing_required_core_feature_blocks_training_row() -> None:
    rows = builder.build_feature_rows([ml_ready_row(actual_sharpe=None)])

    row = rows[0]
    assert row["training_eligible"] is False
    assert row["training_exclusion_reason"] == "missing_required_core_feature"


def test_manifest_reports_positive_negative_distribution() -> None:
    records = [
        ml_ready_row(candidate_id="sc:positive", metric_subject_id="sc:positive", label_review_preferred=1),
        ml_ready_row(
            candidate_id="sc:negative",
            metric_subject_id="sc:negative",
            label_review_preferred=0,
            label_decision="negative",
            actual_total_return=0.05,
            actual_excess_return_vs_proxy=-0.02,
        ),
        ml_ready_row(
            candidate_id="sc:null",
            metric_subject_id="sc:null",
            supervised_label_eligible=False,
            label_review_preferred=None,
            label_decision="null_missing_evidence",
            actual_label_source=None,
            actual_label_role=None,
            actual_label_use_status=None,
        ),
    ]
    rows = builder.build_feature_rows(records)
    manifest = builder.build_manifest(rows, run_id="test", input_ref=Path("input.jsonl"))

    assert manifest["total_candidates"] == 3
    assert manifest["total_rows"] == 3
    assert manifest["total_feature_rows"] == 3
    assert manifest["feature_matrix_version"] == "v0_3_selector_feature_matrix_v1_0"
    assert manifest["matrix_intent"] == "post_evaluation_selector_rule_replication_audit"
    assert manifest["prediction_claim"] == "none"
    assert manifest["trade_signal_claim"] == "none"
    assert manifest["allowed_use"] == "AdoptionCandidate review prioritization only"
    assert manifest["candidate_level_metric_count"] == 3
    assert manifest["training_eligible_rows"] == 2
    assert manifest["positive_rows"] == 1
    assert manifest["negative_rows"] == 1
    assert manifest["null_label_rows"] == 1
    assert manifest["training_feature_columns"] == builder.TRAINING_FEATURE_COLUMNS
    assert manifest["feature_columns_count"] == len(builder.TRAINING_FEATURE_COLUMNS)
    assert manifest["missing_required_core_feature_rows"] == 0
    assert manifest["leakage_excluded_columns_count"] == len(builder.LEAKAGE_RISK_COLUMNS)
    assert "label_review_preferred" in manifest["leakage_excluded_columns"]
    assert manifest["trainability_status"] == "limited_insufficient_training_rows"
    assert manifest["total_return_excess_return_correlation"] is not None


def test_dry_run_cli_outputs_manifest_without_writing(tmp_path: Path, capsys) -> None:
    input_path = tmp_path / "ml_ready.jsonl"
    output_dir = tmp_path / "feature_matrix"
    write_jsonl(input_path, [ml_ready_row()])

    exit_code = builder.main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
            "--run-id",
            "dry_run_test",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert not output_dir.exists()
    result = json.loads(capsys.readouterr().out)
    assert result["mode"] == "dry_run"
    assert result["output_written"] is False
    assert result["manifest"]["training_eligible_rows"] == 1
    assert result["manifest"]["feature_matrix_version"] == "v0_3_selector_feature_matrix_v1_0"
