"""v1.0-rc ManualReviewPacket contract."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
import json
import re

from Quant_mvp.backtest_mvp.evaluation_evidence_v1 import validate_evaluation_evidence_v1
from Quant_mvp.backtest_mvp.selector_evaluator_v1 import validate_selector_score_manifest_v1


PACKET_VERSION = "v1_0_rc_manual_review_packet_v1_0"
ALLOWED_PACKET_MODES = frozenset(
    {
        "manual_review_only",
        "evidence_summary_only",
        "adoption_candidate_manual_check",
        "diagnostic_reference_review",
    }
)
BLOCKED_PACKET_MODES = frozenset(
    {
        "live_trading",
        "paper_trading_execution",
        "brokerage_order",
        "trade_signal",
        "buy_sell_recommendation",
        "automatic_rebalance_instruction",
        "automatic_position_sizing",
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
    "automatic_position_sizing_enabled",
    "move_to_cash_enabled",
    "production_ranking_update_enabled",
    "valuation_fundamental_active_scoring_enabled",
)
EVIDENCE_ONLY_NOTICE = "ManualReviewPacket summarizes candidate-only evidence for manual review support only"
MANUAL_REVIEW_ONLY_NOTICE = "private manual-review support only; not an action, instruction, or recommendation"
PROHIBITED_ACTIONS_NOTICE = (
    "prohibited actions include live trading, brokerage integration, order generation, "
    "buy/sell/hold recommendations, trade-signal framing, automatic position sizing, "
    "automatic live rebalance instructions, move-to-cash commands, expected-return claims, "
    "future-return predictions, proven-alpha claims, production ranking replacement, "
    "and valuation/fundamental active scoring"
)
NOT_INVESTMENT_ADVICE_NOTICE = "not investment advice"
REQUIRED_PACKET_FIELDS = frozenset(
    {
        "packet_version",
        "packet_id",
        "created_at",
        "packet_mode",
        "route_scope",
        "candidate_id",
        "strategy_candidate_id",
        "strategy_candidate_ref",
        "selector_score_manifest_ref",
        "adoption_candidate_review_priority_ref",
        "evidence_refs",
        "evidence_summary",
        "historical_simulation_summary",
        "risk_flags",
        "coverage_gaps",
        "data_quality_flags",
        "horizon_policy_summary",
        "simulation_run_manifest_summary",
        "rebalance_disclosure",
        "rebalancing_role",
        "cost_slippage_turnover_summary",
        "limitation_summary",
        "manual_review_checklist",
        "manual_review_questions",
        "required_human_checks",
        "prohibited_actions_notice",
        "evidence_only_notice",
        "manual_review_only_notice",
        "manual_review_required",
        *PROHIBITED_FLAGS,
    }
)


def build_manual_review_packet_v1(
    *,
    evidence: Mapping[str, Any],
    selector_score_manifest: Mapping[str, Any],
    strategy_candidate_metadata: Mapping[str, Any] | None = None,
    current_condition_status: Mapping[str, Any] | None = None,
    created_at: str | None = None,
    packet_mode: str = "manual_review_only",
    route_scope: str = "v1_0_rc_phase_8_manual_review_packet",
) -> dict[str, Any]:
    evidence_payload = dict(evidence)
    selector_payload = dict(selector_score_manifest)
    validate_evaluation_evidence_v1(evidence_payload)
    validate_selector_score_manifest_v1(selector_payload)
    priority = _find_priority(selector_payload, evidence_payload["candidate_id"], evidence_payload["evidence_id"])
    packet = {
        "packet_version": PACKET_VERSION,
        "packet_id": make_manual_review_packet_id(evidence_payload["candidate_id"], evidence_payload["evidence_id"]),
        "created_at": created_at or _utc_now(),
        "packet_mode": packet_mode,
        "route_scope": route_scope,
        "candidate_id": evidence_payload["candidate_id"],
        "strategy_candidate_id": evidence_payload["strategy_candidate_id"],
        "strategy_candidate_ref": evidence_payload["strategy_candidate_ref"],
        "strategy_candidate_metadata": dict(strategy_candidate_metadata or {}),
        "selector_score_manifest_ref": selector_payload["selector_run_id"],
        "adoption_candidate_review_priority_ref": priority.get("evidence_id"),
        "evidence_refs": [evidence_payload["evidence_id"]],
        "evidence_summary": {
            "evidence_id": evidence_payload["evidence_id"],
            "evidence_status": evidence_payload["evidence_status"],
            "evidence_mode": evidence_payload["evidence_mode"],
            "metric_values": dict(evidence_payload["metric_values"]),
            "selector_priority_bucket": priority.get("review_priority_bucket"),
            "selector_reason_codes": list(priority.get("reason_codes") or []),
        },
        "historical_simulation_summary": {
            "date_range": dict(evidence_payload["date_range"]),
            "evaluation_window": dict(evidence_payload["evaluation_window"]),
            "universe_scope": evidence_payload["universe_scope"],
            "metrics_schema_version": evidence_payload["metrics_schema_version"],
        },
        "risk_flags": _risk_flags(evidence_payload, priority),
        "coverage_gaps": _coverage_gaps(evidence_payload),
        "data_quality_flags": _data_quality_flags(evidence_payload),
        "horizon_policy_summary": {
            "horizon_policy_id": evidence_payload["horizon_policy_id"],
            "signal_frequency": evidence_payload["horizon_policy_snapshot"]["signal_frequency"],
            "holding_period_trading_days": evidence_payload["horizon_policy_snapshot"]["holding_period_trading_days"],
            "rebalance_frequency": evidence_payload["rebalance_frequency"],
        },
        "simulation_run_manifest_summary": {
            "simulation_run_manifest_ref": evidence_payload["simulation_run_manifest_ref"],
            "run_mode": evidence_payload["simulation_run_manifest_snapshot"]["run_mode"],
            "evidence_mode": evidence_payload["simulation_run_manifest_snapshot"]["evidence_mode"],
        },
        "weight_config_summary": (
            {
                "weight_config_id": evidence_payload.get("weight_config_id"),
                "score_weights": evidence_payload.get("weight_config_snapshot", {}).get("score_weights")
                if isinstance(evidence_payload.get("weight_config_snapshot"), Mapping)
                else None,
            }
            if evidence_payload.get("weight_config_snapshot")
            else None
        ),
        "layer_registry_summary": {
            "layer_registry_validation_status": evidence_payload.get("layer_registry_validation_status"),
            "layer_registry_validation_ref": evidence_payload.get("layer_registry_validation_ref"),
        },
        "rebalance_disclosure": evidence_payload["rebalance_disclosure"],
        "rebalancing_role": evidence_payload["rebalancing_role"],
        "cost_slippage_turnover_summary": {
            "cost_model": evidence_payload["cost_model"],
            "slippage_model": evidence_payload["slippage_model"],
            "turnover_summary": dict(evidence_payload["turnover_summary"]),
        },
        "limitation_summary": list(evidence_payload["limitation_summary"])
        + list(selector_payload.get("limitation_summary") or []),
        "manual_review_checklist": _manual_review_checklist(evidence_payload),
        "manual_review_questions": _manual_review_questions(evidence_payload, priority),
        "required_human_checks": [
            "confirm_candidate_scope_and_route_eligibility",
            "confirm_evidence_artifacts_are_current_and_complete",
            "confirm_selector_priority_is_review_prioritization_only",
            "confirm_no_valuation_fundamental_active_scoring_was_used",
        ],
        "current_condition_status": dict(current_condition_status) if isinstance(current_condition_status, Mapping) else None,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "manual_review_only_notice": MANUAL_REVIEW_ONLY_NOTICE,
        "not_investment_advice_notice": NOT_INVESTMENT_ADVICE_NOTICE,
        "live_execution_enabled": False,
        "brokerage_integration_enabled": False,
        "order_generation_enabled": False,
        "user_facing_auto_rebalance_instruction_enabled": False,
        "automatic_position_sizing_enabled": False,
        "move_to_cash_enabled": False,
        "production_ranking_update_enabled": False,
        "valuation_fundamental_active_scoring_enabled": False,
        "manual_review_required": True,
    }
    validate_manual_review_packet_v1(packet)
    return packet


def validate_manual_review_packet_v1(packet: Mapping[str, Any]) -> None:
    missing = sorted(REQUIRED_PACKET_FIELDS.difference(packet))
    if missing:
        raise ValueError(f"ManualReviewPacket missing required fields: {', '.join(missing)}")
    if packet["packet_version"] != PACKET_VERSION:
        raise ValueError("unsupported ManualReviewPacket version")
    if packet["packet_mode"] in BLOCKED_PACKET_MODES or packet["packet_mode"] not in ALLOWED_PACKET_MODES:
        raise ValueError(f"blocked or unsupported packet_mode: {packet['packet_mode']}")
    if packet["manual_review_required"] is not True:
        raise ValueError("ManualReviewPacket requires manual_review_required true")
    for flag in PROHIBITED_FLAGS:
        if bool(packet.get(flag)):
            raise ValueError(f"ManualReviewPacket blocked flag must remain false: {flag}")
    if packet.get("rebalance_disclosure") in (None, "") and packet.get("rebalancing_role") != "none":
        raise ValueError("ManualReviewPacket requires rebalancing disclosure")
    _reject_packet_language(packet)


def make_manual_review_packet_id(candidate_id: str, evidence_id: str) -> str:
    digest = sha256(f"{candidate_id}|{evidence_id}".encode("utf-8")).hexdigest()[:12]
    return f"mrp_v1_0_rc_{digest}"


def _find_priority(
    selector_manifest: Mapping[str, Any],
    candidate_id: str,
    evidence_id: str,
) -> Mapping[str, Any]:
    for priority in selector_manifest.get("candidate_review_priorities", []):
        if priority.get("candidate_id") == candidate_id and priority.get("evidence_id") == evidence_id:
            return priority
    raise ValueError("ManualReviewPacket requires matching selector review priority for evidence")


def _risk_flags(evidence: Mapping[str, Any], priority: Mapping[str, Any]) -> list[str]:
    flags = set(str(flag) for flag in evidence.get("evidence_quality_flags") or [])
    reason_codes = set(str(code) for code in priority.get("reason_codes") or [])
    if "rebalance_material_to_evidence" in reason_codes:
        flags.add("rebalance_material_to_evidence")
    if evidence.get("leakage_check_status") != "pass":
        flags.add("leakage_check_not_passed")
    if evidence.get("no_lookahead_check_status") != "pass":
        flags.add("no_lookahead_check_not_passed")
    return sorted(flags)


def _coverage_gaps(evidence: Mapping[str, Any]) -> list[str]:
    coverage = evidence.get("coverage_summary") if isinstance(evidence.get("coverage_summary"), Mapping) else {}
    gaps: list[str] = []
    if not evidence.get("metric_values"):
        gaps.append("metric_values_missing")
    if coverage.get("coverage_ratio") is None:
        gaps.append("coverage_ratio_missing")
    if coverage.get("invalid_period_count"):
        gaps.append("invalid_periods_present")
    return sorted(set(gaps))


def _data_quality_flags(evidence: Mapping[str, Any]) -> list[str]:
    summary = evidence.get("data_quality_summary") if isinstance(evidence.get("data_quality_summary"), Mapping) else {}
    flags = list(summary.get("flags") or [])
    if summary.get("missing_data_count"):
        flags.append("missing_data_present")
    return sorted(set(str(flag) for flag in flags))


def _manual_review_checklist(evidence: Mapping[str, Any]) -> list[str]:
    checklist = [
        "confirm_candidate_scope_and_route_eligibility",
        "confirm_evidence_artifacts_are_current_and_complete",
        "confirm_horizon_policy_is_intended_for_this_review",
        "confirm_simulation_or_backtest_was_candidate_only_and_evidence_only",
        "confirm_rebalancing_role_and_turnover_cost_slippage_assumptions",
        "confirm_coverage_gaps_and_invalid_periods",
        "confirm_selector_priority_is_review_prioritization_not_action",
        "confirm_no_valuation_fundamental_active_scoring_was_used",
        "confirm_no_live_execution_or_order_generation_is_present",
        "confirm_diagnostic_current_condition_context_is_reference_only_when_present",
    ]
    if evidence.get("rebalancing_role") in {"tested_strategy_logic", "material_effect_on_candidate_evidence"}:
        checklist.append("confirm_material_rebalancing_disclosure_is_understood_as_evidence_context")
    return checklist


def _manual_review_questions(evidence: Mapping[str, Any], priority: Mapping[str, Any]) -> list[str]:
    questions = [
        "Are evidence artifacts complete for the selected horizon?",
        "Are coverage gaps acceptable for manual review?",
        "Do selector reason_codes require additional evidence collection?",
    ]
    if "rebalance_material_to_evidence" in set(priority.get("reason_codes") or []):
        questions.append("How material is the disclosed historical or simulated rebalancing assumption?")
    if not evidence.get("metric_values"):
        questions.append("Which runner integration is needed before metric evidence can be reviewed?")
    return questions


def _reject_packet_language(packet: Mapping[str, Any]) -> None:
    allowed_fields = {
        "prohibited_actions_notice",
        "evidence_only_notice",
        "manual_review_only_notice",
        "not_investment_advice_notice",
        "manual_review_checklist",
        "required_human_checks",
    }
    text = json.dumps(
        {key: value for key, value in packet.items() if key not in allowed_fields},
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    blocked_patterns = (
        r"\bbuy\b",
        r"\bsell\b",
        r"\bhold\b",
        r"\btrade signal\b",
        r"\border instruction\b",
        r"\bautomatic rebalance instruction\b",
        r"\bposition sizing instruction\b",
        r"\bmove to cash\b",
        r"\bexpected return\b",
        r"\bfuture return\b",
        r"\bproven alpha\b",
    )
    for pattern in blocked_patterns:
        if re.search(pattern, text):
            raise ValueError(f"ManualReviewPacket contains prohibited language: {pattern}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


__all__ = (
    "PACKET_VERSION",
    "build_manual_review_packet_v1",
    "make_manual_review_packet_id",
    "validate_manual_review_packet_v1",
)
