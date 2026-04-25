"""Step 16 per-security detail report contracts.

This module defines the structured report shape and guardrails for Step 16.
It does not calculate rankings, run backtests, create trading outputs, or use
valuation/fundamental data.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from enum import Enum
import math
import re
from typing import Any

import numpy as np
import pandas as pd

from src.scores.schema import find_missing_columns, find_valuation_fundamental_columns


STEP16_SECURITY_DETAIL_REPORT_NOTICE = "technical detail report only"

STEP16_REQUIRED_LATEST_RANKING_COLUMNS: tuple[str, ...] = ("ticker", "date")

STEP16_READONLY_RANK_FIELD_COLUMNS: tuple[str, ...] = (
    "rank",
    "coverage_metric",
    "coverage_status",
    "ranking_validity_flag",
    "valid_score_count",
    "expected_score_count",
    "review_routed_score_count",
    "final_score_policy",
)

STEP16_SCORE_SUMMARY_COLUMNS: tuple[str, ...] = (
    "technical_composite_score",
    "final_composite_score",
)

STEP16_FORBIDDEN_EXACT_COLUMNS = frozenset(
    {
        "buy",
        "sell",
        "buy_signal",
        "sell_signal",
        "trading_signal",
        "recommendation",
        "target_price",
        "expected_return",
        "forward_return",
        "future_return",
        "next_return",
        "next_period_return",
        "backtest_return",
        "realized_return",
        "realized_pnl",
        "strategy_return",
        "portfolio_return",
        "benchmark_return",
        "excess_return",
        "alpha",
        "sharpe",
        "mdd",
        "drawdown",
        "win_rate",
        "hit_ratio",
        "valuation_score",
        "fundamental_score",
        "undervalued",
        "cheap",
        "bargain",
        "PER",
        "PBR",
        "ROE",
    }
)

STEP16_FORBIDDEN_COLUMN_PREFIXES: tuple[str, ...] = (
    "buy_",
    "sell_",
    "signal_",
    "trading_signal",
    "target_price",
    "expected_return",
    "forward_return",
    "future_return",
    "next_return",
    "next_period_return",
    "backtest_",
    "realized_",
    "strategy_return",
    "portfolio_return",
    "benchmark_return",
    "excess_return",
    "alpha_",
    "valuation_",
    "fundamental_",
    "financial_",
    "per_",
    "pbr_",
    "roe_",
)

STEP16_FORBIDDEN_COLUMN_SUFFIXES: tuple[str, ...] = (
    "_buy",
    "_sell",
    "_signal",
    "_target_price",
    "_expected_return",
    "_forward_return",
    "_future_return",
    "_backtest_return",
    "_valuation_score",
    "_fundamental_score",
    "_per",
    "_pbr",
    "_roe",
)

STEP16_FORBIDDEN_TEXT_TERMS = frozenset(
    {
        "buy",
        "sell",
        "target_price",
        "target price",
        "expected_return",
        "expected return",
        "forward_return",
        "future_return",
        "backtest_return",
        "backtest return",
        "valuation_score",
        "valuation score",
        "undervalued",
        "cheap",
        "bargain",
        "per",
        "pbr",
        "roe",
    }
)


class SecurityReportDisplayRole(str, Enum):
    """Step 16 display roles; these are not ranking or trading decisions."""

    READONLY_STEP15_SCORE_COMPONENT = "readonly_step15_score_component"
    DIAGNOSTIC_CONTEXT_NOT_RANK_DRIVER = "diagnostic_context_not_rank_driver"
    SOURCE_ADOPTION_CONTEXT = "source_adoption_context"
    FAMILY_COMPONENT_CONTEXT = "family_component_context"


@dataclass(frozen=True)
class SecurityReportBoundaryNotice:
    """Conservative Step 16 report boundary text."""

    scope: str = STEP16_SECURITY_DETAIL_REPORT_NOTICE
    trading_notice: str = "not a trading recommendation"
    backtest_notice: str = "not a backtest"
    analysis_notice: str = "not valuation/fundamental analysis"
    future_data_notice: str = "no forward/future return used"

    def to_dict(self) -> dict[str, str]:
        record = _clean_value(asdict(self))
        validate_security_detail_report_content(record, context="Step 16 boundary notice")
        return record


@dataclass(frozen=True)
class SecurityScoreBreakdown:
    """One score row shown inside a Step 16 detail report."""

    score_name: str
    source_column: str = ""
    score_value: float | None = None
    score_family: str = ""
    score_role: str = ""
    score_branch: str = ""
    eligibility: str = ""
    adoption_state: str = ""
    source_review_status: str = ""
    readonly_step15_component: bool = False
    context_only: bool = False
    display_role: str = SecurityReportDisplayRole.SOURCE_ADOPTION_CONTEXT.value
    status: str = ""
    quality_flag: str = ""
    valid_count: int | None = None
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        record = _clean_value(asdict(self))
        validate_security_detail_report_content(record, context="Step 16 score breakdown")
        return record


@dataclass(frozen=True)
class SecurityComponentBreakdown:
    """One aggregate component shown as read-only Step 15 context."""

    component_name: str
    component_type: str
    source_column: str
    value: float | None
    display_role: str = SecurityReportDisplayRole.FAMILY_COMPONENT_CONTEXT.value

    def to_dict(self) -> dict[str, Any]:
        record = _clean_value(asdict(self))
        validate_security_detail_report_content(record, context="Step 16 component breakdown")
        return record


@dataclass(frozen=True)
class SecurityDetailReport:
    """Structured Step 16 per-security report output."""

    ticker: str
    snapshot_date: str
    report_date: str
    source_latest_ranking_date: str
    rank_fields_are_readonly: bool
    readonly_rank_fields: Mapping[str, Any]
    technical_composite_score: float | None
    final_composite_score: float | None
    final_composite_score_note: str
    score_breakdown: tuple[SecurityScoreBreakdown, ...]
    component_breakdown: tuple[SecurityComponentBreakdown, ...]
    diagnostic_context: tuple[SecurityScoreBreakdown, ...]
    source_adoption_metadata: tuple[Mapping[str, Any], ...]
    quality_flags: Mapping[str, Any]
    explanations: tuple[str, ...]
    boundary_notice: SecurityReportBoundaryNotice = field(
        default_factory=SecurityReportBoundaryNotice
    )

    def to_dict(self) -> dict[str, Any]:
        record = _clean_value(asdict(self))
        validate_security_detail_report_content(record, context="Step 16 security detail report")
        return record

    def to_record(self) -> dict[str, Any]:
        """Alias for DataFrame/JSON-friendly callers."""

        return self.to_dict()


def find_forbidden_step16_report_columns(columns: Iterable[str]) -> list[str]:
    """Return Step 16 input/output columns that cross hard-stop boundaries."""

    forbidden: set[str] = set(find_valuation_fundamental_columns(columns))
    for column in columns:
        normalized = str(column).strip().lower()
        if (
            normalized in STEP16_FORBIDDEN_EXACT_COLUMNS
            or normalized.startswith(STEP16_FORBIDDEN_COLUMN_PREFIXES)
            or normalized.endswith(STEP16_FORBIDDEN_COLUMN_SUFFIXES)
        ):
            forbidden.add(str(column))
    return sorted(forbidden)


def assert_no_forbidden_step16_report_columns(
    columns: Iterable[str],
    *,
    context: str = "Step 16 security detail report input",
) -> None:
    """Reject columns that imply trading, future/performance, or valuation use."""

    forbidden = find_forbidden_step16_report_columns(columns)
    if forbidden:
        raise ValueError(
            f"{context} contains forbidden Step 16 report columns: "
            f"{', '.join(forbidden)}"
        )


def validate_step16_latest_ranking_input(
    frame: pd.DataFrame,
    *,
    context: str = "Step 16 latest ranking input",
) -> None:
    """Validate the already-built Step 15 latest ranking table for reporting."""

    missing = find_missing_columns(frame.columns, STEP16_REQUIRED_LATEST_RANKING_COLUMNS)
    if missing:
        raise ValueError(f"{context} missing required columns: {', '.join(missing)}")
    assert_no_forbidden_step16_report_columns(frame.columns, context=context)
    _assert_tickers_are_safe_strings(frame, context=context)
    _assert_single_snapshot_date(frame, context=context)
    if frame.duplicated(["ticker"]).any():
        raise ValueError(f"{context} must contain at most one row per ticker.")
    _assert_text_values_are_allowed(frame, context=context)


def validate_step16_metadata_table(
    frame: pd.DataFrame | None,
    *,
    context: str = "Step 16 metadata input",
) -> None:
    """Validate optional metadata tables before they are copied into reports."""

    if frame is None:
        return
    assert_no_forbidden_step16_report_columns(frame.columns, context=context)
    _assert_text_values_are_allowed(frame, context=context)


def find_forbidden_step16_report_text(text: str) -> list[str]:
    """Return forbidden generated-report terms found in text."""

    lowered = text.lower()
    return [
        term
        for term in sorted(STEP16_FORBIDDEN_TEXT_TERMS)
        if _contains_forbidden_text_term(text, lowered, term)
    ]


def validate_step16_report_text(
    text: str,
    *,
    context: str = "Step 16 security detail report text",
) -> None:
    """Reject generated report text that crosses Step 16 boundaries."""

    violations = find_forbidden_step16_report_text(text)
    if violations:
        raise ValueError(
            f"{context} contains forbidden Step 16 report language: "
            f"{', '.join(violations)}"
        )


def validate_security_detail_report_content(
    report: Mapping[str, Any],
    *,
    context: str = "Step 16 security detail report",
) -> None:
    """Validate structured report keys and string values recursively."""

    violations: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            key_violations = find_forbidden_step16_report_columns(str(key) for key in value)
            violations.extend(f"{path}.{key}" for key in key_violations)
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                walk(child, child_path)
            return
        if isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
            return
        if isinstance(value, str):
            text_violations = find_forbidden_step16_report_text(value)
            violations.extend(f"{path}: {term}" for term in text_violations)

    walk(report, "")
    if violations:
        raise ValueError(
            f"{context} contains forbidden Step 16 report content: "
            f"{', '.join(sorted(set(violations)))}"
        )


def _assert_tickers_are_safe_strings(frame: pd.DataFrame, *, context: str) -> None:
    invalid = frame["ticker"].map(lambda value: not isinstance(value, str) or value.strip() == "")
    if invalid.any():
        raise ValueError(f"{context} ticker values must be non-empty strings.")
    unsafe = frame["ticker"].map(lambda value: len(value) != 6 or not value.isdigit())
    if unsafe.any():
        raise ValueError(f"{context} ticker values must preserve six-digit string format.")


def _assert_single_snapshot_date(frame: pd.DataFrame, *, context: str) -> None:
    dates = pd.to_datetime(frame["date"], errors="coerce")
    if dates.isna().any():
        raise ValueError(f"{context} contains unparseable date values.")
    if dates.nunique(dropna=False) != 1:
        raise ValueError(f"{context} must contain exactly one latest ranking date.")


def _assert_text_values_are_allowed(frame: pd.DataFrame, *, context: str) -> None:
    object_columns = frame.select_dtypes(include=("object", "string")).columns
    for column in object_columns:
        for value in frame[column].dropna().tolist():
            validate_step16_report_text(str(value), context=f"{context} column {column}")


def _contains_forbidden_text_term(text: str, lowered: str, term: str) -> bool:
    if term in {"PER", "PBR", "ROE"}:
        return re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", text) is not None
    term = term.lower()
    if " " in term or "_" in term:
        return term in lowered
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", lowered) is not None


def _clean_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clean_value(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return tuple(_clean_value(child) for child in value)
    if isinstance(value, list):
        return [_clean_value(child) for child in value]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return None if math.isnan(float(value)) else float(value)
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


__all__ = (
    "STEP16_READONLY_RANK_FIELD_COLUMNS",
    "STEP16_REQUIRED_LATEST_RANKING_COLUMNS",
    "STEP16_SCORE_SUMMARY_COLUMNS",
    "STEP16_SECURITY_DETAIL_REPORT_NOTICE",
    "SecurityComponentBreakdown",
    "SecurityDetailReport",
    "SecurityReportBoundaryNotice",
    "SecurityReportDisplayRole",
    "SecurityScoreBreakdown",
    "assert_no_forbidden_step16_report_columns",
    "find_forbidden_step16_report_columns",
    "find_forbidden_step16_report_text",
    "validate_security_detail_report_content",
    "validate_step16_latest_ranking_input",
    "validate_step16_metadata_table",
    "validate_step16_report_text",
)
