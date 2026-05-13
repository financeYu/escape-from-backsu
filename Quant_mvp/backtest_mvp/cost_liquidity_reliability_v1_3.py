"""v1.3 cost, turnover, and liquidity reliability layer.

This module consumes candidate-only EvaluationEvidenceV1 records and emits
manual-review reliability artifacts. It does not create execution instructions,
operate live systems, or replace production ranking.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from statistics import fmean
from typing import Any
import json
import re

from Quant_mvp.backtest_mvp.evaluation_evidence_v1 import validate_evaluation_evidence_v1


RUNNER_VERSION = "v1_3_cost_turnover_liquidity_reliability_v1_0"
LIQUIDITY_HANDOFF_VERSION = "v1_3_candidate_liquidity_handoff_v1_0"
COST_PROFILE_REGISTRY_VERSION = "v1_3_cost_profile_registry_v1_0"
TURNOVER_PENALTY_REPORT_VERSION = "v1_3_turnover_penalty_report_v1_0"
LIQUIDITY_GUARD_REPORT_VERSION = "v1_3_liquidity_guard_report_v1_0"
REBALANCE_SENSITIVITY_REPORT_VERSION = "v1_3_rebalance_sensitivity_report_v1_0"
GROSS_VS_NET_SUMMARY_VERSION = "v1_3_gross_vs_net_evidence_summary_v1_0"
MANUAL_REVIEW_SECTION_VERSION = "v1_3_manual_review_cost_risk_section_v1_0"
DEFAULT_CREATED_AT = "2026-05-14T00:00:00+00:00"
PROHIBITED_FLAGS = (
    "live_execution_enabled",
    "brokerage_integration_enabled",
    "order_generation_enabled",
    "user_facing_auto_rebalance_instruction_enabled",
    "production_ranking_update_enabled",
    "valuation_fundamental_active_scoring_enabled",
)
EVIDENCE_ONLY_NOTICE = (
    "v1.3 cost, turnover, and liquidity outputs are historical or simulated "
    "candidate-only manual-review support"
)
PROHIBITED_ACTIONS_NOTICE = (
    "prohibited actions include live trading, brokerage integration, order generation, "
    "buy/sell/hold recommendations, trade-signal framing, automatic live rebalance "
    "instructions, move-to-cash commands, future-return claims, proven-alpha claims, "
    "production ranking replacement, and valuation/fundamental active scoring"
)


@dataclass(frozen=True)
class CostLiquidityReliabilityConfig:
    """Config for deterministic v1.3 reliability summaries."""

    cost_profile_id: str = "kr_equity_simulated_cost_profile_v1_3_base"
    fee_rate: float = 0.00015
    tax_rate: float = 0.0018
    slippage_rate: float = 0.0005
    market_impact_rate: float = 0.0
    turnover_warning_threshold: float = 0.75
    turnover_block_threshold: float = 1.50
    cost_drag_warning_threshold: float = 0.02
    cost_drag_block_threshold: float = 0.05
    liquidity_warn_traded_value: float = 5_000_000_000.0
    liquidity_block_traded_value: float = 1_000_000_000.0
    capacity_reference_amount: float | None = None
    capacity_traded_value_fraction: float = 0.05
    created_at: str = DEFAULT_CREATED_AT
    config_ref: str = "Quant_mvp/backtest_mvp/cost_liquidity_reliability_v1_3.py"
    rebalance_sensitivity_multipliers: tuple[tuple[str, float], ...] = (
        ("daily", 1.0),
        ("weekly", 0.45),
        ("monthly", 0.20),
    )


def run_v1_3_cost_turnover_liquidity_reliability(
    evaluation_evidences: Sequence[Mapping[str, Any]],
    *,
    liquidity_records: Sequence[Mapping[str, Any]] | None = None,
    liquidity_handoff: Mapping[str, Any] | None = None,
    config: CostLiquidityReliabilityConfig | None = None,
) -> dict[str, Any]:
    """Build v1.3 reliability artifacts from EvaluationEvidenceV1 records."""

    cfg = config or CostLiquidityReliabilityConfig()
    if liquidity_records is not None and liquidity_handoff is not None:
        raise ValueError("v1.3 reliability layer accepts liquidity_records or liquidity_handoff, not both")
    if not evaluation_evidences:
        raise ValueError("v1.3 reliability layer requires at least one EvaluationEvidenceV1 record")
    evidences = [dict(evidence) for evidence in evaluation_evidences]
    for evidence in evidences:
        validate_evaluation_evidence_v1(evidence)
    evidences.sort(key=lambda item: (str(item["date_range"].get("end")), str(item["candidate_id"])))
    handoff = (
        dict(liquidity_handoff)
        if liquidity_handoff is not None
        else build_v1_3_candidate_liquidity_handoff(evidences, liquidity_records=liquidity_records, config=cfg)
    )
    validate_v1_3_candidate_liquidity_handoff(handoff)
    _validate_handoff_matches_evidence(handoff, evidences)
    handoff_records = list(handoff["candidate_liquidity_rows"])
    liquidity_by_candidate = _liquidity_by_candidate(handoff_records)
    run_id = make_v1_3_reliability_run_id(evidences, handoff_records, cfg)
    registry = _cost_profile_registry(run_id, evidences, cfg)
    turnover_report = _turnover_penalty_report(run_id, evidences, cfg)
    liquidity_report = _liquidity_guard_report(run_id, evidences, liquidity_by_candidate, cfg)
    rebalance_report = _rebalance_sensitivity_report(run_id, evidences, cfg)
    gross_net_summary = _gross_vs_net_summary(run_id, evidences, cfg)
    manual_review = _manual_review_cost_risk_section(
        run_id,
        turnover_report,
        liquidity_report,
        gross_net_summary,
        rebalance_report,
        cfg,
    )
    artifacts = {
        "v1_3_candidate_liquidity_handoff": handoff,
        "v1_3_cost_profile_registry": registry,
        "v1_3_turnover_penalty_report": turnover_report,
        "v1_3_liquidity_guard_report": liquidity_report,
        "v1_3_rebalance_sensitivity_report": rebalance_report,
        "v1_3_gross_vs_net_evidence_summary": gross_net_summary,
        "v1_3_manual_review_cost_risk_section": manual_review,
    }
    validate_v1_3_reliability_artifacts(artifacts)
    return artifacts


def build_v1_3_candidate_liquidity_handoff(
    evaluation_evidences: Sequence[Mapping[str, Any]],
    *,
    liquidity_records: Sequence[Mapping[str, Any]] | None = None,
    config: CostLiquidityReliabilityConfig | None = None,
    handoff_id: str | None = None,
) -> dict[str, Any]:
    """Normalize candidate-level liquidity proxy inputs for v1.3 review."""

    cfg = config or CostLiquidityReliabilityConfig()
    if not evaluation_evidences:
        raise ValueError("v1.3 liquidity handoff requires EvaluationEvidenceV1 records")
    evidences = [dict(evidence) for evidence in evaluation_evidences]
    for evidence in evidences:
        validate_evaluation_evidence_v1(evidence)
    evidences.sort(key=lambda item: (str(item["date_range"].get("end")), str(item["candidate_id"])))
    candidate_ids = {str(evidence["candidate_id"]) for evidence in evidences}
    raw_records = _liquidity_by_candidate(liquidity_records or [])
    unmatched_candidate_ids = sorted(set(raw_records).difference(candidate_ids))
    rows = [
        _handoff_liquidity_row(evidence, raw_records.get(str(evidence["candidate_id"])), cfg)
        for evidence in evidences
    ]
    data_gap_summary = sorted(
        {
            reason
            for row in rows
            for reason in row["reason_codes"]
            if reason.endswith("_missing") or reason == "liquidity_proxy_missing"
        }
        | ({"candidate_id_mismatch"} if unmatched_candidate_ids else set())
    )
    handoff = {
        "handoff_version": LIQUIDITY_HANDOFF_VERSION,
        "handoff_id": handoff_id or make_v1_3_liquidity_handoff_id(evidences, rows, cfg),
        "created_at": cfg.created_at,
        "candidate_count": len(rows),
        "candidate_ids": [row["candidate_id"] for row in rows],
        "candidate_liquidity_rows": rows,
        "liquidity_proxy_fields": [
            "average_traded_value",
            "market_cap_proxy",
            "capacity_reference_amount",
            "liquidity_proxy_source_ref",
        ],
        "liquidity_proxy_field_descriptions": {
            "candidate_id": "must exactly match the EvaluationEvidenceV1 candidate_id",
            "average_traded_value": "KRW amount proxy supplied by the candidate liquidity handoff",
            "market_cap_proxy": "candidate market-cap proxy supplied by the candidate liquidity handoff",
            "capacity_reference_amount": "candidate review capacity amount supplied by the candidate liquidity handoff",
            "liquidity_proxy_source_ref": "source, as-of date, and window reference for the supplied liquidity proxy",
        },
        "unmatched_liquidity_record_candidate_ids": unmatched_candidate_ids,
        "unmatched_liquidity_record_count": len(unmatched_candidate_ids),
        "data_gap_summary": data_gap_summary,
        "handoff_policy": "candidate-level liquidity proxy handoff for v1.3 manual review reliability only",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    validate_v1_3_candidate_liquidity_handoff(handoff)
    return handoff


def validate_v1_3_candidate_liquidity_handoff(handoff: Mapping[str, Any]) -> None:
    required = {
        "handoff_version",
        "handoff_id",
        "created_at",
        "candidate_count",
        "candidate_ids",
        "candidate_liquidity_rows",
        "liquidity_proxy_fields",
        "unmatched_liquidity_record_candidate_ids",
        "unmatched_liquidity_record_count",
        "data_gap_summary",
        "handoff_policy",
    }
    missing = sorted(required.difference(handoff))
    if missing:
        raise ValueError(f"v1.3 liquidity handoff missing: {', '.join(missing)}")
    if handoff["handoff_version"] != LIQUIDITY_HANDOFF_VERSION:
        raise ValueError("unsupported v1.3 liquidity handoff version")
    rows = handoff["candidate_liquidity_rows"]
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        raise ValueError("v1.3 liquidity handoff rows must be a sequence")
    if int(handoff["candidate_count"]) != len(rows):
        raise ValueError("v1.3 liquidity handoff candidate_count mismatch")
    candidate_ids = [str(row.get("candidate_id") or "") for row in rows]
    if candidate_ids != list(handoff["candidate_ids"]):
        raise ValueError("v1.3 liquidity handoff candidate_ids must match row order")
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("v1.3 liquidity handoff candidate_id values must be unique")
    unmatched = handoff["unmatched_liquidity_record_candidate_ids"]
    if not isinstance(unmatched, Sequence) or isinstance(unmatched, (str, bytes, bytearray)):
        raise ValueError("v1.3 liquidity handoff unmatched candidate ids must be a sequence")
    if int(handoff["unmatched_liquidity_record_count"]) != len(unmatched):
        raise ValueError("v1.3 liquidity handoff unmatched candidate count mismatch")
    for row in rows:
        _validate_liquidity_handoff_row(row)
    _validate_blocked_flags(handoff)
    _reject_prohibited_language({"handoff": handoff})


def validate_v1_3_reliability_artifacts(artifacts: Mapping[str, Any]) -> None:
    required = {
        "v1_3_candidate_liquidity_handoff",
        "v1_3_cost_profile_registry",
        "v1_3_turnover_penalty_report",
        "v1_3_liquidity_guard_report",
        "v1_3_rebalance_sensitivity_report",
        "v1_3_gross_vs_net_evidence_summary",
        "v1_3_manual_review_cost_risk_section",
    }
    missing = sorted(required.difference(artifacts))
    if missing:
        raise ValueError(f"v1.3 reliability artifacts missing: {', '.join(missing)}")
    validate_v1_3_candidate_liquidity_handoff(artifacts["v1_3_candidate_liquidity_handoff"])
    if artifacts["v1_3_cost_profile_registry"].get("registry_version") != COST_PROFILE_REGISTRY_VERSION:
        raise ValueError("unsupported v1.3 cost profile registry version")
    if artifacts["v1_3_turnover_penalty_report"].get("report_version") != TURNOVER_PENALTY_REPORT_VERSION:
        raise ValueError("unsupported v1.3 turnover penalty report version")
    if artifacts["v1_3_liquidity_guard_report"].get("report_version") != LIQUIDITY_GUARD_REPORT_VERSION:
        raise ValueError("unsupported v1.3 liquidity guard report version")
    if artifacts["v1_3_rebalance_sensitivity_report"].get("report_version") != REBALANCE_SENSITIVITY_REPORT_VERSION:
        raise ValueError("unsupported v1.3 rebalance sensitivity report version")
    if artifacts["v1_3_gross_vs_net_evidence_summary"].get("summary_version") != GROSS_VS_NET_SUMMARY_VERSION:
        raise ValueError("unsupported v1.3 gross vs net summary version")
    if artifacts["v1_3_manual_review_cost_risk_section"].get("section_version") != MANUAL_REVIEW_SECTION_VERSION:
        raise ValueError("unsupported v1.3 manual review section version")
    for section in artifacts.values():
        _validate_blocked_flags(section)
    _reject_prohibited_language(artifacts)


def make_v1_3_reliability_run_id(
    evidences: Sequence[Mapping[str, Any]],
    liquidity_records: Sequence[Mapping[str, Any]],
    config: CostLiquidityReliabilityConfig,
) -> str:
    payload = {
        "version": RUNNER_VERSION,
        "evidence_refs": [
            {
                "candidate_id": evidence["candidate_id"],
                "evidence_id": evidence["evidence_id"],
                "date_range": evidence["date_range"],
                "metric_values": evidence["metric_values"],
            }
            for evidence in evidences
        ],
        "liquidity_records": sorted(
            [dict(record) for record in liquidity_records],
            key=lambda item: (str(item.get("candidate_id")), str(item.get("evidence_id"))),
        ),
        "config": config.__dict__,
    }
    digest = sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"v1_3_reliability_{digest}"


def make_v1_3_liquidity_handoff_id(
    evidences: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    config: CostLiquidityReliabilityConfig,
) -> str:
    payload = {
        "version": LIQUIDITY_HANDOFF_VERSION,
        "evidence_refs": [
            {
                "candidate_id": evidence["candidate_id"],
                "evidence_id": evidence["evidence_id"],
                "date_range": evidence["date_range"],
            }
            for evidence in evidences
        ],
        "rows": [dict(row) for row in rows],
        "config": {
            "capacity_reference_amount": config.capacity_reference_amount,
            "capacity_traded_value_fraction": config.capacity_traded_value_fraction,
            "liquidity_warn_traded_value": config.liquidity_warn_traded_value,
            "liquidity_block_traded_value": config.liquidity_block_traded_value,
        },
    }
    digest = sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"v1_3_liquidity_handoff_{digest}"


def _cost_profile_registry(
    run_id: str,
    evidences: Sequence[Mapping[str, Any]],
    config: CostLiquidityReliabilityConfig,
) -> dict[str, Any]:
    total_rate = _total_cost_rate(config)
    return {
        "registry_version": COST_PROFILE_REGISTRY_VERSION,
        "run_id": run_id,
        "created_at": config.created_at,
        "active_cost_profile_ref": config.cost_profile_id,
        "profiles": [
            {
                "cost_profile_ref": config.cost_profile_id,
                "fee_rate": config.fee_rate,
                "tax_rate": config.tax_rate,
                "slippage_rate": config.slippage_rate,
                "market_impact_rate": config.market_impact_rate,
                "total_cost_rate": total_rate,
                "cost_formula": "turnover * total_cost_rate",
                "profile_scope": "historical_simulated_candidate_evidence",
            }
        ],
        "evidence_cost_profile_refs": [
            {
                "candidate_id": str(evidence["candidate_id"]),
                "evidence_id": str(evidence["evidence_id"]),
                "cost_profile_ref": config.cost_profile_id,
            }
            for evidence in evidences
        ],
        "config_ref": config.config_ref,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }


def _turnover_penalty_report(
    run_id: str,
    evidences: Sequence[Mapping[str, Any]],
    config: CostLiquidityReliabilityConfig,
) -> dict[str, Any]:
    rows = []
    for evidence in evidences:
        extracted = _extract_evidence_metrics(evidence)
        v1_3_cost_drag = extracted["turnover"] * _total_cost_rate(config)
        status, reasons = _turnover_status(extracted["turnover"], v1_3_cost_drag, config)
        rows.append(
            {
                "candidate_id": evidence["candidate_id"],
                "evidence_id": evidence["evidence_id"],
                "cost_profile_ref": config.cost_profile_id,
                "turnover": extracted["turnover"],
                "source_cost_drag": extracted["source_cost_drag"],
                "v1_3_cost_drag": round(v1_3_cost_drag, 8),
                "turnover_penalty": round(v1_3_cost_drag, 8),
                "gross_evidence_return": extracted["gross_return"],
                "source_net_return": extracted["source_net_return"],
                "v1_3_adjusted_net_return": round(extracted["gross_return"] - v1_3_cost_drag, 8),
                "turnover_status": status,
                "reason_codes": reasons,
            }
        )
    return {
        "report_version": TURNOVER_PENALTY_REPORT_VERSION,
        "run_id": run_id,
        "created_at": config.created_at,
        "candidate_count": len(rows),
        "candidate_turnover_rows": rows,
        "portfolio_turnover_summary": {
            "average_turnover": _mean(row["turnover"] for row in rows),
            "average_v1_3_cost_drag": _mean(row["v1_3_cost_drag"] for row in rows),
            "blocked_count": sum(1 for row in rows if row["turnover_status"] == "block"),
            "warn_count": sum(1 for row in rows if row["turnover_status"] == "warn"),
        },
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }


def _liquidity_guard_report(
    run_id: str,
    evidences: Sequence[Mapping[str, Any]],
    liquidity_by_candidate: Mapping[str, Mapping[str, Any]],
    config: CostLiquidityReliabilityConfig,
) -> dict[str, Any]:
    rows = []
    for evidence in evidences:
        candidate_id = str(evidence["candidate_id"])
        liquidity = liquidity_by_candidate.get(candidate_id)
        rows.append(_liquidity_row(evidence, liquidity, config))
    return {
        "report_version": LIQUIDITY_GUARD_REPORT_VERSION,
        "run_id": run_id,
        "created_at": config.created_at,
        "candidate_count": len(rows),
        "liquidity_rows": rows,
        "liquidity_status_counts": {
            "pass": sum(1 for row in rows if row["liquidity_status"] == "pass"),
            "warn": sum(1 for row in rows if row["liquidity_status"] == "warn"),
            "block": sum(1 for row in rows if row["liquidity_status"] == "block"),
        },
        "data_gap_summary": sorted(
            {
                reason
                for row in rows
                for reason in row["reason_codes"]
                if reason.endswith("_missing") or reason == "liquidity_proxy_missing"
            }
        ),
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }


def _rebalance_sensitivity_report(
    run_id: str,
    evidences: Sequence[Mapping[str, Any]],
    config: CostLiquidityReliabilityConfig,
) -> dict[str, Any]:
    rows = []
    for evidence in evidences:
        extracted = _extract_evidence_metrics(evidence)
        sensitivity_rows = []
        for frequency, multiplier in config.rebalance_sensitivity_multipliers:
            turnover = extracted["turnover"] * max(0.0, float(multiplier))
            cost_drag = turnover * _total_cost_rate(config)
            sensitivity_rows.append(
                {
                    "frequency_label": frequency,
                    "turnover_multiplier": multiplier,
                    "sensitivity_turnover": round(turnover, 8),
                    "sensitivity_cost_drag": round(cost_drag, 8),
                    "sensitivity_net_return": round(extracted["gross_return"] - cost_drag, 8),
                }
            )
        rows.append(
            {
                "candidate_id": evidence["candidate_id"],
                "evidence_id": evidence["evidence_id"],
                "cost_profile_ref": config.cost_profile_id,
                "source_rebalance_frequency": evidence.get("rebalance_frequency"),
                "source_rebalancing_role": evidence.get("rebalancing_role"),
                "sensitivity_rows": sensitivity_rows,
            }
        )
    return {
        "report_version": REBALANCE_SENSITIVITY_REPORT_VERSION,
        "run_id": run_id,
        "created_at": config.created_at,
        "candidate_count": len(rows),
        "sensitivity_policy": "frequency labels compare historical or simulated cost sensitivity only",
        "candidate_sensitivity_rows": rows,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }


def _gross_vs_net_summary(
    run_id: str,
    evidences: Sequence[Mapping[str, Any]],
    config: CostLiquidityReliabilityConfig,
) -> dict[str, Any]:
    rows = []
    for evidence in evidences:
        extracted = _extract_evidence_metrics(evidence)
        v1_3_cost_drag = extracted["turnover"] * _total_cost_rate(config)
        adjusted = extracted["gross_return"] - v1_3_cost_drag
        rows.append(
            {
                "candidate_id": evidence["candidate_id"],
                "evidence_id": evidence["evidence_id"],
                "cost_profile_ref": config.cost_profile_id,
                "gross_evidence_return": extracted["gross_return"],
                "source_net_return": extracted["source_net_return"],
                "v1_3_adjusted_net_return": round(adjusted, 8),
                "gross_minus_source_net": round(extracted["gross_return"] - extracted["source_net_return"], 8),
                "gross_minus_v1_3_net": round(extracted["gross_return"] - adjusted, 8),
                "net_evidence_adjustment": round(adjusted - extracted["source_net_return"], 8),
            }
        )
    return {
        "summary_version": GROSS_VS_NET_SUMMARY_VERSION,
        "run_id": run_id,
        "created_at": config.created_at,
        "candidate_count": len(rows),
        "candidate_rows": rows,
        "aggregate_summary": {
            "average_gross_evidence_return": _mean(row["gross_evidence_return"] for row in rows),
            "average_source_net_return": _mean(row["source_net_return"] for row in rows),
            "average_v1_3_adjusted_net_return": _mean(row["v1_3_adjusted_net_return"] for row in rows),
            "average_net_evidence_adjustment": _mean(row["net_evidence_adjustment"] for row in rows),
        },
        "separation_policy": "gross evidence, source net evidence, and v1.3 adjusted net evidence are reported separately",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }


def _manual_review_cost_risk_section(
    run_id: str,
    turnover_report: Mapping[str, Any],
    liquidity_report: Mapping[str, Any],
    gross_net_summary: Mapping[str, Any],
    rebalance_report: Mapping[str, Any],
    config: CostLiquidityReliabilityConfig,
) -> dict[str, Any]:
    turnover_by_candidate = {
        str(row["candidate_id"]): row
        for row in turnover_report["candidate_turnover_rows"]
    }
    liquidity_by_candidate = {
        str(row["candidate_id"]): row
        for row in liquidity_report["liquidity_rows"]
    }
    gross_net_by_candidate = {
        str(row["candidate_id"]): row
        for row in gross_net_summary["candidate_rows"]
    }
    sections = []
    for candidate_id in sorted(turnover_by_candidate):
        turnover = turnover_by_candidate[candidate_id]
        liquidity = liquidity_by_candidate[candidate_id]
        gross_net = gross_net_by_candidate[candidate_id]
        sections.append(
            {
                "candidate_id": candidate_id,
                "evidence_id": turnover["evidence_id"],
                "cost_profile_ref": config.cost_profile_id,
                "turnover_status": turnover["turnover_status"],
                "liquidity_status": liquidity["liquidity_status"],
                "gross_evidence_return": gross_net["gross_evidence_return"],
                "source_net_return": gross_net["source_net_return"],
                "v1_3_adjusted_net_return": gross_net["v1_3_adjusted_net_return"],
                "limitation_summary": sorted(
                    set(turnover["reason_codes"] + liquidity["reason_codes"])
                ),
                "manual_review_required": True,
            }
        )
    return {
        "section_version": MANUAL_REVIEW_SECTION_VERSION,
        "run_id": run_id,
        "created_at": config.created_at,
        "cost_profile_ref": config.cost_profile_id,
        "candidate_sections": sections,
        "rebalance_sensitivity_ref": rebalance_report["run_id"],
        "manual_review_checklist": [
            "confirm_cost_profile_ref_is_appropriate_for_evidence_review",
            "confirm_turnover_penalty_does_not_dominate_candidate_evidence",
            "confirm_liquidity_status_before_interpreting_candidate_evidence",
            "confirm_rebalance_sensitivity_is_only_historical_or_simulated_context",
            "confirm_gross_and_net_evidence_are_reviewed_separately",
        ],
        "data_gap_summary": list(liquidity_report["data_gap_summary"]),
        "manual_review_required": True,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }


def _liquidity_row(
    evidence: Mapping[str, Any],
    liquidity: Mapping[str, Any] | None,
    config: CostLiquidityReliabilityConfig,
) -> dict[str, Any]:
    if liquidity is None or liquidity.get("liquidity_handoff_status") == "missing":
        return {
            "candidate_id": evidence["candidate_id"],
            "evidence_id": evidence["evidence_id"],
            "liquidity_status": "warn",
            "average_traded_value": None,
            "market_cap_proxy": None,
            "capacity_reference_amount": None,
            "capacity_proxy_amount": None,
            "liquidity_proxy_source_ref": None,
            "liquidity_handoff_fields_complete": False,
            "liquidity_sufficiently_checked": False,
            "reason_codes": ["liquidity_proxy_missing"],
            "manual_review_required": True,
        }
    average_traded_value = _optional_float(liquidity.get("average_traded_value"))
    market_cap_proxy = _optional_float(liquidity.get("market_cap_proxy"))
    capacity_reference = _optional_float(liquidity.get("capacity_reference_amount"))
    liquidity_proxy_source_ref = str(liquidity.get("liquidity_proxy_source_ref") or "").strip() or None
    assessment = _liquidity_assessment(
        average_traded_value,
        market_cap_proxy,
        capacity_reference,
        liquidity_proxy_source_ref,
        config,
    )
    return {
        "candidate_id": evidence["candidate_id"],
        "evidence_id": evidence["evidence_id"],
        "liquidity_status": assessment["status"],
        "average_traded_value": average_traded_value,
        "market_cap_proxy": market_cap_proxy,
        "capacity_reference_amount": capacity_reference,
        "capacity_proxy_amount": assessment["capacity_proxy_amount"],
        "liquidity_proxy_source_ref": liquidity_proxy_source_ref,
        "liquidity_handoff_fields_complete": assessment["fields_complete"],
        "liquidity_sufficiently_checked": assessment["sufficiently_checked"],
        "reason_codes": assessment["reason_codes"],
        "manual_review_required": assessment["status"] != "pass",
    }


def _handoff_liquidity_row(
    evidence: Mapping[str, Any],
    liquidity: Mapping[str, Any] | None,
    config: CostLiquidityReliabilityConfig,
) -> dict[str, Any]:
    candidate_id = str(evidence["candidate_id"])
    if liquidity is None:
        return {
            "candidate_id": candidate_id,
            "evidence_id": evidence["evidence_id"],
            "liquidity_handoff_status": "missing",
            "average_traded_value": None,
            "market_cap_proxy": None,
            "capacity_reference_amount": None,
            "liquidity_proxy_source_ref": None,
            "liquidity_handoff_fields_complete": False,
            "liquidity_sufficiently_checked": False,
            "reason_codes": ["liquidity_proxy_missing"],
            "manual_review_required": True,
        }
    average_traded_value = _optional_float(liquidity.get("average_traded_value"))
    market_cap_proxy = _optional_float(liquidity.get("market_cap_proxy"))
    capacity_reference = _optional_float(liquidity.get("capacity_reference_amount"))
    liquidity_proxy_source_ref = str(liquidity.get("liquidity_proxy_source_ref") or "").strip() or None
    assessment = _liquidity_assessment(
        average_traded_value,
        market_cap_proxy,
        capacity_reference,
        liquidity_proxy_source_ref,
        config,
    )
    field_reasons = [
        reason
        for reason in assessment["reason_codes"]
        if reason.endswith("_missing")
    ]
    status = "complete" if not field_reasons else "partial"
    return {
        "candidate_id": candidate_id,
        "evidence_id": evidence["evidence_id"],
        "liquidity_handoff_status": status,
        "average_traded_value": average_traded_value,
        "market_cap_proxy": market_cap_proxy,
        "capacity_reference_amount": capacity_reference,
        "liquidity_proxy_source_ref": liquidity_proxy_source_ref,
        "liquidity_handoff_fields_complete": assessment["fields_complete"],
        "liquidity_sufficiently_checked": assessment["sufficiently_checked"],
        "reason_codes": assessment["reason_codes"],
        "manual_review_required": not assessment["sufficiently_checked"],
    }


def _liquidity_assessment(
    average_traded_value: float | None,
    market_cap_proxy: float | None,
    capacity_reference: float | None,
    liquidity_proxy_source_ref: str | None,
    config: CostLiquidityReliabilityConfig,
) -> dict[str, Any]:
    reasons: list[str] = []
    status = "pass"
    if average_traded_value is None:
        status = "warn"
        reasons.append("average_traded_value_missing")
    elif average_traded_value <= config.liquidity_block_traded_value:
        status = "block"
        reasons.append("average_traded_value_below_block_threshold")
    elif average_traded_value < config.liquidity_warn_traded_value:
        status = "warn"
        reasons.append("average_traded_value_below_warn_threshold")
    if market_cap_proxy is None:
        if status != "block":
            status = "warn"
        reasons.append("market_cap_proxy_missing")
    capacity_proxy = None
    if capacity_reference is None:
        if status != "block":
            status = "warn"
        reasons.append("capacity_reference_missing")
    if average_traded_value is not None:
        capacity_proxy = average_traded_value * config.capacity_traded_value_fraction
        if capacity_reference is not None and capacity_reference > capacity_proxy:
            if status != "block":
                status = "warn"
            reasons.append("capacity_reference_exceeds_liquidity_proxy")
    if liquidity_proxy_source_ref is None:
        if status != "block":
            status = "warn"
        reasons.append("liquidity_proxy_source_ref_missing")
    fields_complete = not any(reason.endswith("_missing") for reason in reasons)
    sufficiently_checked = status == "pass" and not reasons
    return {
        "status": status,
        "capacity_proxy_amount": capacity_proxy,
        "fields_complete": fields_complete,
        "sufficiently_checked": sufficiently_checked,
        "reason_codes": reasons or ["liquidity_proxy_sufficiently_checked"],
    }


def _turnover_status(
    turnover: float,
    cost_drag: float,
    config: CostLiquidityReliabilityConfig,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    status = "pass"
    if turnover >= config.turnover_block_threshold:
        status = "block"
        reasons.append("turnover_above_block_threshold")
    elif turnover >= config.turnover_warning_threshold:
        status = "warn"
        reasons.append("turnover_above_warn_threshold")
    if cost_drag >= config.cost_drag_block_threshold:
        status = "block"
        reasons.append("cost_drag_above_block_threshold")
    elif cost_drag >= config.cost_drag_warning_threshold and status != "block":
        status = "warn"
        reasons.append("cost_drag_above_warn_threshold")
    return status, reasons or ["turnover_cost_profile_within_thresholds"]


def _extract_evidence_metrics(evidence: Mapping[str, Any]) -> dict[str, float]:
    metrics = evidence["metric_values"]
    returns = metrics.get("realized_return_summary")
    costs = metrics.get("realized_cost_summary")
    if not isinstance(returns, Mapping):
        raise ValueError("v1.3 reliability layer requires realized_return_summary")
    return {
        "gross_return": _required_float(returns.get("gross_return"), "gross_return"),
        "source_net_return": _required_float(returns.get("net_return"), "net_return"),
        "turnover": _required_float(metrics.get("realized_turnover_summary"), "realized_turnover_summary"),
        "source_cost_drag": _required_float(
            costs.get("cost_drag") if isinstance(costs, Mapping) else evidence.get("turnover_summary", {}).get("cost_drag"),
            "cost_drag",
        ),
    }


def _liquidity_by_candidate(records: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    by_candidate: dict[str, Mapping[str, Any]] = {}
    for record in records:
        candidate_id = str(record.get("candidate_id") or "").strip()
        if not candidate_id:
            raise ValueError("v1.3 liquidity record requires candidate_id")
        if candidate_id in by_candidate:
            raise ValueError(f"v1.3 liquidity record duplicate candidate_id: {candidate_id}")
        by_candidate[candidate_id] = dict(record)
    return by_candidate


def _validate_liquidity_handoff_row(row: Mapping[str, Any]) -> None:
    candidate_id = str(row.get("candidate_id") or "").strip()
    evidence_id = str(row.get("evidence_id") or "").strip()
    if not candidate_id:
        raise ValueError("v1.3 liquidity handoff row requires candidate_id")
    if not evidence_id:
        raise ValueError("v1.3 liquidity handoff row requires evidence_id")
    status = str(row.get("liquidity_handoff_status") or "")
    if status not in {"complete", "partial", "missing"}:
        raise ValueError(f"unsupported v1.3 liquidity handoff status: {status}")
    for field_name in ("average_traded_value", "market_cap_proxy", "capacity_reference_amount"):
        value = _optional_float(row.get(field_name))
        if value is not None and value < 0.0:
            raise ValueError(f"v1.3 liquidity handoff field must be non-negative: {field_name}")
    if "liquidity_proxy_source_ref" not in row:
        raise ValueError("v1.3 liquidity handoff row requires liquidity_proxy_source_ref")
    if "liquidity_handoff_fields_complete" not in row:
        raise ValueError("v1.3 liquidity handoff row requires liquidity_handoff_fields_complete")
    if "liquidity_sufficiently_checked" not in row:
        raise ValueError("v1.3 liquidity handoff row requires liquidity_sufficiently_checked")
    reasons = row.get("reason_codes")
    if not isinstance(reasons, Sequence) or isinstance(reasons, (str, bytes, bytearray)) or not reasons:
        raise ValueError("v1.3 liquidity handoff row requires reason_codes")


def _validate_handoff_matches_evidence(
    handoff: Mapping[str, Any],
    evidences: Sequence[Mapping[str, Any]],
) -> None:
    expected = [
        (str(evidence["candidate_id"]), str(evidence["evidence_id"]))
        for evidence in evidences
    ]
    actual = [
        (str(row["candidate_id"]), str(row["evidence_id"]))
        for row in handoff["candidate_liquidity_rows"]
    ]
    if actual != expected:
        raise ValueError("v1.3 liquidity handoff rows must match EvaluationEvidenceV1 candidates")


def _total_cost_rate(config: CostLiquidityReliabilityConfig) -> float:
    return max(0.0, config.fee_rate) + max(0.0, config.tax_rate) + max(0.0, config.slippage_rate) + max(0.0, config.market_impact_rate)


def _required_float(value: Any, field_name: str) -> float:
    result = _optional_float(value)
    if result is None:
        raise ValueError(f"v1.3 reliability layer requires numeric {field_name}")
    return result


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("v1.3 reliability layer requires numeric optional field") from exc


def _mean(values: Sequence[float] | Any) -> float:
    items = [float(value) for value in values]
    return round(fmean(items), 8) if items else 0.0


def _blocked_flags() -> dict[str, bool]:
    return {flag: False for flag in PROHIBITED_FLAGS}


def _validate_blocked_flags(section: Mapping[str, Any]) -> None:
    for flag in PROHIBITED_FLAGS:
        if bool(section.get(flag)):
            raise ValueError(f"v1.3 reliability artifact blocked flag must remain false: {flag}")


def _reject_prohibited_language(payload: Mapping[str, Any]) -> None:
    allowed_fields = {"prohibited_actions_notice", "evidence_only_notice"}
    text = json.dumps(
        _drop_allowed_notice_fields(payload, allowed_fields),
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
        r"\bmove to cash\b",
        r"\bfuture[-_ ]return\b",
        r"\bexpected[-_ ]return\b",
        r"\bproven[-_ ]alpha\b",
        r"\bproduction ranking replacement\b",
    )
    for pattern in blocked_patterns:
        if re.search(pattern, text):
            raise ValueError(f"v1.3 reliability artifacts contain prohibited language: {pattern}")


def _drop_allowed_notice_fields(value: Any, allowed_fields: set[str]) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _drop_allowed_notice_fields(item, allowed_fields)
            for key, item in value.items()
            if key not in allowed_fields
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_drop_allowed_notice_fields(item, allowed_fields) for item in value]
    return value


__all__ = (
    "CostLiquidityReliabilityConfig",
    "LIQUIDITY_HANDOFF_VERSION",
    "RUNNER_VERSION",
    "build_v1_3_candidate_liquidity_handoff",
    "make_v1_3_liquidity_handoff_id",
    "make_v1_3_reliability_run_id",
    "run_v1_3_cost_turnover_liquidity_reliability",
    "validate_v1_3_candidate_liquidity_handoff",
    "validate_v1_3_reliability_artifacts",
)
