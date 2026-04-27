"""v0.2 candidate-only ML artifact guardrails.

These checks protect the frozen MVP v0.1 production ranking and composite
contract while allowing the sidecar-only ``prob_up_1d_candidate`` artifact.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import pandas as pd

from src.validation.common import coerce_frame, column_names, extract_text_from_frame
from src.validation.field_guardrails import find_forbidden_columns_by_rules
from src.validation.text_guardrails import find_forbidden_pattern_labels


PROB_UP_1D_CANDIDATE_COLUMN = "prob_up_1d_candidate"

V0_2_CANDIDATE_REQUIRED_TIMING_FIELDS: tuple[str, ...] = (
    "ticker",
    "date",
    "decision_time",
    "execution_time",
    "label_time",
    "label_availability_time",
)

V0_2_CANDIDATE_FORBIDDEN_EXACT_COLUMNS = frozenset(
    {
        "technical_composite_score",
        "final_composite_score",
        "technical_composite",
        "final_composite",
        "rank",
        "ranking",
        "latest_rank",
        "production_rank",
        "production_ranking",
        "final_rank",
        "technical_rank",
        "buy",
        "sell",
        "hold",
        "recommendation",
        "trading_recommendation",
        "expected_return",
        "expected_alpha",
        "proven_alpha",
        "target_return",
        "target_price",
    }
)

V0_2_CANDIDATE_FORBIDDEN_PREFIXES = (
    "technical_composite_",
    "final_composite_",
    "production_rank",
    "production_ranking",
    "buy_",
    "sell_",
    "hold_",
    "recommendation_",
    "expected_return_",
    "proven_alpha_",
    "target_return_",
    "target_price_",
)

V0_2_CANDIDATE_FORBIDDEN_SUFFIXES = (
    "_technical_composite_score",
    "_final_composite_score",
    "_production_rank",
    "_production_ranking",
    "_buy",
    "_sell",
    "_hold",
    "_recommendation",
    "_expected_return",
    "_proven_alpha",
    "_target_return",
    "_target_price",
)

V0_2_BACKTEST_FEEDBACK_COLUMN_TERMS = frozenset(
    {
        "backtest",
        "sharpe",
        "sortino",
        "drawdown",
        "forward",
        "hit_rate",
        "future",
        "win_rate",
        "holding_return",
        "realized_return",
        "realized_holding_return",
        "forward_return",
        "future_return",
        "paper_return",
        "generated_report",
        "report_output",
        "ranking_output",
        "candidate_sidecar",
        "cache",
        "cagr",
        "profit_factor",
    }
)

V0_2_LABEL_LEAKAGE_COLUMN_TERMS = frozenset(
    {
        "label",
        "target",
        "future",
        "forward",
        "next_day",
        "nextday",
        "tomorrow",
        "t_plus",
        "tplus",
        "realized_return",
        "outcome",
        "y_true",
    }
)

V0_2_FORBIDDEN_TEXT_PATTERNS: Mapping[str, str] = {
    "final composite write": (
        r"\b(?:write|writes|wrote|update|updates|updated|replace|replaces|replaced|"
        r"redefine|redefines|redefined)\b.{0,80}\bfinal[_\s-]?composite[_\s-]?score\b"
    ),
    "technical composite write": (
        r"\b(?:write|writes|wrote|update|updates|updated|replace|replaces|replaced|"
        r"redefine|redefines|redefined)\b.{0,80}\btechnical[_\s-]?composite[_\s-]?score\b"
    ),
    "production ranking activation": (
        r"\b(?:activate|activates|activated|enable|enables|enabled|replace|replaces|replaced)\b"
        r".{0,80}\b(?:production|final|latest)[_\s-]?rank(?:ing)?\b|"
        r"\bproduction[_\s-]?ranking\b.{0,80}\b(?:active|enabled|replaced)\b"
    ),
    "backtest feedback": (
        r"\bbacktest\b.{0,80}\b(?:feed|feeds|feedback|tune|tunes|tuned|optimize|"
        r"optimizes|optimized|select|selects|selected)\b.{0,80}\b(?:score|model|rank|ranking|feature)\b|"
        r"\b(?:realized|future|forward)\s+returns?\b.{0,80}\b(?:feature|model|score|rank|ranking)\b"
    ),
    "trading recommendation": (
        r"\b(?:buy|sell|hold)\s+(?:signal|recommendation|call)\b|"
        r"\btrading\s+recommendation\b"
    ),
    "expected-return wording": r"\bexpected[-\s]+returns?\b|\btarget[-\s]+returns?\b",
    "proven-alpha wording": r"\bproven[-\s]+alpha\b|\balpha\s+(?:is\s+)?proven\b",
    "performance promise": r"\b(?:guaranteed|reliable|robust)\s+(?:profit|return|alpha|outperformance)\b",
}


def find_v0_2_candidate_forbidden_columns(columns: pd.DataFrame | Iterable[str]) -> list[str]:
    """Return candidate artifact columns that violate v0.2 guardrails."""

    names = column_names(columns)
    artifact_substrings = V0_2_BACKTEST_FEEDBACK_COLUMN_TERMS - frozenset({"candidate_sidecar"})
    forbidden: set[str] = set(
        find_forbidden_columns_by_rules(
            names,
            exact=V0_2_CANDIDATE_FORBIDDEN_EXACT_COLUMNS,
            prefixes=V0_2_CANDIDATE_FORBIDDEN_PREFIXES,
            suffixes=V0_2_CANDIDATE_FORBIDDEN_SUFFIXES,
            substrings=artifact_substrings,
            tokens=V0_2_BACKTEST_FEEDBACK_COLUMN_TERMS,
        )
    )
    return sorted(forbidden)


def find_v0_2_candidate_forbidden_feature_columns(feature_columns: Iterable[str]) -> list[str]:
    """Return feature columns that leak labels, future data, or backtest feedback."""

    columns = tuple(str(column) for column in feature_columns)
    forbidden: set[str] = set(
        find_forbidden_columns_by_rules(
            columns,
            exact=V0_2_LABEL_LEAKAGE_COLUMN_TERMS | V0_2_BACKTEST_FEEDBACK_COLUMN_TERMS,
            substrings=V0_2_LABEL_LEAKAGE_COLUMN_TERMS | V0_2_BACKTEST_FEEDBACK_COLUMN_TERMS,
        )
    )
    return sorted(forbidden)


def validate_v0_2_candidate_feature_columns(
    feature_columns: Iterable[str],
    *,
    context: str = "v0.2 candidate ML feature columns",
) -> None:
    """Reject candidate model features with label, future, or backtest leakage."""

    forbidden = find_v0_2_candidate_forbidden_feature_columns(feature_columns)
    if forbidden:
        raise ValueError(
            f"{context} contains forbidden leakage/backtest feature columns: "
            f"{', '.join(forbidden)}"
        )


def validate_v0_2_candidate_artifact_columns(
    columns: pd.DataFrame | Iterable[str],
    *,
    context: str = "v0.2 candidate ML artifact columns",
    require_timing_fields: bool = True,
) -> None:
    """Validate candidate-only artifact columns and required timing fields."""

    names = column_names(columns)
    missing = [
        field for field in V0_2_CANDIDATE_REQUIRED_TIMING_FIELDS if field not in names
    ]
    errors: list[str] = []
    if PROB_UP_1D_CANDIDATE_COLUMN not in names:
        errors.append(f"missing required candidate probability column: {PROB_UP_1D_CANDIDATE_COLUMN}")
    if require_timing_fields and missing:
        errors.append(f"missing required timing fields: {', '.join(missing)}")

    forbidden = find_v0_2_candidate_forbidden_columns(names)
    if forbidden:
        errors.append(
            "contains forbidden production/backtest/trading columns: "
            f"{', '.join(forbidden)}"
        )

    if errors:
        raise ValueError(f"{context} failed validation: {'; '.join(errors)}")


def find_v0_2_candidate_forbidden_text(text: str) -> list[str]:
    """Return forbidden candidate ML language labels."""

    return find_forbidden_pattern_labels(text, V0_2_FORBIDDEN_TEXT_PATTERNS)


def validate_v0_2_candidate_text(
    text: str,
    *,
    context: str = "v0.2 candidate ML text",
) -> None:
    """Reject wording that promotes the sidecar candidate into production use."""

    forbidden = find_v0_2_candidate_forbidden_text(text)
    if forbidden:
        raise ValueError(
            f"{context} contains forbidden v0.2 candidate language: {', '.join(forbidden)}"
        )


def validate_v0_2_candidate_artifact_frame(
    data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    context: str = "v0.2 candidate ML artifact frame",
    feature_columns: Iterable[str] = (),
) -> None:
    """Validate candidate artifact schema, feature refs, and embedded text values."""

    frame = coerce_frame(data)
    validate_v0_2_candidate_artifact_columns(frame.columns, context=context)
    validate_v0_2_candidate_feature_columns(feature_columns, context=context)
    text = extract_text_from_frame(frame)
    validate_v0_2_candidate_text(text, context=context)


__all__ = (
    "PROB_UP_1D_CANDIDATE_COLUMN",
    "V0_2_CANDIDATE_REQUIRED_TIMING_FIELDS",
    "find_v0_2_candidate_forbidden_columns",
    "find_v0_2_candidate_forbidden_feature_columns",
    "find_v0_2_candidate_forbidden_text",
    "validate_v0_2_candidate_artifact_columns",
    "validate_v0_2_candidate_artifact_frame",
    "validate_v0_2_candidate_feature_columns",
    "validate_v0_2_candidate_text",
)
