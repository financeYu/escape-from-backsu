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
    assert row["supervised_label_eligible"] is False
    assert row["adoption_review_eligible"] is False
    assert row["actual_metric_summary_available"] is False
    assert row["evaluation_status"] == "contract_only"
    assert row["prediction_allowed_uses"] == builder.ALLOWED_PREDICTION_USES


def test_evidence_recorded_metric_summary_populates_actual_labels() -> None:
    evidence = evidence_packet(
        status="evidence_recorded",
        failure_flags=[],
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

    assert row["actual_label_source"] == "approved_evaluation_evidence"
    assert row["actual_label_evidence_id"] == "ee_v0_3_test_momentum"
    assert row["actual_total_return"] == 0.12
    assert row["actual_max_drawdown"] == -0.08
    assert row["actual_volatility"] == 0.18
    assert row["actual_turnover"] == 0.42
    assert row["actual_sharpe"] == 1.1
    assert row["actual_oos_stability"] == "walk_forward_pass"
    assert row["supervised_label_eligible"] is True
    assert row["adoption_review_eligible"] is True


def test_evidence_recorded_without_oos_check_is_not_adoption_review_eligible() -> None:
    evidence = evidence_packet(
        status="evidence_recorded",
        failure_flags=[],
        metric_summary={"oos_stability_status": "not_available_single_pass_snapshot"},
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

    assert row["actual_label_source"] == "approved_evaluation_evidence"
    assert row["supervised_label_eligible"] is True
    assert row["adoption_required_checks_ready"] is False
    assert row["adoption_review_eligible"] is False


def test_generic_momentum_proxy_metric_summary_is_not_supervised_label() -> None:
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

    assert row["label_source"] == "unlabeled"
    assert row["actual_label_source"] is None
    assert row["actual_total_return"] is None
    assert row["supervised_label_eligible"] is False
    assert row["ml_training_status"] == "blocked_generic_proxy_metric_summary"
    assert row["actual_label_blocked_reason"] == "generic_momentum_proxy_not_candidate_level"


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

    with pytest.raises(ValueError, match="actual_\\* labels require approved"):
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
    assert manifest["model_training_status"] == "blocked_no_metric_summary_labels"
