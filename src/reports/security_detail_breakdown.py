"""Step 16 security detail score and component breakdown helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from src.composite.contracts import CompositeInputSpec
from src.reports.security_detail_explanations import (
    is_context_metadata,
    score_explanation,
)
from src.reports.security_detail_metadata import safe_float, safe_int, safe_scalar
from src.reports.security_detail_report_contracts import (
    STEP16_READONLY_RANK_FIELD_COLUMNS,
    SecurityComponentBreakdown,
    SecurityReportDisplayRole,
    SecurityScoreBreakdown,
)


def build_score_breakdown(
    row: pd.Series,
    *,
    metadata_by_score: Mapping[str, Mapping[str, Any]],
    registry: Sequence[CompositeInputSpec],
) -> tuple[SecurityScoreBreakdown, ...]:
    breakdown: list[SecurityScoreBreakdown] = []
    for spec in registry:
        if spec.normalized_column not in row.index:
            continue
        metadata = metadata_by_score.get(spec.score_name, {})
        score = SecurityScoreBreakdown(
            score_name=spec.score_name,
            source_column=spec.normalized_column,
            score_value=safe_float(row.get(spec.normalized_column)),
            score_family=str(metadata.get("family", spec.family)),
            score_role=str(metadata.get("role", spec.role.value)),
            score_branch=str(metadata.get("branch", spec.branch)),
            eligibility=str(metadata.get("eligibility", spec.eligibility.value)),
            adoption_state=str(metadata.get("adoption_state", "")),
            source_review_status=str(metadata.get("source_review_status", "")),
            readonly_step15_component=True,
            context_only=False,
            display_role=SecurityReportDisplayRole.READONLY_STEP15_SCORE_COMPONENT.value,
            status=str(safe_scalar(row.get(spec.status_column, "")) or ""),
            quality_flag=str(safe_scalar(row.get(spec.quality_flag_column, "")) or ""),
            valid_count=safe_int(row.get(spec.count_column)),
            explanation=score_explanation(spec.score_name, metadata),
        )
        breakdown.append(score)
    return tuple(breakdown)


def build_diagnostic_context(
    *,
    metadata_by_score: Mapping[str, Mapping[str, Any]],
    score_breakdown: Sequence[SecurityScoreBreakdown],
    registry: Sequence[CompositeInputSpec],
) -> tuple[SecurityScoreBreakdown, ...]:
    displayed = {score.score_name for score in score_breakdown}
    registry_by_name = {spec.score_name: spec for spec in registry}
    context_rows: list[SecurityScoreBreakdown] = []
    for score_name in sorted(metadata_by_score):
        if score_name in displayed:
            continue
        metadata = metadata_by_score[score_name]
        spec = registry_by_name.get(score_name)
        role = str(metadata.get("role", spec.role.value if spec else ""))
        branch = str(metadata.get("branch", spec.branch if spec else ""))
        adoption_state = str(metadata.get("adoption_state", ""))
        if not is_context_metadata(role=role, branch=branch, adoption_state=adoption_state):
            continue
        context_rows.append(
            SecurityScoreBreakdown(
                score_name=score_name,
                source_column=str(metadata.get("normalized_score_column", "")),
                score_value=None,
                score_family=str(metadata.get("family", spec.family if spec else "")),
                score_role=role,
                score_branch=branch,
                eligibility=str(
                    metadata.get("eligibility", spec.eligibility.value if spec else "")
                ),
                adoption_state=adoption_state,
                source_review_status=str(metadata.get("source_review_status", "")),
                readonly_step15_component=False,
                context_only=True,
                display_role=SecurityReportDisplayRole.DIAGNOSTIC_CONTEXT_NOT_RANK_DRIVER.value,
                explanation=score_explanation(score_name, metadata),
            )
        )
    return tuple(context_rows)


def build_component_breakdown(row: pd.Series) -> tuple[SecurityComponentBreakdown, ...]:
    components: list[SecurityComponentBreakdown] = []
    for column in row.index:
        normalized = str(column)
        if not normalized.endswith("_family_score"):
            continue
        component_name = normalized.removesuffix("_family_score")
        components.append(
            SecurityComponentBreakdown(
                component_name=component_name,
                component_type="family_score",
                source_column=normalized,
                value=safe_float(row.get(column)),
            )
        )
    return tuple(components)


def extract_readonly_rank_fields(row: pd.Series) -> dict[str, Any]:
    return {
        column: safe_scalar(row[column])
        for column in STEP16_READONLY_RANK_FIELD_COLUMNS
        if column in row.index
    }


def extract_quality_flags(row: pd.Series) -> dict[str, Any]:
    quality: dict[str, Any] = {}
    for column in row.index:
        normalized = str(column)
        if (
            "warmup" in normalized
            or "coverage" in normalized
            or "quality" in normalized
            or "validity" in normalized
            or normalized.endswith(("_status", "_flag", "_metric", "_count"))
        ):
            quality[normalized] = safe_scalar(row[column])
    return quality


__all__ = (
    "build_component_breakdown",
    "build_diagnostic_context",
    "build_score_breakdown",
    "extract_quality_flags",
    "extract_readonly_rank_fields",
)
