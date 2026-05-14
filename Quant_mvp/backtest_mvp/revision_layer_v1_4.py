"""v1.4 point-in-time revision layer skeleton.

This module defines the v1.4 revision data contract and fail-closed artifact
builders. Outputs are candidate-only manual-review support and do not activate
valuation/fundamental scoring, production ranking, or execution behavior.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from typing import Any
import json
import re

from Quant_mvp.backtest_mvp.evaluation_evidence_v1 import validate_evaluation_evidence_v1


RUNNER_VERSION = "v1_4_revision_layer_skeleton_v1_0"
DATA_CONTRACT_VERSION = "v1_4_revision_data_contract_v1_0"
COVERAGE_REPORT_VERSION = "v1_4_revision_coverage_report_v1_0"
FEATURE_MANIFEST_VERSION = "v1_4_revision_feature_manifest_v1_0"
LAYER_REGISTRY_VERSION = "v1_4_revision_layer_registry_entry_v1_0"
INCREMENTAL_REPORT_VERSION = "v1_4_incremental_revision_evidence_report_v1_0"
MANUAL_REVIEW_VERSION = "v1_4_revision_manual_review_section_v1_0"
DEFAULT_CREATED_AT = "2026-05-14T00:00:00+00:00"
EVIDENCE_ONLY_NOTICE = (
    "v1.4 revision outputs are point-in-time candidate-only manual-review support"
)
PROHIBITED_ACTIONS_NOTICE = (
    "prohibited actions include live trading, brokerage integration, order generation, "
    "buy/sell/hold recommendations, trade-signal framing, automatic rebalance "
    "instructions, production ranking replacement, valuation/fundamental active "
    "scoring, and performance certainty claims"
)
PROHIBITED_FLAGS = (
    "live_execution_enabled",
    "brokerage_integration_enabled",
    "order_generation_enabled",
    "user_facing_auto_rebalance_instruction_enabled",
    "production_ranking_update_enabled",
    "valuation_fundamental_active_scoring_enabled",
)
REQUIRED_REVISION_FIELDS = (
    "candidate_id",
    "evidence_id",
    "revision_source_ref",
    "estimate_as_of_date",
    "available_at",
    "fiscal_period",
    "sector_id",
    "eps_estimate_current",
    "eps_estimate_1m_ago",
    "eps_estimate_3m_ago",
    "analyst_revision_up_count_1m",
    "analyst_revision_down_count_1m",
    "sector_revision_percentile",
)
REVISION_FEATURE_ALLOWLIST = (
    "eps_revision_change_1m",
    "eps_revision_change_3m",
    "revision_diffusion_1m",
    "sector_relative_revision_percentile",
)
FORBIDDEN_REVISION_FEATURE_NAMES = frozenset(
    {
        "raw_label",
        "label",
        "target",
        "future_return",
        "expected_return",
        "predicted_return",
        "actual_eps",
        "reported_eps",
        "post_evaluation_consensus",
        "technical_composite_score",
        "final_composite_score",
        "production_score",
    }
)


@dataclass(frozen=True)
class RevisionLayerConfig:
    """Config for the v1.4 point-in-time revision skeleton."""

    revision_run_id: str | None = None
    created_at: str = DEFAULT_CREATED_AT
    min_candidate_coverage_ratio: float = 0.8
    layer_status_when_covered: str = "candidate_only"
    layer_status_when_uncovered: str = "diagnostic_only"
    config_ref: str = "Quant_mvp/backtest_mvp/revision_layer_v1_4.py"


def run_v1_4_revision_layer(
    evaluation_evidences: Sequence[Mapping[str, Any]],
    *,
    revision_records: Sequence[Mapping[str, Any]] | None = None,
    technical_only_artifacts: Mapping[str, Any] | None = None,
    technical_revision_artifacts: Mapping[str, Any] | None = None,
    config: RevisionLayerConfig | None = None,
) -> dict[str, Any]:
    """Build v1.4 revision skeleton artifacts from PIT revision handoff rows."""

    cfg = config or RevisionLayerConfig()
    if not evaluation_evidences:
        raise ValueError("v1.4 revision layer requires EvaluationEvidenceV1 records")
    evidences = [dict(evidence) for evidence in evaluation_evidences]
    for evidence in evidences:
        validate_evaluation_evidence_v1(evidence)
    evidences.sort(key=lambda item: (str(item["date_range"].get("end")), str(item["candidate_id"])))

    records = [dict(record) for record in (revision_records or [])]
    revision_run_id = cfg.revision_run_id or make_v1_4_revision_run_id(evidences, records, cfg)
    contract = build_v1_4_revision_data_contract(revision_run_id=revision_run_id, config=cfg)
    coverage = build_v1_4_revision_coverage_report(
        evidences,
        records,
        revision_run_id=revision_run_id,
        config=cfg,
    )
    feature_manifest = build_v1_4_revision_feature_manifest(
        coverage,
        revision_run_id=revision_run_id,
        created_at=cfg.created_at,
    )
    registry = build_v1_4_revision_layer_registry_entry(
        coverage,
        feature_manifest,
        revision_run_id=revision_run_id,
        config=cfg,
    )
    incremental = build_v1_4_incremental_revision_evidence_report(
        coverage,
        feature_manifest,
        technical_only_artifacts=technical_only_artifacts,
        technical_revision_artifacts=technical_revision_artifacts,
        revision_run_id=revision_run_id,
        created_at=cfg.created_at,
    )
    manual_review = build_v1_4_revision_manual_review_section(
        coverage,
        registry,
        incremental,
        revision_run_id=revision_run_id,
        created_at=cfg.created_at,
    )
    artifacts = {
        "v1_4_revision_data_contract": contract,
        "v1_4_revision_coverage_report": coverage,
        "v1_4_revision_feature_manifest": feature_manifest,
        "v1_4_revision_layer_registry_entry": registry,
        "v1_4_incremental_revision_evidence_report": incremental,
        "v1_4_revision_manual_review_section": manual_review,
    }
    validate_v1_4_revision_artifacts(artifacts)
    return artifacts


def build_v1_4_revision_data_contract(
    *,
    revision_run_id: str,
    config: RevisionLayerConfig | None = None,
) -> dict[str, Any]:
    cfg = config or RevisionLayerConfig(revision_run_id=revision_run_id)
    contract = {
        "contract_version": DATA_CONTRACT_VERSION,
        "revision_run_id": revision_run_id,
        "created_at": cfg.created_at,
        "required_fields": list(REQUIRED_REVISION_FIELDS),
        "required_field_descriptions": {
            "candidate_id": "must exactly match EvaluationEvidenceV1 candidate_id",
            "evidence_id": "must exactly match EvaluationEvidenceV1 evidence_id",
            "revision_source_ref": "source, extraction batch, vendor or approved local snapshot reference",
            "estimate_as_of_date": "consensus estimate date represented by the row",
            "available_at": "date the row was available for the evaluation date",
            "fiscal_period": "fiscal period for the EPS estimate",
            "sector_id": "sector bucket used for relative revision comparison",
            "eps_estimate_current": "PIT EPS consensus or estimate value available at available_at",
            "eps_estimate_1m_ago": "PIT comparable EPS estimate approximately one month earlier",
            "eps_estimate_3m_ago": "PIT comparable EPS estimate approximately three months earlier",
            "analyst_revision_up_count_1m": "analyst upward revision count in the one-month window",
            "analyst_revision_down_count_1m": "analyst downward revision count in the one-month window",
            "sector_revision_percentile": "sector-relative revision percentile from approved PIT input",
        },
        "pit_policy": "available_at must be on or before the EvaluationEvidenceV1 date_range.end",
        "feature_allowlist": list(REVISION_FEATURE_ALLOWLIST),
        "forbidden_feature_names": sorted(FORBIDDEN_REVISION_FEATURE_NAMES),
        "layer_status_policy": "candidate_only when PIT coverage is sufficient; diagnostic_only otherwise; never active",
        "needed_data": _needed_revision_data(),
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _reject_prohibited_language({"contract": contract})
    return contract


def build_v1_4_revision_coverage_report(
    evaluation_evidences: Sequence[Mapping[str, Any]],
    revision_records: Sequence[Mapping[str, Any]],
    *,
    revision_run_id: str,
    config: RevisionLayerConfig | None = None,
) -> dict[str, Any]:
    cfg = config or RevisionLayerConfig(revision_run_id=revision_run_id)
    by_candidate = _revision_by_candidate(revision_records)
    unmatched = sorted(set(by_candidate).difference(str(evidence["candidate_id"]) for evidence in evaluation_evidences))
    rows = []
    for evidence in evaluation_evidences:
        rows.append(_coverage_row(evidence, by_candidate.get(str(evidence["candidate_id"]))))
    pit_pass_count = sum(1 for row in rows if row["pit_status"] == "pass")
    coverage_ratio = round(pit_pass_count / len(rows), 8) if rows else 0.0
    gap_summary = sorted(
        {
            reason
            for row in rows
            for reason in row["reason_codes"]
            if reason != "revision_pit_available"
        }
        | ({"candidate_id_mismatch"} if unmatched else set())
    )
    report = {
        "report_version": COVERAGE_REPORT_VERSION,
        "revision_run_id": revision_run_id,
        "created_at": cfg.created_at,
        "candidate_count": len(rows),
        "pit_pass_count": pit_pass_count,
        "coverage_ratio": coverage_ratio,
        "coverage_status": "sufficient" if coverage_ratio >= cfg.min_candidate_coverage_ratio else "insufficient",
        "candidate_revision_rows": rows,
        "unmatched_revision_record_candidate_ids": unmatched,
        "unmatched_revision_record_count": len(unmatched),
        "coverage_gap_summary": gap_summary,
        "pit_policy": "available_at must be on or before evaluation_end",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _reject_prohibited_language({"coverage": report})
    return report


def build_v1_4_revision_feature_manifest(
    coverage_report: Mapping[str, Any],
    *,
    revision_run_id: str,
    created_at: str = DEFAULT_CREATED_AT,
) -> dict[str, Any]:
    feature_rows = []
    for row in coverage_report["candidate_revision_rows"]:
        if row["pit_status"] == "pass":
            feature_rows.append(
                {
                    "candidate_id": row["candidate_id"],
                    "evidence_id": row["evidence_id"],
                    "observation_end": row["evaluation_end"],
                    "available_at": row["available_at"],
                    "features": {
                        "eps_revision_change_1m": row["eps_revision_change_1m"],
                        "eps_revision_change_3m": row["eps_revision_change_3m"],
                        "revision_diffusion_1m": row["revision_diffusion_1m"],
                        "sector_relative_revision_percentile": row["sector_revision_percentile"],
                    },
                    "feature_status": "allowlisted_pit_revision_features_only",
                }
            )
    manifest = {
        "manifest_version": FEATURE_MANIFEST_VERSION,
        "revision_run_id": revision_run_id,
        "created_at": created_at,
        "feature_allowlist": list(REVISION_FEATURE_ALLOWLIST),
        "forbidden_feature_names": sorted(FORBIDDEN_REVISION_FEATURE_NAMES),
        "row_count": len(feature_rows),
        "rows": feature_rows,
        "ml_integration_status": (
            "allowlisted_revision_features_ready_for_candidate_only_comparison"
            if feature_rows
            else "skipped_no_pit_revision_features"
        ),
        "label_separation_status": "revision_features_do_not_include_label_or_return_fields",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _validate_revision_feature_manifest(manifest)
    _reject_prohibited_language({"manifest": manifest})
    return manifest


def build_v1_4_revision_layer_registry_entry(
    coverage_report: Mapping[str, Any],
    feature_manifest: Mapping[str, Any],
    *,
    revision_run_id: str,
    config: RevisionLayerConfig | None = None,
) -> dict[str, Any]:
    cfg = config or RevisionLayerConfig(revision_run_id=revision_run_id)
    status = (
        cfg.layer_status_when_covered
        if coverage_report["coverage_status"] == "sufficient" and feature_manifest["row_count"] > 0
        else cfg.layer_status_when_uncovered
    )
    if status == "active":
        raise ValueError("v1.4 revision layer must not be active")
    registry = {
        "registry_version": LAYER_REGISTRY_VERSION,
        "revision_run_id": revision_run_id,
        "created_at": cfg.created_at,
        "layer_name": "point_in_time_revision_layer",
        "layer_status": status,
        "allowed_statuses": ["candidate_only", "diagnostic_only"],
        "coverage_ref": "v1_4_revision_coverage_report",
        "feature_manifest_ref": "v1_4_revision_feature_manifest",
        "blocked_activation_reasons": [
            "requires approved PIT revision source coverage",
            "requires incremental net evidence comparison before later-stage consideration",
            "valuation_fundamental_active_scoring_not_authorized",
        ],
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _reject_prohibited_language({"registry": registry})
    return registry


def build_v1_4_incremental_revision_evidence_report(
    coverage_report: Mapping[str, Any],
    feature_manifest: Mapping[str, Any],
    *,
    technical_only_artifacts: Mapping[str, Any] | None,
    technical_revision_artifacts: Mapping[str, Any] | None,
    revision_run_id: str,
    created_at: str = DEFAULT_CREATED_AT,
) -> dict[str, Any]:
    can_compare = bool(
        feature_manifest["row_count"]
        and technical_only_artifacts is not None
        and technical_revision_artifacts is not None
    )
    report = {
        "report_version": INCREMENTAL_REPORT_VERSION,
        "revision_run_id": revision_run_id,
        "created_at": created_at,
        "comparison_status": "ready_for_manual_review" if can_compare else "skipped",
        "comparison_policy": "technical-only versus technical-plus-revision net evidence comparison",
        "technical_only_ref": "provided" if technical_only_artifacts is not None else "missing",
        "technical_plus_revision_ref": "provided" if technical_revision_artifacts is not None else "missing",
        "revision_feature_row_count": feature_manifest["row_count"],
        "coverage_status": coverage_report["coverage_status"],
        "skipped_reason": None if can_compare else "requires PIT revision features and paired comparison artifacts",
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _reject_prohibited_language({"incremental": report})
    return report


def build_v1_4_revision_manual_review_section(
    coverage_report: Mapping[str, Any],
    registry_entry: Mapping[str, Any],
    incremental_report: Mapping[str, Any],
    *,
    revision_run_id: str,
    created_at: str = DEFAULT_CREATED_AT,
) -> dict[str, Any]:
    section = {
        "section_version": MANUAL_REVIEW_VERSION,
        "revision_run_id": revision_run_id,
        "created_at": created_at,
        "layer_status": registry_entry["layer_status"],
        "coverage_status": coverage_report["coverage_status"],
        "coverage_gap_summary": list(coverage_report["coverage_gap_summary"]),
        "incremental_comparison_status": incremental_report["comparison_status"],
        "manual_review_checklist": [
            "confirm_revision_source_ref_and_available_at_before_interpreting_features",
            "confirm_revision_features_are_allowlisted_and_label_separated",
            "confirm_revision_layer_status_is_candidate_only_or_diagnostic_only",
            "confirm_incremental_comparison_is_manual_review_support_only",
        ],
        "manual_review_required": True,
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        **_blocked_flags(),
    }
    _reject_prohibited_language({"manual_review": section})
    return section


def validate_v1_4_revision_artifacts(artifacts: Mapping[str, Any]) -> None:
    required = {
        "v1_4_revision_data_contract",
        "v1_4_revision_coverage_report",
        "v1_4_revision_feature_manifest",
        "v1_4_revision_layer_registry_entry",
        "v1_4_incremental_revision_evidence_report",
        "v1_4_revision_manual_review_section",
    }
    missing = sorted(required.difference(artifacts))
    if missing:
        raise ValueError(f"v1.4 revision artifacts missing: {', '.join(missing)}")
    registry = artifacts["v1_4_revision_layer_registry_entry"]
    if registry["layer_status"] not in {"candidate_only", "diagnostic_only"}:
        raise ValueError("v1.4 revision layer status must be candidate_only or diagnostic_only")
    _validate_revision_feature_manifest(artifacts["v1_4_revision_feature_manifest"])
    _reject_prohibited_language({"artifacts": artifacts})


def make_v1_4_revision_run_id(
    evidences: Sequence[Mapping[str, Any]],
    revision_records: Sequence[Mapping[str, Any]],
    config: RevisionLayerConfig,
) -> str:
    payload = {
        "evidences": [
            {
                "candidate_id": evidence["candidate_id"],
                "evidence_id": evidence["evidence_id"],
                "date_range": evidence["date_range"],
            }
            for evidence in evidences
        ],
        "revision_records": sorted(
            [dict(record) for record in revision_records],
            key=lambda item: (str(item.get("candidate_id")), str(item.get("available_at"))),
        ),
        "config": config.__dict__,
    }
    digest = sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"v1_4_revision_{digest}"


def _coverage_row(evidence: Mapping[str, Any], record: Mapping[str, Any] | None) -> dict[str, Any]:
    candidate_id = str(evidence["candidate_id"])
    evidence_id = str(evidence["evidence_id"])
    evaluation_end = str(evidence["date_range"]["end"])
    if record is None:
        return {
            "candidate_id": candidate_id,
            "evidence_id": evidence_id,
            "evaluation_end": evaluation_end,
            "pit_status": "missing",
            "available_at": None,
            "revision_source_ref": None,
            "eps_revision_change_1m": None,
            "eps_revision_change_3m": None,
            "revision_diffusion_1m": None,
            "sector_revision_percentile": None,
            "reason_codes": ["revision_record_missing"],
        }
    missing = [field for field in REQUIRED_REVISION_FIELDS if _is_missing(record.get(field))]
    reasons = []
    if missing:
        reasons.extend(f"{field}_missing" for field in missing)
    if str(record.get("evidence_id") or "") != evidence_id:
        reasons.append("evidence_id_mismatch")
    available_at = str(record.get("available_at") or "")
    if available_at and _parse_date(available_at) > _parse_date(evaluation_end):
        reasons.append("revision_available_after_evaluation_end")
    status = "pass" if not reasons else "fail"
    return {
        "candidate_id": candidate_id,
        "evidence_id": evidence_id,
        "evaluation_end": evaluation_end,
        "pit_status": status,
        "available_at": available_at or None,
        "revision_source_ref": str(record.get("revision_source_ref") or "") or None,
        "eps_revision_change_1m": _ratio_change(record.get("eps_estimate_current"), record.get("eps_estimate_1m_ago"))
        if status == "pass"
        else None,
        "eps_revision_change_3m": _ratio_change(record.get("eps_estimate_current"), record.get("eps_estimate_3m_ago"))
        if status == "pass"
        else None,
        "revision_diffusion_1m": _revision_diffusion(
            record.get("analyst_revision_up_count_1m"),
            record.get("analyst_revision_down_count_1m"),
        )
        if status == "pass"
        else None,
        "sector_revision_percentile": _optional_float(record.get("sector_revision_percentile"))
        if status == "pass"
        else None,
        "reason_codes": reasons or ["revision_pit_available"],
    }


def _revision_by_candidate(records: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    by_candidate: dict[str, Mapping[str, Any]] = {}
    for record in records:
        candidate_id = str(record.get("candidate_id") or "").strip()
        if not candidate_id:
            raise ValueError("v1.4 revision record requires candidate_id")
        if candidate_id in by_candidate:
            raise ValueError(f"v1.4 revision record duplicate candidate_id: {candidate_id}")
        by_candidate[candidate_id] = dict(record)
    return by_candidate


def _validate_revision_feature_manifest(manifest: Mapping[str, Any]) -> None:
    feature_allowlist = set(manifest["feature_allowlist"])
    if feature_allowlist != set(REVISION_FEATURE_ALLOWLIST):
        raise ValueError("v1.4 revision feature allowlist mismatch")
    for row in manifest["rows"]:
        features = row["features"]
        feature_names = set(features)
        forbidden = feature_names.intersection(FORBIDDEN_REVISION_FEATURE_NAMES)
        if forbidden:
            raise ValueError(f"v1.4 revision feature manifest includes forbidden fields: {sorted(forbidden)}")
        if not feature_names.issubset(feature_allowlist):
            raise ValueError("v1.4 revision feature manifest contains non-allowlisted features")


def _needed_revision_data() -> list[dict[str, str]]:
    return [
        {
            "field": "candidate_id/evidence_id",
            "reason": "exact lineage from EvaluationEvidenceV1 to revision handoff row",
        },
        {
            "field": "revision_source_ref",
            "reason": "source, extraction batch, and approved snapshot provenance",
        },
        {
            "field": "available_at",
            "reason": "point-in-time cutoff; must be on or before evaluation date",
        },
        {
            "field": "estimate_as_of_date and fiscal_period",
            "reason": "consensus estimate timestamp and comparable fiscal target",
        },
        {
            "field": "eps_estimate_current, eps_estimate_1m_ago, eps_estimate_3m_ago",
            "reason": "1m and 3m EPS revision change calculation",
        },
        {
            "field": "analyst_revision_up_count_1m and analyst_revision_down_count_1m",
            "reason": "revision diffusion calculation",
        },
        {
            "field": "sector_id and sector_revision_percentile",
            "reason": "sector-relative revision comparison",
        },
    ]


def _ratio_change(current: Any, previous: Any) -> float:
    current_value = _required_float(current, "revision estimate current")
    previous_value = _required_float(previous, "revision estimate previous")
    if previous_value == 0.0:
        raise ValueError("v1.4 revision estimate previous value must be non-zero")
    return round((current_value - previous_value) / abs(previous_value), 8)


def _revision_diffusion(up_count: Any, down_count: Any) -> float:
    up = _required_float(up_count, "analyst_revision_up_count_1m")
    down = _required_float(down_count, "analyst_revision_down_count_1m")
    total = up + down
    if total <= 0.0:
        return 0.0
    return round((up - down) / total, 8)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"v1.4 revision date must be ISO YYYY-MM-DD: {value}") from exc


def _required_float(value: Any, field_name: str) -> float:
    result = _optional_float(value)
    if result is None:
        raise ValueError(f"v1.4 revision layer requires numeric {field_name}")
    return result


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("v1.4 revision layer requires numeric optional field") from exc


def _is_missing(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _blocked_flags() -> dict[str, bool]:
    return {flag: False for flag in PROHIBITED_FLAGS}


def _reject_prohibited_language(payload: Mapping[str, Any]) -> None:
    allowed_fields = {"prohibited_actions_notice", "evidence_only_notice"}
    text = json.dumps(_drop_allowed_notice_fields(payload, allowed_fields), ensure_ascii=False, sort_keys=True).lower()
    blocked_patterns = (
        r"\bbuy\b",
        r"\bsell\b",
        r"\bhold\b",
        r"\border\b",
        r"production ranking replacement",
        r"future-return",
        r"proven-alpha",
        r"active scoring",
    )
    for pattern in blocked_patterns:
        if re.search(pattern, text):
            raise ValueError(f"v1.4 revision artifact contains prohibited language: {pattern}")


def _drop_allowed_notice_fields(value: Any, allowed_fields: set[str]) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _drop_allowed_notice_fields(item, allowed_fields)
            for key, item in value.items()
            if key not in allowed_fields
        }
    if isinstance(value, list):
        return [_drop_allowed_notice_fields(item, allowed_fields) for item in value]
    return value
