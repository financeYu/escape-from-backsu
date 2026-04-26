"""Step 18 candidate valuation/fundamental report builder."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from src.valuation.contracts import ValuationCandidateRecord
from src.valuation.registry import DEFAULT_STEP18_METRIC_REGISTRY, MetricSpec
from src.valuation.validation import validate_candidate_records


STEP18_CANDIDATE_REPORT_NOTICES: tuple[str, ...] = (
    "Step 18 candidate valuation/fundamental expansion",
    "not activated in final ranking",
    "not validated alpha signals",
    "must not be used in backtests unless availability-date rules are enforced",
)


def build_step18_candidate_report(
    records: Iterable[Mapping[str, Any] | ValuationCandidateRecord],
    *,
    evaluation_date: object | None = None,
    registry: Sequence[MetricSpec] = DEFAULT_STEP18_METRIC_REGISTRY,
) -> str:
    """Build a small Markdown report for candidate-only valuation data."""

    validated = validate_candidate_records(
        tuple(records),
        evaluation_date=evaluation_date,
        registry=registry,
    )
    category_counts = Counter(record.metric_category for record in validated)
    metric_names = sorted({record.metric for record in validated})
    evaluation_label = "not supplied" if evaluation_date is None else str(evaluation_date)

    lines = [
        "# Step 18 Valuation / Fundamental Candidate Report",
        "",
        "This is Step 18 candidate valuation/fundamental expansion.",
        "These fields are not activated in final ranking.",
        "These fields are not validated alpha signals.",
        "These fields must not be used in backtests unless availability-date rules are enforced.",
        "",
        "## Scope",
        "",
        "- candidate-only explanatory data",
        "- no technical score changes",
        "- no final ranking changes",
        "- no backtest usage without availability-date validation",
        "",
        "## Validation Summary",
        "",
        f"- evaluation_date: {evaluation_label}",
        f"- candidate_records: {len(validated)}",
        f"- metrics: {', '.join(metric_names) if metric_names else 'none'}",
    ]
    for category, count in sorted(category_counts.items()):
        lines.append(f"- {category}: {count}")
    return "\n".join(lines) + "\n"


__all__ = ("STEP18_CANDIDATE_REPORT_NOTICES", "build_step18_candidate_report")
