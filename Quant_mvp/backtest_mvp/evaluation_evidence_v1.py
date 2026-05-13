"""v1.0-rc EvaluationEvidenceV1 contract.

This module converts candidate-only simulation/backtest records into auditable
evidence summaries. It does not run strategies, issue instructions, or update
production ranking.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
import re
import tomllib

from Quant_mvp.backtest_mvp.simulation_run_manifest import validate_simulation_run_manifest
from src.validation.horizon_policy import HorizonPolicy


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVALUATION_EVIDENCE_CONFIG = PROJECT_ROOT / "config" / "evaluation_evidence_v1.toml"

EVIDENCE_VERSION = "v1_0_rc_evaluation_evidence_v1_0"
METRICS_SCHEMA_VERSION = "v1_0_rc_evaluation_metrics_v1_0"
ALLOWED_EVIDENCE_MODES = frozenset(
    {
        "candidate_only_backtest_evidence",
        "candidate_only_simulation_evidence",
        "dry_run_evidence_summary",
    }
)
BLOCKED_EVIDENCE_MODES = frozenset(
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
ALLOWED_REBALANCING_ROLES = frozenset(
    {
        "none",
        "evaluation_mechanics",
        "tested_strategy_logic",
        "material_effect_on_candidate_evidence",
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
ALLOWED_METRIC_NAMES = frozenset(
    {
        "realized_return_summary",
        "realized_volatility_summary",
        "realized_drawdown_summary",
        "realized_turnover_summary",
        "realized_cost_summary",
        "sharpe_like_historical_summary",
        "hit_rate_historical_summary",
        "rank_ic_historical_summary",
        "coverage_ratio",
        "invalid_period_count",
        "missing_data_count",
    }
)
BLOCKED_METRIC_NAMES = frozenset(
    {
        "expected_return",
        "predicted_return",
        "future_return",
        "alpha_signal",
        "trade_signal",
        "buy_score",
        "sell_score",
        "guaranteed_return",
        "production_score",
    }
)
SELECTOR_FEATURE_ALLOWLIST = (
    "evidence_id",
    "candidate_id",
    "strategy_candidate_id",
    "weight_config_id",
    "horizon_policy_id",
    "evidence_status",
    "evidence_mode",
    "metric_values",
    "metric_units",
    "coverage_summary",
    "data_quality_summary",
    "evidence_quality_flags",
    "leakage_check_status",
    "no_lookahead_check_status",
    "rebalance_frequency",
    "rebalance_disclosure",
    "rebalancing_role",
    "turnover_summary",
    "cost_model",
    "slippage_model",
    "universe_scope",
    "date_range",
    "evaluation_window",
)
BLOCKED_SELECTOR_FIELDS = frozenset(
    {
        "raw_future_label",
        "future_return",
        "expected_return",
        "predicted_return",
        "production_score",
        "order_generation_enabled",
        "live_execution_enabled",
        "brokerage_integration_enabled",
        "user_facing_auto_rebalance_instruction_enabled",
        "production_ranking_update_enabled",
        "valuation_fundamental_active_scoring_enabled",
    }
)
EVIDENCE_ONLY_NOTICE = (
    "EvaluationEvidenceV1 is candidate-only evidence-only manual review support; "
    "historical or simulated metrics are not future-return predictions."
)
PROHIBITED_ACTIONS_NOTICE = (
    "prohibited actions include live trading, brokerage integration, order generation, "
    "buy/sell/hold recommendations, trade-signal framing, automatic live rebalance "
    "instructions, move-to-cash commands, expected-return claims, proven-alpha claims, "
    "production ranking replacement, and valuation/fundamental active scoring"
)
REQUIRED_EVIDENCE_FIELDS = frozenset(
    {
        "evidence_version",
        "evidence_id",
        "created_at",
        "route_scope",
        "evidence_mode",
        "evidence_status",
        "candidate_id",
        "strategy_candidate_id",
        "strategy_candidate_ref",
        "simulation_run_manifest_ref",
        "simulation_run_manifest_snapshot",
        "horizon_policy_id",
        "horizon_policy_snapshot",
        "input_artifact_refs",
        "output_artifact_refs",
        "data_context",
        "universe_scope",
        "date_range",
        "evaluation_window",
        "metrics_schema_version",
        "metric_values",
        "metric_units",
        "metric_definitions_ref",
        "cost_model",
        "slippage_model",
        "turnover_summary",
        "rebalance_frequency",
        "rebalance_disclosure",
        "rebalancing_role",
        "evidence_quality_flags",
        "coverage_summary",
        "data_quality_summary",
        "limitation_summary",
        "leakage_check_status",
        "no_lookahead_check_status",
        "selector_allowlist_status",
        "selector_feature_allowlist",
        "evidence_only_notice",
        "prohibited_actions_notice",
        *PROHIBITED_FLAGS,
    }
)


def load_evaluation_evidence_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path is not None else DEFAULT_EVALUATION_EVIDENCE_CONFIG
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    if "metric_allowlist" not in payload:
        raise ValueError("EvaluationEvidenceV1 config requires [metric_allowlist]")
    return payload


def build_evaluation_evidence_v1(
    *,
    candidate_result: Mapping[str, Any],
    simulation_run_manifest: Mapping[str, Any],
    horizon_policy_snapshot: Mapping[str, Any],
    weight_config_snapshot: Mapping[str, Any] | None = None,
    layer_registry_validation: Mapping[str, Any] | None = None,
    created_at: str | None = None,
    route_scope: str = "v1_0_rc_phase_6_evaluation_evidence",
    evidence_mode: str | None = None,
    evidence_status: str = "evidence_recorded",
    metric_definitions_ref: str = "config/evaluation_evidence_v1.toml",
) -> dict[str, Any]:
    """Build a validated EvaluationEvidenceV1 packet from provided summaries."""

    manifest = dict(simulation_run_manifest)
    validate_simulation_run_manifest(manifest)
    policy = HorizonPolicy.from_mapping(horizon_policy_snapshot)
    if manifest.get("horizon_policy_id") != policy.horizon_id:
        raise ValueError("EvaluationEvidenceV1 HorizonPolicy snapshot must match manifest")

    mode = evidence_mode or _mode_from_manifest(manifest)
    metric_values = _extract_metric_values(candidate_result)
    weight_config_id = (
        str(weight_config_snapshot.get("weight_config_id"))
        if isinstance(weight_config_snapshot, Mapping) and weight_config_snapshot.get("weight_config_id")
        else candidate_result.get("weight_config_id")
    )
    candidate_id = str(
        candidate_result.get("candidate_id")
        or candidate_result.get("strategy_candidate_id")
        or manifest.get("strategy_candidate_id")
    )
    strategy_candidate_id = str(candidate_result.get("strategy_candidate_id") or candidate_id)
    strategy_candidate_ref = str(
        candidate_result.get("strategy_candidate_ref") or manifest.get("strategy_candidate_ref")
    )
    _validate_candidate_manifest_lineage(
        candidate_id=candidate_id,
        strategy_candidate_id=strategy_candidate_id,
        strategy_candidate_ref=strategy_candidate_ref,
        manifest=manifest,
    )
    evidence = {
        "evidence_version": EVIDENCE_VERSION,
        "evidence_id": make_evaluation_evidence_id(
            candidate_id=candidate_id,
            simulation_run_id=str(manifest["run_id"]),
            horizon_policy_id=policy.horizon_id,
            weight_config_id=str(weight_config_id or ""),
        ),
        "created_at": created_at or _utc_now(),
        "route_scope": route_scope,
        "evidence_mode": mode,
        "evidence_status": evidence_status,
        "candidate_id": candidate_id,
        "strategy_candidate_id": strategy_candidate_id,
        "strategy_candidate_ref": strategy_candidate_ref,
        "weight_config_id": weight_config_id,
        "weight_config_snapshot": dict(weight_config_snapshot) if isinstance(weight_config_snapshot, Mapping) else None,
        "simulation_run_manifest_ref": str(manifest["run_id"]),
        "simulation_run_manifest_snapshot": manifest,
        "horizon_policy_id": policy.horizon_id,
        "horizon_policy_snapshot": policy.to_dict(),
        "layer_registry_validation_ref": (
            layer_registry_validation.get("validation_ref")
            if isinstance(layer_registry_validation, Mapping)
            else None
        ),
        "layer_registry_validation_status": (
            layer_registry_validation.get("validation_status")
            if isinstance(layer_registry_validation, Mapping)
            else None
        ),
        "input_artifact_refs": list(candidate_result.get("input_artifact_refs") or manifest.get("input_artifact_refs") or []),
        "output_artifact_refs": list(candidate_result.get("output_artifact_refs") or manifest.get("output_artifact_refs") or []),
        "data_context": candidate_result.get("data_context") or manifest.get("data_context"),
        "universe_scope": candidate_result.get("universe_scope") or manifest.get("universe_scope"),
        "date_range": dict(candidate_result.get("date_range") or manifest.get("date_range") or {}),
        "evaluation_window": dict(candidate_result.get("evaluation_window") or manifest.get("date_range") or {}),
        "metrics_schema_version": METRICS_SCHEMA_VERSION,
        "metric_values": metric_values,
        "metric_units": dict(candidate_result.get("metric_units") or _default_metric_units(metric_values)),
        "metric_definitions_ref": metric_definitions_ref,
        "cost_model": candidate_result.get("cost_model") or manifest.get("cost_model"),
        "slippage_model": candidate_result.get("slippage_model") or manifest.get("slippage_model"),
        "turnover_summary": dict(candidate_result.get("turnover_summary") or {}),
        "rebalance_frequency": candidate_result.get("rebalance_frequency") or manifest.get("rebalance_frequency"),
        "rebalance_disclosure": candidate_result.get("rebalance_disclosure") or manifest.get("rebalance_disclosure"),
        "rebalancing_role": str(candidate_result.get("rebalancing_role") or "evaluation_mechanics"),
        "evidence_quality_flags": list(candidate_result.get("evidence_quality_flags") or []),
        "coverage_summary": dict(candidate_result.get("coverage_summary") or {}),
        "data_quality_summary": dict(candidate_result.get("data_quality_summary") or {}),
        "limitation_summary": list(candidate_result.get("limitation_summary") or []),
        "leakage_check_status": str(candidate_result.get("leakage_check_status") or "not_evaluated"),
        "no_lookahead_check_status": str(candidate_result.get("no_lookahead_check_status") or "not_evaluated"),
        "selector_allowlist_status": "explicit_allowlist",
        "selector_feature_allowlist": list(SELECTOR_FEATURE_ALLOWLIST),
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        "live_execution_enabled": False,
        "brokerage_integration_enabled": False,
        "order_generation_enabled": False,
        "user_facing_auto_rebalance_instruction_enabled": False,
        "production_ranking_update_enabled": False,
        "valuation_fundamental_active_scoring_enabled": False,
    }
    validate_evaluation_evidence_v1(evidence)
    return evidence


def build_dry_run_evidence_summary_from_weight_config_record(
    record: Mapping[str, Any],
    *,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Create a dry-run evidence summary from a Phase 4 run record."""

    manifest = dict(record["simulation_run_manifest_snapshot"])
    weight_snapshot = dict(record["weight_config_snapshot"])
    return build_evaluation_evidence_v1(
        candidate_result={
            "candidate_id": manifest["strategy_candidate_id"],
            "strategy_candidate_ref": manifest["strategy_candidate_ref"],
            "metric_values": {},
            "metric_units": {},
            "coverage_summary": {"dry_run_plan_only": True},
            "limitation_summary": ["full_metric_evidence_waits_for_runner_integration"],
            "rebalance_frequency": record.get("rebalance_frequency"),
            "rebalance_disclosure": record.get("rebalance_disclosure"),
            "rebalancing_role": "evaluation_mechanics",
            "input_artifact_refs": manifest.get("input_artifact_refs", []),
        },
        simulation_run_manifest=manifest,
        horizon_policy_snapshot=manifest["horizon_policy_snapshot"],
        weight_config_snapshot=weight_snapshot,
        created_at=created_at,
        evidence_mode="dry_run_evidence_summary",
        evidence_status="dry_run_plan_only",
    )


def validate_evaluation_evidence_v1(evidence: Mapping[str, Any]) -> None:
    missing = sorted(REQUIRED_EVIDENCE_FIELDS.difference(evidence))
    if missing:
        raise ValueError(f"EvaluationEvidenceV1 missing required fields: {', '.join(missing)}")
    if evidence["evidence_version"] != EVIDENCE_VERSION:
        raise ValueError("unsupported EvaluationEvidenceV1 evidence_version")
    if evidence["evidence_mode"] in BLOCKED_EVIDENCE_MODES or evidence["evidence_mode"] not in ALLOWED_EVIDENCE_MODES:
        raise ValueError(f"blocked or unsupported evidence_mode: {evidence['evidence_mode']}")
    if not isinstance(evidence["horizon_policy_snapshot"], Mapping):
        raise ValueError("EvaluationEvidenceV1 requires HorizonPolicy snapshot")
    policy = HorizonPolicy.from_mapping(evidence["horizon_policy_snapshot"])
    if evidence["horizon_policy_id"] != policy.horizon_id:
        raise ValueError("EvaluationEvidenceV1 horizon_policy_id must match HorizonPolicy snapshot")
    if not isinstance(evidence["simulation_run_manifest_snapshot"], Mapping):
        raise ValueError("EvaluationEvidenceV1 requires SimulationRunManifest snapshot")
    manifest = dict(evidence["simulation_run_manifest_snapshot"])
    validate_simulation_run_manifest(manifest)
    if not evidence.get("simulation_run_manifest_ref"):
        raise ValueError("EvaluationEvidenceV1 requires SimulationRunManifest reference")
    if evidence["simulation_run_manifest_ref"] != manifest.get("run_id"):
        raise ValueError("EvaluationEvidenceV1 SimulationRunManifest ref must match snapshot run_id")
    _validate_candidate_manifest_lineage(
        candidate_id=str(evidence["candidate_id"]),
        strategy_candidate_id=str(evidence["strategy_candidate_id"]),
        strategy_candidate_ref=str(evidence["strategy_candidate_ref"]),
        manifest=manifest,
    )
    role = str(evidence.get("rebalancing_role") or "")
    if role not in ALLOWED_REBALANCING_ROLES:
        raise ValueError(f"unsupported rebalancing_role: {role}")
    if evidence.get("rebalance_frequency") != "none" or role != "none":
        disclosure = str(evidence.get("rebalance_disclosure") or "").strip()
        if not disclosure:
            raise ValueError("EvaluationEvidenceV1 requires rebalance disclosure")
        if role in {"tested_strategy_logic", "material_effect_on_candidate_evidence"}:
            normalized = disclosure.lower()
            if "historical" not in normalized and "simulated" not in normalized:
                raise ValueError("material rebalancing disclosure must be historical/simulated")
    for flag in PROHIBITED_FLAGS:
        if bool(evidence.get(flag)):
            raise ValueError(f"EvaluationEvidenceV1 blocked flag must remain false: {flag}")
    if evidence.get("selector_allowlist_status") != "explicit_allowlist":
        raise ValueError("EvaluationEvidenceV1 selector allowlist must be explicit")
    validate_selector_feature_allowlist(evidence.get("selector_feature_allowlist"))
    _validate_metric_values(evidence.get("metric_values"))
    _reject_prohibited_language(evidence)


def validate_selector_feature_allowlist(fields: Any) -> None:
    if not isinstance(fields, Sequence) or isinstance(fields, (str, bytes, bytearray)):
        raise ValueError("selector_feature_allowlist must be a sequence")
    selected = {str(field) for field in fields}
    blocked = sorted(selected & BLOCKED_SELECTOR_FIELDS)
    if blocked:
        raise ValueError(f"selector allowlist contains blocked fields: {', '.join(blocked)}")
    unknown = sorted(selected.difference(SELECTOR_FEATURE_ALLOWLIST))
    if unknown:
        raise ValueError(f"selector allowlist contains unknown fields: {', '.join(unknown)}")


def _validate_candidate_manifest_lineage(
    *,
    candidate_id: str,
    strategy_candidate_id: str,
    strategy_candidate_ref: str,
    manifest: Mapping[str, Any],
) -> None:
    manifest_candidate_id = str(manifest.get("strategy_candidate_id") or "")
    manifest_candidate_ref = str(manifest.get("strategy_candidate_ref") or "")
    if not candidate_id or candidate_id != manifest_candidate_id:
        raise ValueError("EvaluationEvidenceV1 candidate_id must match SimulationRunManifest strategy_candidate_id")
    if strategy_candidate_id != manifest_candidate_id:
        raise ValueError("EvaluationEvidenceV1 strategy_candidate_id must match SimulationRunManifest strategy_candidate_id")
    if strategy_candidate_ref != manifest_candidate_ref:
        raise ValueError("EvaluationEvidenceV1 strategy_candidate_ref must match SimulationRunManifest strategy_candidate_ref")


def make_evaluation_evidence_id(
    *,
    candidate_id: str,
    simulation_run_id: str,
    horizon_policy_id: str,
    weight_config_id: str = "",
) -> str:
    payload = "|".join([candidate_id, simulation_run_id, horizon_policy_id, weight_config_id])
    digest = sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"ee_v1_0_rc_{_slug(candidate_id)}_{_slug(horizon_policy_id)}_{digest}"


def _extract_metric_values(candidate_result: Mapping[str, Any]) -> dict[str, Any]:
    raw = candidate_result.get("metric_values") or {}
    if not isinstance(raw, Mapping):
        raise ValueError("EvaluationEvidenceV1 metric_values must be a mapping")
    return {str(key): value for key, value in raw.items() if value is not None}


def _validate_metric_values(metrics: Any) -> None:
    if not isinstance(metrics, Mapping):
        raise ValueError("EvaluationEvidenceV1 metric_values must be a mapping")
    blocked = sorted({str(name) for name in metrics} & BLOCKED_METRIC_NAMES)
    if blocked:
        raise ValueError(f"blocked EvaluationEvidenceV1 metric names: {', '.join(blocked)}")
    unknown = sorted(set(str(name) for name in metrics).difference(ALLOWED_METRIC_NAMES))
    if unknown:
        raise ValueError(f"non-allowlisted EvaluationEvidenceV1 metric names: {', '.join(unknown)}")


def _default_metric_units(metrics: Mapping[str, Any]) -> dict[str, str]:
    units: dict[str, str] = {}
    for name in metrics:
        if name.endswith("_count"):
            units[name] = "count"
        elif name == "coverage_ratio":
            units[name] = "ratio"
        else:
            units[name] = "historical_simulated_summary"
    return units


def _mode_from_manifest(manifest: Mapping[str, Any]) -> str:
    if manifest.get("run_mode") == "candidate_only_backtest":
        return "candidate_only_backtest_evidence"
    return "candidate_only_simulation_evidence"


def _reject_prohibited_language(evidence: Mapping[str, Any]) -> None:
    allowed_fields = {"prohibited_actions_notice", "evidence_only_notice", "selector_feature_allowlist"}
    payload = {key: value for key, value in evidence.items() if key not in allowed_fields}
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
    blocked_patterns = (
        r"\bexpected_return\b",
        r"\bpredicted_return\b",
        r"\bfuture_return\b",
        r"\bproven_alpha\b",
        r"\balpha_signal\b",
        r"\btrade_signal\b",
        r"\bbuy_score\b",
        r"\bsell_score\b",
        r"\bguaranteed_return\b",
        r"\bproduction_score\b",
        r"buy/sell/hold",
    )
    for pattern in blocked_patterns:
        if re.search(pattern, text):
            raise ValueError(f"EvaluationEvidenceV1 contains prohibited language: {pattern}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug or "unknown"


__all__ = (
    "ALLOWED_EVIDENCE_MODES",
    "ALLOWED_METRIC_NAMES",
    "DEFAULT_EVALUATION_EVIDENCE_CONFIG",
    "EVIDENCE_VERSION",
    "SELECTOR_FEATURE_ALLOWLIST",
    "build_dry_run_evidence_summary_from_weight_config_record",
    "build_evaluation_evidence_v1",
    "load_evaluation_evidence_config",
    "make_evaluation_evidence_id",
    "validate_evaluation_evidence_v1",
    "validate_selector_feature_allowlist",
)
