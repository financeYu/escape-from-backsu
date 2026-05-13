"""v1.0-rc evidence-only selector/evaluator contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
import json
import re

from Quant_mvp.backtest_mvp.evaluation_evidence_v1 import (
    SELECTOR_FEATURE_ALLOWLIST,
    validate_evaluation_evidence_v1,
)


SELECTOR_INPUT_MANIFEST_VERSION = "v1_0_rc_selector_input_manifest_v1_0"
SELECTOR_FEATURE_MATRIX_VERSION = "v1_0_rc_selector_feature_matrix_v1_0"
SELECTOR_TRAINABILITY_REPORT_VERSION = "v1_0_rc_selector_trainability_report_v1_0"
SELECTOR_SCORE_MANIFEST_VERSION = "v1_0_rc_selector_score_manifest_v1_0"
ADOPTION_PRIORITY_VERSION = "v1_0_rc_adoption_candidate_review_priority_v1_0"
ALLOWED_SELECTOR_MODES = frozenset(
    {
        "rule_based_review_prioritization",
        "baseline_ml_review_prioritization",
        "trainability_check_only",
        "dry_run_selector_plan_only",
    }
)
BLOCKED_SELECTOR_MODES = frozenset(
    {
        "live_trading",
        "paper_trading_execution",
        "brokerage_order",
        "trade_signal",
        "buy_sell_recommendation",
        "automatic_rebalance_instruction",
        "move_to_cash",
        "production_execution",
        "production_ranking_update",
    }
)
PROHIBITED_FLAGS = (
    "live_execution_enabled",
    "brokerage_integration_enabled",
    "order_generation_enabled",
    "user_facing_auto_rebalance_instruction_enabled",
    "production_ranking_update_enabled",
    "valuation_fundamental_active_scoring_enabled",
)
EVIDENCE_ONLY_NOTICE = (
    "selector output is evidence-only AdoptionCandidate review prioritization; "
    "it is not a recommendation, execution signal, or production ranking update"
)
PROHIBITED_ACTIONS_NOTICE = (
    "prohibited actions include live trading, brokerage integration, order generation, "
    "buy/sell/hold recommendations, trade-signal framing, automatic rebalance "
    "instructions, move-to-cash commands, expected-return claims, future-return claims, "
    "proven-alpha claims, production ranking replacement, and valuation/fundamental "
    "active scoring"
)
NOT_INVESTMENT_ADVICE_NOTICE = "manual review support only; not investment advice"
DEFAULT_SELECTED_FEATURE_FIELDS = (
    "metric_values",
    "coverage_summary",
    "data_quality_summary",
    "evidence_quality_flags",
    "leakage_check_status",
    "no_lookahead_check_status",
    "rebalance_frequency",
    "rebalance_disclosure",
    "rebalancing_role",
    "turnover_summary",
)


def build_selector_input_manifest_v1(
    evidences: Sequence[Mapping[str, Any]],
    *,
    selector_run_id: str | None = None,
    selected_feature_fields: Sequence[str] | None = None,
    created_at: str | None = None,
    route_scope: str = "v1_0_rc_phase_7_selector",
) -> dict[str, Any]:
    selected = tuple(selected_feature_fields or DEFAULT_SELECTED_FEATURE_FIELDS)
    _validate_selected_fields(selected)
    evidence_list = [dict(evidence) for evidence in evidences]
    for evidence in evidence_list:
        validate_evaluation_evidence_v1(evidence)
    run_id = selector_run_id or make_selector_run_id(evidence_list)
    manifest = {
        "manifest_version": SELECTOR_INPUT_MANIFEST_VERSION,
        "selector_run_id": run_id,
        "created_at": created_at or _utc_now(),
        "route_scope": route_scope,
        "input_evidence_refs": [evidence["evidence_id"] for evidence in evidence_list],
        "input_evidence_versions": sorted({evidence["evidence_version"] for evidence in evidence_list}),
        "selector_feature_allowlist_ref": "EvaluationEvidenceV1.selector_feature_allowlist",
        "selected_feature_fields": list(selected),
        "blocked_feature_fields": _blocked_feature_fields(selected),
        "evidence_quality_filter": "exclude_invalid_or_failed_boundary_evidence",
        "horizon_policy_ids": sorted({evidence["horizon_policy_id"] for evidence in evidence_list}),
        "candidate_count": len(evidence_list),
        "trainability_status": "not_checked",
        "leakage_check_status": "pending_selector_input_validation",
        "no_lookahead_check_status": "pending_selector_input_validation",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        "live_execution_enabled": False,
        "brokerage_integration_enabled": False,
        "order_generation_enabled": False,
        "user_facing_auto_rebalance_instruction_enabled": False,
        "production_ranking_update_enabled": False,
        "valuation_fundamental_active_scoring_enabled": False,
    }
    validate_selector_input_manifest_v1(manifest)
    return manifest


def build_selector_feature_matrix_v1(
    evidences: Sequence[Mapping[str, Any]],
    *,
    input_manifest: Mapping[str, Any],
    created_at: str | None = None,
) -> list[dict[str, Any]]:
    validate_selector_input_manifest_v1(input_manifest)
    selected = tuple(str(field) for field in input_manifest["selected_feature_fields"])
    _validate_evidence_refs_for_input_manifest(evidences, input_manifest)
    rows: list[dict[str, Any]] = []
    for evidence in evidences:
        payload = dict(evidence)
        validate_evaluation_evidence_v1(payload)
        feature_values = {field: _feature_value(payload, field) for field in selected}
        matrix_id = make_matrix_id(payload["evidence_id"], selected)
        row = {
            "matrix_version": SELECTOR_FEATURE_MATRIX_VERSION,
            "matrix_id": matrix_id,
            "created_at": created_at or input_manifest["created_at"],
            "candidate_id": payload["candidate_id"],
            "evidence_id": payload["evidence_id"],
            "horizon_policy_id": payload["horizon_policy_id"],
            "weight_config_id": payload.get("weight_config_id"),
            "feature_values": feature_values,
            "feature_source_refs": {field: payload["evidence_id"] for field in selected},
            "feature_quality_flags": list(payload.get("evidence_quality_flags") or []),
            "missing_feature_policy": "missing_allowed_but_penalized_for_review_prioritization",
            "leakage_guard_status": payload["leakage_check_status"],
            "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        }
        validate_selector_feature_matrix_v1(row)
        rows.append(row)
    return rows


def build_selector_trainability_report_v1(
    feature_rows: Sequence[Mapping[str, Any]],
    *,
    selector_run_id: str,
    minimum_candidate_count: int = 5,
    minimum_non_missing_ratio: float = 0.60,
    approved_label_manifest_ref: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    rows = [dict(row) for row in feature_rows]
    for row in rows:
        validate_selector_feature_matrix_v1(row)
    non_missing_ratios = [_non_missing_ratio(row["feature_values"]) for row in rows]
    average_ratio = sum(non_missing_ratios) / len(non_missing_ratios) if non_missing_ratios else 0.0
    label_status = "approved_label_manifest_available" if approved_label_manifest_ref else "blocked_missing_approved_labels"
    status = "ready_for_optional_baseline_ml"
    blocked_reasons: list[str] = []
    if len(rows) < minimum_candidate_count:
        status = "insufficient_data_no_training"
        blocked_reasons.append("minimum_candidate_count_not_met")
    if average_ratio < minimum_non_missing_ratio:
        status = "insufficient_data_no_training"
        blocked_reasons.append("minimum_feature_coverage_not_met")
    if not approved_label_manifest_ref:
        status = "trainability_check_only"
        blocked_reasons.append("approved_historical_review_label_manifest_missing")
    report = {
        "report_version": SELECTOR_TRAINABILITY_REPORT_VERSION,
        "selector_run_id": selector_run_id,
        "created_at": created_at or _utc_now(),
        "candidate_count": len(rows),
        "minimum_candidate_count": minimum_candidate_count,
        "average_non_missing_feature_ratio": round(average_ratio, 6),
        "minimum_non_missing_feature_ratio": minimum_non_missing_ratio,
        "label_contract_status": label_status,
        "approved_label_manifest_ref": approved_label_manifest_ref,
        "trainability_status": status,
        "training_blocked_reasons": blocked_reasons,
        "model_training_performed": False,
        "ml_baseline_status": "safely_skipped",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
    }
    validate_selector_trainability_report_v1(report)
    return report


def build_rule_based_selector_score_manifest_v1(
    feature_rows: Sequence[Mapping[str, Any]],
    *,
    input_manifest: Mapping[str, Any],
    trainability_report: Mapping[str, Any],
    created_at: str | None = None,
) -> dict[str, Any]:
    validate_selector_input_manifest_v1(input_manifest)
    validate_selector_trainability_report_v1(trainability_report)
    if trainability_report["selector_run_id"] != input_manifest["selector_run_id"]:
        raise ValueError("SelectorScoreManifestV1 trainability report must match selector_run_id")
    rows = [dict(row) for row in feature_rows]
    _validate_feature_rows_for_input_manifest(rows, input_manifest)
    priorities = [_priority_from_row(row) for row in rows]
    priorities.sort(key=lambda item: (-float(item["review_priority_score"]), str(item["candidate_id"])))
    for rank, priority in enumerate(priorities, start=1):
        priority["review_priority_rank"] = rank
        priority["review_priority_bucket"] = _priority_bucket(rank, priority["review_priority_score"])
        validate_adoption_candidate_review_priority_v1(priority)
    manifest = {
        "manifest_version": SELECTOR_SCORE_MANIFEST_VERSION,
        "selector_run_id": input_manifest["selector_run_id"],
        "created_at": created_at or input_manifest["created_at"],
        "selector_mode": "rule_based_review_prioritization",
        "selector_type": "deterministic_rule_based",
        "input_manifest_ref": input_manifest["selector_run_id"],
        "model_manifest_ref": None,
        "rule_manifest_ref": "Quant_mvp.backtest_mvp.selector_evaluator_v1.rule_based_v1",
        "candidate_review_priorities": priorities,
        "priority_score_name": "review_priority_score",
        "priority_score_definition": "deterministic manual-review prioritization from allowlisted evidence quality, coverage, risk, and disclosure fields",
        "priority_bucket": [priority["review_priority_bucket"] for priority in priorities],
        "reason_codes": sorted({code for priority in priorities for code in priority["reason_codes"]}),
        "evidence_refs": [row["evidence_id"] for row in rows],
        "limitation_summary": [
            "rule_based_review_prioritization_only",
            "ml_baseline_safely_skipped_without_approved_label_manifest",
        ],
        "manual_review_required": True,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        "not_investment_advice_notice": NOT_INVESTMENT_ADVICE_NOTICE,
        "live_execution_enabled": False,
        "brokerage_integration_enabled": False,
        "order_generation_enabled": False,
        "user_facing_auto_rebalance_instruction_enabled": False,
        "production_ranking_update_enabled": False,
        "valuation_fundamental_active_scoring_enabled": False,
    }
    validate_selector_score_manifest_v1(manifest)
    return manifest


def validate_selector_input_manifest_v1(manifest: Mapping[str, Any]) -> None:
    required = {
        "manifest_version",
        "selector_run_id",
        "created_at",
        "route_scope",
        "input_evidence_refs",
        "selected_feature_fields",
        "blocked_feature_fields",
        "candidate_count",
        "evidence_only_notice",
        "prohibited_actions_notice",
        *PROHIBITED_FLAGS,
    }
    _require_fields(manifest, required, "SelectorInputManifestV1")
    if manifest["manifest_version"] != SELECTOR_INPUT_MANIFEST_VERSION:
        raise ValueError("unsupported SelectorInputManifestV1 version")
    _validate_selected_fields(tuple(str(field) for field in manifest["selected_feature_fields"]))
    if manifest.get("blocked_feature_fields"):
        raise ValueError("SelectorInputManifestV1 blocked_feature_fields must be empty")
    refs = list(manifest.get("input_evidence_refs") or [])
    if len(refs) != len(set(str(ref) for ref in refs)):
        raise ValueError("SelectorInputManifestV1 input_evidence_refs must be unique")
    if int(manifest["candidate_count"]) != len(refs):
        raise ValueError("SelectorInputManifestV1 candidate_count must match input_evidence_refs")
    for flag in PROHIBITED_FLAGS:
        if bool(manifest.get(flag)):
            raise ValueError(f"SelectorInputManifestV1 blocked flag must remain false: {flag}")


def validate_selector_feature_matrix_v1(row: Mapping[str, Any]) -> None:
    required = {
        "matrix_version",
        "matrix_id",
        "created_at",
        "candidate_id",
        "evidence_id",
        "horizon_policy_id",
        "feature_values",
        "feature_source_refs",
        "feature_quality_flags",
        "missing_feature_policy",
        "leakage_guard_status",
        "evidence_only_notice",
    }
    _require_fields(row, required, "SelectorFeatureMatrixV1")
    if row["matrix_version"] != SELECTOR_FEATURE_MATRIX_VERSION:
        raise ValueError("unsupported SelectorFeatureMatrixV1 version")
    _validate_selected_fields(tuple(str(field) for field in row["feature_values"]))


def validate_selector_trainability_report_v1(report: Mapping[str, Any]) -> None:
    _require_fields(
        report,
        {
            "report_version",
            "selector_run_id",
            "candidate_count",
            "trainability_status",
            "training_blocked_reasons",
            "model_training_performed",
            "ml_baseline_status",
            "evidence_only_notice",
        },
        "SelectorTrainabilityReportV1",
    )
    if report["report_version"] != SELECTOR_TRAINABILITY_REPORT_VERSION:
        raise ValueError("unsupported SelectorTrainabilityReportV1 version")
    if report["model_training_performed"] is True and report.get("trainability_status") != "ready_for_optional_baseline_ml":
        raise ValueError("selector model training requires ready trainability status")


def validate_selector_score_manifest_v1(manifest: Mapping[str, Any]) -> None:
    required = {
        "manifest_version",
        "selector_run_id",
        "created_at",
        "selector_mode",
        "selector_type",
        "input_manifest_ref",
        "candidate_review_priorities",
        "priority_score_name",
        "priority_score_definition",
        "manual_review_required",
        "evidence_only_notice",
        "prohibited_actions_notice",
        *PROHIBITED_FLAGS,
    }
    _require_fields(manifest, required, "SelectorScoreManifestV1")
    if manifest["selector_mode"] in BLOCKED_SELECTOR_MODES or manifest["selector_mode"] not in ALLOWED_SELECTOR_MODES:
        raise ValueError(f"blocked or unsupported selector_mode: {manifest['selector_mode']}")
    if manifest["manual_review_required"] is not True:
        raise ValueError("SelectorScoreManifestV1 requires manual_review_required true")
    for flag in PROHIBITED_FLAGS:
        if bool(manifest.get(flag)):
            raise ValueError(f"SelectorScoreManifestV1 blocked flag must remain false: {flag}")
    for priority in manifest["candidate_review_priorities"]:
        validate_adoption_candidate_review_priority_v1(priority)
    _reject_selector_language(manifest)


def validate_adoption_candidate_review_priority_v1(priority: Mapping[str, Any]) -> None:
    _require_fields(
        priority,
        {
            "priority_version",
            "candidate_id",
            "evidence_id",
            "review_priority_score",
            "review_priority_bucket",
            "reason_codes",
            "evidence_refs",
            "manual_review_required",
            "evidence_only_notice",
        },
        "AdoptionCandidateReviewPriorityV1",
    )
    if priority["priority_version"] != ADOPTION_PRIORITY_VERSION:
        raise ValueError("unsupported AdoptionCandidateReviewPriorityV1 version")
    if priority["manual_review_required"] is not True:
        raise ValueError("AdoptionCandidateReviewPriorityV1 requires manual review")
    _reject_selector_language(priority)


def make_selector_run_id(evidences: Sequence[Mapping[str, Any]]) -> str:
    source = "|".join(sorted(str(evidence.get("evidence_id")) for evidence in evidences))
    digest = sha256(source.encode("utf-8")).hexdigest()[:12]
    return f"selector_v1_0_rc_{digest}"


def make_matrix_id(evidence_id: str, selected_fields: Sequence[str]) -> str:
    digest = sha256((evidence_id + "|" + "|".join(selected_fields)).encode("utf-8")).hexdigest()[:12]
    return f"sfm_v1_0_rc_{digest}"


def _priority_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    validate_selector_feature_matrix_v1(row)
    features = row["feature_values"]
    metric_values = features.get("metric_values") if isinstance(features.get("metric_values"), Mapping) else {}
    coverage = features.get("coverage_summary") if isinstance(features.get("coverage_summary"), Mapping) else {}
    data_quality = features.get("data_quality_summary") if isinstance(features.get("data_quality_summary"), Mapping) else {}
    flags = list(features.get("evidence_quality_flags") or [])
    score = 40.0
    reason_codes: list[str] = []
    if metric_values:
        score += min(25.0, 3.0 * len(metric_values))
        reason_codes.append("metric_summary_available")
    else:
        reason_codes.append("insufficient_evidence")
    coverage_ratio = _as_float(coverage.get("coverage_ratio"))
    if coverage_ratio is not None:
        score += max(0.0, min(20.0, 20.0 * coverage_ratio))
        reason_codes.append("coverage_available")
    else:
        reason_codes.append("coverage_gap")
    if not flags:
        score += 10.0
    else:
        score -= min(20.0, 5.0 * len(flags))
        reason_codes.append("evidence_quality_flag")
    if data_quality:
        reason_codes.append("data_quality_context_available")
    if features.get("rebalancing_role") in {"tested_strategy_logic", "material_effect_on_candidate_evidence"}:
        reason_codes.append("rebalance_material_to_evidence")
    score = round(max(0.0, min(100.0, score)), 6)
    return {
        "priority_version": ADOPTION_PRIORITY_VERSION,
        "candidate_id": row["candidate_id"],
        "evidence_id": row["evidence_id"],
        "review_priority_score": score,
        "review_priority_bucket": "pending_rank_assignment",
        "review_priority_rank": None,
        "reason_codes": sorted(set(reason_codes)),
        "evidence_refs": [row["evidence_id"]],
        "manual_review_required": True,
        "limitation_summary": ["review_priority_is_not_action"],
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
    }


def _priority_bucket(rank: int, score: float) -> str:
    if score < 45:
        return "insufficient_evidence"
    if rank <= 3:
        return "high_review_priority"
    if rank <= 10:
        return "standard_review_priority"
    return "low_review_priority"


def _feature_value(evidence: Mapping[str, Any], field: str) -> Any:
    value = evidence.get(field)
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return value


def _blocked_feature_fields(fields: Sequence[str]) -> list[str]:
    blocked = sorted(set(str(field) for field in fields).difference(SELECTOR_FEATURE_ALLOWLIST))
    return blocked


def _validate_selected_fields(fields: Sequence[str]) -> None:
    unknown = sorted(set(str(field) for field in fields).difference(SELECTOR_FEATURE_ALLOWLIST))
    if unknown:
        raise ValueError(f"selector selected fields outside allowlist: {', '.join(unknown)}")


def _validate_evidence_refs_for_input_manifest(
    evidences: Sequence[Mapping[str, Any]],
    input_manifest: Mapping[str, Any],
) -> None:
    expected = [str(ref) for ref in input_manifest.get("input_evidence_refs") or []]
    actual = [str(evidence.get("evidence_id")) for evidence in evidences]
    if sorted(actual) != sorted(expected):
        raise ValueError("SelectorFeatureMatrixV1 evidences must match SelectorInputManifestV1 input_evidence_refs")
    if len(actual) != len(set(actual)):
        raise ValueError("SelectorFeatureMatrixV1 evidence_id values must be unique")


def _validate_feature_rows_for_input_manifest(
    rows: Sequence[Mapping[str, Any]],
    input_manifest: Mapping[str, Any],
) -> None:
    expected = [str(ref) for ref in input_manifest.get("input_evidence_refs") or []]
    actual = [str(row.get("evidence_id")) for row in rows]
    if sorted(actual) != sorted(expected):
        raise ValueError("SelectorScoreManifestV1 feature rows must match SelectorInputManifestV1 input_evidence_refs")
    if len(actual) != len(set(actual)):
        raise ValueError("SelectorScoreManifestV1 feature row evidence_id values must be unique")


def _non_missing_ratio(values: Mapping[str, Any]) -> float:
    if not values:
        return 0.0
    present = sum(value not in (None, "", [], {}) for value in values.values())
    return present / len(values)


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _require_fields(payload: Mapping[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(fields.difference(payload))
    if missing:
        raise ValueError(f"{label} missing required fields: {', '.join(missing)}")


def _reject_selector_language(payload: Mapping[str, Any]) -> None:
    allowed_fields = {"prohibited_actions_notice", "evidence_only_notice", "not_investment_advice_notice"}
    text = json.dumps(
        {key: value for key, value in payload.items() if key not in allowed_fields},
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    blocked_patterns = (
        r"\bbuy\b",
        r"\bsell\b",
        r"\bhold\b",
        r"\btrade\b",
        r"\bentry\b",
        r"\bexit\b",
        r"\border\b",
        r"rebalance now",
        r"move to cash",
        r"expected return",
        r"future return",
        r"proven alpha",
        r"signal to trade",
    )
    for pattern in blocked_patterns:
        if re.search(pattern, text):
            raise ValueError(f"selector output contains prohibited language: {pattern}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


__all__ = (
    "ADOPTION_PRIORITY_VERSION",
    "SELECTOR_FEATURE_MATRIX_VERSION",
    "SELECTOR_INPUT_MANIFEST_VERSION",
    "SELECTOR_SCORE_MANIFEST_VERSION",
    "SELECTOR_TRAINABILITY_REPORT_VERSION",
    "build_rule_based_selector_score_manifest_v1",
    "build_selector_feature_matrix_v1",
    "build_selector_input_manifest_v1",
    "build_selector_trainability_report_v1",
    "validate_adoption_candidate_review_priority_v1",
    "validate_selector_feature_matrix_v1",
    "validate_selector_input_manifest_v1",
    "validate_selector_score_manifest_v1",
    "validate_selector_trainability_report_v1",
)
