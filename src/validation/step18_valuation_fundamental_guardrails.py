"""Step 18 valuation/fundamental candidate guardrails.

These checks keep candidate explanatory data out of technical scoring,
production ranking, and Step 17 backtests unless later roadmap work explicitly
activates an integration path.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import pandas as pd

from src.valuation.contracts import ValuationCandidateRecord
from src.valuation.registry import DEFAULT_STEP18_METRIC_REGISTRY, MetricSpec
from src.valuation.reports import STEP18_CANDIDATE_REPORT_NOTICES
from src.valuation.validation import (
    assert_no_step18_production_leakage,
    assert_no_step18_score_contamination,
    find_step18_candidate_columns,
    validate_candidate_backtest_availability,
    validate_candidate_records,
)


def validate_step18_candidate_records(
    records: pd.DataFrame | Mapping[str, Any] | Iterable[Mapping[str, Any] | ValuationCandidateRecord],
    *,
    evaluation_date: object | None = None,
    registry: Sequence[MetricSpec] = DEFAULT_STEP18_METRIC_REGISTRY,
) -> tuple[ValuationCandidateRecord, ...]:
    """Validate candidate records through the Step 18 guardrail entrypoint."""

    return validate_candidate_records(
        records,
        evaluation_date=evaluation_date,
        registry=registry,
    )


def validate_step18_backtest_candidate_availability(
    records: pd.DataFrame | Mapping[str, Any] | Iterable[Mapping[str, Any] | ValuationCandidateRecord],
    *,
    decision_date: object,
    registry: Sequence[MetricSpec] = DEFAULT_STEP18_METRIC_REGISTRY,
) -> tuple[ValuationCandidateRecord, ...]:
    """Fail when candidate data is unavailable for a backtest decision date."""

    return validate_candidate_backtest_availability(
        records,
        decision_date=decision_date,
        registry=registry,
    )


def assert_step18_no_production_leakage(
    columns: pd.DataFrame | Iterable[str],
    *,
    context: str = "Step 18 production boundary",
) -> None:
    """Reject Step 18 candidate fields in production ranking/backtest outputs."""

    assert_no_step18_production_leakage(columns, context=context)


def assert_step18_no_score_contamination(
    columns: pd.DataFrame | Iterable[str],
    *,
    context: str = "Step 18 score boundary",
) -> None:
    """Reject Step 18 fields beside protected score/composite columns."""

    assert_no_step18_score_contamination(columns, context=context)


def validate_step18_candidate_report_text(
    report_text: str,
    *,
    context: str = "Step 18 candidate report",
) -> None:
    """Validate that candidate reports carry the required boundary notices."""

    lowered = report_text.lower()
    missing = [
        notice
        for notice in STEP18_CANDIDATE_REPORT_NOTICES
        if notice.lower() not in lowered
    ]
    if missing:
        raise ValueError(f"{context} missing required notices: {', '.join(missing)}")


__all__ = (
    "assert_step18_no_production_leakage",
    "assert_step18_no_score_contamination",
    "find_step18_candidate_columns",
    "validate_step18_backtest_candidate_availability",
    "validate_step18_candidate_records",
    "validate_step18_candidate_report_text",
)
