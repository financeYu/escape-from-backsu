"""Step 18 conservative valuation/fundamental candidate metric registry."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import tomllib

from src.valuation.contracts import MetricCategory


@dataclass(frozen=True)
class MetricSpec:
    """Allowed Step 18 candidate metric metadata."""

    metric_name: str
    metric_category: str
    metric_unit: str
    numeric_required: bool = True
    candidate_only: bool = True
    notes: str = ""


DEFAULT_STEP18_METRIC_REGISTRY: tuple[MetricSpec, ...] = (
    MetricSpec("per", MetricCategory.VALUATION.value, "ratio"),
    MetricSpec("pbr", MetricCategory.VALUATION.value, "ratio"),
    MetricSpec("psr", MetricCategory.VALUATION.value, "ratio"),
    MetricSpec("pcr", MetricCategory.VALUATION.value, "ratio"),
    MetricSpec("dividend_yield", MetricCategory.VALUATION.value, "percent"),
    MetricSpec("roe", MetricCategory.PROFITABILITY.value, "percent"),
    MetricSpec("roa", MetricCategory.PROFITABILITY.value, "percent"),
    MetricSpec("operating_margin", MetricCategory.PROFITABILITY.value, "percent"),
    MetricSpec("net_margin", MetricCategory.PROFITABILITY.value, "percent"),
    MetricSpec("debt_to_equity", MetricCategory.LEVERAGE.value, "ratio"),
    MetricSpec("current_ratio", MetricCategory.QUALITY.value, "ratio"),
    MetricSpec("revenue_growth_yoy", MetricCategory.GROWTH.value, "percent"),
    MetricSpec("operating_income_growth_yoy", MetricCategory.GROWTH.value, "percent"),
    MetricSpec("eps_growth_yoy", MetricCategory.GROWTH.value, "percent"),
)


def metric_registry_by_name(
    registry: Sequence[MetricSpec] = DEFAULT_STEP18_METRIC_REGISTRY,
) -> dict[str, MetricSpec]:
    """Return registry specs keyed by normalized metric name."""

    validate_metric_registry(registry)
    return {spec.metric_name.lower(): spec for spec in registry}


def validate_metric_registry(
    registry: Sequence[MetricSpec] = DEFAULT_STEP18_METRIC_REGISTRY,
) -> None:
    """Validate registry shape without activating any score."""

    names = [spec.metric_name.lower() for spec in registry]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"Step 18 metric registry has duplicate metrics: {', '.join(duplicates)}")
    invalid_categories = sorted(
        {
            spec.metric_category
            for spec in registry
            if spec.metric_category not in {category.value for category in MetricCategory}
        }
    )
    if invalid_categories:
        raise ValueError(
            "Step 18 metric registry has unsupported categories: "
            f"{', '.join(invalid_categories)}"
        )
    active_specs = [spec.metric_name for spec in registry if not spec.candidate_only]
    if active_specs:
        raise ValueError(
            "Step 18 metric registry must remain candidate-only: "
            f"{', '.join(active_specs)}"
        )
    if "ev_ebitda" in names:
        raise ValueError(
            "Step 18 registry must not allow ev_ebitda until enterprise value inputs exist."
        )


def load_metric_registry(
    path: str | Path = "config/valuation_fundamental_metrics.toml",
) -> tuple[MetricSpec, ...]:
    """Load Step 18 candidate metric registry from TOML."""

    with Path(path).open("rb") as handle:
        payload = tomllib.load(handle)
    metrics = payload.get("metrics", [])
    if not isinstance(metrics, list):
        raise ValueError("Step 18 metric registry TOML must define a metrics list.")
    registry = tuple(_metric_spec_from_mapping(metric) for metric in metrics)
    validate_metric_registry(registry)
    return registry


def _metric_spec_from_mapping(values: Mapping[str, object]) -> MetricSpec:
    return MetricSpec(
        metric_name=str(values.get("metric_name", "")).strip().lower(),
        metric_category=str(values.get("metric_category", "")).strip().lower(),
        metric_unit=str(values.get("metric_unit", "")).strip().lower(),
        numeric_required=bool(values.get("numeric_required", True)),
        candidate_only=bool(values.get("candidate_only", True)),
        notes=str(values.get("notes", "")).strip(),
    )


__all__ = (
    "DEFAULT_STEP18_METRIC_REGISTRY",
    "MetricSpec",
    "load_metric_registry",
    "metric_registry_by_name",
    "validate_metric_registry",
)
