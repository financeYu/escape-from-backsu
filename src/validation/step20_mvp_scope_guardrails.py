"""Step 20 KOSPI200 MVP scope guardrails.

These checks validate final MVP hardening material. They do not implement a
new universe, activate valuation/fundamental scoring, tune scores from backtest
results, or create trading recommendations.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import re
from typing import Any

import pandas as pd

from src.scores.schema import find_valuation_fundamental_columns
from src.validation.common import coerce_frame, column_names, extract_text_from_frame
from src.validation.field_guardrails import find_forbidden_columns_by_rules
from src.validation.step15_latest_ranking_guardrails import find_step15_forbidden_columns
from src.validation.step17_backtest_guardrails import (
    find_step17_evaluation_fields,
    find_step17_forbidden_report_language,
)
from src.validation.step18_valuation_fundamental_guardrails import (
    find_step18_forbidden_report_language,
)
from src.validation.text_guardrails import find_forbidden_pattern_labels


STEP20_MVP_SCOPE_NOTICE = "kospi200_mvp_technical_scanner_v0_1_scope"

STEP20_REQUIRED_RELEASE_CONFIRMATIONS: tuple[str, ...] = (
    "kosdaq150 was not implemented",
    "futures/options were not implemented",
    "valuation/fundamental scoring remains inactive",
    "backtest outputs did not feed upstream scoring or ranking",
    "mvp remains kospi200-only",
)

STEP20_FORBIDDEN_COLUMN_EXACT = frozenset(
    {
        "kosdaq150",
        "kosdaq_150",
        "futures",
        "options",
        "universe_id",
        "universe_name",
        "multi_universe_rank",
        "valuation_score",
        "fundamental_score",
        "undervalued_score",
        "cheap_score",
        "target_price",
        "buy",
        "sell",
        "hold",
        "recommendation",
        "proven_alpha",
    }
)

STEP20_FORBIDDEN_COLUMN_PREFIXES = (
    "kosdaq150_",
    "kosdaq_150_",
    "futures_",
    "options_",
    "multi_universe_",
    "valuation_",
    "fundamental_",
    "undervalued_",
    "cheap_",
    "target_price",
    "buy_",
    "sell_",
    "hold_",
    "recommendation_",
)

STEP20_FORBIDDEN_COLUMN_SUFFIXES = (
    "_kosdaq150",
    "_kosdaq_150",
    "_futures",
    "_options",
    "_valuation_score",
    "_fundamental_score",
    "_target_price",
    "_buy",
    "_sell",
    "_hold",
    "_recommendation",
)

STEP20_FORBIDDEN_SCOPE_PATTERNS: Mapping[str, str] = {
    "KOSDAQ150 implementation": (
        r"\b(?:add|added|activate|activated|enable|enabled|implement|implemented|"
        r"include|included|ingest|ingested|rank|ranked)\s+(?:the\s+)?kosdaq150\b|"
        r"\bkosdaq150\b.{0,80}\b(?:active|enabled|implemented|included|ingested|ranked)\b"
    ),
    "futures/options implementation": (
        r"\b(?:futures|options)\b.{0,80}\b(?:active|enabled|implemented|included|ingested|ranked)\b|"
        r"\b(?:add|added|activate|activated|enable|enabled|implement|implemented)\s+"
        r"(?:futures|options)\b"
    ),
    "multi-universe ranking": r"\bmulti[-_\s]?universe\b.{0,80}\b(?:rank|ranking|scanner)\b",
    "valuation/fundamental scoring activation": (
        r"\b(?:valuation|fundamental)[-_\s]?score\b.{0,80}\b(?:active|enabled|activated|used)\b|"
        r"\b(?:activate|enabled|use|used)\s+(?:valuation|fundamental)\s+scoring\b"
    ),
    "backtest feedback into scoring": (
        r"\bbacktest\b.{0,80}\b(?:tune|tuned|optimize|optimized|update|updated|"
        r"change|changed|redefine|redefined)\b.{0,80}\b(?:score|scoring|rank|ranking)\b|"
        r"\b(?:realized|future|forward)\s+returns?\b.{0,80}\b(?:score|scoring|rank|ranking)\b"
    ),
    "trading recommendation": (
        r"\b(?:buy|sell|hold)\s+(?:signal|recommendation|call)\b|"
        r"\btrading\s+recommendation\b"
    ),
    "proven alpha": r"\bproven\s+alpha\b|\balpha\s+(?:is\s+)?proven\b",
}


def find_step20_forbidden_columns(columns: pd.DataFrame | Iterable[str]) -> list[str]:
    """Return columns that violate the Step 20 KOSPI200 MVP scope."""

    names = column_names(columns)
    forbidden: set[str] = set(find_step15_forbidden_columns(names))
    forbidden.update(find_valuation_fundamental_columns(names))
    forbidden.update(
        find_forbidden_columns_by_rules(
            names,
            exact=STEP20_FORBIDDEN_COLUMN_EXACT,
            prefixes=STEP20_FORBIDDEN_COLUMN_PREFIXES,
            suffixes=STEP20_FORBIDDEN_COLUMN_SUFFIXES,
        )
    )
    return sorted(forbidden)


def validate_step20_mvp_scope_columns(
    columns: pd.DataFrame | Iterable[str],
    *,
    context: str = "Step 20 MVP scope columns",
) -> None:
    """Reject columns that expand or contaminate the KOSPI200 technical MVP."""

    forbidden = find_step20_forbidden_columns(columns)
    if forbidden:
        raise ValueError(
            f"{context} contains forbidden Step 20 MVP columns: {', '.join(forbidden)}"
        )


def validate_step20_mvp_scope_frame(
    data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    context: str = "Step 20 MVP scope frame",
) -> None:
    """Validate structured Step 20 material and text values."""

    frame = coerce_frame(data)
    validate_step20_mvp_scope_columns(frame.columns, context=context)
    report_text = extract_text_from_frame(frame)
    validate_step20_mvp_scope_text(report_text, context=context, require_notice=False)
    evaluation_fields = find_step17_evaluation_fields(frame.columns)
    if evaluation_fields:
        raise ValueError(
            f"{context} contains Step 17 evaluation fields outside output-only context: "
            f"{', '.join(evaluation_fields)}"
        )


def find_step20_forbidden_scope_language(text: str) -> list[str]:
    """Return positive scope-creep phrases while allowing explicit negation."""

    forbidden = find_forbidden_pattern_labels(
        text,
        STEP20_FORBIDDEN_SCOPE_PATTERNS,
        is_allowed_match=_is_allowed_negated_scope_match,
    )
    forbidden.extend(f"Step 17: {item}" for item in find_step17_forbidden_report_language(text))
    forbidden.extend(f"Step 18: {item}" for item in find_step18_forbidden_report_language(text))
    return sorted(set(forbidden))


def validate_step20_mvp_scope_text(
    text: str,
    *,
    context: str = "Step 20 MVP scope text",
    require_notice: bool = False,
) -> None:
    """Validate Step 20 release, audit, and sanity-report text."""

    lowered = text.lower()
    errors: list[str] = []
    if require_notice and STEP20_MVP_SCOPE_NOTICE not in lowered:
        errors.append(f"missing required notice: {STEP20_MVP_SCOPE_NOTICE}")
    forbidden = find_step20_forbidden_scope_language(text)
    if forbidden:
        errors.append(f"contains forbidden Step 20 scope language: {', '.join(forbidden)}")
    if errors:
        raise ValueError(f"{context} failed validation: {'; '.join(errors)}")


def validate_step20_release_report_text(
    text: str,
    *,
    context: str = "Step 20 release report",
) -> None:
    """Validate the final Step 20 report has required MVP freeze confirmations."""

    validate_step20_mvp_scope_text(text, context=context, require_notice=True)
    lowered = text.lower()
    missing = [
        phrase
        for phrase in STEP20_REQUIRED_RELEASE_CONFIRMATIONS
        if phrase not in lowered
    ]
    if missing:
        raise ValueError(
            f"{context} missing required Step 20 confirmations: {', '.join(missing)}"
        )


def _is_allowed_negated_scope_match(lowered: str, match: re.Match[str], _label: str) -> bool:
    window = lowered[max(0, match.start() - 32) : min(len(lowered), match.end() + 32)]
    allowed_phrases = (
        "not implemented",
        "was not implemented",
        "were not implemented",
        "not part of mvp",
        "post-mvp",
        "forbidden",
        "inactive",
        "not active",
        "not a ",
        "not ",
        "did not feed",
        "must not feed",
        "not used to tune",
        "no ",
    )
    return any(phrase in window for phrase in allowed_phrases)


__all__ = (
    "STEP20_MVP_SCOPE_NOTICE",
    "STEP20_REQUIRED_RELEASE_CONFIRMATIONS",
    "find_step20_forbidden_columns",
    "find_step20_forbidden_scope_language",
    "validate_step20_mvp_scope_columns",
    "validate_step20_mvp_scope_frame",
    "validate_step20_mvp_scope_text",
    "validate_step20_release_report_text",
)
