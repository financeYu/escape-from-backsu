from __future__ import annotations

import src.validation.v1_0_rc_freeze_readiness as readiness
from src.validation.v1_0_rc_freeze_readiness import (
    FREEZE_READY,
    FREEZE_READY_WITH_MINOR_FOLLOW_UPS,
    NOT_FREEZE_READY,
    STATUS_COMPLETE,
    audit_boundaries,
    audit_horizon_policy,
    audit_rebalance_disclosure,
    build_artifact_lineage_matrix,
    build_contract_freeze_list,
    build_contract_manifest,
    build_core_boundary_lock,
    build_freeze_readiness_report,
    build_ml_reproduction_report,
    build_phase_status_matrix,
    build_sample_readiness_artifacts,
    classify_horizon_reference,
    contains_prohibited_action_language,
    contains_user_facing_rebalance_instruction,
    determine_freeze_verdict,
    audit_route_state_alignment,
)


def _passing_validation_results():
    return [
        {
            "command": ".venv\\Scripts\\python.exe -m pytest -q tests/validation/test_v1_0_rc_freeze_readiness.py",
            "result": "PASS: synthetic",
            "run_in_this_session": True,
            "reason_if_not_run": "",
        },
        {
            "command": ".venv\\Scripts\\python.exe -m pytest -q tests/validation",
            "result": "PASS: synthetic",
            "run_in_this_session": True,
            "reason_if_not_run": "",
        },
        {
            "command": ".venv\\Scripts\\python.exe -m pytest -q tests/backtest/test_v1_0_horizon_policy.py tests/backtest/test_v1_0_simulation_run_manifest.py tests/backtest/test_v1_0_weight_config_loop.py tests/backtest/test_v1_0_layer_registry.py tests/backtest/test_v1_0_evaluation_evidence_v1.py tests/backtest/test_v1_0_selector_evaluator.py tests/backtest/test_v1_0_manual_review_packet.py",
            "result": "PASS: synthetic",
            "run_in_this_session": True,
            "reason_if_not_run": "",
        },
        {
            "command": ".venv\\Scripts\\python.exe -m pytest -q tests/backtest",
            "result": "PASS: synthetic",
            "run_in_this_session": True,
            "reason_if_not_run": "",
        },
    ]


def test_v1_0_rc_phase_status_matrix_detects_required_phases():
    matrix = build_phase_status_matrix()

    assert [row["phase_id"] for row in matrix] == [f"Phase {index}" for index in range(10)]
    assert all(row["status"] == STATUS_COMPLETE for row in matrix)


def test_v1_0_rc_route_state_alignment_matches_phase9_authority_docs():
    audit = audit_route_state_alignment()

    assert audit["status"] == STATUS_COMPLETE
    assert audit["expected_route_state"] == "complete_local_v1_0_freeze_baseline"
    assert audit["missing_required_markers"] == []
    assert audit["stale_markers"] == []


def test_v1_0_rc_route_state_alignment_rejects_stale_phase5_authority_docs(tmp_path):
    phase_status = [{"phase_id": f"Phase {index}", "status": STATUS_COMPLETE} for index in range(9)]
    required_docs = {
        "docs/root_hard_stops.md": "open through Phase 5 only\nPhase 6+ modules without later explicit task approval\n",
        "docs/roadmap_status.md": "Phase 6+ remains unopened\n",
        "docs/context/EXTENSION_REGISTRY.toml": 'status = "active_v1_0_rc_phase_5_readiness_route"\n',
        "docs/extension/v1_0_freeze_plan.md": "Phase 6+: NOT OPEN / requires later explicit task approval\n",
    }
    for relative_path, text in required_docs.items():
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    audit = audit_route_state_alignment(tmp_path, phase_status)

    assert audit["status"] == "NEEDS FIX"
    assert audit["stale_markers"]


def test_v1_0_rc_contract_manifest_requires_core_contracts():
    manifest = build_contract_manifest()
    names = {row["contract_name"] for row in manifest}

    assert {
        "HorizonPolicy",
        "SimulationRunManifest",
        "WeightConfig",
        "WeightConfigRunPlan",
        "LayerRegistry",
        "LayerAdapter",
        "LayerValidation",
        "EvaluationEvidenceV1",
        "SelectorInputManifestV1",
        "SelectorFeatureMatrixV1",
        "SelectorTrainabilityReportV1",
        "SelectorScoreManifestV1",
        "AdoptionCandidateReviewPriorityV1",
        "ManualReviewPacket",
        "FreezeReadinessPacket",
    }.issubset(names)


def test_v1_0_rc_contract_freeze_list_locks_step2_items():
    freeze_list = build_contract_freeze_list()

    assert [row["freeze_item"] for row in freeze_list] == [
        "HorizonPolicy",
        "SimulationRunManifest",
        "WeightConfigRunPlan / RunRecord boundary",
        "LayerRegistry status/category model",
        "EvaluationEvidenceV1",
        "SelectorFeatureMatrix / SelectorScoreManifest",
        "AdoptionCandidateReviewPriority",
        "ManualReviewPacket",
        "Phase 9 FreezeReadinessPacket",
    ]
    assert all(row["status"] == STATUS_COMPLETE for row in freeze_list)


def test_v1_0_rc_contract_freeze_list_rejects_missing_covered_contract():
    freeze_list = build_contract_freeze_list(contract_manifest=[])

    assert all(row["status"] == "NEEDS FIX" for row in freeze_list)
    assert any("missing contracts" in blocker for row in freeze_list for blocker in row["blockers"])


def test_v1_0_rc_ml_reproduction_report_checks_freeze_trigger_sections():
    report = build_ml_reproduction_report()

    assert [row["section"] for row in report["sections"]] == [
        "Dataset snapshot",
        "Label manifest",
        "Feature allowlist",
        "Split policy",
        "Leakage checks",
        "Baseline",
        "ML result",
        "Profit reproduction",
        "Stability",
        "Failure cases",
        "Guardrail result",
        "Verdict",
    ]
    assert report["freeze_trigger_confirmed"] is True
    assert report["freeze_trigger_verdict"] == "PASS"
    assert report["blockers"] == []


def test_v1_0_rc_ml_reproduction_report_passes_required_trigger_inputs():
    report = build_ml_reproduction_report()
    statuses = {row["section"]: row["status"] for row in report["sections"]}
    contents = {row["section"]: row["content"] for row in report["sections"]}

    assert statuses["Label manifest"] == "PASS"
    assert statuses["Split policy"] == "PASS"
    assert statuses["Leakage checks"] == "PASS"
    assert statuses["ML result"] == "PASS"
    assert statuses["Profit reproduction"] == "PASS"
    assert statuses["Stability"] == "PASS"
    assert statuses["Guardrail result"] == "PASS"
    assert "approved_label_manifest_ref=reports/review/v1_0_rc_ml_reproduction_report.md#label-manifest" in contents["Label manifest"]
    assert "model_training_performed=True" in contents["ML result"]
    assert "label_feature_overlap_status=PASS" in contents["ML result"]


def test_v1_0_rc_freeze_report_blocks_failed_ml_trigger(monkeypatch):
    def failed_ml_report():
        return {
            "freeze_trigger_confirmed": False,
            "freeze_trigger_verdict": "FAIL",
            "blockers": ["synthetic_ml_failure"],
        }

    monkeypatch.setattr(readiness, "build_ml_reproduction_report", failed_ml_report)
    report = readiness.build_freeze_readiness_report(validation_results=_passing_validation_results())

    assert report["freeze_readiness_verdict"] == NOT_FREEZE_READY
    assert any("ML reproduction freeze trigger did not pass" in blocker for blocker in report["blockers"])


def test_v1_0_rc_contract_manifest_requires_prohibited_flags_false():
    manifest = build_contract_manifest()

    for row in manifest:
        assert row["live_execution_enabled"] is False
        assert row["brokerage_integration_enabled"] is False
        assert row["order_generation_enabled"] is False
        assert row["user_facing_auto_rebalance_instruction_enabled"] is False
        assert row["production_ranking_update_enabled"] is False
        assert row["valuation_fundamental_active_scoring_enabled"] is False


def test_v1_0_rc_contract_manifest_detects_prohibited_config_flags(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "horizon_policy.toml").write_text(
        "[defaults]\nlive_execution_enabled = true\n",
        encoding="utf-8",
    )

    manifest = build_contract_manifest(tmp_path)
    horizon = next(row for row in manifest if row["contract_name"] == "HorizonPolicy")

    assert horizon["live_execution_enabled"] is True
    assert horizon["freeze_readiness_status"] == "NEEDS FIX"


def test_v1_0_rc_lineage_matrix_blocks_backtest_feedback_to_scoring():
    lineage = build_artifact_lineage_matrix()

    assert all(row["production_ranking_update_allowed"] is False for row in lineage)
    assert not any(row["target_artifact"] == "production_score_formula" for row in lineage)


def test_v1_0_rc_lineage_matrix_blocks_production_ranking_update():
    lineage = build_artifact_lineage_matrix()

    assert all(row["live_execution_allowed"] is False for row in lineage)
    assert all(row["validation_status"] == STATUS_COMPLETE for row in lineage)


def test_v1_0_rc_horizon_policy_audit_requires_1d_1w_1m():
    audit = audit_horizon_policy()

    assert audit["one_day_one_week_one_month_supported"] is True
    assert audit["one_day_five_day_twenty_day_supported"] is True
    assert {"1d", "5d", "20d"}.issubset(audit["supported_horizons"])
    assert audit["explicit_default_1d"] is True
    assert audit["status"] == STATUS_COMPLETE


def test_v1_0_rc_horizon_policy_audit_rejects_hidden_1d_hardcoding():
    classification = classify_horizon_reference(
        "Quant_mvp/backtest_mvp/new_active_path.py",
        "holding_period_days = 1",
    )

    assert classification == "suspicious active hardcoding"


def test_v1_0_rc_rebalance_audit_requires_material_disclosure():
    audit = audit_rebalance_disclosure()

    assert audit["historical_simulated_rebalancing_allowed"] is True
    assert audit["rebalance_frequency_retained_across_artifacts"] is True
    assert audit["material_rebalancing_disclosure_present"] is True
    assert audit["status"] == STATUS_COMPLETE


def test_v1_0_rc_rebalance_audit_marks_manifest_role_not_applicable():
    audit = audit_rebalance_disclosure()
    manifest_row = next(row for row in audit["rows"] if row["artifact"] == "SimulationRunManifest")

    assert manifest_row["rebalancing_role_present"] == "not_applicable"
    assert manifest_row["status"] == STATUS_COMPLETE


def test_v1_0_rc_rebalance_audit_blocks_user_facing_instruction():
    payload = {"review_text": "rebalance now"}

    assert contains_user_facing_rebalance_instruction(payload) is True


def test_v1_0_rc_evidence_boundary_blocks_live_execution():
    audit = audit_boundaries()

    assert audit["core_boundary_lock"]["status"] == STATUS_COMPLETE
    assert audit["prohibited_flags_false"] is True
    assert audit["evidence_only_boundary_preserved"] is True


def test_v1_0_rc_core_boundary_lock_freezes_step1_contract():
    lock = build_core_boundary_lock(
        evidence_only=True,
        candidate_only=True,
        manual_review_support=True,
        live_trading_enabled=False,
        brokerage_integration_enabled=False,
        order_generation_enabled=False,
        buy_sell_hold_framing_present=False,
        valuation_fundamental_active_scoring_enabled=False,
        futures_index_macro_regime_active_scoring_enabled=False,
        production_ranking_replacement_enabled=False,
    )

    assert lock["status"] == STATUS_COMPLETE
    assert lock["blockers"] == []


def test_v1_0_rc_core_boundary_lock_rejects_production_or_trading_escape():
    lock = build_core_boundary_lock(
        evidence_only=True,
        candidate_only=True,
        manual_review_support=False,
        live_trading_enabled=True,
        brokerage_integration_enabled=True,
        order_generation_enabled=True,
        buy_sell_hold_framing_present=True,
        valuation_fundamental_active_scoring_enabled=True,
        futures_index_macro_regime_active_scoring_enabled=True,
        production_ranking_replacement_enabled=True,
    )

    assert lock["status"] == "NEEDS FIX"
    assert len(lock["blockers"]) == 8


def test_v1_0_rc_evidence_boundary_blocks_brokerage_and_orders():
    report = build_freeze_readiness_report()

    core = report["boundary_audit"]["core_boundary_lock"]
    assert core["brokerage_integration_enabled"] is False
    assert core["order_generation_enabled"] is False
    assert core["production_ranking_replacement_enabled"] is False
    assert report["boundary_audit"]["production_ranking_changed"] is False
    assert report["boundary_audit"]["backtest_feedback_score_optimization_introduced"] is False


def test_v1_0_rc_selector_language_rejects_buy_sell_hold():
    assert contains_prohibited_action_language({"reason_codes": ["buy"]}) is True


def test_v1_0_rc_selector_language_rejects_trade_signal_framing():
    assert contains_prohibited_action_language({"evidence_summary": "trade signal"}) is True


def test_v1_0_rc_manual_review_packet_requires_manual_review():
    sample = build_sample_readiness_artifacts()

    assert sample["manual_review_packet"]["manual_review_required"] is True


def test_v1_0_rc_manual_review_packet_rejects_order_instruction():
    assert contains_prohibited_action_language({"manual_review_questions": ["place order"]}) is True


def test_v1_0_rc_blocks_valuation_fundamental_active_scoring():
    audit = audit_boundaries()

    assert audit["valuation_fundamental_active_scoring_enabled"] is False


def test_v1_0_rc_blocks_futures_index_macro_regime_active_scoring():
    audit = audit_boundaries()

    assert audit["valuation_fundamental_active_layers"] == []
    assert audit["futures_index_macro_regime_active_layers"] == []
    assert audit["futures_index_macro_regime_active_scoring_enabled"] is False


def test_v1_0_rc_freeze_verdict_not_ready_when_tests_not_recorded():
    report = build_freeze_readiness_report()

    assert report["freeze_readiness_verdict"] == NOT_FREEZE_READY
    assert any("required validation not passed" in blocker for blocker in report["blockers"])


def test_v1_0_rc_freeze_verdict_ready_with_recorded_validation_results():
    validation_results = [
        {
            "command": ".venv\\Scripts\\python.exe -m pytest -q tests/validation/test_v1_0_rc_freeze_readiness.py",
            "result": "19 passed",
            "run_in_this_session": True,
            "reason_if_not_run": "",
        },
        {
            "command": ".venv\\Scripts\\python.exe -m pytest -q tests/validation",
            "result": "171 passed",
            "run_in_this_session": True,
            "reason_if_not_run": "",
        },
        {
            "command": ".venv\\Scripts\\python.exe -m pytest -q tests/backtest/test_v1_0_horizon_policy.py tests/backtest/test_v1_0_simulation_run_manifest.py tests/backtest/test_v1_0_weight_config_loop.py tests/backtest/test_v1_0_layer_registry.py tests/backtest/test_v1_0_evaluation_evidence_v1.py tests/backtest/test_v1_0_selector_evaluator.py tests/backtest/test_v1_0_manual_review_packet.py",
            "result": "119 passed",
            "run_in_this_session": True,
            "reason_if_not_run": "",
        },
        {
            "command": ".venv\\Scripts\\python.exe -m pytest -q tests/backtest",
            "result": "173 passed",
            "run_in_this_session": True,
            "reason_if_not_run": "",
        },
    ]

    report = build_freeze_readiness_report(validation_results=validation_results)

    assert report["freeze_readiness_verdict"] == FREEZE_READY_WITH_MINOR_FOLLOW_UPS


def test_v1_0_rc_freeze_verdict_not_ready_when_required_contract_missing():
    verdict = determine_freeze_verdict(
        phase_status=[{"status": STATUS_COMPLETE}],
        contract_manifest=[{"freeze_readiness_status": "NOT FOUND"}],
        audit_statuses=[STATUS_COMPLETE],
        blockers=[],
        minor_followups=[],
    )

    assert verdict == NOT_FREEZE_READY


def test_v1_0_rc_freeze_verdict_ready_when_all_checks_pass():
    verdict = determine_freeze_verdict(
        phase_status=[{"status": STATUS_COMPLETE}],
        contract_manifest=[{"freeze_readiness_status": STATUS_COMPLETE}],
        audit_statuses=[STATUS_COMPLETE],
        blockers=[],
        minor_followups=[],
    )

    assert verdict == FREEZE_READY
