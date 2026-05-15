"""v1.5 point-in-time valuation, quality, and profitability layer.

The layer consumes explicit point-in-time fundamental handoff rows and emits
candidate-only manual-review diagnostics. It never activates valuation scoring,
production ranking, live execution, or transaction behavior.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from math import isfinite
from statistics import fmean
from typing import Any
import json
import re

from Quant_mvp.backtest_mvp.evaluation_evidence_v1 import validate_evaluation_evidence_v1


RUNNER_VERSION = "v1_5_valuation_quality_layer_v1_0"
DATA_CONTRACT_VERSION = "v1_5_fundamental_data_contract_v1_0"
PIT_VALIDATION_VERSION = "v1_5_pit_fundamental_validation_report_v1_0"
VALUATION_MANIFEST_VERSION = "v1_5_valuation_feature_manifest_v1_0"
QUALITY_MANIFEST_VERSION = "v1_5_quality_profitability_feature_manifest_v1_0"
INVESTMENT_MANIFEST_VERSION = "v1_5_investment_feature_manifest_v1_0"
SECTOR_REPORT_VERSION = "v1_5_sector_relative_valuation_report_v1_0"
LAYER_REGISTRY_ENTRY_VERSION = "v1_5_layer_registry_entry_v1_0"
INCREMENTAL_REPORT_VERSION = "v1_5_incremental_valuation_evidence_report_v1_0"
MANUAL_REVIEW_VERSION = "v1_5_manual_review_valuation_section_v1_0"
VALIDATION_MANIFEST_VERSION = "v1_5_validation_manifest_v1_0"
COMPLETION_REPORT_VERSION = "v1_5_completion_report_v1_0"
DEFAULT_CREATED_AT = "2026-05-15T00:00:00+00:00"

EVIDENCE_ONLY_NOTICE = (
    "v1.5 valuation, quality, and profitability outputs are candidate-only "
    "manual-review diagnostics"
)
PROHIBITED_ACTIONS_NOTICE = (
    "prohibited actions include live trading, brokerage integration, order generation, "
    "buy/sell/hold recommendations, trade-signal framing, automatic rebalance "
    "instructions, production ranking replacement, future-return claims, proven-alpha "
    "claims, valuation/fundamental active scoring, and production activation"
)
PROHIBITED_FLAGS = (
    "live_execution_enabled",
    "brokerage_integration_enabled",
    "order_generation_enabled",
    "user_facing_auto_rebalance_instruction_enabled",
    "production_ranking_update_enabled",
    "valuation_fundamental_active_scoring_enabled",
)

REQUIRED_FUNDAMENTAL_FIELDS = (
    "candidate_id",
    "evidence_id",
    "ticker",
    "evaluation_date",
    "fiscal_period",
    "report_period_end_date",
    "filing_date_or_disclosure_date",
    "availability_date",
    "source_ref",
    "field_name",
    "value",
    "unit",
)
OPTIONAL_FUNDAMENTAL_FIELDS = (
    "currency",
    "sector_id",
    "industry_id",
    "industry_name",
    "reporting_lag_policy",
    "stale_data_policy",
    "restatement_policy",
    "pit_validation_status",
    "coverage_status",
    "data_quality_flags",
    "blocked_reason",
    "pending_reason",
)
UNSAFE_QUALITY_FLAGS = frozenset(
    {
        "future_filled",
        "backfilled",
        "filled_from_future",
        "unsafe_imputation",
        "missing_availability_date",
    }
)
FORBIDDEN_FEATURE_NAMES = frozenset(
    {
        "label",
        "target",
        "raw_label",
        "future_return",
        "expected_return",
        "predicted_return",
        "technical_composite_score",
        "final_composite_score",
        "production_score",
        "trade_signal",
    }
)
FIELD_ALIASES = {
    "per": "price_to_earnings",
    "p_e": "price_to_earnings",
    "price_earnings": "price_to_earnings",
    "pbr": "price_to_book",
    "p_b": "price_to_book",
    "price_book": "price_to_book",
    "psr": "price_to_sales",
    "p_s": "price_to_sales",
    "price_sales": "price_to_sales",
    "roe": "roe",
    "roa": "roa",
}


@dataclass(frozen=True)
class ValuationQualityLayerConfig:
    """Config for deterministic v1.5 diagnostics."""

    valuation_run_id: str | None = None
    created_at: str = DEFAULT_CREATED_AT
    min_candidate_coverage_ratio: float = 0.8
    max_stale_age_days: int = 540
    max_reporting_lag_days: int = 180
    min_sector_peer_count: int = 2
    layer_status_when_covered: str = "candidate_only"
    layer_status_when_uncovered: str = "diagnostic_only"
    config_ref: str = "Quant_mvp/backtest_mvp/valuation_quality_layer_v1_5.py"


def run_v1_5_valuation_quality_layer(
    evaluation_evidences: Sequence[Mapping[str, Any]],
    *,
    fundamental_records: Sequence[Mapping[str, Any]] | None = None,
    technical_ml_artifacts: Mapping[str, Any] | None = None,
    technical_ml_valuation_artifacts: Mapping[str, Any] | None = None,
    config: ValuationQualityLayerConfig | None = None,
) -> dict[str, Any]:
    """Build v1.5 pending-data valuation and quality diagnostics."""

    cfg = config or ValuationQualityLayerConfig()
    if not evaluation_evidences:
        raise ValueError("v1.5 valuation layer requires EvaluationEvidenceV1 records")
    evidences = [dict(evidence) for evidence in evaluation_evidences]
    for evidence in evidences:
        validate_evaluation_evidence_v1(evidence)
    evidences.sort(key=lambda item: (str(item["date_range"].get("end")), str(item["candidate_id"])))
    records = [dict(record) for record in (fundamental_records or [])]
    valuation_run_id = cfg.valuation_run_id or make_v1_5_valuation_run_id(evidences, records, cfg)

    contract = build_v1_5_fundamental_data_contract(valuation_run_id=valuation_run_id, config=cfg)
    pit_validation = build_v1_5_pit_validation_report(
        evidences,
        records,
        valuation_run_id=valuation_run_id,
        config=cfg,
    )
    valuation_manifest = build_v1_5_valuation_feature_manifest(
        pit_validation,
        valuation_run_id=valuation_run_id,
        created_at=cfg.created_at,
    )
    quality_manifest = build_v1_5_quality_profitability_feature_manifest(
        pit_validation,
        valuation_run_id=valuation_run_id,
        created_at=cfg.created_at,
    )
    investment_manifest = build_v1_5_investment_feature_manifest(
        pit_validation,
        valuation_run_id=valuation_run_id,
        created_at=cfg.created_at,
    )
    sector_report = build_v1_5_sector_relative_valuation_report(
        valuation_manifest,
        quality_manifest,
        investment_manifest,
        valuation_run_id=valuation_run_id,
        config=cfg,
    )
    registry_entry = build_v1_5_layer_registry_entry(
        pit_validation,
        valuation_manifest,
        quality_manifest,
        investment_manifest,
        valuation_run_id=valuation_run_id,
        config=cfg,
    )
    incremental = build_v1_5_incremental_valuation_evidence_report(
        pit_validation,
        valuation_manifest,
        quality_manifest,
        investment_manifest,
        sector_report,
        technical_ml_artifacts=technical_ml_artifacts,
        technical_ml_valuation_artifacts=technical_ml_valuation_artifacts,
        valuation_run_id=valuation_run_id,
        created_at=cfg.created_at,
    )
    manual_review = build_v1_5_manual_review_valuation_section(
        pit_validation,
        valuation_manifest,
        quality_manifest,
        investment_manifest,
        sector_report,
        incremental,
        registry_entry,
        valuation_run_id=valuation_run_id,
        created_at=cfg.created_at,
    )
    validation_manifest = build_v1_5_validation_manifest(
        pit_validation,
        registry_entry,
        valuation_run_id=valuation_run_id,
        created_at=cfg.created_at,
    )
    completion_report = build_v1_5_completion_report(
        pit_validation,
        valuation_manifest,
        quality_manifest,
        investment_manifest,
        sector_report,
        incremental,
        validation_manifest,
        valuation_run_id=valuation_run_id,
        created_at=cfg.created_at,
    )
    artifacts = {
        "v1_5_fundamental_data_contract": contract,
        "v1_5_pit_validation_report": pit_validation,
        "v1_5_valuation_feature_manifest": valuation_manifest,
        "v1_5_quality_profitability_feature_manifest": quality_manifest,
        "v1_5_investment_feature_manifest": investment_manifest,
        "v1_5_sector_relative_valuation_report": sector_report,
        "v1_5_layer_registry_entry": registry_entry,
        "v1_5_incremental_valuation_evidence_report": incremental,
        "v1_5_manual_review_valuation_section": manual_review,
        "v1_5_validation_manifest": validation_manifest,
        "v1_5_completion_report": completion_report,
    }
    validate_v1_5_valuation_quality_artifacts(artifacts)
    return artifacts


def build_v1_5_fundamental_data_contract(
    *,
    valuation_run_id: str,
    config: ValuationQualityLayerConfig | None = None,
) -> dict[str, Any]:
    cfg = config or ValuationQualityLayerConfig(valuation_run_id=valuation_run_id)
    contract = {
        "contract_version": DATA_CONTRACT_VERSION,
        "valuation_run_id": valuation_run_id,
        "created_at": cfg.created_at,
        "extends_existing_contract": "src/valuation Step 18 candidate-only PIT contract",
        "required_fields": list(REQUIRED_FUNDAMENTAL_FIELDS),
        "optional_fields": list(OPTIONAL_FUNDAMENTAL_FIELDS),
        "field_descriptions": {
            "ticker": "KOSPI200 ticker or approved candidate ticker lineage",
            "evaluation_date": "candidate evidence observation end date used for PIT cutoff",
            "fiscal_period": "fiscal period represented by the row",
            "report_period_end_date": "period end date for the financial statement or derived ratio",
            "filing_date_or_disclosure_date": "source filing or disclosure date",
            "availability_date": "date the row was available for evaluation",
            "source_ref": "source report, disclosure, vendor snapshot, or approved fixture reference",
            "field_name": "fundamental field or precomputed PIT diagnostic name",
            "value": "numeric field value",
            "unit": "ratio, percent, currency amount, shares, or count",
            "sector_id": "sector bucket for sector-relative diagnostics",
            "reporting_lag_policy": "must be explicit when lag exceeds configured maximum",
            "stale_data_policy": "must be explicit when age exceeds configured maximum",
            "restatement_policy": "must identify whether later-restated values are excluded",
            "coverage_status": "available or pending_data",
        },
        "reporting_lag_policy": {
            "max_reporting_lag_days": cfg.max_reporting_lag_days,
            "pending_reason": "reporting_lag_policy_violation",
        },
        "stale_data_policy": {
            "max_stale_age_days": cfg.max_stale_age_days,
            "pending_reason": "stale_data_policy_violation",
        },
        "restatement_policy": "later restated values must carry restatement availability metadata and cannot leak before evaluation_date",
        "feature_families": {
            "valuation": list(_valuation_feature_specs()),
            "quality_profitability": list(_quality_feature_specs()),
            "investment": list(_investment_feature_specs()),
        },
        "unsupported_feature_policy": "unsupported features remain listed with pending_data reason",
        "minimum_data_handoff_request": _minimum_data_handoff_request(),
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _reject_prohibited_language({"contract": contract})
    return contract


def build_v1_5_pit_validation_report(
    evaluation_evidences: Sequence[Mapping[str, Any]],
    fundamental_records: Sequence[Mapping[str, Any]],
    *,
    valuation_run_id: str,
    config: ValuationQualityLayerConfig | None = None,
) -> dict[str, Any]:
    cfg = config or ValuationQualityLayerConfig(valuation_run_id=valuation_run_id)
    record_index = _records_by_candidate_field(fundamental_records)
    rows: list[dict[str, Any]] = []
    for evidence in evaluation_evidences:
        candidate_id = str(evidence["candidate_id"])
        candidate_records = record_index.get(candidate_id, {})
        if not candidate_records:
            rows.append(_missing_candidate_validation_row(evidence))
            continue
        for record in candidate_records.values():
            rows.append(_pit_validation_row(evidence, record, cfg))
    unmatched = sorted(set(record_index).difference(str(evidence["candidate_id"]) for evidence in evaluation_evidences))
    pass_rows = [row for row in rows if row["pit_status"] == "pass"]
    candidate_ids = {str(evidence["candidate_id"]) for evidence in evaluation_evidences}
    covered_candidates = {row["candidate_id"] for row in pass_rows}
    coverage_ratio = round(len(covered_candidates) / len(candidate_ids), 8) if candidate_ids else 0.0
    gap_summary = sorted(
        {
            reason
            for row in rows
            for reason in row["reason_codes"]
            if reason != "pit_fundamental_available"
        }
        | ({"candidate_id_mismatch"} if unmatched else set())
    )
    report = {
        "report_version": PIT_VALIDATION_VERSION,
        "valuation_run_id": valuation_run_id,
        "created_at": cfg.created_at,
        "candidate_count": len(candidate_ids),
        "record_count": len(rows),
        "pit_pass_record_count": len(pass_rows),
        "covered_candidate_count": len(covered_candidates),
        "coverage_ratio": coverage_ratio,
        "coverage_status": "sufficient" if coverage_ratio >= cfg.min_candidate_coverage_ratio else "pending_data",
        "candidate_fundamental_rows": rows,
        "unmatched_fundamental_record_candidate_ids": unmatched,
        "unmatched_fundamental_record_count": len(unmatched),
        "coverage_gap_summary": gap_summary,
        "pit_policy": "availability_date and filing/disclosure date must be on or before evaluation_date",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _reject_prohibited_language({"pit_validation": report})
    return report


def build_v1_5_valuation_feature_manifest(
    pit_validation_report: Mapping[str, Any],
    *,
    valuation_run_id: str,
    created_at: str = DEFAULT_CREATED_AT,
) -> dict[str, Any]:
    return _build_feature_manifest(
        pit_validation_report,
        manifest_version=VALUATION_MANIFEST_VERSION,
        manifest_key="v1_5_valuation_feature_manifest",
        family="valuation",
        feature_specs=_valuation_feature_specs(),
        unsupported_features=_unsupported_valuation_features(),
        valuation_run_id=valuation_run_id,
        created_at=created_at,
    )


def build_v1_5_quality_profitability_feature_manifest(
    pit_validation_report: Mapping[str, Any],
    *,
    valuation_run_id: str,
    created_at: str = DEFAULT_CREATED_AT,
) -> dict[str, Any]:
    return _build_feature_manifest(
        pit_validation_report,
        manifest_version=QUALITY_MANIFEST_VERSION,
        manifest_key="v1_5_quality_profitability_feature_manifest",
        family="quality_profitability",
        feature_specs=_quality_feature_specs(),
        unsupported_features=_unsupported_quality_features(),
        valuation_run_id=valuation_run_id,
        created_at=created_at,
    )


def build_v1_5_investment_feature_manifest(
    pit_validation_report: Mapping[str, Any],
    *,
    valuation_run_id: str,
    created_at: str = DEFAULT_CREATED_AT,
) -> dict[str, Any]:
    return _build_feature_manifest(
        pit_validation_report,
        manifest_version=INVESTMENT_MANIFEST_VERSION,
        manifest_key="v1_5_investment_feature_manifest",
        family="investment",
        feature_specs=_investment_feature_specs(),
        unsupported_features=_unsupported_investment_features(),
        valuation_run_id=valuation_run_id,
        created_at=created_at,
    )


def build_v1_5_sector_relative_valuation_report(
    valuation_manifest: Mapping[str, Any],
    quality_manifest: Mapping[str, Any],
    investment_manifest: Mapping[str, Any],
    *,
    valuation_run_id: str,
    config: ValuationQualityLayerConfig | None = None,
) -> dict[str, Any]:
    cfg = config or ValuationQualityLayerConfig(valuation_run_id=valuation_run_id)
    raw_rows = []
    for manifest in (valuation_manifest, quality_manifest, investment_manifest):
        for row in manifest["rows"]:
            sector_id = row.get("sector_id")
            for feature_name, raw_value in row["raw_features"].items():
                raw_rows.append(
                    {
                        "candidate_id": row["candidate_id"],
                        "evidence_id": row["evidence_id"],
                        "sector_id": sector_id,
                        "feature_name": feature_name,
                        "raw_value": raw_value,
                        "feature_family": manifest["feature_family"],
                    }
                )
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in raw_rows:
        key = (str(row.get("sector_id") or ""), str(row["feature_name"]))
        grouped.setdefault(key, []).append(row)
    sector_relative_rows = []
    for row in raw_rows:
        peers = grouped.get((str(row.get("sector_id") or ""), str(row["feature_name"])), [])
        numeric = [float(peer["raw_value"]) for peer in peers if _optional_float(peer.get("raw_value")) is not None]
        peer_count = len(numeric)
        if not row.get("sector_id"):
            status = "pending_data"
            adjusted = None
            reason = "sector_id_missing"
        elif peer_count < cfg.min_sector_peer_count:
            status = "pending_data"
            adjusted = None
            reason = "minimum_sector_peer_count_not_met"
        else:
            sector_mean = fmean(numeric)
            adjusted = round(float(row["raw_value"]) - sector_mean, 8)
            status = "available"
            reason = "sector_relative_value_available"
        sector_relative_rows.append(
            {
                "candidate_id": row["candidate_id"],
                "evidence_id": row["evidence_id"],
                "sector_id": row.get("sector_id"),
                "feature_name": row["feature_name"],
                "raw_value": row["raw_value"],
                "sector_adjusted_value": adjusted,
                "peer_count": peer_count,
                "sector_relative_status": status,
                "reason_code": reason,
            }
        )
    report = {
        "report_version": SECTOR_REPORT_VERSION,
        "valuation_run_id": valuation_run_id,
        "created_at": cfg.created_at,
        "raw_feature_rows": raw_rows,
        "sector_relative_rows": sector_relative_rows,
        "raw_and_adjusted_separation_status": "raw_values_and_sector_adjusted_values_are_separate",
        "minimum_sector_peer_count": cfg.min_sector_peer_count,
        "pending_sector_data_count": sum(
            1 for row in sector_relative_rows if row["sector_relative_status"] == "pending_data"
        ),
        "insufficient_sector_data_count": sum(
            1 for row in sector_relative_rows if row["sector_relative_status"] == "pending_data"
        ),
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _reject_prohibited_language({"sector_report": report})
    return report


def build_v1_5_layer_registry_entry(
    pit_validation_report: Mapping[str, Any],
    valuation_manifest: Mapping[str, Any],
    quality_manifest: Mapping[str, Any],
    investment_manifest: Mapping[str, Any],
    *,
    valuation_run_id: str,
    config: ValuationQualityLayerConfig | None = None,
) -> dict[str, Any]:
    cfg = config or ValuationQualityLayerConfig(valuation_run_id=valuation_run_id)
    feature_count = (
        int(valuation_manifest["row_count"])
        + int(quality_manifest["row_count"])
        + int(investment_manifest["row_count"])
    )
    covered = pit_validation_report["coverage_status"] == "sufficient" and feature_count > 0
    status = cfg.layer_status_when_covered if covered else cfg.layer_status_when_uncovered
    if status == "active":
        raise ValueError("v1.5 valuation layer must not be active")
    registry = {
        "registry_version": LAYER_REGISTRY_ENTRY_VERSION,
        "valuation_run_id": valuation_run_id,
        "created_at": cfg.created_at,
        "layer_id": "v1_5_valuation_quality_profitability_layer",
        "layer_name": "v1.5 valuation quality profitability diagnostics",
        "layer_category": "valuation",
        "layer_status": status,
        "allowed_statuses": ["candidate_only", "diagnostic_only"],
        "coverage_ref": "v1_5_pit_validation_report",
        "feature_manifest_refs": [
            "v1_5_valuation_feature_manifest",
            "v1_5_quality_profitability_feature_manifest",
            "v1_5_investment_feature_manifest",
        ],
        "blocked_activation_reasons": [
            "requires verified PIT fundamental coverage before any stronger downstream use",
            "valuation_fundamental_active_scoring_not_authorized",
            "production_ranking_update_not_authorized",
        ],
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _reject_prohibited_language({"registry_entry": registry})
    return registry


def build_v1_5_incremental_valuation_evidence_report(
    pit_validation_report: Mapping[str, Any],
    valuation_manifest: Mapping[str, Any],
    quality_manifest: Mapping[str, Any],
    investment_manifest: Mapping[str, Any],
    sector_report: Mapping[str, Any],
    *,
    technical_ml_artifacts: Mapping[str, Any] | None,
    technical_ml_valuation_artifacts: Mapping[str, Any] | None,
    valuation_run_id: str,
    created_at: str = DEFAULT_CREATED_AT,
) -> dict[str, Any]:
    feature_count = (
        int(valuation_manifest["row_count"])
        + int(quality_manifest["row_count"])
        + int(investment_manifest["row_count"])
    )
    can_compare = feature_count > 0 and technical_ml_artifacts is not None and technical_ml_valuation_artifacts is not None
    report = {
        "report_version": INCREMENTAL_REPORT_VERSION,
        "valuation_run_id": valuation_run_id,
        "created_at": created_at,
        "comparison_status": "ready_for_manual_review" if can_compare else "pending_data",
        "comparison_policy": "technical plus ML evidence versus technical plus ML plus valuation-quality diagnostics",
        "allowed_comparison_dimensions": [
            "false_positive_reduction_diagnostic",
            "risk_adjusted_evidence_comparison",
            "coverage_change",
            "data_quality_limitations",
            "sector_relative_diagnostic_usefulness",
            "pending_data_status",
        ],
        "technical_ml_ref": "provided" if technical_ml_artifacts is not None else "missing",
        "technical_ml_plus_valuation_ref": "provided" if technical_ml_valuation_artifacts is not None else "missing",
        "feature_row_count": feature_count,
        "coverage_status": pit_validation_report["coverage_status"],
        "sector_relative_available_count": sum(
            1 for row in sector_report["sector_relative_rows"] if row["sector_relative_status"] == "available"
        ),
        "pending_reason": None if can_compare else "requires PIT feature rows and paired comparison artifacts",
        "skipped_reason": None if can_compare else "requires PIT feature rows and paired comparison artifacts",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _reject_prohibited_language({"incremental": report})
    return report


def build_v1_5_manual_review_valuation_section(
    pit_validation_report: Mapping[str, Any],
    valuation_manifest: Mapping[str, Any],
    quality_manifest: Mapping[str, Any],
    investment_manifest: Mapping[str, Any],
    sector_report: Mapping[str, Any],
    incremental_report: Mapping[str, Any],
    registry_entry: Mapping[str, Any],
    *,
    valuation_run_id: str,
    created_at: str = DEFAULT_CREATED_AT,
) -> dict[str, Any]:
    section = {
        "section_version": MANUAL_REVIEW_VERSION,
        "valuation_run_id": valuation_run_id,
        "created_at": created_at,
        "valuation_layer_status": registry_entry["layer_status"],
        "quality_profitability_layer_status": quality_manifest["manifest_status"],
        "investment_feature_status": investment_manifest["manifest_status"],
        "pit_validation_status": pit_validation_report["coverage_status"],
        "coverage_summary": {
            "candidate_count": pit_validation_report["candidate_count"],
            "covered_candidate_count": pit_validation_report["covered_candidate_count"],
            "coverage_ratio": pit_validation_report["coverage_ratio"],
            "coverage_gap_summary": list(pit_validation_report["coverage_gap_summary"]),
        },
        "sector_relative_summary": {
            "raw_feature_count": len(sector_report["raw_feature_rows"]),
            "sector_relative_available_count": sum(
                1 for row in sector_report["sector_relative_rows"] if row["sector_relative_status"] == "available"
            ),
            "pending_sector_data_count": sector_report["pending_sector_data_count"],
            "insufficient_sector_data_count": sector_report["insufficient_sector_data_count"],
        },
        "incremental_evidence_summary": {
            "comparison_status": incremental_report["comparison_status"],
            "pending_reason": incremental_report["pending_reason"],
            "skipped_reason": incremental_report["skipped_reason"],
        },
        "data_quality_flags": sorted(
            {
                flag
                for row in pit_validation_report["candidate_fundamental_rows"]
                for flag in row.get("data_quality_flags", [])
            }
        ),
        "coverage_gaps": list(pit_validation_report["coverage_gap_summary"]),
        "limitations": _manual_review_limitations(
            pit_validation_report,
            valuation_manifest,
            quality_manifest,
            investment_manifest,
            incremental_report,
        ),
        "required_human_checks": [
            "confirm_source_ref_and_availability_date_before_interpreting_fundamentals",
            "confirm_restated_values_do_not_leak_before_evaluation_date",
            "confirm_raw_and_sector_relative_values_are_reviewed_separately",
            "confirm_v1_5_layer_is_candidate_only_or_diagnostic_only",
            "confirm_incremental_comparison_is_manual_review_support_only",
        ],
        "manual_review_required": True,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _reject_prohibited_language({"manual_review": section})
    return section


def build_v1_5_validation_manifest(
    pit_validation_report: Mapping[str, Any],
    registry_entry: Mapping[str, Any],
    *,
    valuation_run_id: str,
    created_at: str = DEFAULT_CREATED_AT,
) -> dict[str, Any]:
    manifest = {
        "validation_manifest_version": VALIDATION_MANIFEST_VERSION,
        "valuation_run_id": valuation_run_id,
        "created_at": created_at,
        "pit_validation_report_ref": "v1_5_pit_validation_report",
        "layer_registry_entry_ref": registry_entry["layer_id"],
        "guardrail_status": "pass",
        "coverage_status": pit_validation_report["coverage_status"],
        "tests_required": [
            "PIT availability alignment",
            "missing availability metadata",
            "stale or restated data handling",
            "feature allowlist and pending-data features",
            "sector-relative separation",
            "ManualReviewPacket-compatible valuation section",
            "LayerRegistry status",
            "guardrail wording checks",
        ],
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _reject_prohibited_language({"validation_manifest": manifest})
    return manifest


def build_v1_5_completion_report(
    pit_validation_report: Mapping[str, Any],
    valuation_manifest: Mapping[str, Any],
    quality_manifest: Mapping[str, Any],
    investment_manifest: Mapping[str, Any],
    sector_report: Mapping[str, Any],
    incremental_report: Mapping[str, Any],
    validation_manifest: Mapping[str, Any],
    *,
    valuation_run_id: str,
    created_at: str = DEFAULT_CREATED_AT,
) -> dict[str, Any]:
    has_fixture_features = any(
        int(manifest["row_count"]) > 0
        for manifest in (valuation_manifest, quality_manifest, investment_manifest)
    )
    if pit_validation_report["coverage_status"] == "sufficient" and has_fixture_features:
        verdict = "COMPLETE"
    else:
        verdict = "LIMITED COMPLETE"
    report = {
        "completion_report_version": COMPLETION_REPORT_VERSION,
        "valuation_run_id": valuation_run_id,
        "created_at": created_at,
        "stage": "v1.5 valuation quality profitability layer",
        "completion_verdict": verdict,
        "data_status": {
            "pit_fundamentals_availability": pit_validation_report["coverage_status"],
            "coverage_gap_summary": list(pit_validation_report["coverage_gap_summary"]),
            "real_data_status": "not_verified_by_v1_5_contract_runner",
        },
        "minimum_data_handoff_request": _minimum_data_handoff_request(),
        "artifact_keys": [
            "v1_5_fundamental_data_contract",
            "v1_5_pit_validation_report",
            "v1_5_valuation_feature_manifest",
            "v1_5_quality_profitability_feature_manifest",
            "v1_5_investment_feature_manifest",
            "v1_5_sector_relative_valuation_report",
            "v1_5_incremental_valuation_evidence_report",
            "v1_5_manual_review_valuation_section",
            "v1_5_validation_manifest",
        ],
        "pending_or_deferred_items": sorted(
            set(pit_validation_report["coverage_gap_summary"])
            | {item["feature_name"] for item in valuation_manifest["unsupported_features"]}
            | {item["feature_name"] for item in quality_manifest["unsupported_features"]}
            | {item["feature_name"] for item in investment_manifest["unsupported_features"]}
            | ({"incremental_comparison_pending_data"} if incremental_report["comparison_status"] == "pending_data" else set())
            | ({"sector_relative_pending_data"} if sector_report["pending_sector_data_count"] else set())
        ),
        "skipped_or_blocked_items": sorted(
            set(pit_validation_report["coverage_gap_summary"])
            | {item["feature_name"] for item in valuation_manifest["unsupported_features"]}
            | {item["feature_name"] for item in quality_manifest["unsupported_features"]}
            | {item["feature_name"] for item in investment_manifest["unsupported_features"]}
            | ({"incremental_comparison_pending_data"} if incremental_report["comparison_status"] == "pending_data" else set())
            | ({"sector_relative_pending_data"} if sector_report["pending_sector_data_count"] else set())
        ),
        "validation_ref": validation_manifest["validation_manifest_version"],
        "next_stage_recommendation": "v1.6 can start after v1.5 LIMITED COMPLETE is accepted with PIT data limitations visible",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _reject_prohibited_language({"completion": report})
    return report


def validate_v1_5_valuation_quality_artifacts(artifacts: Mapping[str, Any]) -> None:
    required = {
        "v1_5_fundamental_data_contract",
        "v1_5_pit_validation_report",
        "v1_5_valuation_feature_manifest",
        "v1_5_quality_profitability_feature_manifest",
        "v1_5_investment_feature_manifest",
        "v1_5_sector_relative_valuation_report",
        "v1_5_layer_registry_entry",
        "v1_5_incremental_valuation_evidence_report",
        "v1_5_manual_review_valuation_section",
        "v1_5_validation_manifest",
        "v1_5_completion_report",
    }
    missing = sorted(required.difference(artifacts))
    if missing:
        raise ValueError(f"v1.5 valuation artifacts missing: {', '.join(missing)}")
    if artifacts["v1_5_layer_registry_entry"]["layer_status"] not in {"candidate_only", "diagnostic_only"}:
        raise ValueError("v1.5 layer status must be candidate_only or diagnostic_only")
    for key in (
        "v1_5_valuation_feature_manifest",
        "v1_5_quality_profitability_feature_manifest",
        "v1_5_investment_feature_manifest",
    ):
        _validate_feature_manifest(artifacts[key])
    for section in artifacts.values():
        _validate_blocked_flags(section)
    _reject_prohibited_language({"artifacts": artifacts})


def make_v1_5_valuation_run_id(
    evidences: Sequence[Mapping[str, Any]],
    fundamental_records: Sequence[Mapping[str, Any]],
    config: ValuationQualityLayerConfig,
) -> str:
    payload = {
        "version": RUNNER_VERSION,
        "evidence_refs": [
            {
                "candidate_id": evidence["candidate_id"],
                "evidence_id": evidence["evidence_id"],
                "date_range": evidence["date_range"],
            }
            for evidence in evidences
        ],
        "fundamental_records": sorted(
            [dict(record) for record in fundamental_records],
            key=lambda item: (
                str(item.get("candidate_id")),
                _normalize_field_name(item.get("field_name") or item.get("metric")),
            ),
        ),
        "config": config.__dict__,
    }
    digest = sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"v1_5_valuation_{digest}"


def _build_feature_manifest(
    pit_validation_report: Mapping[str, Any],
    *,
    manifest_version: str,
    manifest_key: str,
    family: str,
    feature_specs: Mapping[str, Mapping[str, Any]],
    unsupported_features: Sequence[Mapping[str, str]],
    valuation_run_id: str,
    created_at: str,
) -> dict[str, Any]:
    valid_by_candidate = _valid_fundamental_rows_by_candidate(pit_validation_report)
    all_candidate_ids = sorted(
        {row["candidate_id"] for row in pit_validation_report["candidate_fundamental_rows"]}
    )
    rows = []
    for candidate_id in all_candidate_ids:
        source_rows = valid_by_candidate.get(candidate_id, {})
        raw_features: dict[str, float] = {}
        feature_source_refs: dict[str, str] = {}
        for feature_name, spec in feature_specs.items():
            value = _feature_value_from_spec(source_rows, spec)
            if value is None:
                continue
            raw_features[feature_name] = value
            feature_source_refs[feature_name] = source_rows[str(spec["source_field"])]["source_ref"]
        evidence_id = _first_row_value(pit_validation_report, candidate_id, "evidence_id")
        sector_id = _first_row_value(pit_validation_report, candidate_id, "sector_id")
        rows.append(
            {
                "candidate_id": candidate_id,
                "evidence_id": evidence_id,
                "observation_end": _first_row_value(pit_validation_report, candidate_id, "evaluation_date"),
                "sector_id": sector_id,
                "raw_features": raw_features,
                "feature_source_refs": feature_source_refs,
                "feature_status": "available" if raw_features else "pending_data",
                "reason_codes": ["pit_features_available"] if raw_features else [f"{family}_feature_data_missing"],
            }
        )
    available_rows = [row for row in rows if row["raw_features"]]
    manifest = {
        "manifest_version": manifest_version,
        "manifest_key": manifest_key,
        "valuation_run_id": valuation_run_id,
        "created_at": created_at,
        "feature_family": family,
        "feature_allowlist": list(feature_specs),
        "forbidden_feature_names": sorted(FORBIDDEN_FEATURE_NAMES),
        "row_count": len(available_rows),
        "rows": rows,
        "unsupported_features": [dict(item) for item in unsupported_features],
        "manifest_status": "available" if available_rows else "pending_data",
        "label_separation_status": f"{family}_features_do_not_include_label_or_return_fields",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _validate_feature_manifest(manifest)
    _reject_prohibited_language({manifest_key: manifest})
    return manifest


def _pit_validation_row(
    evidence: Mapping[str, Any],
    record: Mapping[str, Any],
    config: ValuationQualityLayerConfig,
) -> dict[str, Any]:
    candidate_id = str(evidence["candidate_id"])
    evidence_id = str(evidence["evidence_id"])
    evaluation_date = str(record.get("evaluation_date") or evidence["date_range"]["end"])
    field_name = _normalize_field_name(record.get("field_name") or record.get("metric"))
    reasons: list[str] = []
    missing = _missing_fundamental_fields(record, evaluation_date=evaluation_date)
    reasons.extend(f"{field}_missing" for field in missing)
    if str(record.get("evidence_id") or "") != evidence_id:
        reasons.append("evidence_id_mismatch")
    availability_date = _date_text(record, ("availability_date", "available_at", "available_date", "as_of_date"))
    filing_date = _date_text(record, ("filing_date", "disclosure_date"))
    report_period_end = _date_text(record, ("report_period_end_date", "period_end_date"))
    try:
        evaluation_dt = _parse_date(evaluation_date)
        availability_dt = _parse_date(availability_date) if availability_date else None
        filing_dt = _parse_date(filing_date) if filing_date else None
        report_end_dt = _parse_date(report_period_end) if report_period_end else None
    except ValueError as exc:
        reasons.append(str(exc))
        evaluation_dt = _parse_date(str(evidence["date_range"]["end"]))
        availability_dt = None
        filing_dt = None
        report_end_dt = None
    if availability_dt and availability_dt > evaluation_dt:
        reasons.append("fundamental_available_after_evaluation_date")
    if filing_dt and filing_dt > evaluation_dt:
        reasons.append("filing_or_disclosure_after_evaluation_date")
    if filing_dt and availability_dt:
        lag_days = (availability_dt - filing_dt).days
        if lag_days < 0:
            reasons.append("availability_before_filing_or_disclosure")
        elif lag_days > config.max_reporting_lag_days:
            reasons.append("reporting_lag_policy_violation")
    if availability_dt:
        stale_days = (evaluation_dt - availability_dt).days
        if stale_days > config.max_stale_age_days:
            reasons.append("stale_data_policy_violation")
    if report_end_dt and report_end_dt > evaluation_dt:
        reasons.append("report_period_after_evaluation_date")
    flags = _quality_flags(record.get("data_quality_flags") or record.get("quality_flags"))
    unsafe_flags = sorted(set(flags).intersection(UNSAFE_QUALITY_FLAGS))
    reasons.extend(f"{flag}_quality_flag" for flag in unsafe_flags)
    restatement_status = str(record.get("restatement_policy") or record.get("restatement_policy_status") or "").strip()
    restatement_available_at = _date_text(record, ("restatement_available_at",))
    if restatement_status in {"restated_after_evaluation", "unverified_restatement"}:
        reasons.append("restatement_policy_unverified")
    if restatement_available_at:
        try:
            if _parse_date(restatement_available_at) > evaluation_dt:
                reasons.append("restatement_available_after_evaluation_date")
        except ValueError as exc:
            reasons.append(str(exc))
    try:
        value = _optional_float(record.get("value", record.get("metric_value")))
    except ValueError as exc:
        reasons.append(str(exc))
        value = None
    if value is None:
        reasons.append("value_not_numeric")
    status = "pass" if not reasons else "pending_data"
    coverage_status = "available" if status == "pass" else "pending_data"
    return {
        "candidate_id": candidate_id,
        "evidence_id": evidence_id,
        "ticker": str(record.get("ticker") or record.get("symbol") or ""),
        "evaluation_date": evaluation_date,
        "fiscal_period": str(record.get("fiscal_period") or record.get("period") or ""),
        "report_period_end_date": report_period_end,
        "filing_date": filing_date,
        "availability_date": availability_date,
        "source_ref": _source_ref(record),
        "field_name": field_name,
        "value": value,
        "unit": str(record.get("unit") or record.get("metric_unit") or ""),
        "currency": str(record.get("currency") or ""),
        "sector_id": str(record.get("sector_id") or record.get("sector") or ""),
        "industry_id": str(record.get("industry_id") or ""),
        "pit_status": status,
        "coverage_status": coverage_status,
        "data_quality_flags": list(flags),
        "blocked_reason": ";".join(reasons) if reasons else None,
        "pending_reason": ";".join(reasons) if reasons else None,
        "reason_codes": reasons or ["pit_fundamental_available"],
    }


def _missing_candidate_validation_row(evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(evidence["candidate_id"]),
        "evidence_id": str(evidence["evidence_id"]),
        "ticker": "",
        "evaluation_date": str(evidence["date_range"]["end"]),
        "fiscal_period": "",
        "report_period_end_date": None,
        "filing_date": None,
        "availability_date": None,
        "source_ref": None,
        "field_name": None,
        "value": None,
        "unit": "",
        "currency": "",
        "sector_id": "",
        "industry_id": "",
        "pit_status": "pending_data",
        "coverage_status": "pending_data",
        "data_quality_flags": [],
        "blocked_reason": "fundamental_record_missing",
        "pending_reason": "fundamental_record_missing",
        "reason_codes": ["fundamental_record_missing"],
    }


def _records_by_candidate_field(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Mapping[str, Any]]]:
    indexed: dict[str, dict[str, Mapping[str, Any]]] = {}
    for record in records:
        candidate_id = str(record.get("candidate_id") or "").strip()
        if not candidate_id:
            raise ValueError("v1.5 fundamental record requires candidate_id")
        field_name = _normalize_field_name(record.get("field_name") or record.get("metric"))
        if not field_name:
            raise ValueError("v1.5 fundamental record requires field_name or metric")
        candidate_records = indexed.setdefault(candidate_id, {})
        if field_name in candidate_records:
            raise ValueError(f"v1.5 fundamental record duplicate candidate_id/field_name: {candidate_id}/{field_name}")
        candidate_records[field_name] = dict(record)
    return indexed


def _missing_fundamental_fields(record: Mapping[str, Any], *, evaluation_date: str) -> list[str]:
    checks = {
        "ticker": record.get("ticker") or record.get("symbol"),
        "evaluation_date": evaluation_date,
        "fiscal_period": record.get("fiscal_period") or record.get("period"),
        "report_period_end_date": record.get("report_period_end_date") or record.get("period_end_date"),
        "filing_date_or_disclosure_date": record.get("filing_date") or record.get("disclosure_date"),
        "availability_date": _date_text(record, ("availability_date", "available_at", "available_date", "as_of_date")),
        "source_ref": _source_ref(record),
        "field_name": record.get("field_name") or record.get("metric"),
        "unit": record.get("unit") or record.get("metric_unit"),
    }
    if record.get("value", record.get("metric_value")) is None:
        checks["value"] = None
    return [field for field, value in checks.items() if _is_missing(value)]


def _valuation_feature_specs() -> dict[str, dict[str, Any]]:
    return {
        "price_to_book": {"source_field": "price_to_book", "transform": "identity"},
        "book_to_price": {"source_field": "price_to_book", "transform": "inverse"},
        "price_to_earnings": {"source_field": "price_to_earnings", "transform": "identity"},
        "earnings_to_price": {"source_field": "price_to_earnings", "transform": "inverse"},
        "price_to_sales": {"source_field": "price_to_sales", "transform": "identity"},
        "sales_to_price": {"source_field": "price_to_sales", "transform": "inverse"},
        "dividend_yield": {"source_field": "dividend_yield", "transform": "identity"},
    }


def _quality_feature_specs() -> dict[str, dict[str, Any]]:
    return {
        "roe": {"source_field": "roe", "transform": "identity"},
        "roa": {"source_field": "roa", "transform": "identity"},
        "gross_profitability_assets": {"source_field": "gross_profitability_assets", "transform": "identity"},
        "operating_margin": {"source_field": "operating_margin", "transform": "identity"},
        "net_margin": {"source_field": "net_margin", "transform": "identity"},
        "debt_ratio": {"source_field": "debt_ratio", "transform": "identity"},
        "interest_coverage": {"source_field": "interest_coverage", "transform": "identity"},
        "cash_flow_quality": {"source_field": "cash_flow_quality", "transform": "identity"},
        "earnings_stability": {"source_field": "earnings_stability", "transform": "identity"},
    }


def _investment_feature_specs() -> dict[str, dict[str, Any]]:
    return {
        "asset_growth": {"source_field": "asset_growth", "transform": "identity"},
        "capex_intensity": {"source_field": "capex_intensity", "transform": "identity"},
        "accruals_proxy": {"source_field": "accruals_proxy", "transform": "identity"},
        "share_issuance_dilution_proxy": {"source_field": "share_issuance_dilution_proxy", "transform": "identity"},
        "inventory_growth": {"source_field": "inventory_growth", "transform": "identity"},
    }


def _unsupported_valuation_features() -> list[dict[str, str]]:
    return [
        {
            "feature_name": "free_cash_flow_yield",
            "status": "pending_data",
            "reason": "requires PIT free cash flow and market capitalization fields",
        },
        {
            "feature_name": "enterprise_value_based_features",
            "status": "pending_data",
            "reason": "requires PIT enterprise value components",
        },
    ]


def _unsupported_quality_features() -> list[dict[str, str]]:
    return [
        {
            "feature_name": "advanced_cash_conversion_quality",
            "status": "pending_data",
            "reason": "requires PIT multi-statement cash flow and accrual inputs",
        }
    ]


def _unsupported_investment_features() -> list[dict[str, str]]:
    return [
        {
            "feature_name": "internally_derived_multi_period_investment_features",
            "status": "pending_data",
            "reason": "v1.5 accepts precomputed PIT rows but does not infer multi-period investment diagnostics from incomplete fundamentals",
        }
    ]


def _valid_fundamental_rows_by_candidate(
    pit_validation_report: Mapping[str, Any],
) -> dict[str, dict[str, Mapping[str, Any]]]:
    result: dict[str, dict[str, Mapping[str, Any]]] = {}
    for row in pit_validation_report["candidate_fundamental_rows"]:
        if row["pit_status"] != "pass" or not row.get("field_name"):
            continue
        result.setdefault(str(row["candidate_id"]), {})[str(row["field_name"])] = row
    return result


def _feature_value_from_spec(
    source_rows: Mapping[str, Mapping[str, Any]],
    spec: Mapping[str, Any],
) -> float | None:
    source_field = str(spec["source_field"])
    row = source_rows.get(source_field)
    if row is None:
        return None
    value = _optional_float(row.get("value"))
    if value is None:
        return None
    if spec.get("transform") == "inverse":
        if value == 0.0:
            return None
        return round(1.0 / value, 8)
    return round(value, 8)


def _first_row_value(
    pit_validation_report: Mapping[str, Any],
    candidate_id: str,
    field_name: str,
) -> Any:
    for row in pit_validation_report["candidate_fundamental_rows"]:
        if str(row["candidate_id"]) == candidate_id:
            return row.get(field_name)
    return None


def _manual_review_limitations(
    pit_validation_report: Mapping[str, Any],
    valuation_manifest: Mapping[str, Any],
    quality_manifest: Mapping[str, Any],
    investment_manifest: Mapping[str, Any],
    incremental_report: Mapping[str, Any],
) -> list[str]:
    limitations = set(pit_validation_report["coverage_gap_summary"])
    for manifest in (valuation_manifest, quality_manifest, investment_manifest):
        if manifest["manifest_status"] != "available":
            limitations.add(f"{manifest['feature_family']}_features_pending_data")
    if incremental_report["comparison_status"] == "pending_data":
        limitations.add("incremental_evidence_comparison_pending_data")
    return sorted(limitations or {"none"})


def _minimum_data_handoff_request() -> list[str]:
    return [
        "candidate_id/evidence_id/ticker/evaluation_date for each EvaluationEvidenceV1 candidate",
        "fiscal_period/report_period_end_date/filing_date_or_disclosure_date/availability_date",
        "source_ref proving when the fundamental value became available",
        "numeric field_name/value/unit/currency rows for PIT valuation, quality, profitability, and investment diagnostics",
        "sector_id/industry_id plus enough same-sector peer rows for sector-relative diagnostics",
        "restatement_policy/stale_data_policy/reporting_lag_policy/data_quality_flags",
        "paired technical_ml and technical_ml_plus_valuation comparison artifacts for incremental evidence",
    ]


def _normalize_field_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return FIELD_ALIASES.get(text, text)


def _date_text(record: Mapping[str, Any], field_names: Sequence[str]) -> str:
    for field_name in field_names:
        value = record.get(field_name)
        if not _is_missing(value):
            return str(value)
    return ""


def _source_ref(record: Mapping[str, Any]) -> str | None:
    for field_name in ("source_ref", "source_report_id", "disclosure_id", "source", "source_vendor"):
        value = record.get(field_name)
        if not _is_missing(value):
            return str(value)
    return None


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"v1.5 fundamental date must be ISO YYYY-MM-DD: {value}") from exc


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("v1.5 fundamental value must be numeric") from exc
    if not isfinite(result):
        raise ValueError("v1.5 fundamental value must be finite")
    return result


def _quality_flags(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        raw_flags = value.split(",") if "," in value else value.split("|")
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        raw_flags = [str(flag) for flag in value]
    else:
        raw_flags = [str(value)]
    return tuple(dict.fromkeys(flag.strip() for flag in raw_flags if flag and flag.strip()))


def _is_missing(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _validate_feature_manifest(manifest: Mapping[str, Any]) -> None:
    feature_allowlist = set(manifest["feature_allowlist"])
    forbidden_allowlist = feature_allowlist.intersection(FORBIDDEN_FEATURE_NAMES)
    if forbidden_allowlist:
        raise ValueError(f"v1.5 feature allowlist includes forbidden features: {sorted(forbidden_allowlist)}")
    for row in manifest["rows"]:
        feature_names = set(row["raw_features"])
        forbidden = feature_names.intersection(FORBIDDEN_FEATURE_NAMES)
        if forbidden:
            raise ValueError(f"v1.5 feature manifest includes forbidden features: {sorted(forbidden)}")
        if not feature_names.issubset(feature_allowlist):
            raise ValueError("v1.5 feature manifest contains non-allowlisted features")


def _blocked_flags() -> dict[str, bool]:
    return {flag: False for flag in PROHIBITED_FLAGS}


def _validate_blocked_flags(section: Mapping[str, Any]) -> None:
    for flag in PROHIBITED_FLAGS:
        if bool(section.get(flag)):
            raise ValueError(f"v1.5 blocked flag must remain false: {flag}")


def _reject_prohibited_language(payload: Mapping[str, Any]) -> None:
    allowed_fields = {
        "prohibited_actions_notice",
        "evidence_only_notice",
        "forbidden_feature_names",
        "allowed_comparison_dimensions",
    }
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
        r"\bfuture[-_ ]return\b",
        r"\bexpected[-_ ]return\b",
        r"\bpredicted[-_ ]return\b",
        r"\bproven[-_ ]alpha\b",
        r"\bproduction ranking replacement\b",
    )
    for pattern in blocked_patterns:
        if re.search(pattern, text):
            raise ValueError(f"v1.5 valuation artifacts contain prohibited language: {pattern}")


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
    "DATA_CONTRACT_VERSION",
    "PIT_VALIDATION_VERSION",
    "RUNNER_VERSION",
    "ValuationQualityLayerConfig",
    "build_v1_5_fundamental_data_contract",
    "build_v1_5_incremental_valuation_evidence_report",
    "build_v1_5_investment_feature_manifest",
    "build_v1_5_layer_registry_entry",
    "build_v1_5_manual_review_valuation_section",
    "build_v1_5_pit_validation_report",
    "build_v1_5_quality_profitability_feature_manifest",
    "build_v1_5_sector_relative_valuation_report",
    "build_v1_5_validation_manifest",
    "build_v1_5_valuation_feature_manifest",
    "make_v1_5_valuation_run_id",
    "run_v1_5_valuation_quality_layer",
    "validate_v1_5_valuation_quality_artifacts",
)
