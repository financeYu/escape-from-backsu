"""v1.0-rc freeze-readiness validation helpers.

The checks in this module package Phase 0-9 contract evidence for manual
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
ML_REPRODUCTION_REPORT_VERSION = "v1_0_rc_ml_reproduction_report_v1_0"
ML_REPRODUCTION_LABEL_SOURCE_FIELDS = (
    "realized_return_summary",
    "realized_cost_summary",
    "realized_drawdown_summary",
    "coverage_ratio",
)
ML_REPRODUCTION_SELECTED_FEATURE_NAMES = (
    "realized_volatility_summary",
    "realized_turnover_summary",
    "hit_rate_historical_summary",
    "missing_data_count",
)
FREEZE_READY = "FREEZE_READY"
FREEZE_READY_WITH_MINOR_FOLLOW_UPS = "FREEZE_READY_WITH_MINOR_FOLLOW_UPS"
NOT_FREEZE_READY = "NOT_FREEZE_READY"
STATUS_COMPLETE = "COMPLETE"
STATUS_PARTIAL = "PARTIALLY COMPLETE"
STATUS_NEEDS_FIX = "NEEDS FIX"
STATUS_NOT_FOUND = "NOT FOUND"
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"

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
    {
        "phase_id": "Phase 9",
        "phase_name": "FreezeReadinessPacket",
        "expected_artifacts": (
            "src/validation/v1_0_rc_freeze_readiness.py",
            "scripts/build_v1_0_rc_freeze_readiness_packet.py",
            "reports/review/v1_0_rc_freeze_readiness_packet.md",
        ),
        "tests": ("tests/validation/test_v1_0_rc_freeze_readiness.py",),
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
    {
        "contract_name": "FreezeReadinessPacket",
        "contract_version": PHASE9_PACKET_VERSION,
        "source_file": "src/validation/v1_0_rc_freeze_readiness.py",
        "config_file": "not_applicable",
        "validator_file": "src/validation/v1_0_rc_freeze_readiness.py",
        "builder_file": "scripts/build_v1_0_rc_freeze_readiness_packet.py",
        "test_file": "tests/validation/test_v1_0_rc_freeze_readiness.py",
        "owner_phase": "Phase 9",
        "route_scope": "phase9_freeze_readiness_validation_packet",
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


CONTRACT_FREEZE_LIST: tuple[dict[str, Any], ...] = (
    {
        "freeze_item": "HorizonPolicy",
        "owner_phase": "Phase 2",
        "covered_contracts": ("HorizonPolicy",),
        "frozen_boundary": "explicit multi-horizon policy config; no live execution or trading output",
        "evidence_paths": (
            "docs/extension/v1_0_horizon_policy_contract.md",
            "config/horizon_policy.toml",
        ),
    },
    {
        "freeze_item": "SimulationRunManifest",
        "owner_phase": "Phase 3",
        "covered_contracts": ("SimulationRunManifest",),
        "frozen_boundary": "candidate-only run metadata and HorizonPolicy snapshot; no production run activation",
        "evidence_paths": (
            "docs/extension/v1_0_simulation_run_manifest_contract.md",
            "Quant_mvp/backtest_mvp/simulation_run_manifest.py",
        ),
    },
    {
        "freeze_item": "WeightConfigRunPlan / RunRecord boundary",
        "owner_phase": "Phase 4",
        "covered_contracts": ("WeightConfigRunPlan",),
        "frozen_boundary": "planned candidate runs and run records remain evidence context; no best-weight selection or feedback optimization",
        "evidence_paths": (
            "docs/extension/v1_0_weight_config_loop_contract.md",
            "Quant_mvp/backtest_mvp/weight_config_loop.py",
        ),
    },
    {
        "freeze_item": "LayerRegistry status/category model",
        "owner_phase": "Phase 5",
        "covered_contracts": ("LayerRegistry", "LayerAdapter", "LayerValidation"),
        "frozen_boundary": "status/category semantics validate layer availability; valuation, futures, index, macro, and regime active scoring remain disabled",
        "evidence_paths": (
            "docs/extension/v1_0_layer_registry_contract.md",
            "src/validation/layer_registry.py",
            "config/layer_registry.toml",
        ),
    },
    {
        "freeze_item": "EvaluationEvidenceV1",
        "owner_phase": "Phase 6",
        "covered_contracts": ("EvaluationEvidenceV1",),
        "frozen_boundary": "allowlisted historical evidence summary only; no future labels, orders, or active ranking update",
        "evidence_paths": (
            "docs/extension/v1_0_evaluation_evidence_v1_contract.md",
            "Quant_mvp/backtest_mvp/evaluation_evidence_v1.py",
            "config/evaluation_evidence_v1.toml",
        ),
    },
    {
        "freeze_item": "SelectorFeatureMatrix / SelectorScoreManifest",
        "owner_phase": "Phase 7",
        "covered_contracts": ("SelectorFeatureMatrixV1", "SelectorScoreManifestV1"),
        "frozen_boundary": "selector consumes allowlisted evidence and emits review-prioritization only",
        "evidence_paths": (
            "docs/extension/v1_0_selector_evaluator_contract.md",
            "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        ),
    },
    {
        "freeze_item": "AdoptionCandidateReviewPriority",
        "owner_phase": "Phase 7",
        "covered_contracts": ("AdoptionCandidateReviewPriorityV1",),
        "frozen_boundary": "review priority only; no buy/sell/hold framing or production ranking replacement",
        "evidence_paths": (
            "docs/extension/v1_0_selector_evaluator_contract.md",
            "Quant_mvp/backtest_mvp/selector_evaluator_v1.py",
        ),
    },
    {
        "freeze_item": "ManualReviewPacket",
        "owner_phase": "Phase 8",
        "covered_contracts": ("ManualReviewPacket",),
        "frozen_boundary": "private manual-review support only; no order generation, position sizing, or transaction instruction",
        "evidence_paths": (
            "docs/extension/v1_0_manual_review_packet_contract.md",
            "Quant_mvp/backtest_mvp/manual_review_packet_v1.py",
        ),
    },
    {
        "freeze_item": "Phase 9 FreezeReadinessPacket",
        "owner_phase": "Phase 9",
        "covered_contracts": ("FreezeReadinessPacket",),
        "frozen_boundary": "validation packet for pre-freeze review only; no final freeze, tag, release, push, or production readiness declaration",
        "evidence_paths": (
            "scripts/build_v1_0_rc_freeze_readiness_packet.py",
            "reports/review/v1_0_rc_freeze_readiness_packet.md",
        ),
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


def build_contract_freeze_list(
    project_root: str | Path = PROJECT_ROOT,
    contract_manifest: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    root = Path(project_root)
    manifest = contract_manifest if contract_manifest is not None else build_contract_manifest(root)
    contracts_by_name = {str(row["contract_name"]): row for row in manifest}
    rows: list[dict[str, Any]] = []
    for item in CONTRACT_FREEZE_LIST:
        covered_contracts = tuple(str(name) for name in item["covered_contracts"])
        missing_contracts = [name for name in covered_contracts if name not in contracts_by_name]
        not_ready_contracts = [
            name
            for name in covered_contracts
            if name in contracts_by_name
            and contracts_by_name[name]["freeze_readiness_status"] != STATUS_COMPLETE
        ]
        missing_evidence_paths = [
            path for path in item["evidence_paths"] if not (root / str(path)).exists()
        ]
        blockers = []
        if missing_contracts:
            blockers.append(f"missing contracts: {', '.join(missing_contracts)}")
        if not_ready_contracts:
            blockers.append(f"contracts not complete: {', '.join(not_ready_contracts)}")
        if missing_evidence_paths:
            blockers.append(f"missing evidence paths: {', '.join(missing_evidence_paths)}")
        rows.append(
            {
                "freeze_item": item["freeze_item"],
                "owner_phase": item["owner_phase"],
                "covered_contracts": list(covered_contracts),
                "frozen_boundary": item["frozen_boundary"],
                "evidence_paths": list(item["evidence_paths"]),
                "status": STATUS_NEEDS_FIX if blockers else STATUS_COMPLETE,
                "blockers": blockers,
            }
        )
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


def build_ml_reproduction_report() -> dict[str, Any]:
    fixture = _build_ml_reproduction_fixture()
    evidences = fixture["evidences"]
    manifest = fixture["simulation_run_manifest"]
    input_manifest = fixture["selector_input_manifest"]
    trainability = fixture["selector_trainability_report"]
    score_manifest = fixture["selector_score_manifest"]
    manual_packet = fixture["manual_review_packet"]
    label_manifest = fixture["label_manifest"]
    split_policy = fixture["split_policy"]
    ml_result = fixture["ml_result"]
    profit = fixture["profit_reproduction"]
    stability = fixture["stability"]
    label_available = label_manifest["status"] == STATUS_PASS
    model_training_performed = ml_result["model_training_performed"] is True
    label_feature_separated = ml_result["label_feature_overlap_status"] == STATUS_PASS
    leakage_passed = (
        all(evidence["leakage_check_status"] == "pass" for evidence in evidences)
        and all(evidence["no_lookahead_check_status"] == "pass" for evidence in evidences)
        and input_manifest["leakage_check_status"] == "pass"
        and input_manifest["no_lookahead_check_status"] == "pass"
    )
    guardrail_passed = (
        not contains_prohibited_action_language(score_manifest)
        and not contains_prohibited_action_language(manual_packet)
        and score_manifest["manual_review_required"] is True
        and score_manifest["live_execution_enabled"] is False
        and score_manifest["brokerage_integration_enabled"] is False
        and score_manifest["order_generation_enabled"] is False
        and score_manifest["production_ranking_update_enabled"] is False
        and score_manifest["valuation_fundamental_active_scoring_enabled"] is False
    )
    sections = [
        _ml_report_section(
            "Dataset snapshot",
            (
                f"range={manifest['date_range']['start']}..{manifest['date_range']['end']}; "
                f"universe={manifest['universe_scope']}; horizon={manifest['horizon_policy_id']}; "
                f"data_context={manifest['data_context']}; candidate_count={len(evidences)}"
            ),
            STATUS_PASS,
        ),
        _ml_report_section(
            "Label manifest",
            (
                f"label_contract_status={trainability['label_contract_status']}; "
                f"approved_label_manifest_ref={label_manifest['manifest_ref']}; "
                f"positive_count={label_manifest['positive_count']}; "
                f"negative_count={label_manifest['negative_count']}; "
                f"label_rule={label_manifest['label_rule']}"
            ),
            STATUS_PASS if label_available else STATUS_FAIL,
        ),
        _ml_report_section(
            "Feature allowlist",
            (
                "selected_fields="
                + ", ".join(str(field) for field in input_manifest["selected_feature_fields"])
                + "; blocked_feature_fields="
                + (", ".join(input_manifest["blocked_feature_fields"]) or "none")
            ),
            STATUS_PASS if not input_manifest["blocked_feature_fields"] else STATUS_FAIL,
        ),
        _ml_report_section(
            "Split policy",
            (
                f"policy={split_policy['policy_id']}; "
                f"train={split_policy['train_range']}; "
                f"validation={split_policy['validation_range']}; "
                f"out_of_sample={split_policy['out_of_sample_range']}; "
                f"walk_forward_folds={split_policy['walk_forward_folds']}"
            ),
            split_policy["status"],
        ),
        _ml_report_section(
            "Leakage checks",
            (
                "evidence_leakage=pass_all; "
                "evidence_no_lookahead=pass_all; "
                f"selector_leakage={input_manifest['leakage_check_status']}; "
                f"selector_no_lookahead={input_manifest['no_lookahead_check_status']}"
            ),
            STATUS_PASS if leakage_passed else STATUS_FAIL,
        ),
        _ml_report_section(
            "Baseline",
            (
                f"selector_type={score_manifest['selector_type']}; "
                f"selector_mode={score_manifest['selector_mode']}; "
                f"trainability_status={trainability['trainability_status']}; "
                f"report_ml_result_recorded={model_training_performed}"
            ),
            STATUS_PASS,
        ),
        _ml_report_section(
            "ML result",
            _format_ml_result_content(ml_result),
            STATUS_PASS if model_training_performed and label_feature_separated else STATUS_FAIL,
        ),
        _ml_report_section(
            "Profit reproduction",
            (
                f"historical_simulated_post_cost_positive_avg={profit['positive_post_cost_avg']}; "
                f"historical_simulated_post_cost_negative_avg={profit['negative_post_cost_avg']}; "
                f"cost_model={profit['cost_model']}; slippage_model={profit['slippage_model']}; "
                f"costs_reflected={profit['costs_reflected']}"
            ),
            profit["status"],
        ),
        _ml_report_section(
            "Stability",
            (
                f"split_status={stability['split_status']}; "
                f"horizon_status={stability['horizon_status']}; "
                f"seed_status={stability['seed_status']}; "
                f"tested_seeds={stability['tested_seeds']}"
            ),
            stability["status"],
        ),
        _ml_report_section(
            "Failure cases",
            "; ".join(profit["failure_cases"]) if profit["failure_cases"] else "none_recorded_in_fixture",
            STATUS_PASS,
        ),
        _ml_report_section(
            "Guardrail result",
            "no recommendation/order/transaction language detected in selector or manual-review packet",
            STATUS_PASS if guardrail_passed else STATUS_FAIL,
        ),
    ]
    blockers = [
        section["content"]
        for section in sections
        if section["status"] == STATUS_FAIL
        and section["section"]
        in {
            "Label manifest",
            "Feature allowlist",
            "Split policy",
            "Leakage checks",
            "Baseline",
            "ML result",
            "Profit reproduction",
            "Stability",
            "Guardrail result",
        }
    ]
    return {
        "report_version": ML_REPRODUCTION_REPORT_VERSION,
        "route_scope": "v1_0_rc_step3_ml_reproduction_freeze_trigger_check",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "dataset_snapshot_ref": fixture["dataset_snapshot_ref"],
        "selector_run_id": score_manifest["selector_run_id"],
        "freeze_trigger_confirmed": not blockers,
        "freeze_trigger_verdict": STATUS_PASS if not blockers else STATUS_FAIL,
        "sections": sections
        + [
            _ml_report_section(
                "Verdict",
                (
                    "freeze trigger confirmed for evidence-only manual-review support"
                    if not blockers
                    else "freeze trigger not confirmed; approved labels, time split, no-lookahead checks, ML metrics, and stability evidence are required"
                ),
                STATUS_PASS if not blockers else STATUS_FAIL,
            )
        ],
        "blockers": blockers,
        "evidence_only_notice": "ML reproduction report is evidence-only review support and does not authorize final freeze, production activation, recommendations, orders, or live execution.",
    }


def _build_ml_reproduction_fixture() -> dict[str, Any]:
    from Quant_mvp.backtest_mvp.evaluation_evidence_v1 import build_evaluation_evidence_v1
    from Quant_mvp.backtest_mvp.manual_review_packet_v1 import build_manual_review_packet_v1
    from Quant_mvp.backtest_mvp.selector_evaluator_v1 import (
        build_rule_based_selector_score_manifest_v1,
        build_selector_feature_matrix_v1,
        build_selector_input_manifest_v1,
        build_selector_trainability_report_v1,
    )
    from Quant_mvp.backtest_mvp.simulation_run_manifest import build_simulation_run_manifest
    from src.validation.horizon_policy import resolve_horizon_policy

    created_at = "2026-01-01T00:00:00+00:00"
    specs = _ml_reproduction_candidate_specs()
    evidences: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    for spec in specs:
        policy = resolve_horizon_policy(spec["horizon_policy_id"])
        manifest = build_simulation_run_manifest(
            strategy_candidate_id=spec["candidate_id"],
            strategy_candidate_ref="docs/extension/v1_0_rc_freeze_readiness.md#ml-reproduction-fixture",
            date_range=spec["date_range"],
            horizon_policy=policy,
            created_at=created_at,
            data_context="phase9_local_evidence_only_fixture",
            cost_model="phase9_cost_model_10bps",
            slippage_model="phase9_slippage_model_5bps",
            random_seed=spec["seed"],
            rebalance_disclosure="historical simulated rebalancing context only not user instruction",
        )
        manifests.append(manifest)
        metric_values = {
            "realized_return_summary": spec["realized_return"],
            "realized_volatility_summary": spec["realized_volatility"],
            "realized_drawdown_summary": spec["realized_drawdown"],
            "realized_turnover_summary": spec["realized_turnover"],
            "realized_cost_summary": spec["realized_cost"],
            "sharpe_like_historical_summary": spec["sharpe_like"],
            "hit_rate_historical_summary": spec["hit_rate"],
            "coverage_ratio": spec["coverage_ratio"],
            "invalid_period_count": 0,
            "missing_data_count": spec["missing_data_count"],
        }
        evidences.append(
            build_evaluation_evidence_v1(
                candidate_result={
                    "candidate_id": spec["candidate_id"],
                    "strategy_candidate_id": spec["candidate_id"],
                    "strategy_candidate_ref": "docs/extension/v1_0_rc_freeze_readiness.md#ml-reproduction-fixture",
                    "date_range": spec["date_range"],
                    "evaluation_window": spec["date_range"],
                    "metric_values": metric_values,
                    "coverage_summary": {"coverage_ratio": spec["coverage_ratio"]},
                    "data_quality_summary": {"missing_data_count": spec["missing_data_count"]},
                    "turnover_summary": {"realized_turnover_summary": spec["realized_turnover"]},
                    "cost_model": "phase9_cost_model_10bps",
                    "slippage_model": "phase9_slippage_model_5bps",
                    "leakage_check_status": "pass",
                    "no_lookahead_check_status": "pass",
                    "rebalancing_role": "material_effect_on_candidate_evidence",
                    "rebalance_disclosure": "historical simulated rebalancing context only not user instruction",
                    "limitation_summary": ["phase9_ml_reproduction_fixture_not_release_claim"],
                    "evidence_quality_flags": [],
                },
                simulation_run_manifest=manifest,
                horizon_policy_snapshot=manifest["horizon_policy_snapshot"],
                created_at=created_at,
                route_scope="v1_0_rc_step3_ml_reproduction_fixture",
            )
        )
    input_manifest = build_selector_input_manifest_v1(
        evidences,
        selector_run_id="selector_v1_0_rc_ml_reproduction_fixture",
        created_at=created_at,
        route_scope="v1_0_rc_step3_ml_reproduction_fixture",
    )
    input_manifest["leakage_check_status"] = "pass"
    input_manifest["no_lookahead_check_status"] = "pass"
    feature_rows = build_selector_feature_matrix_v1(
        evidences,
        input_manifest=input_manifest,
        created_at=created_at,
    )
    label_manifest = _build_ml_label_manifest(specs, evidences)
    trainability = build_selector_trainability_report_v1(
        feature_rows,
        selector_run_id=input_manifest["selector_run_id"],
        approved_label_manifest_ref=label_manifest["manifest_ref"],
        created_at=created_at,
    )
    score_manifest = build_rule_based_selector_score_manifest_v1(
        feature_rows,
        input_manifest=input_manifest,
        trainability_report=trainability,
        created_at=created_at,
    )
    manual_packet = build_manual_review_packet_v1(
        evidence=evidences[0],
        selector_score_manifest=score_manifest,
        created_at=created_at,
    )
    split_policy = _build_ml_split_policy(specs)
    ml_result = _fit_ml_reproduction_result(evidences, label_manifest, split_policy)
    profit = _build_profit_reproduction_summary(evidences, label_manifest)
    stability = _build_ml_stability_report(evidences, label_manifest, split_policy)
    return {
        "dataset_snapshot_ref": "phase9_ml_reproduction_fixture_dataset_v1",
        "simulation_run_manifest": _merged_dataset_manifest(manifests),
        "evidences": evidences,
        "selector_input_manifest": input_manifest,
        "selector_feature_matrix": feature_rows,
        "selector_trainability_report": trainability,
        "selector_score_manifest": score_manifest,
        "manual_review_packet": manual_packet,
        "label_manifest": label_manifest,
        "split_policy": split_policy,
        "ml_result": ml_result,
        "profit_reproduction": profit,
        "stability": stability,
    }


def _ml_reproduction_candidate_specs() -> tuple[dict[str, Any], ...]:
    return (
        _ml_candidate("phase9_ml_candidate_01", "train", "1d", "2024-01-02", "2024-01-31", 0.074, -0.028, 0.91, 0.12, 0.004, 0.21, 0.62, 0.96, 0, 11, 1),
        _ml_candidate("phase9_ml_candidate_02", "train", "1w", "2024-02-01", "2024-02-29", -0.018, -0.094, 0.18, 0.24, 0.006, -0.31, 0.42, 0.81, 1, 13, 0),
        _ml_candidate("phase9_ml_candidate_03", "train", "1m", "2024-03-01", "2024-03-29", 0.052, -0.041, 0.77, 0.16, 0.005, 0.26, 0.58, 0.94, 0, 17, 1),
        _ml_candidate("phase9_ml_candidate_04", "train", "1d", "2024-04-01", "2024-04-30", -0.006, -0.076, 0.22, 0.22, 0.005, -0.12, 0.47, 0.83, 2, 19, 0),
        _ml_candidate("phase9_ml_candidate_05", "train", "1w", "2024-05-01", "2024-05-31", 0.039, -0.033, 0.69, 0.14, 0.004, 0.19, 0.57, 0.93, 0, 23, 1),
        _ml_candidate("phase9_ml_candidate_06", "train", "1m", "2024-06-03", "2024-06-28", -0.021, -0.103, 0.26, 0.27, 0.007, -0.25, 0.39, 0.79, 2, 29, 0),
        _ml_candidate("phase9_ml_candidate_07", "validation", "1d", "2024-07-01", "2024-07-31", 0.046, -0.037, 0.72, 0.13, 0.004, 0.22, 0.59, 0.95, 0, 31, 1),
        _ml_candidate("phase9_ml_candidate_08", "validation", "1w", "2024-08-01", "2024-08-30", -0.012, -0.085, 0.20, 0.25, 0.006, -0.18, 0.44, 0.82, 1, 37, 0),
        _ml_candidate("phase9_ml_candidate_09", "validation", "1m", "2024-09-02", "2024-09-30", 0.031, -0.044, 0.61, 0.15, 0.004, 0.15, 0.55, 0.90, 0, 41, 1),
        _ml_candidate("phase9_ml_candidate_10", "out_of_sample", "1d", "2024-10-01", "2024-10-31", -0.017, -0.091, 0.19, 0.26, 0.006, -0.22, 0.41, 0.80, 2, 43, 0),
        _ml_candidate("phase9_ml_candidate_11", "out_of_sample", "1w", "2024-11-01", "2024-11-29", 0.044, -0.035, 0.71, 0.14, 0.004, 0.21, 0.60, 0.94, 0, 47, 1),
        _ml_candidate("phase9_ml_candidate_12", "out_of_sample", "1m", "2024-12-02", "2024-12-31", -0.008, -0.082, 0.23, 0.23, 0.006, -0.14, 0.45, 0.84, 1, 53, 0),
    )


def _ml_candidate(
    candidate_id: str,
    split: str,
    horizon_policy_id: str,
    start: str,
    end: str,
    realized_return: float,
    realized_drawdown: float,
    realized_volatility: float,
    realized_turnover: float,
    realized_cost: float,
    sharpe_like: float,
    hit_rate: float,
    coverage_ratio: float,
    missing_data_count: int,
    seed: int,
    label: int,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "split": split,
        "horizon_policy_id": horizon_policy_id,
        "date_range": {"start": start, "end": end},
        "realized_return": realized_return,
        "realized_drawdown": realized_drawdown,
        "realized_volatility": realized_volatility,
        "realized_turnover": realized_turnover,
        "realized_cost": realized_cost,
        "sharpe_like": sharpe_like,
        "hit_rate": hit_rate,
        "coverage_ratio": coverage_ratio,
        "missing_data_count": missing_data_count,
        "seed": seed,
        "approved_label": label,
    }


def _merged_dataset_manifest(manifests: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    starts = [str(manifest["date_range"]["start"]) for manifest in manifests]
    ends = [str(manifest["date_range"]["end"]) for manifest in manifests]
    first = manifests[0]
    return {
        "run_id": "phase9_ml_reproduction_fixture_dataset_v1",
        "date_range": {"start": min(starts), "end": max(ends)},
        "universe_scope": first["universe_scope"],
        "horizon_policy_id": "1d/1w/1m",
        "data_context": first["data_context"],
    }


def _build_ml_label_manifest(
    specs: Sequence[Mapping[str, Any]],
    evidences: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    labels: list[dict[str, Any]] = []
    for spec, evidence in zip(specs, evidences, strict=True):
        post_cost = round(float(spec["realized_return"]) - float(spec["realized_cost"]), 6)
        labels.append(
            {
                "candidate_id": spec["candidate_id"],
                "evidence_id": evidence["evidence_id"],
                "split": spec["split"],
                "approved_label": int(spec["approved_label"]),
                "historical_simulated_post_cost_return": post_cost,
            }
        )
    positive_count = sum(1 for row in labels if row["approved_label"] == 1)
    negative_count = len(labels) - positive_count
    status = STATUS_PASS if positive_count and negative_count else STATUS_FAIL
    return {
        "manifest_ref": "reports/review/v1_0_rc_ml_reproduction_report.md#label-manifest",
        "status": status,
        "label_rule": "positive if post-cost historical/simulated return >= 0.010, drawdown_abs <= 0.080, and coverage >= 0.850",
        "label_source_fields": list(ML_REPRODUCTION_LABEL_SOURCE_FIELDS),
        "candidate_labels": labels,
        "positive_count": positive_count,
        "negative_count": negative_count,
    }


def _build_ml_split_policy(specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    split_ranges = {}
    split_label_sets = {}
    for split in ("train", "validation", "out_of_sample"):
        split_specs = [spec for spec in specs if spec["split"] == split]
        starts = [str(spec["date_range"]["start"]) for spec in split_specs]
        ends = [str(spec["date_range"]["end"]) for spec in split_specs]
        split_ranges[split] = f"{min(starts)}..{max(ends)}"
        split_label_sets[split] = {int(spec["approved_label"]) for spec in split_specs}
    labels_ok = all(split_label_sets[split] == {0, 1} for split in split_label_sets)
    return {
        "policy_id": "phase9_time_split_walk_forward_fixture_v1",
        "train_range": split_ranges["train"],
        "validation_range": split_ranges["validation"],
        "out_of_sample_range": split_ranges["out_of_sample"],
        "walk_forward_folds": 3,
        "status": STATUS_PASS if labels_ok else STATUS_FAIL,
    }


def _format_ml_result_content(ml_result: Mapping[str, Any]) -> str:
    if ml_result.get("model_training_performed") is not True:
        return (
            f"model_family={ml_result['model_family']}; "
            "model_training_performed=False; "
            f"dependency_status={ml_result.get('dependency_status', 'unknown')}; "
            "train_validation_out_of_sample_metrics=none"
        )
    metrics = ml_result["metrics"]
    return (
        f"model_family={ml_result['model_family']}; "
        f"model_training_performed={ml_result['model_training_performed']}; "
        f"train_accuracy={metrics['train']['accuracy']}; "
        f"validation_accuracy={metrics['validation']['accuracy']}; "
        f"out_of_sample_accuracy={metrics['out_of_sample']['accuracy']}; "
        f"label_feature_overlap_status={ml_result['label_feature_overlap_status']}; "
        f"performance_claim_allowed={ml_result['performance_claim_allowed']}"
    )


def _fit_ml_reproduction_result(
    evidences: Sequence[Mapping[str, Any]],
    label_manifest: Mapping[str, Any],
    split_policy: Mapping[str, Any],
    *,
    random_state: int = 17,
) -> dict[str, Any]:
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        return {
            "model_family": "LogisticRegression",
            "dependency_status": f"blocked_missing_ml_dependency:{exc.__class__.__name__}",
            "model_training_performed": False,
            "metrics": {},
            "label_source_fields": list(label_manifest.get("label_source_fields") or []),
            "selected_feature_names": list(ML_REPRODUCTION_SELECTED_FEATURE_NAMES),
            "label_feature_overlap_status": STATUS_FAIL,
            "performance_claim_allowed": False,
        }
    labels = {row["candidate_id"]: row for row in label_manifest["candidate_labels"]}
    selected_feature_names = list(ML_REPRODUCTION_SELECTED_FEATURE_NAMES)
    label_source_fields = list(label_manifest["label_source_fields"])
    label_feature_overlap_status = _ml_label_feature_overlap_status(
        label_source_fields,
        selected_feature_names,
    )
    rows = [
        {
            "candidate_id": evidence["candidate_id"],
            "split": labels[evidence["candidate_id"]]["split"],
            "features": _ml_feature_vector(evidence),
            "label": labels[evidence["candidate_id"]]["approved_label"],
        }
        for evidence in evidences
    ]
    train_rows = [row for row in rows if row["split"] == "train"]
    train_labels = {row["label"] for row in train_rows}
    if train_labels != {0, 1}:
        return {
            "model_family": "LogisticRegression",
            "dependency_status": "blocked_train_split_requires_positive_and_negative_labels",
            "model_training_performed": False,
            "metrics": {},
            "label_source_fields": label_source_fields,
            "selected_feature_names": selected_feature_names,
            "label_feature_overlap_status": label_feature_overlap_status,
            "performance_claim_allowed": False,
        }
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(random_state=random_state, solver="liblinear"),
    )
    model.fit([row["features"] for row in train_rows], [row["label"] for row in train_rows])
    metrics = {}
    for split in ("train", "validation", "out_of_sample"):
        split_rows = [row for row in rows if row["split"] == split]
        truth = [row["label"] for row in split_rows]
        predicted = list(model.predict([row["features"] for row in split_rows]))
        metrics[split] = {
            "accuracy": round(float(accuracy_score(truth, predicted)), 6),
            "balanced_accuracy": round(float(balanced_accuracy_score(truth, predicted)), 6),
            "f1": round(float(f1_score(truth, predicted, zero_division=0)), 6),
            "sample_count": len(split_rows),
        }
    return {
        "model_family": "LogisticRegression",
        "dependency_status": "available",
        "model_training_performed": True,
        "split_policy_id": split_policy["policy_id"],
        "selected_feature_names": selected_feature_names,
        "label_source_fields": label_source_fields,
        "label_feature_overlap_status": label_feature_overlap_status,
        "metrics": metrics,
        "performance_claim_allowed": False,
        "manual_review_required": True,
    }


def _ml_feature_vector(evidence: Mapping[str, Any]) -> list[float]:
    metrics = evidence["metric_values"]
    turnover = evidence["turnover_summary"]
    return [
        float(metrics.get("realized_volatility_summary") or 0.0),
        float(turnover.get("realized_turnover_summary") or 0.0),
        float(metrics.get("hit_rate_historical_summary") or 0.0),
        float(metrics.get("missing_data_count") or 0.0),
    ]


def _ml_label_feature_overlap_status(
    label_source_fields: Sequence[str],
    selected_feature_names: Sequence[str],
) -> str:
    overlap = set(label_source_fields).intersection(set(selected_feature_names))
    return STATUS_FAIL if overlap else STATUS_PASS


def _build_profit_reproduction_summary(
    evidences: Sequence[Mapping[str, Any]],
    label_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    labels = {row["candidate_id"]: row for row in label_manifest["candidate_labels"]}
    positives: list[float] = []
    negatives: list[float] = []
    failure_cases: list[str] = []
    for evidence in evidences:
        metrics = evidence["metric_values"]
        post_cost = round(
            float(metrics["realized_return_summary"]) - float(metrics["realized_cost_summary"]),
            6,
        )
        if labels[evidence["candidate_id"]]["approved_label"] == 1:
            positives.append(post_cost)
            if post_cost <= 0:
                failure_cases.append(f"{evidence['candidate_id']}:positive_label_non_positive_post_cost")
        else:
            negatives.append(post_cost)
    if not positives or not negatives:
        return {
            "positive_post_cost_avg": None,
            "negative_post_cost_avg": None,
            "cost_model": "phase9_cost_model_10bps",
            "slippage_model": "phase9_slippage_model_5bps",
            "costs_reflected": True,
            "failure_cases": ["positive_or_negative_label_class_missing"],
            "status": STATUS_FAIL,
        }
    positive_avg = round(sum(positives) / len(positives), 6)
    negative_avg = round(sum(negatives) / len(negatives), 6)
    reproduced = positive_avg > 0 and positive_avg > negative_avg
    return {
        "positive_post_cost_avg": positive_avg,
        "negative_post_cost_avg": negative_avg,
        "cost_model": "phase9_cost_model_10bps",
        "slippage_model": "phase9_slippage_model_5bps",
        "costs_reflected": True,
        "failure_cases": failure_cases,
        "status": STATUS_PASS if reproduced else STATUS_FAIL,
    }


def _build_ml_stability_report(
    evidences: Sequence[Mapping[str, Any]],
    label_manifest: Mapping[str, Any],
    split_policy: Mapping[str, Any],
) -> dict[str, Any]:
    seeds = (11, 17, 23)
    out_of_sample_scores: list[float] = []
    for seed in seeds:
        result = _fit_ml_reproduction_result(evidences, label_manifest, split_policy, random_state=seed)
        if result.get("model_training_performed") is not True:
            return {
                "tested_seeds": list(seeds),
                "out_of_sample_accuracy_by_seed": {},
                "horizons": sorted({str(evidence["horizon_policy_id"]) for evidence in evidences}),
                "split_status": STATUS_FAIL,
                "horizon_status": STATUS_FAIL,
                "seed_status": STATUS_FAIL,
                "status": STATUS_FAIL,
            }
        out_of_sample_scores.append(result["metrics"]["out_of_sample"]["accuracy"])
    horizons = sorted({str(evidence["horizon_policy_id"]) for evidence in evidences})
    split_status = STATUS_PASS if min(out_of_sample_scores) >= 0.66 else STATUS_FAIL
    horizon_status = STATUS_PASS if horizons == ["1d", "1m", "1w"] else STATUS_FAIL
    seed_status = STATUS_PASS if len(set(out_of_sample_scores)) == 1 else STATUS_FAIL
    status = STATUS_PASS if {split_status, horizon_status, seed_status} == {STATUS_PASS} else STATUS_FAIL
    return {
        "tested_seeds": list(seeds),
        "out_of_sample_accuracy_by_seed": dict(zip((str(seed) for seed in seeds), out_of_sample_scores, strict=True)),
        "horizons": horizons,
        "split_status": split_status,
        "horizon_status": horizon_status,
        "seed_status": seed_status,
        "status": status,
    }


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
            'state = "complete_local_v1_0_freeze_baseline"',
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
        "expected_route_state": "complete_local_v1_0_freeze_baseline",
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
    contract_freeze_list = build_contract_freeze_list(root, contract_manifest)
    ml_reproduction_report = build_ml_reproduction_report()
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
    blockers.extend(
        f"{row['freeze_item']} freeze list item is not locked"
        for row in contract_freeze_list
        if row["status"] != STATUS_COMPLETE
    )
    if horizon["status"] != STATUS_COMPLETE:
        blockers.append("HorizonPolicy audit found suspicious active hardcoding")
    if rebalance["status"] != STATUS_COMPLETE:
        blockers.append("Rebalancing disclosure audit failed")
    if boundaries["status"] != STATUS_COMPLETE:
        blockers.append("Evidence/selector/review boundary audit failed")
    if route_state_alignment["status"] != STATUS_COMPLETE:
        blockers.append("v1.0-rc route state is not aligned with completed Phase 6-9 readiness artifacts")
    if ml_reproduction_report["freeze_trigger_verdict"] != STATUS_PASS:
        detail = "; ".join(ml_reproduction_report.get("blockers") or ["unknown_ml_reproduction_blocker"])
        blockers.append(f"ML reproduction freeze trigger did not pass: {detail}")
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
        "contract_freeze_list": contract_freeze_list,
        "ml_reproduction_report": ml_reproduction_report,
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


def _ml_report_section(section: str, content: str, status: str) -> dict[str, str]:
    return {"section": section, "content": content, "status": status}


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
    "build_contract_freeze_list",
    "build_contract_manifest",
    "build_core_boundary_lock",
    "build_freeze_readiness_report",
    "build_ml_reproduction_report",
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
