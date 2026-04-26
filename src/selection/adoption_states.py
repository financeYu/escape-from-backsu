"""Step 14 adoption state vocabulary and classification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd

from .adoption_compat import CONTRACT_ALLOWED_STEP14_ADOPTION_STATES
from .adoption_rules import (
    ACCEPTABLE_COVERAGE_STATUSES,
    ACCEPTABLE_REDUNDANCY_STATUSES,
    BLOCKING_COVERAGE_STATUSES,
    BLOCKING_REDUNDANCY_STATUSES,
    CONTEXT_ROLES,
    DIAGNOSTIC_ROLES,
    SEVERE_REDUNDANCY_STATUSES,
    UNCLEAR_REDUNDANCY_STATUSES,
)


class AdoptionState(str, Enum):
    """Step 14 synthesis states, not downstream ranking or trading decisions."""

    CORE_ADOPTED = "core_adopted"
    CONDITIONAL_ADOPTED = "conditional_adopted"
    TECHNICAL_ONLY = "technical_only"
    REGIME_ONLY = "regime_only"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    RESEARCH_ONLY = "research_only"
    REJECTED = "rejected"
    BLOCKED_BY_DATA = "blocked_by_data"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


ALLOWED_STEP14_ADOPTION_STATES = frozenset(
    CONTRACT_ALLOWED_STEP14_ADOPTION_STATES or frozenset(state.value for state in AdoptionState)
)


@dataclass(frozen=True)
class _AdoptionInputs:
    review_status: str
    eligibility: str
    role: str
    branch: str
    coverage_status: str
    redundancy_status: str
    manual_review_required: bool


def classify_adoption_state(row: pd.Series) -> tuple[AdoptionState, str, str, bool]:
    """Classify one Step 13 review row into a conservative Step 14 state."""

    values = _adoption_inputs(row)
    for classifier in (
        _classify_source_review_state,
        _classify_pre_adoption_blockers,
        _classify_role_and_condition,
        _classify_adopt_candidate,
    ):
        decision = classifier(values)
        if decision is not None:
            return decision
    return _decision(
        AdoptionState.NEEDS_MANUAL_REVIEW,
        f"Unrecognized or unsupported Step 13 review status {values.review_status} requires review.",
        "Unknown statuses are not interpreted optimistically.",
        True,
    )


def _adoption_inputs(row: pd.Series) -> _AdoptionInputs:
    return _AdoptionInputs(
        review_status=status_value(row["review_status"]),
        eligibility=status_value(row["eligibility"]),
        role=status_value(row["role"]),
        branch=status_value(row["branch"]),
        coverage_status=status_value(row.get("coverage_status", "unknown")),
        redundancy_status=status_value(row.get("redundancy_status", "unknown")),
        manual_review_required=as_bool(row["manual_review_required"]),
    )


def _classify_source_review_state(
    values: _AdoptionInputs,
) -> tuple[AdoptionState, str, str, bool] | None:
    if values.review_status == "blocked_by_data":
        return _decision(
            AdoptionState.BLOCKED_BY_DATA,
            "Step 13 review marks required input material as blocked by data.",
            "Blocked rows require upstream data repair before any later use.",
            values.manual_review_required,
        )
    if values.review_status == "needs_manual_review":
        return _decision(
            AdoptionState.NEEDS_MANUAL_REVIEW,
            "Step 13 review leaves an unresolved manual review requirement.",
            "Manual review must resolve the open issue before this row can be adopted.",
            True,
        )
    if values.review_status == "reject_candidate":
        return _decision(
            AdoptionState.REJECTED,
            "Step 13 review rejected the candidate on technical review grounds.",
            "Rejected rows are retained only for traceability.",
            values.manual_review_required,
        )
    if values.review_status == "research_only":
        return _decision(
            AdoptionState.RESEARCH_ONLY,
            "Step 13 review keeps the row as research material only.",
            "Additional evidence or clearer implementation support is required.",
            values.manual_review_required,
        )
    if values.review_status == "diagnostic_only":
        return _decision(
            AdoptionState.DIAGNOSTIC_ONLY,
            "Step 13 review marks the row as diagnostic material only.",
            "Diagnostic rows remain context or validation material.",
            values.manual_review_required,
        )
    return None


def _classify_pre_adoption_blockers(
    values: _AdoptionInputs,
) -> tuple[AdoptionState, str, str, bool] | None:
    if _is_diagnostic_only(
        branch=values.branch,
        eligibility=values.eligibility,
        role=values.role,
    ):
        return _decision(
            AdoptionState.DIAGNOSTIC_ONLY,
            "Diagnostic branch or diagnostic role prevents core adoption.",
            "Diagnostic rows remain context or validation material.",
            values.manual_review_required,
        )
    if values.manual_review_required:
        return _decision(
            AdoptionState.NEEDS_MANUAL_REVIEW,
            "Step 13 review carries an unresolved manual review requirement.",
            "Manual review must resolve the open issue before this row can be adopted.",
            True,
        )
    if values.coverage_status in BLOCKING_COVERAGE_STATUSES:
        return _decision(
            AdoptionState.BLOCKED_BY_DATA,
            f"Coverage status {values.coverage_status} blocks automatic adoption.",
            "Coverage must be repaired before this row can be adopted.",
            True,
        )
    if values.redundancy_status in BLOCKING_REDUNDANCY_STATUSES:
        return _decision(
            AdoptionState.BLOCKED_BY_DATA,
            f"Redundancy status {values.redundancy_status} blocks automatic adoption.",
            "Diagnostic input must be repaired before this row can be adopted.",
            True,
        )
    if values.redundancy_status in UNCLEAR_REDUNDANCY_STATUSES:
        return _decision(
            AdoptionState.NEEDS_MANUAL_REVIEW,
            f"Redundancy status {values.redundancy_status} leaves distinctness unresolved.",
            "Manual review must resolve the unclear redundancy result.",
            True,
        )
    return None


def _classify_role_and_condition(
    values: _AdoptionInputs,
) -> tuple[AdoptionState, str, str, bool] | None:
    if values.role == "setup_context":
        return _decision(
            AdoptionState.REGIME_ONLY,
            "Setup context role is kept as regime material, not core adoption.",
            "Regime-only rows can provide context but do not become core rows here.",
            False,
        )
    if values.role == "confirmation":
        return _decision(
            AdoptionState.CONDITIONAL_ADOPTED,
            "Confirmation role can support adoption only as conditional material.",
            "Confirmation rows need explicit downstream design before stronger use.",
            True,
        )
    if values.review_status == "conditional_candidate" or values.eligibility == "conditional":
        return _decision(
            AdoptionState.CONDITIONAL_ADOPTED,
            "Step 13 review or Step 11 eligibility is conditional.",
            "Conditional rows retain one or more unresolved technical constraints.",
            True,
        )
    if values.redundancy_status in SEVERE_REDUNDANCY_STATUSES:
        return _decision(
            AdoptionState.CONDITIONAL_ADOPTED,
            f"Redundancy status {values.redundancy_status} prevents core adoption.",
            "Redundancy must be resolved before stronger adoption can be considered.",
            True,
        )
    return None


def _classify_adopt_candidate(
    values: _AdoptionInputs,
) -> tuple[AdoptionState, str, str, bool] | None:
    if values.review_status != "adopt_candidate":
        return None
    if _clean_core_candidate(
        eligibility=values.eligibility,
        role=values.role,
        coverage_status=values.coverage_status,
        redundancy_status=values.redundancy_status,
    ):
        return _decision(
            AdoptionState.CORE_ADOPTED,
            "Eligible technical candidate has acceptable coverage and no blocking review flags.",
            "This is Step 14 synthesis material only and assigns no downstream weight.",
            False,
        )
    return _decision(
        AdoptionState.CONDITIONAL_ADOPTED,
        "Adopt candidate is downgraded because at least one core condition is not clean.",
        "The unresolved condition must be reviewed before stronger adoption.",
        True,
    )


def status_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    if pd.isna(value):
        return "unknown"
    return str(value).strip()


def as_bool(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    raise ValueError("Step 14 manual_review_required values must be boolean.")


def _decision(
    state: AdoptionState,
    reason: str,
    limitations: str,
    manual_review_required: bool,
) -> tuple[AdoptionState, str, str, bool]:
    return state, reason, limitations, bool(manual_review_required)


def _clean_core_candidate(
    *,
    eligibility: str,
    role: str,
    coverage_status: str,
    redundancy_status: str,
) -> bool:
    return (
        eligibility == "eligible"
        and role not in CONTEXT_ROLES
        and role not in DIAGNOSTIC_ROLES
        and coverage_status in ACCEPTABLE_COVERAGE_STATUSES
        and redundancy_status in ACCEPTABLE_REDUNDANCY_STATUSES
    )


def _is_diagnostic_only(*, branch: str, eligibility: str, role: str) -> bool:
    return branch == "diagnostic" or eligibility == "diagnostic_only" or role in DIAGNOSTIC_ROLES


__all__ = (
    "ALLOWED_STEP14_ADOPTION_STATES",
    "AdoptionState",
    "as_bool",
    "classify_adoption_state",
    "status_value",
)
