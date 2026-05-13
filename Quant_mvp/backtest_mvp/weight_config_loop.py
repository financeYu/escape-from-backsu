"""v1.0-rc WeightConfig loop planning.

This module builds deterministic candidate-only run plans. It does not run
production ranking, choose best weights, or feed backtest metrics upstream.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import hashlib
import tomllib

from Quant_mvp.backtest_mvp.simulation_run_manifest import (
    build_simulation_run_manifest,
    validate_simulation_run_manifest,
)
from src.validation.horizon_policy import HorizonPolicy, resolve_horizon_policy
from src.validation.layer_registry import (
    LayerRegistry,
    load_layer_registry,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEIGHT_CONFIG_LOOP_CONFIG = PROJECT_ROOT / "config" / "weight_config_loop.toml"

WEIGHT_CONFIG_SCHEMA_VERSION = "v1_0_rc_weight_config_loop_0_1"
ALLOWED_EVALUATION_MODES = frozenset(
    {"candidate_only_backtest", "candidate_only_simulation", "dry_run_plan_only"}
)
BLOCKED_EVALUATION_MODES = frozenset(
    {
        "live_trading",
        "paper_trading",
        "brokerage_order",
        "trade_signal",
        "buy_sell_recommendation",
        "automatic_rebalance_instruction",
        "move_to_cash",
        "production_execution",
    }
)
ALLOWED_WEIGHT_SUM_POLICIES = frozenset({"sum_to_one"})
ALLOWED_MISSING_SCORE_POLICIES = frozenset({"fail_closed"})
ALLOWED_INACTIVE_SCORE_POLICIES = frozenset({"reject"})
ALLOWED_DIAGNOSTIC_SCORE_POLICIES = frozenset({"exclude_from_active_weights"})
EVIDENCE_ONLY_NOTICE = "candidate-only evidence-only WeightConfig loop plan for manual review support"
PROHIBITED_ACTIONS_NOTICE = (
    "does not create live execution, brokerage integration, order generation, "
    "recommendation language, trade-signal framing, live automatic rebalance "
    "instructions, move-to-cash commands, future-return claims, production "
    "ranking replacement, or valuation/fundamental scoring activation"
)
REQUIRED_WEIGHT_CONFIG_FIELDS = frozenset(
    {
        "weight_config_id",
        "weight_config_version",
        "weight_config_source",
        "score_family",
        "score_group",
        "score_weights",
        "normalization_ref",
        "horizon_policy_id",
        "horizon_policy_snapshot",
        "candidate_id",
        "evaluation_mode",
        "generated_by",
        "grid_spec",
        "candidate_set_spec",
        "constraints",
        "weight_sum_policy",
        "missing_score_policy",
        "inactive_score_policy",
        "diagnostic_score_policy",
        "created_at",
        "config_digest",
        "evidence_only_notice",
        "prohibited_actions_notice",
    }
)


@dataclass(frozen=True)
class WeightConfigCandidate:
    weight_config_id: str
    weight_config_version: str
    weight_config_source: str
    score_family: str
    score_group: str
    score_weights: Mapping[str, float]
    normalization_ref: str
    horizon_policy_id: str
    horizon_policy_snapshot: Mapping[str, Any]
    candidate_id: str
    evaluation_mode: str
    generated_by: str
    grid_spec: str
    candidate_set_spec: Mapping[str, Any]
    constraints: Mapping[str, Any]
    weight_sum_policy: str
    missing_score_policy: str
    inactive_score_policy: str
    diagnostic_score_policy: str
    created_at: str
    config_digest: str
    evidence_only_notice: str
    prohibited_actions_notice: str

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, Any],
        *,
        defaults: Mapping[str, Any],
        horizon_policy: HorizonPolicy,
        config_digest: str,
        created_at: str,
    ) -> "WeightConfigCandidate":
        merged = dict(defaults)
        merged.update(values)
        score_weights = _score_weights(values.get("score_weights"))
        candidate = cls(
            weight_config_id=_required_text(merged, "weight_config_id"),
            weight_config_version=_required_text(merged, "weight_config_version"),
            weight_config_source=_required_text(merged, "weight_config_source"),
            score_family=_required_text(merged, "score_family"),
            score_group=_required_text(merged, "score_group"),
            score_weights=score_weights,
            normalization_ref=_required_text(merged, "normalization_ref"),
            horizon_policy_id=horizon_policy.horizon_id,
            horizon_policy_snapshot=horizon_policy.to_dict(),
            candidate_id=_required_text(merged, "candidate_id"),
            evaluation_mode=_required_text(merged, "evaluation_mode"),
            generated_by=_required_text(merged, "generated_by"),
            grid_spec=_required_text(merged, "grid_spec"),
            candidate_set_spec=dict(defaults.get("candidate_set_spec", {})),
            constraints=dict(defaults.get("constraints", {})),
            weight_sum_policy=_required_text(merged, "weight_sum_policy"),
            missing_score_policy=_required_text(merged, "missing_score_policy"),
            inactive_score_policy=_required_text(merged, "inactive_score_policy"),
            diagnostic_score_policy=_required_text(merged, "diagnostic_score_policy"),
            created_at=created_at,
            config_digest=config_digest,
            evidence_only_notice=str(merged.get("evidence_only_notice") or EVIDENCE_ONLY_NOTICE),
            prohibited_actions_notice=str(
                merged.get("prohibited_actions_notice") or PROHIBITED_ACTIONS_NOTICE
            ),
        )
        validate_weight_config_candidate(candidate)
        return candidate

    def to_dict(self) -> dict[str, Any]:
        return {
            "weight_config_id": self.weight_config_id,
            "weight_config_version": self.weight_config_version,
            "weight_config_source": self.weight_config_source,
            "score_family": self.score_family,
            "score_group": self.score_group,
            "score_weights": dict(self.score_weights),
            "normalization_ref": self.normalization_ref,
            "horizon_policy_id": self.horizon_policy_id,
            "horizon_policy_snapshot": dict(self.horizon_policy_snapshot),
            "candidate_id": self.candidate_id,
            "evaluation_mode": self.evaluation_mode,
            "generated_by": self.generated_by,
            "grid_spec": self.grid_spec,
            "candidate_set_spec": dict(self.candidate_set_spec),
            "constraints": dict(self.constraints),
            "weight_sum_policy": self.weight_sum_policy,
            "missing_score_policy": self.missing_score_policy,
            "inactive_score_policy": self.inactive_score_policy,
            "diagnostic_score_policy": self.diagnostic_score_policy,
            "created_at": self.created_at,
            "config_digest": self.config_digest,
            "evidence_only_notice": self.evidence_only_notice,
            "prohibited_actions_notice": self.prohibited_actions_notice,
        }


def load_weight_config_loop_config(config_path: str | Path | None = None) -> tuple[dict[str, Any], str]:
    path = Path(config_path) if config_path is not None else DEFAULT_WEIGHT_CONFIG_LOOP_CONFIG
    raw = path.read_bytes()
    payload = tomllib.loads(raw.decode("utf-8"))
    if "weight_config" not in payload:
        raise ValueError("WeightConfig loop config must define [[weight_config]] entries")
    return payload, hashlib.sha256(raw).hexdigest()


def load_weight_config_candidates(
    *,
    config_path: str | Path | None = None,
    horizon_policy_id: str | None = None,
    evaluation_mode: str | None = None,
    layer_registry: LayerRegistry | None = None,
    created_at: str = "not_recorded_plan_time",
) -> tuple[WeightConfigCandidate, ...]:
    payload, digest = load_weight_config_loop_config(config_path)
    defaults = dict(payload.get("defaults", {}))
    if evaluation_mode is not None:
        _validate_evaluation_mode(evaluation_mode)
        defaults["evaluation_mode"] = evaluation_mode
    selected_horizon_id = horizon_policy_id or defaults.get("horizon_policy_id")
    horizon_policy = resolve_horizon_policy(str(selected_horizon_id) if selected_horizon_id else None)
    entries = tuple(
        WeightConfigCandidate.from_mapping(
            entry,
            defaults=defaults,
            horizon_policy=horizon_policy,
            config_digest=digest,
            created_at=created_at,
        )
        for entry in payload.get("weight_config", ())
        if isinstance(entry, Mapping)
    )
    validate_weight_config_candidates(entries, max_candidate_count=int(defaults.get("max_candidate_count", 0)))
    registry = layer_registry or load_layer_registry()
    for candidate in entries:
        registry.validate_active_weight_layers(tuple(candidate.score_weights))
    return entries


def build_weight_config_loop_plan(
    *,
    config_path: str | Path | None = None,
    horizon_policy_id: str | None = None,
    layer_registry: LayerRegistry | None = None,
    evaluation_mode: str | None = None,
    candidate_id: str | None = None,
    strategy_candidate_ref: str | None = None,
    date_range: Mapping[str, str] | None = None,
    created_at: str = "not_recorded_plan_time",
    code_version: str = "local_not_recorded",
) -> dict[str, Any]:
    payload, digest = load_weight_config_loop_config(config_path)
    defaults = dict(payload.get("defaults", {}))
    mode = str(evaluation_mode or defaults.get("evaluation_mode") or "dry_run_plan_only")
    _validate_evaluation_mode(mode)
    selected_candidate_id = str(candidate_id or defaults.get("candidate_id") or "candidate_not_recorded")
    selected_strategy_ref = str(
        strategy_candidate_ref
        or defaults.get("strategy_candidate_ref")
        or "strategy_candidate_ref_not_recorded"
    )
    selected_date_range = dict(date_range or defaults.get("date_range") or {})
    if not selected_date_range:
        raise ValueError("WeightConfig loop plan requires date_range")
    registry = layer_registry or load_layer_registry()
    candidates = load_weight_config_candidates(
        config_path=config_path,
        horizon_policy_id=horizon_policy_id,
        evaluation_mode=mode,
        layer_registry=registry,
        created_at=created_at,
    )
    records = tuple(
        _build_run_record(
            candidate,
            evaluation_mode=mode,
            strategy_candidate_id=selected_candidate_id,
            strategy_candidate_ref=selected_strategy_ref,
            date_range=selected_date_range,
            rebalance_disclosure=str(
                defaults.get("rebalance_disclosure")
                or "rebalancing_is_historical_simulation_context_only_not_user_instruction"
            ),
            created_at=created_at,
            code_version=code_version,
        )
        for candidate in candidates
    )
    plan = {
        "schema_version": WEIGHT_CONFIG_SCHEMA_VERSION,
        "plan_kind": "WeightConfigLoopPlan",
        "evaluation_mode": mode,
        "horizon_policy_id": candidates[0].horizon_policy_id if candidates else None,
        "horizon_policy_snapshot": dict(candidates[0].horizon_policy_snapshot) if candidates else None,
        "candidate_id": selected_candidate_id,
        "strategy_candidate_id": selected_candidate_id,
        "strategy_candidate_ref": selected_strategy_ref,
        "date_range": selected_date_range,
        "weight_config_count": len(records),
        "max_candidate_count": int(defaults.get("max_candidate_count", len(records))),
        "config_digest": digest,
        "layer_registry_digest": registry.config_digest,
        "records": [dict(record) for record in records],
        "evidence_only_notice": defaults.get("evidence_only_notice") or EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": defaults.get("prohibited_actions_notice")
        or PROHIBITED_ACTIONS_NOTICE,
        "production_ranking_changed": False,
        "best_weight_selected": False,
        "phase6_evidence_v1_enabled": False,
        "live_execution_enabled": False,
        "brokerage_integration_enabled": False,
        "order_generation_enabled": False,
        "user_facing_auto_rebalance_instruction_enabled": False,
    }
    validate_weight_config_loop_plan(plan)
    return plan


def validate_weight_config_candidate(candidate: WeightConfigCandidate | Mapping[str, Any]) -> None:
    payload = candidate.to_dict() if isinstance(candidate, WeightConfigCandidate) else dict(candidate)
    missing = sorted(REQUIRED_WEIGHT_CONFIG_FIELDS.difference(payload))
    if missing:
        raise ValueError(f"WeightConfig missing required fields: {', '.join(missing)}")
    _validate_evaluation_mode(str(payload["evaluation_mode"]))
    if payload["weight_sum_policy"] not in ALLOWED_WEIGHT_SUM_POLICIES:
        raise ValueError(f"unsupported weight_sum_policy: {payload['weight_sum_policy']}")
    if payload["missing_score_policy"] not in ALLOWED_MISSING_SCORE_POLICIES:
        raise ValueError(f"unsupported missing_score_policy: {payload['missing_score_policy']}")
    if payload["inactive_score_policy"] not in ALLOWED_INACTIVE_SCORE_POLICIES:
        raise ValueError(f"unsupported inactive_score_policy: {payload['inactive_score_policy']}")
    if payload["diagnostic_score_policy"] not in ALLOWED_DIAGNOSTIC_SCORE_POLICIES:
        raise ValueError(f"unsupported diagnostic_score_policy: {payload['diagnostic_score_policy']}")
    weights = _score_weights(payload.get("score_weights"))
    if not weights:
        raise ValueError("WeightConfig score_weights must not be empty")
    if any(weight < 0 for weight in weights.values()):
        raise ValueError("WeightConfig score_weights must be non-negative")
    if payload["weight_sum_policy"] == "sum_to_one" and abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError("WeightConfig score_weights must sum to 1.0")
    if not isinstance(payload.get("horizon_policy_snapshot"), Mapping):
        raise ValueError("WeightConfig requires horizon_policy_snapshot")
    HorizonPolicy.from_mapping(payload["horizon_policy_snapshot"])


def validate_weight_config_candidates(
    candidates: tuple[WeightConfigCandidate, ...],
    *,
    max_candidate_count: int,
) -> None:
    if not candidates:
        raise ValueError("WeightConfig loop requires at least one candidate")
    ids = [candidate.weight_config_id for candidate in candidates]
    duplicates = sorted({weight_config_id for weight_config_id in ids if ids.count(weight_config_id) > 1})
    if duplicates:
        raise ValueError(f"WeightConfig duplicate weight_config_id: {', '.join(duplicates)}")
    if max_candidate_count < 1:
        raise ValueError("WeightConfig max_candidate_count must be at least 1")
    if len(candidates) > max_candidate_count:
        raise ValueError("WeightConfig candidate count exceeds max_candidate_count")
    for candidate in candidates:
        validate_weight_config_candidate(candidate)


def validate_weight_config_loop_plan(plan: Mapping[str, Any]) -> None:
    _validate_evaluation_mode(str(plan.get("evaluation_mode")))
    if bool(plan.get("production_ranking_changed")):
        raise ValueError("WeightConfig loop must not change production ranking")
    if bool(plan.get("best_weight_selected")):
        raise ValueError("WeightConfig loop must not select best weights")
    if bool(plan.get("phase6_evidence_v1_enabled")):
        raise ValueError("WeightConfig loop must not enable Phase 6")
    for flag in (
        "live_execution_enabled",
        "brokerage_integration_enabled",
        "order_generation_enabled",
        "user_facing_auto_rebalance_instruction_enabled",
    ):
        if bool(plan.get(flag)):
            raise ValueError(f"WeightConfig loop blocked flag must remain false: {flag}")
    for record in plan.get("records", ()):
        validate_weight_config_candidate(record["weight_config_snapshot"])
        manifest = dict(record["simulation_run_manifest_snapshot"])
        validate_simulation_run_manifest(manifest)
        if "weight_config_snapshot" not in manifest:
            raise ValueError("SimulationRunManifest snapshot must include weight_config_snapshot")


def _build_run_record(
    candidate: WeightConfigCandidate,
    *,
    evaluation_mode: str,
    strategy_candidate_id: str,
    strategy_candidate_ref: str,
    date_range: Mapping[str, str],
    rebalance_disclosure: str,
    created_at: str,
    code_version: str,
) -> Mapping[str, Any]:
    manifest_mode = (
        evaluation_mode
        if evaluation_mode in {"candidate_only_backtest", "candidate_only_simulation"}
        else "candidate_only_simulation"
    )
    manifest = build_simulation_run_manifest(
        strategy_candidate_id=strategy_candidate_id,
        strategy_candidate_ref=strategy_candidate_ref,
        date_range=date_range,
        horizon_policy=candidate.horizon_policy_snapshot,
        created_at=created_at,
        route_scope="v1_0_rc_weight_config_loop",
        run_mode=manifest_mode,
        evidence_mode="evidence_only",
        input_artifact_refs=[candidate.weight_config_source, "config/layer_registry.toml"],
        output_artifact_refs=[],
        rebalance_disclosure=rebalance_disclosure,
        code_version=code_version,
        config_refs=[candidate.weight_config_source, "config/horizon_policy.toml", "config/layer_registry.toml"],
        live_execution_enabled=False,
        brokerage_integration_enabled=False,
        order_generation_enabled=False,
        user_facing_auto_rebalance_instruction_enabled=False,
        phase4_weight_loop_enabled=False,
    )
    manifest["weight_config_snapshot"] = candidate.to_dict()
    validate_simulation_run_manifest(manifest)
    return {
        "weight_config_id": candidate.weight_config_id,
        "evaluation_mode": evaluation_mode,
        "weight_config_snapshot": candidate.to_dict(),
        "simulation_run_manifest_ref": manifest["run_id"],
        "simulation_run_manifest_snapshot": manifest,
        "rebalance_frequency": manifest["rebalance_frequency"],
        "rebalance_disclosure": manifest["rebalance_disclosure"],
        "run_status": "planned_candidate_only",
        "production_ranking_changed": False,
        "best_weight_selected": False,
        "phase6_evidence_v1_enabled": False,
    }


def _validate_evaluation_mode(mode: str) -> None:
    if mode in BLOCKED_EVALUATION_MODES or mode not in ALLOWED_EVALUATION_MODES:
        raise ValueError(f"blocked or unsupported WeightConfig evaluation_mode: {mode}")


def _score_weights(values: Any) -> dict[str, float]:
    if not isinstance(values, Mapping):
        raise ValueError("WeightConfig score_weights must be a mapping")
    parsed: dict[str, float] = {}
    for key, value in values.items():
        score_key = str(key).strip()
        if not score_key:
            raise ValueError("WeightConfig score_weights keys must be non-empty")
        try:
            weight = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("WeightConfig score_weights must be numeric") from exc
        parsed[score_key] = weight
    return parsed


def _required_text(values: Mapping[str, Any], field_name: str) -> str:
    text = str(values.get(field_name) or "").strip()
    if not text:
        raise ValueError(f"WeightConfig field must be non-empty: {field_name}")
    return text


__all__ = (
    "ALLOWED_EVALUATION_MODES",
    "DEFAULT_WEIGHT_CONFIG_LOOP_CONFIG",
    "WEIGHT_CONFIG_SCHEMA_VERSION",
    "WeightConfigCandidate",
    "build_weight_config_loop_plan",
    "load_weight_config_candidates",
    "load_weight_config_loop_config",
    "validate_weight_config_candidate",
    "validate_weight_config_candidates",
    "validate_weight_config_loop_plan",
)
