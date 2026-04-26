"""Compatibility layer for Step 14 adoption synthesis contracts."""

from __future__ import annotations

FALLBACK_REQUIRED_STEP14_COLUMNS: tuple[str, ...] = (
    "score_name",
    "family",
    "branch",
    "role",
    "eligibility",
    "source_review_status",
    "adoption_state",
    "adoption_reason",
    "evidence_sources",
    "limitations",
    "manual_review_required",
)
FALLBACK_OPTIONAL_STEP14_COLUMNS: tuple[str, ...] = (
    "normalized_score_column",
    "score_input_column",
    "coverage_status",
    "redundancy_status",
    "complexity_status",
    "regime_fit_status",
    "downstream_usage_note",
)

try:
    from .adoption_synthesis_contracts import (
        ALLOWED_STEP14_ADOPTION_STATES as CONTRACT_ALLOWED_STEP14_ADOPTION_STATES,
        STEP14_ADOPTION_SYNTHESIS_COLUMNS as CONTRACT_STEP14_ADOPTION_SYNTHESIS_COLUMNS,
        STEP14_ADOPTION_SYNTHESIS_NOTICE as CONTRACT_STEP14_ADOPTION_SYNTHESIS_NOTICE,
        STEP14_OPTIONAL_ADOPTION_SYNTHESIS_COLUMNS as CONTRACT_OPTIONAL_STEP14_COLUMNS,
        STEP14_REQUIRED_ADOPTION_SYNTHESIS_COLUMNS as CONTRACT_REQUIRED_STEP14_COLUMNS,
        find_forbidden_adoption_columns as contract_find_forbidden_adoption_columns,
        validate_adoption_synthesis_table as contract_validate_adoption_synthesis_table,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - exercised when Worker A is not present.
    if exc.name not in {
        "src.selection.adoption_synthesis_contracts",
        "selection.adoption_synthesis_contracts",
        "adoption_synthesis_contracts",
    }:
        raise
    CONTRACT_ALLOWED_STEP14_ADOPTION_STATES = None
    CONTRACT_STEP14_ADOPTION_SYNTHESIS_COLUMNS = None
    CONTRACT_STEP14_ADOPTION_SYNTHESIS_NOTICE = None
    CONTRACT_OPTIONAL_STEP14_COLUMNS = ()
    CONTRACT_REQUIRED_STEP14_COLUMNS = None
    contract_find_forbidden_adoption_columns = None
    contract_validate_adoption_synthesis_table = None


STEP14_CONTRACT_NOTICE = (
    CONTRACT_STEP14_ADOPTION_SYNTHESIS_NOTICE or "adoption synthesis material only"
)
STEP14_ADOPTION_MATERIAL_NOTICE = STEP14_CONTRACT_NOTICE

STEP14_REQUIRED_ADOPTION_TABLE_COLUMNS: tuple[str, ...] = (
    CONTRACT_REQUIRED_STEP14_COLUMNS or FALLBACK_REQUIRED_STEP14_COLUMNS
)
STEP14_OPTIONAL_ADOPTION_TABLE_COLUMNS: tuple[str, ...] = tuple(
    CONTRACT_OPTIONAL_STEP14_COLUMNS or FALLBACK_OPTIONAL_STEP14_COLUMNS
)
STEP14_ADOPTION_TABLE_COLUMNS: tuple[str, ...] = tuple(
    CONTRACT_STEP14_ADOPTION_SYNTHESIS_COLUMNS
    or (*FALLBACK_REQUIRED_STEP14_COLUMNS, *FALLBACK_OPTIONAL_STEP14_COLUMNS)
)

__all__ = (
    "CONTRACT_ALLOWED_STEP14_ADOPTION_STATES",
    "STEP14_ADOPTION_MATERIAL_NOTICE",
    "STEP14_ADOPTION_TABLE_COLUMNS",
    "STEP14_OPTIONAL_ADOPTION_TABLE_COLUMNS",
    "STEP14_REQUIRED_ADOPTION_TABLE_COLUMNS",
    "contract_find_forbidden_adoption_columns",
    "contract_validate_adoption_synthesis_table",
)
