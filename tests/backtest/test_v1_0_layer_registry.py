from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.validation.layer_registry import (  # noqa: E402
    LayerAdapter,
    LayerDefinition,
    LayerRegistry,
    load_layer_registry,
    load_layer_registry_config,
)


def _layer_payload(layer_id: str = "technical_fixture_layer") -> dict[str, object]:
    payload, _ = load_layer_registry_config()
    layer = dict(payload["layer"][0])
    layer["layer_id"] = layer_id
    return layer


def test_layer_registry_loads_fixture_layers() -> None:
    registry = load_layer_registry()

    assert {"technical_momentum_layer", "statistical_volatility_layer"}.issubset(registry.by_id)
    assert registry.by_id["valuation_placeholder_layer"].layer_status == "candidate_only"
    assert registry.by_id["diagnostic_data_quality_layer"].layer_status == "diagnostic_only"
    assert registry.by_id["futures_macro_reference_layer"].layer_status == "inactive"


def test_layer_registry_rejects_duplicate_layer_ids() -> None:
    first = LayerDefinition.from_mapping(_layer_payload("duplicate_layer"))
    second = LayerDefinition.from_mapping(_layer_payload("duplicate_layer"))

    with pytest.raises(ValueError, match="duplicate layer_id"):
        LayerRegistry(layers=(first, second))


def test_layer_registry_rejects_unknown_status() -> None:
    layer = _layer_payload()
    layer["layer_status"] = "unknown"

    with pytest.raises(ValueError, match="unknown LayerRegistry layer_status"):
        LayerDefinition.from_mapping(layer)


def test_layer_registry_rejects_unknown_category() -> None:
    layer = _layer_payload()
    layer["layer_category"] = "mystery"

    with pytest.raises(ValueError, match="unknown LayerRegistry layer_category"):
        LayerDefinition.from_mapping(layer)


def test_layer_registry_blocks_valuation_active_scoring() -> None:
    layer = _layer_payload("valuation_bad_layer")
    layer["layer_category"] = "valuation"
    layer["layer_status"] = "active"

    with pytest.raises(ValueError, match="valuation/fundamental layers cannot be active"):
        LayerDefinition.from_mapping(layer)


def test_layer_registry_blocks_fundamental_active_scoring() -> None:
    layer = _layer_payload("fundamental_bad_layer")
    layer["layer_category"] = "fundamental"
    layer["valuation_fundamental_active_scoring_enabled"] = True

    with pytest.raises(ValueError, match="valuation/fundamental active scoring"):
        LayerDefinition.from_mapping(layer)


@pytest.mark.parametrize("category", ["futures", "index", "macro", "regime"])
def test_layer_registry_blocks_futures_index_macro_regime_active_scoring(category: str) -> None:
    layer = _layer_payload(f"{category}_bad_layer")
    layer["layer_category"] = category
    layer["layer_status"] = "active"

    with pytest.raises(ValueError, match="cannot be active scoring"):
        LayerDefinition.from_mapping(layer)


def test_layer_registry_blocks_live_execution() -> None:
    layer = _layer_payload("live_bad_layer")
    layer["live_execution_enabled"] = True

    with pytest.raises(ValueError, match="live_execution_enabled"):
        LayerDefinition.from_mapping(layer)


def test_layer_registry_blocks_order_generation() -> None:
    layer = _layer_payload("order_bad_layer")
    layer["order_generation_enabled"] = True

    with pytest.raises(ValueError, match="order_generation_enabled"):
        LayerDefinition.from_mapping(layer)


def test_layer_registry_blocks_trade_signal_role() -> None:
    layer = _layer_payload("diagnostic_bad_layer")
    layer["layer_status"] = "diagnostic_only"
    layer["ranking_role"] = "trade_signal"

    with pytest.raises(ValueError, match="diagnostic/reference layers must not claim ranking_role"):
        LayerDefinition.from_mapping(layer)


def test_layer_registry_allows_candidate_only_placeholder() -> None:
    registry = load_layer_registry()
    layer = registry.by_id["valuation_placeholder_layer"]

    assert layer.layer_status == "candidate_only"
    assert layer.production_enabled is False
    assert layer.valuation_fundamental_active_scoring_enabled is False


def test_layer_registry_allows_diagnostic_only_without_scoring_role() -> None:
    registry = load_layer_registry()
    layer = registry.by_id["diagnostic_data_quality_layer"]

    assert layer.layer_status == "diagnostic_only"
    assert layer.ranking_role == "none"
    assert layer.scoring_role == "diagnostic_context"


def test_layer_adapter_interface_exists_without_future_implementation() -> None:
    adapter = LayerAdapter("technical_momentum_layer")

    adapter.validate_inputs({})
    assert adapter.describe_contract()["phase"] == "v1.0-rc Phase 5 interface only"
    with pytest.raises(NotImplementedError):
        adapter.build_candidate_output({})
