from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "Quant_mvp" / "scripts" / "build_v0_3_ml_ready_candidate_inputs.py"
SPEC = importlib.util.spec_from_file_location("build_v0_3_ml_ready_candidate_inputs", SCRIPT_PATH)
assert SPEC is not None
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def selector_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "evidence_card_id": "ecard:test_momentum",
        "parent_evidence_card_id": None,
        "canonical_paper_id": "doi:test",
        "publication_date": "2020-01-02",
        "publication_year": 2020,
        "ml_use_status": "eligible_for_candidate_selector_review",
        "importance_score": 80,
        "importance_bucket": "high",
        "research_branch": "technical",
        "downstream_route": "technical_score_architect",
        "signal_family_candidate": "momentum",
        "formula_clarity": "exact",
        "implementation_readiness": 3,
        "classification_confidence": "high",
        "evidence_status": "abstract_supported",
        "reproducibility_level": "not_reported",
        "transaction_costs_discussed": False,
        "lookahead_bias_discussed": False,
        "survivorship_bias_discussed": False,
        "risk_flags": ["transaction_cost_missing_flag"],
        "blocked_reasons": [],
    }
    record.update(overrides)
    return record


def registry_record(**overrides: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "candidate_id": "sc:ecard:test_momentum",
        "candidate_version": "v0.3.0",
        "linked_strategy_hypothesis_id": "sh:ecard:test_momentum",
        "status": "evaluable",
        "next_action": "create_evaluation_evidence",
        "created_at": "2026-04-28",
        "blocking_issues": [],
        "data_requirements": ["daily_ohlcv"],
        "feature_requirements": ["medium_horizon_return_bucket"],
        "required_evidence": ["EvaluationEvidence schema record"],
        "test_period": "2015-01-01 through 2025-12-31",
        "experiment_scope": {"strategy_type": "momentum"},
    }
    candidate.update(overrides)
    return {
        "strategy_candidate": candidate,
        "linked_strategy_hypothesis": {
            "strategy_hypothesis_id": "sh:ecard:test_momentum",
            "strategy_type": "momentum",
        },
        "evaluation_readiness": {"ready_for_evaluation": True},
    }


def evidence_packet(**overrides: object) -> dict[str, object]:
    packet: dict[str, object] = {
        "evaluation_id": "ee_v0_3_test_momentum",
        "candidate_id": "sc:ecard:test_momentum",
        "candidate_version": "v0.3.0",
        "hypothesis_id": "sh:ecard:test_momentum",
        "status": "contract_only",
        "metric_subject_type": "strategy_candidate",
        "metric_subject_id": "sc:ecard:test_momentum",
        "candidate_metric_match": True,
        "candidate_metric_match_reason": "candidate_id_matches_candidate_level_evaluation_evidence",
        "created_at": "2026-05-06",
        "updated_at": "2026-05-06",
        "evaluation_window": {
            "start": "2015-01-01",
            "end": "2025-12-31",
            "rationale": "predeclared_candidate_contract_window_pending_approved_run",
        },
        "failure_flags": ["not_yet_run"],
        "required_evaluation_checks": {
            "cost": {"status": "required_before_approved_run"},
            "drawdown": {"status": "required_before_approved_run"},
            "volatility": {"status": "required_before_approved_run"},
            "turnover": {"status": "required_before_approved_run"},
            "oos_walk_forward_stability": {"status": "required_before_adoption_review"},
            "no_lookahead": {"status": "required_before_approved_run"},
            "no_feedback": {"status": "active_boundary_check"},
        },
        "_source_path": "Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/test.md",
    }
    packet.update(overrides)
    return packet


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def write_evidence_md(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# EvaluationEvidence test\n\n```json\n"
        + json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n```\n",
        encoding="utf-8",
    )


def test_contract_only_row_keeps_actual_and_prediction_labels_null() -> None:
    row = builder.build_ml_ready_row(
        registry_record(),
        selector_record(),
        evidence_packet(),
        registry_ref=Path("registry.jsonl"),
        selector_ref=Path("selector.jsonl"),
        row_generated_at="2026-05-06T00:00:00+00:00",
    )

    for column in builder.ACTUAL_LABEL_COLUMNS:
        assert row[column] is None
    for column in builder.PREDICTION_COLUMNS:
        assert row[column] is None
    assert row["label_source"] == "unlabeled"
    assert row["metric_source"] is None
    assert row["metric_subject_type"] is None
    assert row["candidate_metric_match"] is False
    assert row["candidate_metric_match_reason"] == "metric_summary_missing_or_unavailable"
    assert row["reference_feature_candidate"] is False
    assert row["supervised_label_eligible"] is False
    assert row["adoption_review_eligible"] is False
    assert row["actual_metric_summary_available"] is False
    assert row["evaluation_status"] == "contract_only"
    assert row["prediction_allowed_uses"] == builder.ALLOWED_PREDICTION_USES


def test_evidence_recorded_metric_summary_populates_actual_labels() -> None:
    evidence = evidence_packet(
        status="evidence_recorded",
        failure_flags=[],
        metric_summary={"benchmark_relative_return": 0.04, "oos_stability_status": "walk_forward_pass"},
        performance_metric_summary={"total_return": 0.12},
        risk_metric_summary={
            "max_drawdown": -0.08,
            "annualized_volatility": 0.18,
            "turnover_proxy": 0.42,
            "sharpe_ratio": 1.1,
        },
        required_evaluation_checks={
            "cost": {"status": "recorded"},
            "drawdown": {"status": "recorded"},
            "volatility": {"status": "recorded"},
            "turnover": {"status": "recorded"},
            "oos_walk_forward_stability": {"status": "walk_forward_pass"},
            "no_lookahead": {"status": "recorded_boundary_check"},
            "no_feedback": {"status": "active_boundary_check"},
        },
    )

    row = builder.build_ml_ready_row(
        registry_record(),
        selector_record(),
        evidence,
        registry_ref=Path("registry.jsonl"),
        selector_ref=Path("selector.jsonl"),
        row_generated_at="2026-05-06T00:00:00+00:00",
    )

    assert row["metric_source"] == "approved_evaluation_evidence"
    assert row["metric_role"] == "candidate_specific"
    assert row["metric_use_status"] == "candidate_level_supervised_label_candidate"
    assert row["metric_subject_type"] == "strategy_candidate"
    assert row["metric_subject_id"] == "sc:ecard:test_momentum"
    assert row["candidate_metric_match"] is True
    assert row["candidate_metric_match_reason"] == "candidate_id_matches_candidate_level_evaluation_evidence"
    assert row["reference_feature_candidate"] is False
    assert row["label_source"] == "candidate_level_evaluation_evidence"
    assert row["actual_label_source"] == "candidate_level_evaluation_evidence"
    assert row["actual_label_role"] == "candidate_specific"
    assert row["actual_label_use_status"] == "candidate_level_supervised_label_candidate"
    assert row["actual_label_evidence_id"] == "ee_v0_3_test_momentum"
    assert row["actual_total_return"] == 0.12
    assert row["actual_excess_return_vs_proxy"] == 0.04
    assert row["actual_max_drawdown"] == -0.08
    assert row["actual_volatility"] == 0.18
    assert row["actual_turnover"] == 0.42
    assert row["actual_sharpe"] == 1.1
    assert row["actual_oos_stability"] == "walk_forward_pass"
    assert row["label_pass_minimum_gate"] == 1
    assert row["label_review_preferred"] == 1
    assert row["label_decision"] == "positive"
    assert row["supervised_label_eligible"] is True
    assert row["adoption_review_eligible"] is True


def test_evidence_recorded_without_oos_check_is_not_adoption_review_eligible() -> None:
    evidence = evidence_packet(
        status="evidence_recorded",
        failure_flags=[],
        metric_summary={"benchmark_relative_return": 0.04, "oos_stability_status": "not_available_single_pass_snapshot"},
        performance_metric_summary={"total_return": 0.12},
        risk_metric_summary={
            "max_drawdown": -0.08,
            "annualized_volatility": 0.18,
            "turnover_proxy": 0.42,
            "sharpe_ratio": 1.1,
        },
    )

    row = builder.build_ml_ready_row(
        registry_record(),
        selector_record(),
        evidence,
        registry_ref=Path("registry.jsonl"),
        selector_ref=Path("selector.jsonl"),
        row_generated_at="2026-05-06T00:00:00+00:00",
    )

    assert row["metric_source"] == "approved_evaluation_evidence"
    assert row["candidate_metric_match"] is True
    assert row["label_source"] == "candidate_level_evaluation_evidence"
    assert row["actual_label_source"] == "candidate_level_evaluation_evidence"
    assert row["actual_label_role"] == "candidate_specific"
    assert row["actual_label_use_status"] == "candidate_level_supervised_label_candidate"
    assert row["label_pass_minimum_gate"] == 1
    assert row["label_review_preferred"] is None
    assert row["label_decision"] == "rule_inconclusive"
    assert row["supervised_label_eligible"] is False
    assert row["adoption_required_checks_ready"] is False
    assert row["adoption_review_eligible"] is False


def test_oos_pass_can_create_training_positive_without_adoption_metric_gate() -> None:
    evidence = evidence_packet(
        status="evidence_recorded",
        failure_flags=[],
        metric_summary={
            "benchmark_relative_return": 0.12,
            "oos_stability_status": "recorded_walk_forward_pass",
        },
        performance_metric_summary={"total_return": 0.20},
        risk_metric_summary={
            "max_drawdown": -0.50,
            "annualized_volatility": 0.60,
            "turnover_proxy": 0.42,
            "sharpe_ratio": 0.59,
        },
        required_evaluation_checks={
            "oos_walk_forward_stability": {"status": "recorded_walk_forward_pass"},
            "no_feedback": {"status": "active_boundary_check"},
            "no_lookahead": {"status": "recorded_boundary_check"},
        },
    )

    row = builder.build_ml_ready_row(
        registry_record(),
        selector_record(),
        evidence,
        registry_ref=Path("registry.jsonl"),
        selector_ref=Path("selector.jsonl"),
        row_generated_at="2026-05-06T00:00:00+00:00",
    )

    assert row["label_pass_minimum_gate"] == 0
    assert row["label_review_preferred"] == 1
    assert row["label_decision"] == "positive"
    assert row["supervised_label_eligible"] is True
    assert row["adoption_required_checks_ready"] is True
    assert row["adoption_review_eligible"] is False


def test_candidate_matched_reference_metric_is_not_supervised_label() -> None:
    evidence = evidence_packet(
        status="evidence_recorded",
        failure_flags=[],
        label_use_status="benchmark_reference_feature_candidate",
        metric_summary={"oos_stability_status": "walk_forward_pass"},
        performance_metric_summary={"total_return": 0.12},
        risk_metric_summary={
            "max_drawdown": -0.08,
            "annualized_volatility": 0.18,
            "turnover_proxy": 0.42,
            "sharpe_ratio": 1.1,
        },
        required_evaluation_checks={
            "cost": {"status": "recorded"},
            "drawdown": {"status": "recorded"},
            "volatility": {"status": "recorded"},
            "turnover": {"status": "recorded"},
            "oos_walk_forward_stability": {"status": "walk_forward_pass"},
            "no_lookahead": {"status": "recorded_boundary_check"},
            "no_feedback": {"status": "active_boundary_check"},
        },
    )

    row = builder.build_ml_ready_row(
        registry_record(),
        selector_record(),
        evidence,
        registry_ref=Path("registry.jsonl"),
        selector_ref=Path("selector.jsonl"),
        row_generated_at="2026-05-06T00:00:00+00:00",
    )

    assert row["metric_source"] == "approved_evaluation_evidence"
    assert row["metric_use_status"] == "benchmark_reference_feature_candidate"
    assert row["metric_subject_type"] == "strategy_candidate"
    assert row["metric_subject_id"] == "sc:ecard:test_momentum"
    assert row["candidate_metric_match"] is True
    assert row["reference_feature_candidate"] is True
    assert row["label_source"] == "unlabeled"
    assert row["actual_label_source"] is None
    assert row["actual_label_use_status"] is None
    assert row["supervised_label_eligible"] is False
    assert row["adoption_review_eligible"] is False
    assert row["ml_training_status"] == "blocked_no_candidate_level_metric"
    assert row["actual_label_blocked_reason"] == "metric_use_status_not_supervised_label"


def test_shared_rule_limitation_alone_does_not_convert_candidate_metric_to_generic_proxy() -> None:
    evidence = evidence_packet(
        status="evidence_recorded",
        failure_flags=[],
        known_limitations=["shared_strategy_rule_fingerprint_not_candidate_specific_label"],
        metric_summary={"benchmark_relative_return": 0.04, "oos_stability_status": "walk_forward_pass"},
        performance_metric_summary={"total_return": 0.12},
        risk_metric_summary={
            "max_drawdown": -0.08,
            "annualized_volatility": 0.18,
            "turnover_proxy": 0.42,
            "sharpe_ratio": 1.1,
        },
        required_evaluation_checks={
            "cost": {"status": "recorded"},
            "drawdown": {"status": "recorded"},
            "volatility": {"status": "recorded"},
            "turnover": {"status": "recorded"},
            "oos_walk_forward_stability": {"status": "walk_forward_pass"},
            "no_lookahead": {"status": "recorded_boundary_check"},
            "no_feedback": {"status": "active_boundary_check"},
        },
    )

    row = builder.build_ml_ready_row(
        registry_record(),
        selector_record(),
        evidence,
        registry_ref=Path("registry.jsonl"),
        selector_ref=Path("selector.jsonl"),
        row_generated_at="2026-05-06T00:00:00+00:00",
    )

    assert row["metric_subject_type"] == "strategy_candidate"
    assert row["metric_subject_id"] == "sc:ecard:test_momentum"
    assert row["candidate_metric_match"] is True
    assert row["metric_role"] == "candidate_specific"
    assert row["metric_use_status"] == "candidate_level_supervised_label_candidate"
    assert row["reference_feature_candidate"] is False
    assert row["label_source"] == "candidate_level_evaluation_evidence"
    assert row["supervised_label_eligible"] is True


def test_generic_momentum_proxy_metric_summary_is_not_supervised_label() -> None:
    evidence = evidence_packet(
        status="evidence_recorded",
        failure_flags=[],
        label_use_status="generic_momentum_proxy_not_supervised",
        known_limitations=["shared_strategy_rule_fingerprint_not_candidate_specific_label"],
        metric_summary={
            "label_role": "generic_momentum_proxy",
            "oos_stability_status": "walk_forward_pass",
        },
        performance_metric_summary={"total_return": 0.12},
        risk_metric_summary={
            "max_drawdown": -0.08,
            "annualized_volatility": 0.18,
            "turnover_proxy": 0.42,
            "sharpe_ratio": 1.1,
        },
        required_evaluation_checks={
            "cost": {"status": "recorded"},
            "drawdown": {"status": "recorded"},
            "volatility": {"status": "recorded"},
            "turnover": {"status": "recorded"},
            "oos_walk_forward_stability": {"status": "walk_forward_pass"},
            "no_lookahead": {"status": "recorded_boundary_check"},
            "no_feedback": {"status": "active_boundary_check"},
        },
    )

    row = builder.build_ml_ready_row(
        registry_record(),
        selector_record(),
        evidence,
        registry_ref=Path("registry.jsonl"),
        selector_ref=Path("selector.jsonl"),
        row_generated_at="2026-05-06T00:00:00+00:00",
    )

    assert row["metric_source"] == "approved_evaluation_evidence"
    assert row["metric_role"] == "generic_momentum_proxy"
    assert row["metric_use_status"] == "benchmark_reference_feature_candidate"
    assert row["metric_subject_type"] == "generic_proxy"
    assert row["metric_subject_id"] == "generic_momentum_proxy"
    assert row["candidate_metric_match"] is False
    assert row["candidate_metric_match_reason"] == "generic_momentum_proxy_not_candidate_level"
    assert row["reference_feature_candidate"] is True
    assert row["label_source"] == "unlabeled"
    assert row["actual_label_source"] is None
    assert row["actual_label_role"] is None
    assert row["actual_label_use_status"] is None
    assert row["actual_total_return"] == 0.12
    assert row["actual_max_drawdown"] == -0.08
    assert row["actual_volatility"] == 0.18
    assert row["actual_turnover"] == 0.42
    assert row["actual_sharpe"] == 1.1
    assert row["supervised_label_eligible"] is False
    assert row["adoption_review_eligible"] is False
    assert row["ml_training_status"] == "blocked_generic_proxy_metric_summary"
    assert row["actual_label_blocked_reason"] == "generic_momentum_proxy_not_candidate_level"


def test_manifest_with_only_generic_actual_labels_keeps_training_blocked() -> None:
    evidence = evidence_packet(
        status="evidence_recorded",
        failure_flags=[],
        label_use_status="generic_momentum_proxy_not_supervised",
        known_limitations=["shared_strategy_rule_fingerprint_not_candidate_specific_label"],
        metric_summary={
            "label_role": "generic_momentum_proxy",
            "oos_stability_status": "not_available_single_pass_snapshot",
        },
        performance_metric_summary={"total_return": 0.12},
        risk_metric_summary={
            "max_drawdown": -0.08,
            "annualized_volatility": 0.18,
            "turnover_proxy": 0.42,
            "sharpe_ratio": 1.1,
        },
    )
    row = builder.build_ml_ready_row(
        registry_record(),
        selector_record(),
        evidence,
        registry_ref=Path("registry.jsonl"),
        selector_ref=Path("selector.jsonl"),
        row_generated_at="2026-05-06T00:00:00+00:00",
    )

    manifest = builder.build_manifest([row], run_id="generic_actual_label_test")

    assert manifest["total_rows"] == 1
    assert manifest["metric_available_count"] == 1
    assert manifest["candidate_level_metric_count"] == 0
    assert manifest["generic_proxy_metric_count"] == 1
    assert manifest["blocked_generic_proxy_not_candidate_level"] == 1
    assert manifest["null_missing_evidence"] == 0
    assert manifest["excluded_untradable"] == 0
    assert manifest["actual_label_count"] == 0
    assert manifest["supervised_label_eligible_count"] == 0
    assert manifest["adoption_review_eligible_count"] == 0
    assert manifest["model_training_status"] == "blocked_binary_supervised_ml_no_candidate_level_labels"
    assert manifest["binary_supervised_ml_status"] == "blocked_no_candidate_level_supervised_labels"
    assert "replace_generic_momentum_proxy_with_candidate_specific_evaluation_before_training" in manifest[
        "approval_required_next_steps"
    ]
    assert "train_momentum_only_surrogate_after_metric_summary_exists" not in manifest[
        "approval_required_next_steps"
    ]


def test_validator_rejects_actual_without_approved_evidence() -> None:
    row = builder.build_ml_ready_row(
        registry_record(),
        selector_record(),
        evidence_packet(),
        registry_ref=Path("registry.jsonl"),
        selector_ref=Path("selector.jsonl"),
        row_generated_at="2026-05-06T00:00:00+00:00",
    )
    row["actual_total_return"] = 0.25

    with pytest.raises(ValueError, match="actual_\\* metrics require approved"):
        builder.validate_ml_ready_row(row)


def test_validator_rejects_pseudo_model_as_supervised_label() -> None:
    row = builder.build_ml_ready_row(
        registry_record(),
        selector_record(),
        evidence_packet(),
        registry_ref=Path("registry.jsonl"),
        selector_ref=Path("selector.jsonl"),
        row_generated_at="2026-05-06T00:00:00+00:00",
    )
    row["label_source"] = "pseudo_model"
    row["supervised_label_eligible"] = True

    with pytest.raises(ValueError, match="pseudo_model rows"):
        builder.validate_ml_ready_row(row)


def test_validator_rejects_random_split_without_group_isolation() -> None:
    row = builder.build_ml_ready_row(
        registry_record(),
        selector_record(),
        evidence_packet(),
        registry_ref=Path("registry.jsonl"),
        selector_ref=Path("selector.jsonl"),
        row_generated_at="2026-05-06T00:00:00+00:00",
    )
    row["split_policy"] = "random"

    with pytest.raises(ValueError, match="random split is disallowed"):
        builder.validate_ml_ready_row(row)


def test_manifest_blocks_binary_ml_when_supervised_labels_have_single_class() -> None:
    records = [
        {
            "candidate_id": f"sc:ecard:negative_{index}",
            "metric_source": "approved_evaluation_evidence",
            "metric_subject_type": "strategy_candidate",
            "metric_subject_id": f"sc:ecard:negative_{index}",
            "candidate_metric_match": True,
            "label_decision": "negative",
            "label_review_preferred": 0,
            "actual_label_source": "candidate_level_evaluation_evidence",
            "supervised_label_eligible": True,
            "adoption_required_checks_ready": True,
            "evaluation_status": "evidence_recorded",
            "candidate_status": "evaluable",
            "strategy_type": "momentum",
            "ml_training_status": "eligible_candidate_level_label",
        }
        for index in range(2)
    ]

    manifest = builder.build_manifest(records, run_id="single_class_test")

    assert manifest["supervised_label_eligible_count"] == 2
    assert manifest["label_positive"] == 0
    assert manifest["label_negative"] == 2
    assert manifest["model_training_status"] == "blocked_no_positive_negative_classes"
    assert manifest["binary_supervised_ml_status"] == "blocked_no_positive_negative_classes"
    assert "train_momentum_only_surrogate_after_metric_summary_exists" not in manifest[
        "approval_required_next_steps"
    ]


def test_manifest_allows_binary_ml_status_only_when_positive_and_negative_exist() -> None:
    records = []
    for label_decision, label_value in [("positive", 1), ("negative", 0)]:
        records.append(
            {
                "candidate_id": f"sc:ecard:{label_decision}",
                "metric_source": "approved_evaluation_evidence",
                "metric_subject_type": "strategy_candidate",
                "metric_subject_id": f"sc:ecard:{label_decision}",
                "candidate_metric_match": True,
                "label_decision": label_decision,
                "label_review_preferred": label_value,
                "actual_label_source": "candidate_level_evaluation_evidence",
                "supervised_label_eligible": True,
                "adoption_required_checks_ready": True,
                "evaluation_status": "evidence_recorded",
                "candidate_status": "evaluable",
                "strategy_type": "momentum",
                "ml_training_status": "eligible_candidate_level_label",
            }
        )

    manifest = builder.build_manifest(records, run_id="two_class_test")

    assert manifest["label_positive"] == 1
    assert manifest["label_negative"] == 1
    assert manifest["model_training_status"] == "labels_available_for_later_approval"
    assert (
        manifest["binary_supervised_ml_status"]
        == "candidate_level_supervised_labels_available_for_later_approval"
    )
    assert "train_momentum_only_surrogate_after_metric_summary_exists" in manifest[
        "approval_required_next_steps"
    ]


def test_build_ml_ready_candidate_inputs_writes_outputs(tmp_path: Path) -> None:
    selector_path = tmp_path / "selector.jsonl"
    registry_path = tmp_path / "registry.jsonl"
    evidence_dir = tmp_path / "evidence"
    output_dir = tmp_path / "ml_ready"

    write_jsonl(selector_path, [selector_record()])
    write_jsonl(registry_path, [registry_record()])
    write_evidence_md(evidence_dir / "momentum" / "ee_v0_3_test_momentum.md", evidence_packet())

    paths = builder.build_ml_ready_candidate_inputs(
        selector_path,
        registry_path,
        evidence_dir,
        output_dir,
        run_id="test_run",
    )

    assert paths["jsonl"].exists()
    assert paths["csv"].exists()
    assert paths["manifest"].exists()
    rows = [json.loads(line) for line in paths["jsonl"].read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["candidate_id"] == "sc:ecard:test_momentum"
    assert rows[0]["actual_label_source"] is None
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["record_count"] == 1
    assert manifest["actual_label_count"] == 0
    assert manifest["metric_available_count"] == 0
    assert manifest["candidate_level_metric_count"] == 0
    assert manifest["model_training_status"] == "blocked_binary_supervised_ml_no_candidate_level_labels"


def test_dry_run_cli_validates_local_inputs_without_writing_outputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    selector_path = tmp_path / "selector.jsonl"
    registry_path = tmp_path / "registry.jsonl"
    evidence_dir = tmp_path / "evidence"
    output_dir = tmp_path / "ml_ready"

    write_jsonl(selector_path, [selector_record()])
    write_jsonl(registry_path, [registry_record()])
    write_evidence_md(evidence_dir / "momentum" / "ee_v0_3_test_momentum.md", evidence_packet())

    exit_code = builder.main(
        [
            "--selector-input",
            str(selector_path),
            "--registry",
            str(registry_path),
            "--evidence-dir",
            str(evidence_dir),
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
    assert result["record_count"] == 1
    assert result["manifest"]["run_id"] == "dry_run_test"
    assert result["manifest"]["actual_label_count"] == 0
    assert result["manifest"]["supervised_label_eligible_count"] == 0
    assert result["manifest"]["metric_available_count"] == 0
    assert result["manifest"]["candidate_level_metric_count"] == 0
    assert result["manifest"]["ml_training_status_counts"] == {
        "blocked_no_candidate_level_metric": 1,
    }
