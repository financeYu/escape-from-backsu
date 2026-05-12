"""v1.0-rc SimulationRunManifest contract.

The manifest records candidate-only simulation/backtest context for evidence
review. It does not create live execution, order generation, or production
activation behavior.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
import re

from src.validation.horizon_policy import HorizonPolicy, resolve_horizon_policy


MANIFEST_VERSION = "v1_0_rc_simulation_run_manifest_0_1"
ALLOWED_RUN_MODES = frozenset({"candidate_only_backtest", "candidate_only_simulation"})
ALLOWED_EVIDENCE_MODES = frozenset({"candidate_only", "evidence_only"})
EVIDENCE_ONLY_NOTICE = (
    "candidate-only evidence-only simulation manifest for manual review support; "
    "not production activation or execution readiness"
)
PROHIBITED_ACTIONS_NOTICE = (
    "prohibited actions include live execution, brokerage integration, order generation, "
    "user-facing recommendation language, trade-signal framing, live automatic rebalance "
    "instructions, move-to-cash commands, future-return claims, and valuation/fundamental "
    "scoring activation"
)
BLOCKED_RUNTIME_VALUES = frozenset(
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
REQUIRED_MANIFEST_FIELDS = frozenset(
    {
        "manifest_version",
        "run_id",
        "created_at",
        "route_scope",
        "run_mode",
        "evidence_mode",
        "strategy_candidate_id",
        "strategy_candidate_ref",
        "input_artifact_refs",
        "output_artifact_refs",
        "data_context",
        "universe_scope",
        "date_range",
        "horizon_policy_id",
        "horizon_policy_snapshot",
        "signal_frequency",
        "entry_lag_trading_days",
        "holding_period_trading_days",
        "rebalance_frequency",
        "label_horizon",
        "simulation_horizon",
        "calendar_policy",
        "rebalance_disclosure",
        "cost_model",
        "slippage_model",
        "turnover_tracking_enabled",
        "random_seed",
        "code_version",
        "config_refs",
        "evidence_only_notice",
        "prohibited_actions_notice",
        "live_execution_enabled",
        "brokerage_integration_enabled",
        "order_generation_enabled",
        "user_facing_auto_rebalance_instruction_enabled",
        "phase4_weight_loop_enabled",
    }
)


def build_simulation_run_manifest(
    *,
    strategy_candidate_id: str,
    strategy_candidate_ref: str,
    date_range: Mapping[str, str],
    horizon_policy: HorizonPolicy | Mapping[str, Any] | None = None,
    horizon_policy_id: str | None = None,
    run_id: str | None = None,
    created_at: str | None = None,
    route_scope: str = "v1_0_rc_candidate_evidence",
    run_mode: str = "candidate_only_backtest",
    evidence_mode: str = "evidence_only",
    input_artifact_refs: Sequence[str] | None = None,
    output_artifact_refs: Sequence[str] | None = None,
    data_context: str = "candidate_only_local_context",
    universe_scope: str = "KOSPI200_candidate_only",
    rebalance_disclosure: str | None = None,
    cost_model: str = "configured_or_not_applicable",
    slippage_model: str = "configured_or_not_applicable",
    turnover_tracking_enabled: bool = True,
    random_seed: int | None = None,
    code_version: str = "local_not_recorded",
    config_refs: Sequence[str] | None = None,
    live_execution_enabled: bool = False,
    brokerage_integration_enabled: bool = False,
    order_generation_enabled: bool = False,
    user_facing_auto_rebalance_instruction_enabled: bool = False,
    phase4_weight_loop_enabled: bool = False,
) -> dict[str, Any]:
    """Build and validate a candidate-only SimulationRunManifest."""

    policy = _resolve_policy(horizon_policy, horizon_policy_id)
    disclosure = rebalance_disclosure or _default_rebalance_disclosure(policy)
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "run_id": run_id
        or make_simulation_run_id(
            strategy_candidate_id=strategy_candidate_id,
            horizon_policy_id=policy.horizon_id,
            date_range=date_range,
            config_refs=config_refs or ("config/horizon_policy.toml",),
        ),
        "created_at": created_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "route_scope": route_scope,
        "run_mode": run_mode,
        "evidence_mode": evidence_mode,
        "strategy_candidate_id": strategy_candidate_id,
        "strategy_candidate_ref": strategy_candidate_ref,
        "input_artifact_refs": list(input_artifact_refs or []),
        "output_artifact_refs": list(output_artifact_refs or []),
        "data_context": data_context,
        "universe_scope": universe_scope,
        "date_range": dict(date_range),
        "horizon_policy_id": policy.horizon_id,
        "horizon_policy_snapshot": policy.to_dict(),
        "signal_frequency": policy.signal_frequency,
        "entry_lag_trading_days": policy.entry_lag_trading_days,
        "holding_period_trading_days": policy.holding_period_trading_days,
        "rebalance_frequency": policy.rebalance_frequency,
        "label_horizon": policy.label_horizon,
        "simulation_horizon": policy.simulation_horizon,
        "calendar_policy": policy.calendar_policy,
        "rebalance_disclosure": disclosure,
        "cost_model": cost_model,
        "slippage_model": slippage_model,
        "turnover_tracking_enabled": bool(turnover_tracking_enabled),
        "random_seed": random_seed,
        "code_version": code_version,
        "config_refs": list(config_refs or ["config/horizon_policy.toml"]),
        "evidence_only_notice": EVIDENCE_ONLY_NOTICE,
        "prohibited_actions_notice": PROHIBITED_ACTIONS_NOTICE,
        "live_execution_enabled": bool(live_execution_enabled),
        "brokerage_integration_enabled": bool(brokerage_integration_enabled),
        "order_generation_enabled": bool(order_generation_enabled),
        "user_facing_auto_rebalance_instruction_enabled": bool(
            user_facing_auto_rebalance_instruction_enabled
        ),
        "phase4_weight_loop_enabled": bool(phase4_weight_loop_enabled),
    }
    validate_simulation_run_manifest(manifest)
    return manifest


def validate_simulation_run_manifest(manifest: Mapping[str, Any]) -> None:
    """Validate evidence-only SimulationRunManifest boundaries."""

    missing = sorted(REQUIRED_MANIFEST_FIELDS.difference(manifest))
    if missing:
        raise ValueError(f"SimulationRunManifest missing required fields: {', '.join(missing)}")
    if manifest["manifest_version"] != MANIFEST_VERSION:
        raise ValueError("unsupported SimulationRunManifest manifest_version")
    if manifest["run_mode"] not in ALLOWED_RUN_MODES:
        raise ValueError(f"blocked or unsupported run_mode: {manifest['run_mode']}")
    if manifest["evidence_mode"] not in ALLOWED_EVIDENCE_MODES:
        raise ValueError(f"blocked or unsupported evidence_mode: {manifest['evidence_mode']}")
    if not isinstance(manifest["horizon_policy_snapshot"], Mapping):
        raise ValueError("SimulationRunManifest requires a HorizonPolicy snapshot")
    policy = HorizonPolicy.from_mapping(manifest["horizon_policy_snapshot"])
    for field_name in (
        "horizon_policy_id",
        "signal_frequency",
        "entry_lag_trading_days",
        "holding_period_trading_days",
        "rebalance_frequency",
        "label_horizon",
        "simulation_horizon",
        "calendar_policy",
    ):
        expected = policy.horizon_id if field_name == "horizon_policy_id" else getattr(policy, field_name)
        if manifest[field_name] != expected:
            raise ValueError(f"SimulationRunManifest {field_name} must match HorizonPolicy snapshot")
    if manifest["rebalance_frequency"] != "none" and not str(manifest["rebalance_disclosure"]).strip():
        raise ValueError("SimulationRunManifest requires rebalance_disclosure when rebalancing is present")
    for flag in (
        "live_execution_enabled",
        "brokerage_integration_enabled",
        "order_generation_enabled",
        "user_facing_auto_rebalance_instruction_enabled",
        "phase4_weight_loop_enabled",
    ):
        if bool(manifest[flag]):
            raise ValueError(f"SimulationRunManifest blocked flag must remain false: {flag}")
    _reject_blocked_runtime_values(manifest)


def make_simulation_run_id(
    *,
    strategy_candidate_id: str,
    horizon_policy_id: str,
    date_range: Mapping[str, str],
    config_refs: Sequence[str],
) -> str:
    """Return a stable local run ID for the manifest inputs."""

    start = str(date_range.get("start") or "unknown_start")
    end = str(date_range.get("end") or "unknown_end")
    digest_source = "|".join([strategy_candidate_id, horizon_policy_id, start, end, *config_refs])
    digest = sha256(digest_source.encode("utf-8")).hexdigest()[:12]
    slug = _slug(f"{strategy_candidate_id}_{horizon_policy_id}_{start}_{end}")
    return f"sim_v1_0_rc_{slug}_{digest}"


def _resolve_policy(
    policy: HorizonPolicy | Mapping[str, Any] | None,
    horizon_policy_id: str | None,
) -> HorizonPolicy:
    if isinstance(policy, HorizonPolicy):
        return policy
    if isinstance(policy, Mapping):
        return HorizonPolicy.from_mapping(policy)
    return resolve_horizon_policy(horizon_policy_id)


def _default_rebalance_disclosure(policy: HorizonPolicy) -> str:
    if policy.rebalance_frequency == "none":
        return "rebalancing_not_used_in_this_candidate_only_simulation"
    return (
        f"{policy.rebalance_frequency}_rebalancing_is_historical_simulation_context_only; "
        "not_user_instruction"
    )


def _reject_blocked_runtime_values(manifest: Mapping[str, Any]) -> None:
    allowed_notice_fields = {"prohibited_actions_notice"}
    for key, value in manifest.items():
        if key in allowed_notice_fields:
            continue
        values = value.values() if isinstance(value, Mapping) else value
        if isinstance(values, str):
            candidates = [values]
        elif isinstance(values, Sequence) and not isinstance(values, (bytes, bytearray)):
            candidates = [str(item) for item in values]
        else:
            candidates = [str(values)]
        for text in candidates:
            normalized = text.strip().lower()
            if normalized in BLOCKED_RUNTIME_VALUES:
                raise ValueError(f"SimulationRunManifest contains blocked runtime value: {normalized}")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug or "unknown"


__all__ = (
    "ALLOWED_EVIDENCE_MODES",
    "ALLOWED_RUN_MODES",
    "EVIDENCE_ONLY_NOTICE",
    "MANIFEST_VERSION",
    "PROHIBITED_ACTIONS_NOTICE",
    "build_simulation_run_manifest",
    "make_simulation_run_id",
    "validate_simulation_run_manifest",
)
