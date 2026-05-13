"""v1.0-rc LayerRegistry loader and validator.

The registry is an extension contract. It keeps future layers explicit while
blocking production activation, live execution, and inactive scoring paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import hashlib
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LAYER_REGISTRY_CONFIG = PROJECT_ROOT / "config" / "layer_registry.toml"

ALLOWED_LAYER_STATUSES = frozenset(
    {"active", "inactive", "candidate_only", "diagnostic_only", "diagnostic_reference"}
)
ALLOWED_LAYER_CATEGORIES = frozenset(
    {
        "technical",
        "statistical",
        "regime",
        "macro",
        "valuation",
        "fundamental",
        "futures",
        "index",
        "diagnostic",
        "reference",
    }
)
ALLOWED_MODES = frozenset({"candidate_only_backtest", "candidate_only_simulation", "dry_run_plan_only"})
BLOCKED_MODES = frozenset(
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
NON_ACTIVE_SCORING_CATEGORIES = frozenset(
    {"valuation", "fundamental", "futures", "index", "macro", "regime"}
)
ACTIVE_WEIGHT_CATEGORIES = frozenset({"technical", "statistical"})
REQUIRED_LAYER_FIELDS = frozenset(
    {
        "layer_id",
        "layer_name",
        "layer_version",
        "layer_category",
        "layer_status",
        "adapter_ref",
        "input_schema_ref",
        "output_schema_ref",
        "required_inputs",
        "optional_inputs",
        "output_fields",
        "owner_route",
        "allowed_modes",
        "blocked_modes",
        "evidence_role",
        "scoring_role",
        "ranking_role",
        "production_enabled",
        "candidate_only_enabled",
        "diagnostic_only_enabled",
        "valuation_fundamental_active_scoring_enabled",
        "live_execution_enabled",
        "notes",
        "validation_rules",
        "dependency_refs",
    }
)


@dataclass(frozen=True)
class LayerDefinition:
    layer_id: str
    layer_name: str
    layer_version: str
    layer_category: str
    layer_status: str
    adapter_ref: str
    input_schema_ref: str
    output_schema_ref: str
    required_inputs: tuple[str, ...]
    optional_inputs: tuple[str, ...]
    output_fields: tuple[str, ...]
    owner_route: str
    allowed_modes: tuple[str, ...]
    blocked_modes: tuple[str, ...]
    evidence_role: str
    scoring_role: str
    ranking_role: str
    production_enabled: bool
    candidate_only_enabled: bool
    diagnostic_only_enabled: bool
    valuation_fundamental_active_scoring_enabled: bool
    live_execution_enabled: bool
    brokerage_integration_enabled: bool = False
    order_generation_enabled: bool = False
    notes: str = ""
    validation_rules: tuple[str, ...] = ()
    dependency_refs: tuple[str, ...] = ()
    config_digest: str = ""

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, Any],
        *,
        config_digest: str = "",
    ) -> "LayerDefinition":
        missing = sorted(REQUIRED_LAYER_FIELDS.difference(values))
        if missing:
            raise ValueError(f"LayerRegistry entry missing required fields: {', '.join(missing)}")
        layer = cls(
            layer_id=_required_text(values, "layer_id"),
            layer_name=_required_text(values, "layer_name"),
            layer_version=_required_text(values, "layer_version"),
            layer_category=_required_text(values, "layer_category").lower(),
            layer_status=_required_text(values, "layer_status").lower(),
            adapter_ref=_required_text(values, "adapter_ref"),
            input_schema_ref=_required_text(values, "input_schema_ref"),
            output_schema_ref=_required_text(values, "output_schema_ref"),
            required_inputs=_text_tuple(values.get("required_inputs", ())),
            optional_inputs=_text_tuple(values.get("optional_inputs", ())),
            output_fields=_text_tuple(values.get("output_fields", ())),
            owner_route=_required_text(values, "owner_route"),
            allowed_modes=_text_tuple(values.get("allowed_modes", ())),
            blocked_modes=_text_tuple(values.get("blocked_modes", ())),
            evidence_role=_required_text(values, "evidence_role"),
            scoring_role=_required_text(values, "scoring_role"),
            ranking_role=_required_text(values, "ranking_role"),
            production_enabled=bool(values.get("production_enabled", False)),
            candidate_only_enabled=bool(values.get("candidate_only_enabled", False)),
            diagnostic_only_enabled=bool(values.get("diagnostic_only_enabled", False)),
            valuation_fundamental_active_scoring_enabled=bool(
                values.get("valuation_fundamental_active_scoring_enabled", False)
            ),
            live_execution_enabled=bool(values.get("live_execution_enabled", False)),
            brokerage_integration_enabled=bool(values.get("brokerage_integration_enabled", False)),
            order_generation_enabled=bool(values.get("order_generation_enabled", False)),
            notes=str(values.get("notes") or ""),
            validation_rules=_text_tuple(values.get("validation_rules", ())),
            dependency_refs=_text_tuple(values.get("dependency_refs", ())),
            config_digest=config_digest,
        )
        validate_layer_definition(layer)
        return layer

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "layer_name": self.layer_name,
            "layer_version": self.layer_version,
            "layer_category": self.layer_category,
            "layer_status": self.layer_status,
            "adapter_ref": self.adapter_ref,
            "input_schema_ref": self.input_schema_ref,
            "output_schema_ref": self.output_schema_ref,
            "required_inputs": list(self.required_inputs),
            "optional_inputs": list(self.optional_inputs),
            "output_fields": list(self.output_fields),
            "owner_route": self.owner_route,
            "allowed_modes": list(self.allowed_modes),
            "blocked_modes": list(self.blocked_modes),
            "evidence_role": self.evidence_role,
            "scoring_role": self.scoring_role,
            "ranking_role": self.ranking_role,
            "production_enabled": self.production_enabled,
            "candidate_only_enabled": self.candidate_only_enabled,
            "diagnostic_only_enabled": self.diagnostic_only_enabled,
            "valuation_fundamental_active_scoring_enabled": (
                self.valuation_fundamental_active_scoring_enabled
            ),
            "live_execution_enabled": self.live_execution_enabled,
            "brokerage_integration_enabled": self.brokerage_integration_enabled,
            "order_generation_enabled": self.order_generation_enabled,
            "notes": self.notes,
            "validation_rules": list(self.validation_rules),
            "dependency_refs": list(self.dependency_refs),
            "config_digest": self.config_digest,
        }


@dataclass(frozen=True)
class LayerRegistry:
    layers: tuple[LayerDefinition, ...]
    config_digest: str = ""

    def __post_init__(self) -> None:
        validate_layer_registry(self)

    @property
    def by_id(self) -> dict[str, LayerDefinition]:
        return {layer.layer_id: layer for layer in self.layers}

    def require_layer(self, layer_id: str) -> LayerDefinition:
        try:
            return self.by_id[layer_id]
        except KeyError as exc:
            raise ValueError(f"unknown LayerRegistry layer_id: {layer_id}") from exc

    def validate_active_weight_layers(self, layer_ids: tuple[str, ...]) -> None:
        for layer_id in layer_ids:
            layer = self.require_layer(layer_id)
            if not is_active_weight_layer(layer):
                raise ValueError(f"LayerRegistry layer cannot be used as active weight: {layer_id}")


class LayerAdapter:
    """Minimal adapter contract for future layer implementations."""

    layer_id: str

    def __init__(self, layer_id: str) -> None:
        self.layer_id = layer_id

    def validate_inputs(self, inputs: Mapping[str, Any]) -> None:
        if not isinstance(inputs, Mapping):
            raise ValueError("LayerAdapter inputs must be a mapping")

    def build_candidate_output(self, inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        raise NotImplementedError("LayerAdapter candidate output is not implemented in Phase 5")

    def build_diagnostic_output(self, inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        raise NotImplementedError("LayerAdapter diagnostic output is not implemented in Phase 5")

    def describe_contract(self) -> dict[str, str]:
        return {"layer_id": self.layer_id, "phase": "v1.0-rc Phase 5 interface only"}


class NonComputingLayerAdapter(LayerAdapter):
    """No-op descriptor for inactive or placeholder layers."""

    def build_candidate_output(self, inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        self.validate_inputs(inputs)
        return {"layer_id": self.layer_id, "status": "non_computing_placeholder"}

    def build_diagnostic_output(self, inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        self.validate_inputs(inputs)
        return {"layer_id": self.layer_id, "status": "non_computing_placeholder"}


def load_layer_registry_config(config_path: str | Path | None = None) -> tuple[dict[str, Any], str]:
    path = Path(config_path) if config_path is not None else DEFAULT_LAYER_REGISTRY_CONFIG
    raw = path.read_bytes()
    payload = tomllib.loads(raw.decode("utf-8"))
    if "layer" not in payload:
        raise ValueError("LayerRegistry config must define [[layer]] entries")
    return payload, hashlib.sha256(raw).hexdigest()


def load_layer_registry(config_path: str | Path | None = None) -> LayerRegistry:
    payload, digest = load_layer_registry_config(config_path)
    layers = tuple(
        LayerDefinition.from_mapping(entry, config_digest=digest)
        for entry in payload.get("layer", ())
        if isinstance(entry, Mapping)
    )
    return LayerRegistry(layers=layers, config_digest=digest)


def validate_layer_registry(registry: LayerRegistry) -> None:
    if not registry.layers:
        raise ValueError("LayerRegistry must contain at least one layer")
    ids = [layer.layer_id for layer in registry.layers]
    duplicates = sorted({layer_id for layer_id in ids if ids.count(layer_id) > 1})
    if duplicates:
        raise ValueError(f"LayerRegistry duplicate layer_id: {', '.join(duplicates)}")
    for layer in registry.layers:
        validate_layer_definition(layer)


def validate_layer_definition(layer: LayerDefinition) -> None:
    if layer.layer_status not in ALLOWED_LAYER_STATUSES:
        raise ValueError(f"unknown LayerRegistry layer_status: {layer.layer_status}")
    if layer.layer_category not in ALLOWED_LAYER_CATEGORIES:
        raise ValueError(f"unknown LayerRegistry layer_category: {layer.layer_category}")
    unknown_allowed = sorted(set(layer.allowed_modes).difference(ALLOWED_MODES))
    if unknown_allowed:
        raise ValueError(f"LayerRegistry allowed_modes contain unsupported modes: {', '.join(unknown_allowed)}")
    missing_blocked = sorted(BLOCKED_MODES.difference(layer.blocked_modes))
    if missing_blocked:
        raise ValueError(f"LayerRegistry blocked_modes missing: {', '.join(missing_blocked)}")
    if layer.production_enabled:
        raise ValueError(f"LayerRegistry production_enabled must remain false: {layer.layer_id}")
    if layer.live_execution_enabled:
        raise ValueError(f"LayerRegistry live_execution_enabled must remain false: {layer.layer_id}")
    if layer.brokerage_integration_enabled:
        raise ValueError(f"LayerRegistry brokerage_integration_enabled must remain false: {layer.layer_id}")
    if layer.order_generation_enabled:
        raise ValueError(f"LayerRegistry order_generation_enabled must remain false: {layer.layer_id}")
    if (
        layer.layer_category in {"valuation", "fundamental"}
        and layer.valuation_fundamental_active_scoring_enabled
    ):
        raise ValueError("valuation/fundamental active scoring must remain disabled")
    if layer.layer_category in {"valuation", "fundamental"} and layer.layer_status == "active":
        raise ValueError("valuation/fundamental layers cannot be active in Phase 5")
    if layer.layer_category in {"futures", "index", "macro", "regime"} and layer.layer_status == "active":
        raise ValueError("futures/index/macro/regime layers cannot be active scoring layers in Phase 5")
    if layer.layer_category in NON_ACTIVE_SCORING_CATEGORIES and layer.scoring_role not in {
        "none",
        "diagnostic_context",
        "candidate_placeholder",
        "reference_only",
    }:
        raise ValueError("future expansion layers must not claim active scoring_role")
    if layer.layer_status in {"diagnostic_only", "diagnostic_reference"}:
        if layer.ranking_role != "none":
            raise ValueError("diagnostic/reference layers must not claim ranking_role")
        if layer.scoring_role not in {"none", "diagnostic_context", "reference_only"}:
            raise ValueError("diagnostic/reference layers must not claim scoring role")
    if layer.layer_status == "candidate_only" and layer.ranking_role != "none":
        raise ValueError("candidate_only layers must not feed production ranking")


def is_active_weight_layer(layer: LayerDefinition) -> bool:
    return (
        layer.layer_status == "active"
        and layer.layer_category in ACTIVE_WEIGHT_CATEGORIES
        and layer.scoring_role == "candidate_evidence_input"
        and layer.ranking_role == "none"
        and layer.candidate_only_enabled
        and not layer.production_enabled
        and not layer.live_execution_enabled
    )


def _required_text(values: Mapping[str, Any], field_name: str) -> str:
    text = str(values.get(field_name) or "").strip()
    if not text:
        raise ValueError(f"LayerRegistry field must be non-empty: {field_name}")
    return text


def _text_tuple(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        return (values,)
    return tuple(str(value).strip() for value in values if str(value).strip())


__all__ = (
    "ALLOWED_LAYER_CATEGORIES",
    "ALLOWED_LAYER_STATUSES",
    "BLOCKED_MODES",
    "DEFAULT_LAYER_REGISTRY_CONFIG",
    "LayerAdapter",
    "LayerDefinition",
    "LayerRegistry",
    "NonComputingLayerAdapter",
    "is_active_weight_layer",
    "load_layer_registry",
    "load_layer_registry_config",
    "validate_layer_definition",
    "validate_layer_registry",
)
