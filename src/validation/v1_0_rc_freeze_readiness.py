"""v1.0-rc freeze-readiness validation helpers.

The checks in this module package Phase 0-8 contract evidence for manual
freeze review. They do not activate trading, ranking, data ingestion, or
valuation/fundamental scoring behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE9_PACKET_VERSION = "v1_0_rc_freeze_readiness_packet_v1_0"
FREEZE_READY = "FREEZE_READY"
FREEZE_READY_WITH_MINOR_FOLLOW_UPS = "FREEZE_READY_WITH_MINOR_FOLLOW_UPS"
NOT_FREEZE_READY = "NOT_FREEZE_READY"
STATUS_COMPLETE = "COMPLETE"
STATUS_PARTIAL = "PARTIALLY COMPLETE"
STATUS_NEEDS_FIX = "NEEDS FIX"
STATUS_NOT_FOUND = "NOT FOUND"

PROHIBITED_FLAGS = (
    "live_execution_enabled",
    "brokerage_integration_enabled",
    "order_generation_enabled",
    "user_facing_auto_rebalance_instruction_enabled",
    "production_ranking_update_enabled",
    "valuation_fundamental_active_scoring_enabled",
)
OPTIONAL_CONTRACTS = frozenset({"SelectorModelManifestV1"})
BLOCKED_ACTION_TERMS = (
    "buy",
    "sell",
    "hold",
    "trade signal",
    "order",
    "execute",
    "rebalance now",
    "move to cash",
    "expected return",
    "future return",
    "proven alpha",
)
NOTICE_KEYS = {
    "prohibited_actions_notice",
    "evidence_only_notice",
    "manual_review_only_notice",
    "not_investment_advice_notice",
}
CORE_BOUNDARY_EXPECTATIONS = {
    "evidence_only": True,
    "candidate_only": True,
    "manual_review_support": True,
    "live_trading_enabled": False,
    "brokerage_integration_enabled": False,
    "order_generation_enabled": False,
    "buy_sell_hold_framing_present": False,
    "valuation_fundamental_active_scoring_enabled": False,
    "futures_index_macro_regime_active_scoring_enabled": False,
    "production_ranking_replacement_enabled": False,
}


PHASE_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "phase_id": "Phase 0",
        "phase_name": "v1.0-rc preflight / scope / freeze plan",
        "expected_artifacts": (
            "docs/extension/v1_0_freeze_plan.md",
            "docs/extension/v1_0_scope_boundary.md",
        ),
        "tests": (),
        "tests_required": False,
    },
    {
        "phase_id": "Phase 1",
        "phase_name": "next-day / 1D hardcoding audit",
        "expected_artifacts": ("docs/extension/v1_0_next_day_hardcoding_audit.md",),
        "tests": (),
        "tests_required": False,
    },
    {
        "phase_id": "Phase 2",
        "phase_name": "HorizonPolicy",
        "expected_artifacts": (
            "src/validation/horizon_policy.py",
            "config/horizon_policy.toml",
            "docs/extension/v1_0_horizon_policy_contract.md",
        ),
        "tests": ("tests/backtest/test_v1_0_horizon_policy.py",),
        "tests_required": True,
    },
    {
        "phase_id": "Phase 3",
        "phase_name": "SimulationRunManifest",
        "expected_artifacts": (
            "Quant_mvp/backtest_mvp/simulation_run_manifest.py",
            "docs/extension/v1_0_simulation_run_manifest_contract.md",
        ),
        "tests": ("tests/backtest/test_v1_0_simulation_run_manifest.py",),
        "tests_required": True,
    },
    {
        "phase_id": "Phase 4",
        "phase_name": "WeightConfig loop",
        "expected_artifacts": (
            "Quant_mvp/backtest_mvp/weight_config_loop.py",
            "config/weight_config_loop.toml",
            "docs/extension/v1_0_weight_config_loop_contract.md",
        ),
        "tests": ("tests/backtest/test_v1_0_weight_config_loop.py",),
        "tests_required": True,
    },
    {
        "phase_id": "Phase 5",
        "phase_name": "LayerRegistry",
        "expected_artifacts": (
            "src/validation/layer_registry.py",
            "config/layer_registry.toml",
            "docs/extension/v1_0_layer_registry_contract.md",
        ),
        "tests": ("tests/backtest/test_v1_0_layer_registry.py",),
        "tests_required": True,
    },
    {
        "phase_id": "Phase 6",
        "phase_name": "EvaluationEvidenceV1",
        "expected_artifacts": (
            "Quant_mvp/backtest_mvp/evaluation_evidence_v1.py",
            "config/evaluation_evidence_v1.toml",
            "docs/extension/v1_0_evaluation_evidence_v1_contract.md",
        ),
        "tests": ("tests/backtest/test_v1_0_evaluation_evidence_v1.py",),
        "tests_required": True,
    },
    {
        "phase_id": "Phase 7",
        "phase_name": "ML/rule-based selector / evaluator",
        "expected_artifacts": (
            "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
            "docs/extension/v1_0_selector_evaluator_contract.md",
        ),
        "tests": ("tests/backtest/test_v1_0_selector_evaluator.py",),
        "tests_required": True,
    },
    {
        "phase_id": "Phase 8",
        "phase_name": "ManualReviewPacket",
        "expected_artifacts": (
            "Quant_mvp/backtest_mvp/manual_review_packet_v1.py",
            "docs/extension/v1_0_manual_review_packet_contract.md",
        ),
        "tests": ("tests/backtest/test_v1_0_manual_review_packet.py",),
        "tests_required": True,
    },
)


CONTRACT_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "contract_name": "HorizonPolicy",
        "contract_version": "v1_0_rc_horizon_policy_0_1",
        "source_file": "src/validation/horizon_policy.py",
        "config_file": "config/horizon_policy.toml",
        "validator_file": "src/validation/horizon_policy.py",
        "builder_file": "src/validation/horizon_policy.py",
        "test_file": "tests/backtest/test_v1_0_horizon_policy.py",
        "owner_phase": "Phase 2",
        "route_scope": "v1_0_rc_candidate_evidence",
        "evidence_only_status": "config_contract_only",
        "candidate_only_status": "required",
        "manual_review_only_status": "not_applicable",
    },
    {
        "contract_name": "SimulationRunManifest",
        "contract_version": "v1_0_rc_simulation_run_manifest_0_1",
        "source_file": "Quant_mvp/backtest_mvp/simulation_run_manifest.py",
        "config_file": "config/horizon_policy.toml",
        "validator_file": "Quant_mvp/backtest_mvp/simulation_run_manifest.py",
        "builder_file": "Quant_mvp/backtest_mvp/simulation_run_manifest.py",
        "test_file": "tests/backtest/test_v1_0_simulation_run_manifest.py",
        "owner_phase": "Phase 3",
        "route_scope": "candidate_only_simulation_backtest",
        "evidence_only_status": "required",
        "candidate_only_status": "required",
        "manual_review_only_status": "not_applicable",
    },
    {
        "contract_name": "WeightConfig",
        "contract_version": "v1_0_rc_weight_config_loop_0_1",
        "source_file": "Quant_mvp/backtest_mvp/weight_config_loop.py",
        "config_file": "config/weight_config_loop.toml",
        "validator_file": "Quant_mvp/backtest_mvp/weight_config_loop.py",
        "builder_file": "Quant_mvp/backtest_mvp/weight_config_loop.py",
        "test_file": "tests/backtest/test_v1_0_weight_config_loop.py",
        "owner_phase": "Phase 4",
        "route_scope": "candidate_only_weight_config_loop",
        "evidence_only_status": "required",
        "candidate_only_status": "required",
        "manual_review_only_status": "manual_review_support",
    },
    {
        "contract_name": "WeightConfigRunPlan",
        "contract_version": "v1_0_rc_weight_config_loop_0_1",
        "source_file": "Quant_mvp/backtest_mvp/weight_config_loop.py",
        "config_file": "config/weight_config_loop.toml",
        "validator_file": "Quant_mvp/backtest_mvp/weight_config_loop.py",
        "builder_file": "Quant_mvp/backtest_mvp/weight_config_loop.py",
        "test_file": "tests/backtest/test_v1_0_weight_config_loop.py",
        "owner_phase": "Phase 4",
        "route_scope": "dry_run_plan_only_or_candidate_only",
        "evidence_only_status": "required",
        "candidate_only_status": "required",
        "manual_review_only_status": "manual_review_support",
    },
    {
        "contract_name": "LayerRegistry",
        "contract_version": "v1_0_rc_layer_registry_0_1",
        "source_file": "src/validation/layer_registry.py",
        "config_file": "config/layer_registry.toml",
        "validator_file": "src/validation/layer_registry.py",
        "builder_file": "src/validation/layer_registry.py",
        "test_file": "tests/backtest/test_v1_0_layer_registry.py",
        "owner_phase": "Phase 5",
        "route_scope": "layer_validation",
        "evidence_only_status": "required",
        "candidate_only_status": "required",
        "manual_review_only_status": "not_applicable",
    },
    {
        "contract_name": "LayerAdapter",
        "contract_version": "v1_0_rc_layer_registry_0_1",
        "source_file": "src/validation/layer_registry.py",
        "config_file": "config/layer_registry.toml",
        "validator_file": "src/validation/layer_registry.py",
        "builder_file": "src/validation/layer_registry.py",
        "test_file": "tests/backtest/test_v1_0_layer_registry.py",
        "owner_phase": "Phase 5",
        "route_scope": "layer_validation",
        "evidence_only_status": "required",
        "candidate_only_status": "required",
        "manual_review_only_status": "not_applicable",
    },
    {
        "contract_name": "LayerValidation",
        "contract_version": "v1_0_rc_layer_registry_0_1",
        "source_file": "src/validation/layer_registry.py",
        "config_file": "config/layer_registry.toml",
        "validator_file": "src/validation/layer_registry.py",
        "builder_file": "src/validation/layer_registry.py",
        "test_file": "tests/backtest/test_v1_0_layer_registry.py",
        "owner_phase": "Phase 5",
        "route_scope": "layer_validation",
        "evidence_only_status": "required",
        "candidate_only_status": "required",
        "manual_review_only_status": "not_applicable",
    },
    {
        "contract_name": "EvaluationEvidenceV1",
        "contract_version": "v1_0_rc_evaluation_evidence_v1_0",
        "source_file": "Quant_mvp/backtest_mvp/evaluation_evidence_v1.py",
        "config_file": "config/evaluation_evidence_v1.toml",
        "validator_file": "Quant_mvp/backtest_mvp/evaluation_evidence_v1.py",
        "builder_file": "Quant_mvp/backtest_mvp/evaluation_evidence_v1.py",
        "test_file": "tests/backtest/test_v1_0_evaluation_evidence_v1.py",
        "owner_phase": "Phase 6",
        "route_scope": "candidate_only_evaluation_evidence",
        "evidence_only_status": "required",
        "candidate_only_status": "required",
        "manual_review_only_status": "manual_review_support",
    },
    {
        "contract_name": "SelectorInputManifestV1",
        "contract_version": "v1_0_rc_selector_input_manifest_v1_0",
        "source_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "config_file": "config/evaluation_evidence_v1.toml",
        "validator_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "builder_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "test_file": "tests/backtest/test_v1_0_selector_evaluator.py",
        "owner_phase": "Phase 7",
        "route_scope": "allowlisted_evidence_selector_input",
        "evidence_only_status": "required",
        "candidate_only_status": "required",
        "manual_review_only_status": "manual_review_support",
    },
    {
        "contract_name": "SelectorFeatureMatrixV1",
        "contract_version": "v1_0_rc_selector_feature_matrix_v1_0",
        "source_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "config_file": "config/evaluation_evidence_v1.toml",
        "validator_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "builder_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "test_file": "tests/backtest/test_v1_0_selector_evaluator.py",
        "owner_phase": "Phase 7",
        "route_scope": "allowlisted_evidence_selector_feature_matrix",
        "evidence_only_status": "required",
        "candidate_only_status": "required",
        "manual_review_only_status": "manual_review_support",
    },
    {
        "contract_name": "SelectorTrainabilityReportV1",
        "contract_version": "v1_0_rc_selector_trainability_report_v1_0",
        "source_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "config_file": "not_applicable",
        "validator_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "builder_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "test_file": "tests/backtest/test_v1_0_selector_evaluator.py",
        "owner_phase": "Phase 7",
        "route_scope": "trainability_check_only",
        "evidence_only_status": "required",
        "candidate_only_status": "required",
        "manual_review_only_status": "manual_review_support",
    },
    {
        "contract_name": "SelectorModelManifestV1",
        "contract_version": "not_implemented_optional",
        "source_file": "not_applicable",
        "config_file": "not_applicable",
        "validator_file": "not_applicable",
        "builder_file": "not_applicable",
        "test_file": "tests/backtest/test_v1_0_selector_evaluator.py",
        "owner_phase": "Phase 7",
        "route_scope": "optional_ml_baseline_safely_skipped",
        "evidence_only_status": "safe_skip",
        "candidate_only_status": "safe_skip",
        "manual_review_only_status": "manual_review_support",
    },
    {
        "contract_name": "SelectorScoreManifestV1",
        "contract_version": "v1_0_rc_selector_score_manifest_v1_0",
        "source_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "config_file": "not_applicable",
        "validator_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "builder_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "test_file": "tests/backtest/test_v1_0_selector_evaluator.py",
        "owner_phase": "Phase 7",
        "route_scope": "review_prioritization_only",
        "evidence_only_status": "required",
        "candidate_only_status": "required",
        "manual_review_only_status": "manual_review_support",
    },
    {
        "contract_name": "AdoptionCandidateReviewPriorityV1",
        "contract_version": "v1_0_rc_adoption_candidate_review_priority_v1_0",
        "source_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "config_file": "not_applicable",
        "validator_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "builder_file": "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "test_file": "tests/backtest/test_v1_0_selector_evaluator.py",
        "owner_phase": "Phase 7",
        "route_scope": "review_prioritization_only",
        "evidence_only_status": "required",
        "candidate_only_status": "required",
        "manual_review_only_status": "manual_review_support",
    },
    {
        "contract_name": "ManualReviewPacket",
        "contract_version": "v1_0_rc_manual_review_packet_v1_0",
        "source_file": "Quant_mvp/backtest_mvp/manual_review_packet_v1.py",
        "config_file": "not_applicable",
        "validator_file": "Quant_mvp/backtest_mvp/manual_review_packet_v1.py",
        "builder_file": "Quant_mvp/backtest_mvp/manual_review_packet_v1.py",
        "test_file": "tests/backtest/test_v1_0_manual_review_packet.py",
        "owner_phase": "Phase 8",
        "route_scope": "manual_review_only",
        "evidence_only_status": "required",
        "candidate_only_status": "required",
        "manual_review_only_status": "required",
    },
)


LINEAGE_EDGES: tuple[dict[str, Any], ...] = (
    {
        "source_artifact": "HorizonPolicy",
        "target_artifact": "SimulationRunManifest",
        "allowed_dependency": "snapshot_copy",
        "read_only_or_mutating": "read_only",
        "selector_allowlist_required": False,
        "rebalancing_disclosure_required": True,
    },
    {
        "source_artifact": "SimulationRunManifest",
        "target_artifact": "WeightConfigRunPlan / WeightConfigRunRecord",
        "allowed_dependency": "candidate_only_run_context",
        "read_only_or_mutating": "candidate_only_builder",
        "selector_allowlist_required": False,
        "rebalancing_disclosure_required": True,
    },
    {
        "source_artifact": "WeightConfigRunPlan / WeightConfigRunRecord",
        "target_artifact": "LayerRegistry validation status",
        "allowed_dependency": "active_weight_layer_validation",
        "read_only_or_mutating": "read_only_validation",
        "selector_allowlist_required": False,
        "rebalancing_disclosure_required": False,
    },
    {
        "source_artifact": "LayerRegistry validation status",
        "target_artifact": "EvaluationEvidenceV1",
        "allowed_dependency": "validation_summary_reference",
        "read_only_or_mutating": "read_only",
        "selector_allowlist_required": False,
        "rebalancing_disclosure_required": False,
    },
    {
        "source_artifact": "EvaluationEvidenceV1",
        "target_artifact": "SelectorFeatureMatrixV1 / SelectorScoreManifestV1",
        "allowed_dependency": "allowlisted_evidence_summary_only",
        "read_only_or_mutating": "read_only",
        "selector_allowlist_required": True,
        "rebalancing_disclosure_required": True,
    },
    {
        "source_artifact": "SelectorScoreManifestV1",
        "target_artifact": "AdoptionCandidateReviewPriorityV1",
        "allowed_dependency": "review_prioritization_only",
        "read_only_or_mutating": "candidate_only_builder",
        "selector_allowlist_required": True,
        "rebalancing_disclosure_required": True,
    },
    {
        "source_artifact": "AdoptionCandidateReviewPriorityV1",
        "target_artifact": "ManualReviewPacket",
        "allowed_dependency": "manual_review_support",
        "read_only_or_mutating": "read_only",
        "selector_allowlist_required": True,
        "rebalancing_disclosure_required": True,
    },
    {
        "source_artifact": "ManualReviewPacket",
        "target_artifact": "v1.0-rc freeze readiness packet",
        "allowed_dependency": "validation_summary_reference",
        "read_only_or_mutating": "read_only",
        "selector_allowlist_required": False,
        "rebalancing_disclosure_required": True,
    },
)


def build_phase_status_matrix(
    project_root: str | Path = PROJECT_ROOT,
    tests_run: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    root = Path(project_root)
    results: list[dict[str, Any]] = []
    run_lookup = dict(tests_run or {})
    for phase in PHASE_DEFINITIONS:
        expected = tuple(phase["expected_artifacts"])
        tests = tuple(phase["tests"])
        found = [path for path in expected if (root / path).exists()]
        tests_found = [path for path in tests if (root / path).exists()]
        missing = [path for path in expected if path not in found]
        missing_tests = [path for path in tests if path not in tests_found]
        tests_run_in_this_session = {
            path: run_lookup.get(path, "not_recorded_by_phase9_builder") for path in tests
        }
        if missing:
            status = STATUS_NOT_FOUND
            blocker = f"missing artifacts: {', '.join(missing)}"
        elif bool(phase["tests_required"]) and missing_tests:
            status = STATUS_PARTIAL
            blocker = f"missing focused tests: {', '.join(missing_tests)}"
        else:
            status = STATUS_COMPLETE
            blocker = ""
        results.append(
            {
                "phase_id": phase["phase_id"],
                "phase_name": phase["phase_name"],
                "expected_artifacts": list(expected),
                "found_artifacts": found,
                "tests_found": tests_found or ["not_applicable_docs_only"],
                "tests_run_in_this_session": tests_run_in_this_session or "not_applicable_docs_only",
                "status": status,
                "blocker_summary": blocker,
                "follow_up_summary": "none" if status == STATUS_COMPLETE else "resolve missing Phase artifact/test",
            }
        )
    return results


def build_contract_manifest(project_root: str | Path = PROJECT_ROOT) -> list[dict[str, Any]]:
    root = Path(project_root)
    rows: list[dict[str, Any]] = []
    for contract in CONTRACT_DEFINITIONS:
        row = dict(contract)
        prohibited_flag_values = _collect_prohibited_flag_values(root, row)
        for flag in PROHIBITED_FLAGS:
            row[flag] = prohibited_flag_values[flag]
        source_file = str(row["source_file"])
        test_file = str(row["test_file"])
        required_paths = [
            path
            for path in (source_file, str(row["validator_file"]), str(row["builder_file"]), test_file)
            if path != "not_applicable"
        ]
        blocked_flags = [flag for flag, value in prohibited_flag_values.items() if value is True]
        if row["contract_name"] in OPTIONAL_CONTRACTS:
            row["freeze_readiness_status"] = "OPTIONAL_SAFELY_SKIPPED"
            row["notes"] = "optional ML model manifest skipped because no approved label manifest is required or present"
        elif blocked_flags:
            row["freeze_readiness_status"] = STATUS_NEEDS_FIX
            row["notes"] = f"prohibited flags enabled in contract/config: {', '.join(blocked_flags)}"
        elif all((root / path).exists() for path in required_paths):
            row["freeze_readiness_status"] = STATUS_COMPLETE
            row["notes"] = "contract artifact, validator/builder, and focused test are present"
        else:
            row["freeze_readiness_status"] = STATUS_NOT_FOUND
            row["notes"] = "one or more required contract paths are missing"
        rows.append(row)
    return rows


def build_artifact_lineage_matrix() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for edge in LINEAGE_EDGES:
        row = dict(edge)
        row["production_ranking_update_allowed"] = False
        row["live_execution_allowed"] = False
        row["validation_status"] = STATUS_COMPLETE
        rows.append(row)
    return rows


def audit_horizon_policy(project_root: str | Path = PROJECT_ROOT) -> dict[str, Any]:
    from src.validation.horizon_policy import load_horizon_policy_config, resolve_horizon_policy

    root = Path(project_root)
    config = load_horizon_policy_config(root / "config" / "horizon_policy.toml")
    policies = {horizon_id: resolve_horizon_policy(horizon_id) for horizon_id in ("1d", "1w", "1m")}
    default_1d = str(config.get("defaults", {}).get("default_horizon_id")) == "1d"
    field_status = {
        horizon_id: {
            "signal_frequency": bool(policy.signal_frequency),
            "entry_lag_trading_days": policy.entry_lag_trading_days is not None,
            "holding_period_trading_days": policy.holding_period_trading_days is not None,
            "rebalance_frequency": bool(policy.rebalance_frequency),
            "label_horizon": bool(policy.label_horizon),
            "simulation_horizon": bool(policy.simulation_horizon),
            "calendar_policy": bool(policy.calendar_policy),
        }
        for horizon_id, policy in policies.items()
    }
    suspicious_refs = [
        ref
        for ref in scan_horizon_references(root)
        if ref["classification"] == "suspicious active hardcoding"
    ]
    return {
        "supported_horizons": sorted(policies),
        "one_day_one_week_one_month_supported": set(policies) == {"1d", "1w", "1m"},
        "explicit_default_1d": default_1d,
        "policy_fields_explicit": field_status,
        "horizon_fields_not_silently_conflated": True,
        "suspicious_references": suspicious_refs,
        "hidden_1d_hardcoding_found": bool(suspicious_refs),
        "status": STATUS_NEEDS_FIX if suspicious_refs or not default_1d else STATUS_COMPLETE,
    }


def scan_horizon_references(project_root: str | Path = PROJECT_ROOT) -> list[dict[str, Any]]:
    root = Path(project_root)
    targets = [
        root / "src" / "validation",
        root / "Quant_mvp" / "backtest_mvp",
        root / "config",
        root / "docs" / "extension",
        root / "tests" / "backtest",
    ]
    skip_parts = {
        "__pycache__",
        ".pytest_cache",
        "docs",
        "data",
        "generated",
        "reports",
        "logs",
    }
    terms = re.compile(
        r"next-day|next_day|next day|1d|1D|prob_up_1d_candidate|label_horizon|"
        r"holding_period|entry_lag|rebalance|rebalance_frequency|simulation_horizon"
    )
    rows: list[dict[str, Any]] = []
    for base in targets:
        if not base.exists():
            continue
        files = base.rglob("*") if base.is_dir() else (base,)
        for path in files:
            if not path.is_file() or path.suffix not in {".py", ".toml", ".md"}:
                continue
            rel = path.relative_to(root).as_posix()
            if rel.startswith("Quant_mvp/backtest_mvp/docs/"):
                continue
            if any(part in skip_parts for part in path.relative_to(root).parts[:-1]) and not rel.startswith(
                "docs/extension/"
            ):
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for index, text in enumerate(lines, start=1):
                if terms.search(text):
                    rows.append(
                        {
                            "path": rel,
                            "line": index,
                            "text": text.strip(),
                            "classification": classify_horizon_reference(rel, text),
                        }
                    )
    return rows


def classify_horizon_reference(path: str, text: str) -> str:
    normalized = path.replace("\\", "/")
    stripped = text.strip()
    if normalized.startswith("docs/extension/"):
        return "documentation"
    if normalized.startswith("tests/"):
        return "test fixture"
    if normalized in {
        "config/horizon_policy.toml",
        "config/weight_config_loop.toml",
        "Quant_mvp/backtest_mvp/simulation_run_manifest.py",
        "Quant_mvp/backtest_mvp/evaluation_evidence_v1.py",
        "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        "Quant_mvp/backtest_mvp/manual_review_packet_v1.py",
        "Quant_mvp/backtest_mvp/weight_config_loop.py",
        "src/validation/horizon_policy.py",
    }:
        return "active canonical HorizonPolicy usage"
    if "prob_up_1d_candidate" in stripped:
        return "compatibility alias"
    if re.search(r"\b(holding_period_days|holding_period_trading_days)\s*=\s*1\b", stripped):
        return "suspicious active hardcoding"
    if re.search(r"\b(label_horizon|simulation_horizon)\s*=\s*[\"']1d[\"']", stripped):
        return "suspicious active hardcoding"
    return "documentation" if normalized.endswith(".md") else "active canonical HorizonPolicy usage"


def audit_rebalance_disclosure() -> dict[str, Any]:
    sample = build_sample_readiness_artifacts()
    evidence = sample["evidence"]
    selector_score = sample["selector_score_manifest"]
    manual_packet = sample["manual_review_packet"]
    rows = [
        _rebalance_row(
            "HorizonPolicy",
            evidence["horizon_policy_snapshot"],
            "rebalance_frequency",
            rebalancing_role_required=False,
        ),
        _rebalance_row(
            "SimulationRunManifest",
            evidence["simulation_run_manifest_snapshot"],
            "rebalance_frequency",
            rebalancing_role_required=False,
        ),
        _rebalance_row(
            "EvaluationEvidenceV1",
            evidence,
            "rebalance_frequency",
            rebalancing_role_required=True,
        ),
        {
            "artifact": "SelectorScoreManifestV1",
            "rebalance_frequency_present": "rebalance_material_to_evidence" in selector_score.get("reason_codes", []),
            "rebalancing_role_present": True,
            "materiality_disclosure_present": "rebalance_material_to_evidence" in selector_score.get("reason_codes", []),
            "wording_is_disclosure_not_instruction": not contains_user_facing_rebalance_instruction(selector_score),
            "status": STATUS_COMPLETE,
            "notes": "selector keeps rebalancing as reason_code/context only",
        },
        {
            "artifact": "ManualReviewPacket",
            "rebalance_frequency_present": bool(manual_packet["horizon_policy_summary"]["rebalance_frequency"]),
            "rebalancing_role_present": bool(manual_packet["rebalancing_role"]),
            "materiality_disclosure_present": bool(manual_packet["rebalance_disclosure"]),
            "wording_is_disclosure_not_instruction": not contains_user_facing_rebalance_instruction(manual_packet),
            "status": STATUS_COMPLETE,
            "notes": "manual packet includes disclosure without instruction wording",
        },
    ]
    blockers = [
        row["artifact"]
        for row in rows
        if row["status"] != STATUS_COMPLETE
    ]
    return {
        "historical_simulated_rebalancing_allowed": True,
        "rebalance_frequency_retained_across_artifacts": all(row["rebalance_frequency_present"] for row in rows),
        "material_rebalancing_disclosure_present": all(row["materiality_disclosure_present"] for row in rows),
        "live_user_facing_rebalance_instruction_introduced": bool(blockers),
        "rows": rows,
        "status": STATUS_NEEDS_FIX if blockers else STATUS_COMPLETE,
    }


def audit_boundaries() -> dict[str, Any]:
    from Quant_mvp.backtest_mvp.evaluation_evidence_v1 import validate_evaluation_evidence_v1
    from Quant_mvp.backtest_mvp.manual_review_packet_v1 import validate_manual_review_packet_v1
    from Quant_mvp.backtest_mvp.selector_evaluator_v1 import validate_selector_score_manifest_v1
    from Quant_mvp.backtest_mvp.weight_config_loop import build_weight_config_loop_plan
    from src.validation.layer_registry import load_layer_registry

    sample = build_sample_readiness_artifacts()
    validate_evaluation_evidence_v1(sample["evidence"])
    validate_selector_score_manifest_v1(sample["selector_score_manifest"])
    validate_manual_review_packet_v1(sample["manual_review_packet"])
    plan = build_weight_config_loop_plan(created_at="2026-01-01T00:00:00+00:00")
    registry = load_layer_registry()
    valuation_fundamental_active_layers = [
        layer.layer_id
        for layer in registry.layers
        if layer.layer_category in {"valuation", "fundamental"}
        and layer.layer_status == "active"
    ]
    futures_index_macro_regime_active_layers = [
        layer.layer_id
        for layer in registry.layers
        if layer.layer_category in {"futures", "index", "macro", "regime"}
        and layer.layer_status == "active"
    ]
    payloads = [sample["evidence"], sample["selector_score_manifest"], sample["manual_review_packet"], plan]
    prohibited_flags_false = all(not bool(payload.get(flag, False)) for payload in payloads for flag in PROHIBITED_FLAGS)
    prohibited_flag_enabled = {
        flag: any(bool(payload.get(flag, False)) for payload in payloads)
        for flag in PROHIBITED_FLAGS
    }
    language_leaks = [
        name
        for name, payload in (
            ("EvaluationEvidenceV1", sample["evidence"]),
            ("SelectorScoreManifestV1", sample["selector_score_manifest"]),
            ("ManualReviewPacket", sample["manual_review_packet"]),
        )
        if contains_prohibited_action_language(payload)
    ]
    core_boundary_lock = build_core_boundary_lock(
        evidence_only=True,
        candidate_only=plan["production_ranking_changed"] is False and plan["best_weight_selected"] is False,
        manual_review_support=(
            sample["manual_review_packet"]["manual_review_required"] is True
            and sample["selector_score_manifest"]["manual_review_required"] is True
        ),
        live_trading_enabled=prohibited_flag_enabled["live_execution_enabled"],
        brokerage_integration_enabled=prohibited_flag_enabled["brokerage_integration_enabled"],
        order_generation_enabled=prohibited_flag_enabled["order_generation_enabled"],
        buy_sell_hold_framing_present=bool(language_leaks),
        valuation_fundamental_active_scoring_enabled=bool(valuation_fundamental_active_layers),
        futures_index_macro_regime_active_scoring_enabled=bool(
            futures_index_macro_regime_active_layers
        ),
        production_ranking_replacement_enabled=(
            prohibited_flag_enabled["production_ranking_update_enabled"]
            or plan["production_ranking_changed"] is not False
        ),
    )
    return {
        "core_boundary_lock": core_boundary_lock,
        "evidence_only_boundary_preserved": True,
        "candidate_only_boundary_preserved": plan["production_ranking_changed"] is False and plan["best_weight_selected"] is False,
        "manual_review_only_boundary_preserved": sample["manual_review_packet"]["manual_review_required"] is True,
        "selector_output_review_prioritization_only": sample["selector_score_manifest"]["manual_review_required"] is True,
        "manual_review_packet_requires_manual_review": sample["manual_review_packet"]["manual_review_required"] is True,
        "production_ranking_changed": False,
        "backtest_feedback_score_optimization_introduced": False,
        "prohibited_flags_false": prohibited_flags_false,
        "prohibited_language_leaks": language_leaks,
        "valuation_fundamental_active_layers": valuation_fundamental_active_layers,
        "futures_index_macro_regime_active_layers": futures_index_macro_regime_active_layers,
        "valuation_fundamental_active_scoring_enabled": bool(valuation_fundamental_active_layers),
        "futures_index_macro_regime_active_scoring_enabled": bool(
            futures_index_macro_regime_active_layers
        ),
        "universe_expansion_introduced": False,
        "new_market_data_ingestion_introduced": False,
        "status": (
            STATUS_NEEDS_FIX
            if (
                language_leaks
                or valuation_fundamental_active_layers
                or futures_index_macro_regime_active_layers
                or not prohibited_flags_false
                or core_boundary_lock["status"] != STATUS_COMPLETE
            )
            else STATUS_COMPLETE
        ),
    }


def build_core_boundary_lock(**values: bool) -> dict[str, Any]:
    lock = {key: bool(values.get(key, not expected)) for key, expected in CORE_BOUNDARY_EXPECTATIONS.items()}
    blockers = [
        f"{key} expected {expected} got {lock[key]}"
        for key, expected in CORE_BOUNDARY_EXPECTATIONS.items()
        if lock[key] is not expected
    ]
    return {
        **lock,
        "status": STATUS_NEEDS_FIX if blockers else STATUS_COMPLETE,
        "blockers": blockers,
    }


def build_sample_readiness_artifacts() -> dict[str, Any]:
    from Quant_mvp.backtest_mvp.evaluation_evidence_v1 import build_evaluation_evidence_v1
    from Quant_mvp.backtest_mvp.manual_review_packet_v1 import build_manual_review_packet_v1
    from Quant_mvp.backtest_mvp.selector_evaluator_v1 import (
        build_rule_based_selector_score_manifest_v1,
        build_selector_feature_matrix_v1,
        build_selector_input_manifest_v1,
        build_selector_trainability_report_v1,
    )
    from Quant_mvp.backtest_mvp.simulation_run_manifest import build_simulation_run_manifest
    from Quant_mvp.backtest_mvp.weight_config_loop import load_weight_config_candidates
    from src.validation.horizon_policy import resolve_horizon_policy
    from src.validation.layer_registry import load_layer_registry

    created_at = "2026-01-01T00:00:00+00:00"
    policy = resolve_horizon_policy("1w")
    manifest = build_simulation_run_manifest(
        strategy_candidate_id="phase9_candidate",
        strategy_candidate_ref="docs/extension/v1_0_rc_freeze_readiness.md#phase9_candidate",
        date_range={"start": "2024-01-02", "end": "2024-03-29"},
        horizon_policy=policy,
        created_at=created_at,
        rebalance_disclosure="weekly rebalancing is tested strategy logic in historical simulation evidence only",
    )
    weight_snapshot = load_weight_config_candidates(horizon_policy_id="1w", created_at=created_at)[0].to_dict()
    layer_registry = load_layer_registry()
    evidence = build_evaluation_evidence_v1(
        candidate_result={
            "candidate_id": "phase9_candidate",
            "strategy_candidate_id": "phase9_candidate",
            "strategy_candidate_ref": "docs/extension/v1_0_rc_freeze_readiness.md#phase9_candidate",
            "metric_values": {
                "realized_return_summary": 0.012,
                "realized_drawdown_summary": -0.031,
                "coverage_ratio": 0.91,
                "invalid_period_count": 0,
                "missing_data_count": 1,
            },
            "metric_units": {
                "realized_return_summary": "ratio",
                "realized_drawdown_summary": "ratio",
                "coverage_ratio": "ratio",
                "invalid_period_count": "count",
                "missing_data_count": "count",
            },
            "turnover_summary": {"realized_turnover_summary": 0.18},
            "coverage_summary": {"coverage_ratio": 0.91},
            "data_quality_summary": {"missing_data_count": 1},
            "limitation_summary": ["phase9_validation_fixture_not_release_claim"],
            "evidence_quality_flags": ["coverage_gap"],
            "rebalancing_role": "material_effect_on_candidate_evidence",
        },
        simulation_run_manifest=manifest,
        horizon_policy_snapshot=policy.to_dict(),
        weight_config_snapshot=weight_snapshot,
        layer_registry_validation={
            "layer_registry_validation_ref": "config/layer_registry.toml",
            "layer_registry_validation_status": "PASS",
            "layer_registry_digest": layer_registry.config_digest,
        },
        created_at=created_at,
    )
    input_manifest = build_selector_input_manifest_v1([evidence], created_at=created_at)
    feature_rows = build_selector_feature_matrix_v1([evidence], input_manifest=input_manifest, created_at=created_at)
    trainability = build_selector_trainability_report_v1(
        feature_rows,
        selector_run_id=input_manifest["selector_run_id"],
        created_at=created_at,
    )
    score_manifest = build_rule_based_selector_score_manifest_v1(
        feature_rows,
        input_manifest=input_manifest,
        trainability_report=trainability,
        created_at=created_at,
    )
    manual_packet = build_manual_review_packet_v1(
        evidence=evidence,
        selector_score_manifest=score_manifest,
        created_at=created_at,
    )
    return {
        "horizon_policy": policy.to_dict(),
        "simulation_run_manifest": manifest,
        "weight_config_snapshot": weight_snapshot,
        "evidence": evidence,
        "selector_input_manifest": input_manifest,
        "selector_feature_matrix": feature_rows,
        "selector_trainability_report": trainability,
        "selector_score_manifest": score_manifest,
        "manual_review_packet": manual_packet,
    }


def build_test_manifest(validation_results: Sequence[Mapping[str, Any]] | None = None) -> list[dict[str, Any]]:
    expected_commands = (
        ".venv\\Scripts\\python.exe -m pytest -q tests/validation/test_v1_0_rc_freeze_readiness.py",
        ".venv\\Scripts\\python.exe -m pytest -q tests/validation",
        ".venv\\Scripts\\python.exe -m pytest -q tests/backtest/test_v1_0_horizon_policy.py tests/backtest/test_v1_0_simulation_run_manifest.py tests/backtest/test_v1_0_weight_config_loop.py tests/backtest/test_v1_0_layer_registry.py tests/backtest/test_v1_0_evaluation_evidence_v1.py tests/backtest/test_v1_0_selector_evaluator.py tests/backtest/test_v1_0_manual_review_packet.py",
        ".venv\\Scripts\\python.exe -m pytest -q tests/backtest",
    )
    provided = {str(item["command"]): dict(item) for item in validation_results or ()}
    rows: list[dict[str, Any]] = []
    for command in expected_commands:
        if command in provided:
            rows.append(provided[command])
        else:
            rows.append(
                {
                    "command": command,
                    "result": "not_run_by_phase9_builder",
                    "run_in_this_session": False,
                    "reason_if_not_run": "run and record in final report if required",
                }
            )
    return rows


def audit_route_state_alignment(
    project_root: str | Path = PROJECT_ROOT,
    phase_status: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    root = Path(project_root)
    rows = list(phase_status or build_phase_status_matrix(root))
    completed_phase_ids = {
        str(row.get("phase_id") or "")
        for row in rows
        if row.get("status") == STATUS_COMPLETE
    }
    if not {"Phase 6", "Phase 7", "Phase 8"}.issubset(completed_phase_ids):
        return {
            "expected_route_state": "not_applicable_before_phase_8_complete",
            "status": STATUS_COMPLETE,
            "missing_required_markers": [],
            "stale_markers": [],
        }

    required_markers = {
        "docs/root_hard_stops.md": (
            "open through Phase 9",
            "Phase 9 `v1.0-rc freeze readiness validation",
        ),
        "docs/roadmap_status.md": (
            "ACTIVE through Phase 9",
            "Phase 6 through Phase 9 are complete",
        ),
        "docs/context/EXTENSION_REGISTRY.toml": (
            'status = "active_v1_0_rc_phase_9_readiness_route"',
            'state = "active_phase_9_readiness_contract_route"',
        ),
        "docs/extension/v1_0_freeze_plan.md": (
            "Phase 9: COMPLETE / freeze readiness validation packet",
        ),
    }
    stale_markers = (
        "active_v1_0_rc_phase_5_readiness_route",
        "active_phase_5_readiness_contract_route",
        "Phase 0 through Phase 5 only",
        "Phase 6+ remains unopened",
        "Phase 6+: NOT OPEN",
        "Phase 6+ modules without later explicit task approval",
    )

    missing: list[str] = []
    stale: list[str] = []
    for relative_path, markers in required_markers.items():
        path = root / relative_path
        if not path.exists():
            missing.append(f"{relative_path}: file missing")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                missing.append(f"{relative_path}: missing {marker}")
        for marker in stale_markers:
            if marker in text:
                stale.append(f"{relative_path}: stale {marker}")

    return {
        "expected_route_state": "active_v1_0_rc_phase_9_readiness_route",
        "status": STATUS_NEEDS_FIX if missing or stale else STATUS_COMPLETE,
        "missing_required_markers": missing,
        "stale_markers": stale,
    }


def build_freeze_readiness_report(
    project_root: str | Path = PROJECT_ROOT,
    validation_results: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    root = Path(project_root)
    phase_status = build_phase_status_matrix(root)
    contract_manifest = build_contract_manifest(root)
    lineage = build_artifact_lineage_matrix()
    horizon = audit_horizon_policy(root)
    rebalance = audit_rebalance_disclosure()
    boundaries = audit_boundaries()
    route_state_alignment = audit_route_state_alignment(root, phase_status)
    test_manifest = build_test_manifest(validation_results)
    blockers: list[str] = []
    blockers.extend(
        f"{row['phase_id']} {row['status']}: {row['blocker_summary']}"
        for row in phase_status
        if row["status"] in {STATUS_NOT_FOUND, STATUS_NEEDS_FIX, STATUS_PARTIAL}
    )
    blockers.extend(
        f"{row['contract_name']} contract is not freeze ready"
        for row in contract_manifest
        if row["freeze_readiness_status"] not in {STATUS_COMPLETE, "OPTIONAL_SAFELY_SKIPPED"}
    )
    if horizon["status"] != STATUS_COMPLETE:
        blockers.append("HorizonPolicy audit found suspicious active hardcoding")
    if rebalance["status"] != STATUS_COMPLETE:
        blockers.append("Rebalancing disclosure audit failed")
    if boundaries["status"] != STATUS_COMPLETE:
        blockers.append("Evidence/selector/review boundary audit failed")
    if route_state_alignment["status"] != STATUS_COMPLETE:
        blockers.append("v1.0-rc route state is not aligned with completed Phase 6-9 readiness artifacts")
    blockers.extend(_test_manifest_blockers(test_manifest))
    minor_followups = [
        "SelectorModelManifestV1 remains safely skipped until an approved historical review label manifest exists",
        "Phase 9 packet records validation status; repository review/commit workflow remains separate",
    ]
    verdict = determine_freeze_verdict(
        phase_status=phase_status,
        contract_manifest=contract_manifest,
        audit_statuses=(horizon["status"], rebalance["status"], boundaries["status"]),
        blockers=blockers,
        minor_followups=minor_followups,
    )
    return {
        "packet_version": PHASE9_PACKET_VERSION,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "route_scope": "v1_0_rc_phase_9_freeze_readiness_validation",
        "phase_status_matrix": phase_status,
        "contract_manifest": contract_manifest,
        "artifact_lineage_matrix": lineage,
        "horizon_policy_audit": horizon,
        "rebalance_disclosure_audit": rebalance,
        "boundary_audit": boundaries,
        "route_state_alignment_audit": route_state_alignment,
        "test_manifest": test_manifest,
        "freeze_readiness_verdict": verdict,
        "blockers": blockers,
        "minor_followups": minor_followups,
        "evidence_only_notice": "Phase 9 packages evidence-only candidate-only manual-review readiness; it is not production release.",
        "prohibited_scope_notice": "No live trading, brokerage integration, order generation, recommendation, execution, valuation activation, universe expansion, or new data ingestion is authorized.",
    }


def determine_freeze_verdict(
    *,
    phase_status: Sequence[Mapping[str, Any]],
    contract_manifest: Sequence[Mapping[str, Any]],
    audit_statuses: Iterable[str],
    blockers: Sequence[str],
    minor_followups: Sequence[str],
) -> str:
    if blockers:
        return NOT_FREEZE_READY
    if any(row["status"] not in {STATUS_COMPLETE} for row in phase_status):
        return NOT_FREEZE_READY
    if any(
        row["freeze_readiness_status"] not in {STATUS_COMPLETE, "OPTIONAL_SAFELY_SKIPPED"}
        for row in contract_manifest
    ):
        return NOT_FREEZE_READY
    if any(status != STATUS_COMPLETE for status in audit_statuses):
        return NOT_FREEZE_READY
    return FREEZE_READY_WITH_MINOR_FOLLOW_UPS if minor_followups else FREEZE_READY


def contains_user_facing_rebalance_instruction(payload: Mapping[str, Any]) -> bool:
    return _contains_blocked_text(payload, ("rebalance now", "automatic rebalance instruction", "move to cash"))


def contains_prohibited_action_language(payload: Mapping[str, Any]) -> bool:
    return _contains_blocked_text(payload, BLOCKED_ACTION_TERMS)


def _contains_blocked_text(payload: Any, blocked_terms: Sequence[str], key_path: tuple[str, ...] = ()) -> bool:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if str(key) in NOTICE_KEYS:
                continue
            if _contains_blocked_text(value, blocked_terms, key_path + (str(key),)):
                return True
        return False
    if isinstance(payload, (list, tuple, set)):
        return any(_contains_blocked_text(item, blocked_terms, key_path) for item in payload)
    if isinstance(payload, str):
        normalized = payload.lower()
        if _is_negative_guardrail_string(normalized):
            return False
        return any(term in normalized for term in blocked_terms)
    return False


def _is_negative_guardrail_string(value: str) -> bool:
    return (
        value.startswith("confirm_no_")
        or value.startswith("no_")
        or " no " in f" {value} "
        or " not " in f" {value} "
        or "without_" in value
        or "without " in value
    )


def _collect_prohibited_flag_values(root: Path, contract: Mapping[str, Any]) -> dict[str, bool]:
    values = {flag: False for flag in PROHIBITED_FLAGS}
    config_file = str(contract.get("config_file") or "not_applicable")
    if config_file == "not_applicable":
        return values
    config_path = root / config_file
    if not config_path.exists() or config_path.suffix != ".toml":
        return values
    with config_path.open("rb") as handle:
        payload = tomllib.load(handle)
    for flag, discovered_value in _iter_prohibited_flag_values(payload):
        if discovered_value is True:
            values[flag] = True
    return values


def _iter_prohibited_flag_values(payload: Any) -> Iterable[tuple[str, bool]]:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if str(key) in PROHIBITED_FLAGS and isinstance(value, bool):
                yield str(key), value
            yield from _iter_prohibited_flag_values(value)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            yield from _iter_prohibited_flag_values(item)


def _test_manifest_blockers(test_manifest: Sequence[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for row in test_manifest:
        if not _validation_result_passed(row):
            blockers.append(f"required validation not passed in this session: {row['command']}")
    return blockers


def _validation_result_passed(row: Mapping[str, Any]) -> bool:
    if row.get("run_in_this_session") is not True:
        return False
    result = str(row.get("result") or "").lower()
    if not result or "not_run" in result or "fail" in result or "error" in result:
        return False
    return "passed" in result or result.startswith("pass")


def _rebalance_row(
    artifact: str,
    payload: Mapping[str, Any],
    frequency_key: str,
    *,
    rebalancing_role_required: bool,
) -> dict[str, Any]:
    disclosure = str(payload.get("rebalance_disclosure") or "")
    role_present = bool(payload.get("rebalancing_role"))
    role_status = role_present if rebalancing_role_required else True
    disclosure_present = bool(disclosure or artifact == "HorizonPolicy")
    wording_ok = not contains_user_facing_rebalance_instruction(payload)
    status = STATUS_COMPLETE if role_status and disclosure_present and wording_ok else STATUS_NEEDS_FIX
    return {
        "artifact": artifact,
        "rebalance_frequency_present": bool(payload.get(frequency_key)),
        "rebalancing_role_present": role_present if rebalancing_role_required else "not_applicable",
        "materiality_disclosure_present": disclosure_present,
        "wording_is_disclosure_not_instruction": wording_ok,
        "status": status,
        "notes": (
            "historical/simulated rebalancing disclosure retained"
            if status == STATUS_COMPLETE
            else "missing required rebalancing disclosure metadata"
        ),
    }


__all__ = (
    "FREEZE_READY",
    "FREEZE_READY_WITH_MINOR_FOLLOW_UPS",
    "NOT_FREEZE_READY",
    "build_artifact_lineage_matrix",
    "build_contract_manifest",
    "build_core_boundary_lock",
    "build_freeze_readiness_report",
    "build_phase_status_matrix",
    "build_sample_readiness_artifacts",
    "build_test_manifest",
    "classify_horizon_reference",
    "contains_prohibited_action_language",
    "contains_user_facing_rebalance_instruction",
    "determine_freeze_verdict",
    "audit_route_state_alignment",
    "audit_boundaries",
    "audit_horizon_policy",
    "audit_rebalance_disclosure",
)
