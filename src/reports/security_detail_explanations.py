"""Step 16 security detail explanation helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

from src.reports.security_detail_metadata import is_present, safe_scalar
from src.reports.security_detail_report_contracts import validate_step16_report_text


DIRECT_ADOPTION_STATES = frozenset({"core_adopted", "technical_only"})
CONTEXT_ADOPTION_STATES = frozenset(
    {
        "conditional_adopted",
        "regime_only",
        "diagnostic_only",
        "research_only",
    }
)
EXPLANATION_ADOPTION_STATES = frozenset(
    {
        "rejected",
        "blocked_by_data",
        "needs_manual_review",
    }
)
CONTEXT_ROLES = frozenset({"confirmation", "setup_context", "diagnostic_context"})
HEALTHY_STATUS_VALUES = frozenset({"", "ok", "valid", "adequate", "ready", "false"})

ROW_EXPLANATION_COLUMNS: tuple[str, ...] = (
    "diagnostic_note",
    "ranking_reason_code",
    "blocked_reason",
    "manual_review_reason",
    "limitations",
)


def build_security_explanations(
    row: pd.Series,
    *,
    metadata_by_score: Mapping[str, Mapping[str, Any]],
) -> tuple[str, ...]:
    explanations: list[str] = []
    for column in (
        "coverage_status",
        "ranking_validity_flag",
        "data_quality_flag",
        "score_warmup_state",
        "score_coverage_status",
        "score_data_quality_flag",
    ):
        if column not in row.index:
            continue
        value = safe_scalar(row[column])
        if _status_value(value) not in HEALTHY_STATUS_VALUES:
            explanations.append(
                f"{column} is {value}; Step 16 keeps this row as technical context only."
            )
    if "rank" in row.index and not is_present(row["rank"]):
        explanations.append("Step 15 rank is unavailable for this row.")
    for column in ROW_EXPLANATION_COLUMNS:
        if column in row.index and is_present(row[column]):
            text = str(safe_scalar(row[column]))
            validate_step16_report_text(text, context=f"Step 16 explanation column {column}")
            explanations.append(f"{column}: {text}")
    for score_name in sorted(metadata_by_score):
        metadata = metadata_by_score[score_name]
        adoption_state = str(metadata.get("adoption_state", ""))
        manual_review_required = bool(metadata.get("manual_review_required", False))
        if adoption_state not in EXPLANATION_ADOPTION_STATES and not manual_review_required:
            continue
        detail = score_explanation(score_name, metadata)
        if detail:
            explanations.append(detail)
        else:
            explanations.append(f"{score_name} adoption_state is {adoption_state}.")
    return tuple(_dedupe(explanations))


def score_explanation(score_name: str, metadata: Mapping[str, Any]) -> str:
    adoption_state = str(metadata.get("adoption_state", ""))
    manual_review_required = bool(metadata.get("manual_review_required", False))
    parts: list[str] = []
    if adoption_state:
        parts.append(f"{score_name} adoption_state is {adoption_state}.")
    if manual_review_required:
        parts.append(f"{score_name} requires manual review before stronger downstream use.")
    for column in ("adoption_reason", "limitations"):
        value = metadata.get(column)
        if is_present(value):
            text = str(value)
            validate_step16_report_text(text, context=f"Step 16 {column}")
            parts.append(text)
    return " ".join(parts)


def is_context_metadata(*, role: str, branch: str, adoption_state: str) -> bool:
    if role in CONTEXT_ROLES or branch == "diagnostic":
        return True
    if adoption_state in CONTEXT_ADOPTION_STATES:
        return True
    return adoption_state not in DIRECT_ADOPTION_STATES and adoption_state != ""


def _status_value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


__all__ = (
    "build_security_explanations",
    "is_context_metadata",
    "score_explanation",
)
