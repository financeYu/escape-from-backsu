"""Step 18 valuation/fundamental candidate guardrails.

These checks keep candidate explanatory data out of technical scoring,
production ranking, and Step 17 backtests unless later roadmap work explicitly
activates an integration path.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import re
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


STEP18_FORBIDDEN_REPORT_LANGUAGE_PATTERNS: Mapping[str, str] = {
    "alpha proven": r"\balpha\s+(?:is\s+)?proven\b|\bproven\s+alpha\b",
    "predictive alpha": (
        r"\bpredictive\s+alpha\b|"
        r"\balpha\s+(?:prediction|forecast)\b|"
        r"\balpha\s+(?:will|can|should)\s+(?:predict|forecast)\b"
    ),
    "future prediction": (
        r"\bfuture\s+(?:prediction|forecast)\b|"
        r"\bpredicts?\s+future\b|"
        r"\bforecast(?:s|ed|ing)?\s+future\b"
    ),
    "future return claim": (
        r"\bfuture[_\s-]?return\b|"
        r"\bforward[_\s-]?return\b|"
        r"\bexpected[_\s-]?return\b"
    ),
    "buy recommendation": r"\bbuy\s+(?:signal|recommendation|call|setup)\b",
    "sell recommendation": r"\bsell\s+(?:signal|recommendation|call|setup)\b",
    "hold recommendation": r"\bhold\s+(?:signal|recommendation|call|setup)\b",
    "trading signal": r"\btrading\s+signal\b",
    "trading recommendation": r"\btrading\s+recommendation\b",
    "investment recommendation": r"\binvestment\s+recommendation\b",
    "target price": r"\btarget[_\s-]?price\b|\bprice\s+target\b",
    "valuation score": r"\bvaluation[_\s-]?score\b",
    "fundamental score": r"\bfundamental[_\s-]?score\b",
    "market beating": (
        r"\bmarket[-\s]?beating\b|"
        r"\boutperform(?:s|ed|ing)?\s+the\s+market\b"
    ),
}


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
    """Validate that candidate reports carry notices and avoid Step 18 claims."""

    lowered = report_text.lower()
    missing = [
        notice
        for notice in STEP18_CANDIDATE_REPORT_NOTICES
        if notice.lower() not in lowered
    ]
    forbidden_language = find_step18_forbidden_report_language(report_text)
    errors: list[str] = []
    if missing:
        errors.append(f"missing required notices: {', '.join(missing)}")
    if forbidden_language:
        errors.append(f"contains forbidden report language: {', '.join(forbidden_language)}")
    if errors:
        raise ValueError(f"{context} failed Step 18 validation: {'; '.join(errors)}")


def find_step18_forbidden_report_language(text: str) -> list[str]:
    """Return Step 18 report phrases that imply signals, predictions, or scores."""

    lowered = text.lower()
    forbidden: list[str] = []
    for label, pattern in STEP18_FORBIDDEN_REPORT_LANGUAGE_PATTERNS.items():
        if _contains_forbidden_report_pattern(lowered, pattern):
            forbidden.append(label)
    return sorted(forbidden)


def _contains_forbidden_report_pattern(lowered: str, pattern: str) -> bool:
    for match in re.finditer(pattern, lowered):
        if _is_allowed_negated_report_match(lowered, match):
            continue
        return True
    return False


def _is_allowed_negated_report_match(lowered: str, match: re.Match[str]) -> bool:
    prefix = lowered[max(0, match.start() - 24) : match.start()]
    return any(
        negation in prefix
        for negation in (
            "not a ",
            "not an ",
            "not ",
            "no ",
            "without ",
            "non-",
        )
    )


__all__ = (
    "assert_step18_no_production_leakage",
    "assert_step18_no_score_contamination",
    "find_step18_candidate_columns",
    "find_step18_forbidden_report_language",
    "validate_step18_backtest_candidate_availability",
    "validate_step18_candidate_records",
    "validate_step18_candidate_report_text",
)
