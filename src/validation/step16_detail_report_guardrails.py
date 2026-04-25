"""Step 16 detail report validation guardrails.

This module validates Step 16 per-security report inputs and outputs. It does
not generate reports, calculate rankings, run backtests, create trading
signals, or perform valuation/fundamental scoring.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import re
from typing import Any

import pandas as pd

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY, CompositeInputSpec
from src.scores.schema import find_valuation_fundamental_columns
from src.validation.step15_latest_ranking_guardrails import (
    build_allowed_step15_score_like_columns,
)


STEP16_DETAIL_REPORT_NOTICE = "technical-only detail report"

STEP16_ALLOWED_BASE_COLUMNS = frozenset(
    {
        "ticker",
        "date",
        "as_of_date",
        "security_name",
        "name",
        "rank",
        "technical_composite_score",
        "final_composite_score",
        "coverage_metric",
        "data_quality_flag",
        "coverage_status",
        "ranking_validity_flag",
        "validity_flag",
        "valid_score_count",
        "expected_score_count",
        "review_routed_score_count",
        "final_score_policy",
        "score_name",
        "score_value",
        "normalized_score",
        "normalized_score_column",
        "score_input_column",
        "family",
        "branch",
        "role",
        "eligibility",
        "adoption_state",
        "source_review_status",
        "limitations",
        "manual_review_required",
        "source_run_id",
        "generated_at",
        "report_notice",
        "boundary_notice",
        "report_boundary",
    }
)

STEP16_CONTEXT_ONLY_EXACT_COLUMNS = frozenset(
    {
        "diagnostic_context",
        "diagnostic_context_score",
        "diagnostic_note",
        "diagnostic_status",
        "context_score",
        "context_note",
        "regime_context",
        "regime_fit_status",
        "redundancy_status",
        "complexity_status",
        "review_route",
        "ranking_reason_code",
    }
)

STEP16_ALLOWED_STATUS_SUFFIXES = (
    "_status",
    "_flag",
    "_count",
    "_metric",
    "_note",
    "_reason",
    "_reason_code",
)

STEP16_FORBIDDEN_EXACT_COLUMNS = frozenset(
    {
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
        "alpha_label",
        "alpha_signal",
        "signal",
        "buy",
        "sell",
        "hold",
        "buy_signal",
        "sell_signal",
        "hold_signal",
        "trading_signal",
        "recommendation",
        "target_price",
        "expected_return",
        "position_size",
        "valuation_score",
        "fundamental_score",
        "undervalued",
        "cheap",
        "bargain",
        "per",
        "pbr",
        "roe",
        "eps",
        "bps",
        "book_value",
        "earnings",
        "net_income",
        "revenue",
        "sales",
        "operating_income",
        "cash_flow",
        "free_cash_flow",
        "market_cap",
        "shares_outstanding",
        "dividend_yield",
        "debt_to_equity",
        "analyst_rating",
        "analyst_revision",
    }
)

STEP16_FORBIDDEN_PREFIXES = (
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
    "signal_",
    "buy_",
    "sell_",
    "hold_",
    "trading_signal",
    "target_price",
    "expected_return",
    "position_size",
    "valuation_",
    "fundamental_",
    "financial_",
    "analyst_",
    "earnings_",
    "revenue_",
    "sales_",
    "cash_flow_",
    "dividend_",
    "market_cap_",
)

STEP16_FORBIDDEN_SUFFIXES = (
    "_forward_return",
    "_future_return",
    "_next_return",
    "_backtest_return",
    "_alpha",
    "_signal",
    "_buy",
    "_sell",
    "_hold",
    "_target_price",
    "_expected_return",
    "_position_size",
)

STEP16_FORBIDDEN_SUBSTRINGS = (
    "future_return",
    "forward_return",
    "next_day_return",
    "next_month_return",
    "next_period_return",
    "label_return",
    "target_return",
    "backtest_return",
    "realized_return",
    "realized_pnl",
    "strategy_return",
    "portfolio_return",
    "benchmark_return",
    "excess_return",
    "sharpe",
    "sortino",
    "mdd",
    "drawdown",
    "cagr",
    "win_rate",
    "hit_rate",
    "hit_ratio",
    "profit_factor",
    "turnover",
    "slippage",
    "transaction_cost",
    "fee",
)

STEP16_FORBIDDEN_COLUMN_TOKENS = frozenset(
    {
        "alpha",
        "signal",
        "buy",
        "sell",
        "hold",
        "cheap",
        "bargain",
        "undervalued",
    }
)

STEP16_RANK_MUTATION_COLUMNS = frozenset(
    {
        "new_rank",
        "step16_rank",
        "detail_rank",
        "rerank",
        "re_rank",
        "reranked_rank",
        "rank_delta",
        "rank_change",
        "ranking_score",
        "ranking_output",
        "rank_generated_at",
    }
)

STEP16_REPORT_TEXT_FIELDS = frozenset(
    {
        "report_notice",
        "boundary_notice",
        "report_boundary",
        "summary",
        "narrative",
        "explanation",
        "technical_context",
        "diagnostic_note",
        "context_note",
        "limitations",
        "reason",
        "commentary",
    }
)

STEP16_FORBIDDEN_REPORT_LANGUAGE = frozenset(
    {
        "alpha",
        "alpha evidence",
        "backtest",
        "backtested",
        "performance",
        "outperformance",
        "profitable",
        "market beating",
        "market-beating",
        "buy",
        "sell",
        "hold",
        "buy signal",
        "sell signal",
        "hold signal",
        "trading signal",
        "trading recommendation",
        "investment recommendation",
        "target price",
        "expected return",
        "position size",
        "undervalued",
        "cheap",
        "bargain",
        "value stock",
        "valuation",
        "fundamental",
        "valuation score",
        "fundamental score",
        "per ratio",
        "p/e",
        "pbr",
        "roe",
        "sharpe",
        "mdd",
        "cagr",
        "hit rate",
        "win rate",
        "turnover",
        "slippage",
        "fees",
        "portfolio result",
    }
)


@dataclass(frozen=True)
class Step16DetailReportValidationResult:
    """Validation result for Step 16 report boundary checks."""

    context: str
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    forbidden_fields: tuple[str, ...] = ()
    read_only_fields: tuple[str, ...] = ()
    context_only_fields: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return whether the validation passed."""

        return not self.errors

    @property
    def valid(self) -> bool:
        """Alias for callers that prefer shorter result names."""

        return self.is_valid

    def raise_for_errors(self) -> None:
        """Raise a compact ValueError when validation failed."""

        if self.errors:
            raise ValueError(f"{self.context} failed Step 16 validation: {'; '.join(self.errors)}")


def validate_step16_detail_report_input(
    data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    registry: Iterable[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
    context: str = "Step 16 detail report input",
    raise_on_error: bool = True,
) -> Step16DetailReportValidationResult:
    """Validate Step 16 report input without mutating ranking state."""

    frame = _coerce_frame(data)
    columns = _column_names(frame)
    errors: list[str] = []
    warnings: list[str] = []

    forbidden = find_step16_forbidden_fields(columns)
    if forbidden:
        errors.append(f"contains forbidden columns: {', '.join(forbidden)}")

    unknown_scores = find_unknown_step16_score_like_columns(columns, registry=registry)
    if unknown_scores:
        errors.append(f"contains unsupported score-like columns: {', '.join(unknown_scores)}")

    rank_mutations = find_step16_rank_mutation_fields(columns)
    if rank_mutations:
        errors.append(f"contains Step 16 rank/re-rank fields: {', '.join(rank_mutations)}")

    read_only = _read_only_fields(columns)
    if read_only:
        warnings.append("Step 15 rank fields are read-only display context.")

    context_only = find_step16_context_only_fields(columns)
    if context_only:
        warnings.append("Diagnostic/context fields are context-only, not direct alpha signals.")

    result = Step16DetailReportValidationResult(
        context=context,
        errors=tuple(errors),
        warnings=tuple(warnings),
        forbidden_fields=tuple(sorted(set(forbidden).union(rank_mutations))),
        read_only_fields=tuple(read_only),
        context_only_fields=tuple(context_only),
    )
    if raise_on_error:
        result.raise_for_errors()
    return result


def validate_step16_detail_report_output(
    report: str | pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    registry: Iterable[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
    context: str = "Step 16 detail report output",
    require_notice: bool = True,
    raise_on_error: bool = True,
) -> Step16DetailReportValidationResult:
    """Validate Step 16 report output boundaries and narrative language."""

    if isinstance(report, str):
        frame = pd.DataFrame()
        columns: tuple[str, ...] = ()
        report_text = report
    else:
        frame = _coerce_frame(report)
        columns = _column_names(frame)
        report_text = _extract_report_text(frame)

    base_result = validate_step16_detail_report_input(
        frame if columns else {},
        registry=registry,
        context=context,
        raise_on_error=False,
    )
    errors = list(base_result.errors)
    warnings = list(base_result.warnings)

    forbidden_language = find_step16_forbidden_report_language(report_text)
    if forbidden_language:
        errors.append(f"contains forbidden report language: {', '.join(forbidden_language)}")

    if require_notice and STEP16_DETAIL_REPORT_NOTICE not in report_text.lower():
        errors.append(f"missing required notice: {STEP16_DETAIL_REPORT_NOTICE}")

    result = Step16DetailReportValidationResult(
        context=context,
        errors=tuple(errors),
        warnings=tuple(warnings),
        forbidden_fields=base_result.forbidden_fields,
        read_only_fields=base_result.read_only_fields,
        context_only_fields=base_result.context_only_fields,
    )
    if raise_on_error:
        result.raise_for_errors()
    return result


def validate_step16_report_boundary(
    input_data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    output_data: str | pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    registry: Iterable[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
    context: str = "Step 16 report boundary",
    raise_on_error: bool = True,
) -> Step16DetailReportValidationResult:
    """Validate the one-way Step 15 ranking snapshot to Step 16 report boundary."""

    input_result = validate_step16_detail_report_input(
        input_data,
        registry=registry,
        context=f"{context} input",
        raise_on_error=False,
    )
    output_result = validate_step16_detail_report_output(
        output_data,
        registry=registry,
        context=f"{context} output",
        raise_on_error=False,
    )

    errors = [*input_result.errors, *output_result.errors]
    warnings = [*input_result.warnings, *output_result.warnings]
    read_only = sorted(set(input_result.read_only_fields).union(output_result.read_only_fields))
    context_only = sorted(
        set(input_result.context_only_fields).union(output_result.context_only_fields)
    )
    forbidden = sorted(
        set(input_result.forbidden_fields).union(output_result.forbidden_fields)
    )

    rank_errors = _rank_read_only_errors(input_data, output_data)
    errors.extend(rank_errors)

    result = Step16DetailReportValidationResult(
        context=context,
        errors=tuple(errors),
        warnings=tuple(dict.fromkeys(warnings)),
        forbidden_fields=tuple(forbidden),
        read_only_fields=tuple(read_only),
        context_only_fields=tuple(context_only),
    )
    if raise_on_error:
        result.raise_for_errors()
    return result


def build_allowed_step16_technical_columns(
    *,
    registry: Iterable[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
) -> frozenset[str]:
    """Build columns Step 16 may display as technical-only context."""

    allowed = set(STEP16_ALLOWED_BASE_COLUMNS)
    allowed.update(build_allowed_step15_score_like_columns(registry=registry))
    for spec in registry:
        allowed.add(spec.normalized_column)
        allowed.add(spec.status_column)
        allowed.add(spec.quality_flag_column)
        allowed.add(spec.coverage_column)
        allowed.add(spec.count_column)
        allowed.add(f"{spec.family}_family_score")
    return frozenset(allowed)


def find_step16_forbidden_fields(columns: pd.DataFrame | Iterable[str]) -> list[str]:
    """Return Step 16 fields that cross future, trading, or valuation boundaries."""

    column_names = _column_names(columns)
    forbidden: set[str] = set(find_valuation_fundamental_columns(column_names))
    for column in column_names:
        normalized = column.lower()
        tokens = set(normalized.split("_"))
        if (
            normalized in STEP16_FORBIDDEN_EXACT_COLUMNS
            or normalized.startswith(STEP16_FORBIDDEN_PREFIXES)
            or normalized.endswith(STEP16_FORBIDDEN_SUFFIXES)
            or any(term in normalized for term in STEP16_FORBIDDEN_SUBSTRINGS)
            or bool(tokens.intersection(STEP16_FORBIDDEN_COLUMN_TOKENS))
        ):
            forbidden.add(column)
    return sorted(forbidden)


def find_step16_rank_mutation_fields(columns: pd.DataFrame | Iterable[str]) -> list[str]:
    """Return Step 16 fields that imply new ranking or re-ranking."""

    rank_fields: list[str] = []
    for column in _column_names(columns):
        normalized = column.lower()
        if normalized in STEP16_RANK_MUTATION_COLUMNS or normalized.startswith(
            ("rerank_", "re_rank_", "step16_rank_", "new_rank_")
        ):
            rank_fields.append(column)
    return sorted(set(rank_fields))


def find_step16_context_only_fields(columns: pd.DataFrame | Iterable[str]) -> list[str]:
    """Return diagnostic/context fields that must stay explanatory only."""

    context_fields: list[str] = []
    for column in _column_names(columns):
        normalized = column.lower()
        if (
            normalized in STEP16_CONTEXT_ONLY_EXACT_COLUMNS
            or "diagnostic" in normalized
            or normalized.startswith(("context_", "regime_context"))
        ):
            context_fields.append(column)
    return sorted(set(context_fields))


def find_unknown_step16_score_like_columns(
    columns: pd.DataFrame | Iterable[str],
    *,
    registry: Iterable[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
) -> list[str]:
    """Return score-like fields that are neither known technical nor context-only."""

    allowed = build_allowed_step16_technical_columns(registry=registry)
    forbidden = set(find_step16_forbidden_fields(columns))
    context_only = set(find_step16_context_only_fields(columns))
    unknown: list[str] = []
    for column in _column_names(columns):
        normalized = column.lower()
        if column in allowed or column in forbidden or column in context_only:
            continue
        if _is_status_or_flag_column(normalized):
            continue
        if _is_score_like_column(normalized):
            unknown.append(column)
    return sorted(unknown)


def find_step16_forbidden_report_language(text: str) -> list[str]:
    """Return forbidden Step 16 generated-report phrases found in text."""

    lowered = text.lower()
    return [
        term
        for term in sorted(STEP16_FORBIDDEN_REPORT_LANGUAGE)
        if _contains_forbidden_term(lowered, term)
    ]


def _rank_read_only_errors(
    input_data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    output_data: str | pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> list[str]:
    if isinstance(output_data, str):
        return []
    input_frame = _coerce_frame(input_data)
    output_frame = _coerce_frame(output_data)
    if "rank" not in output_frame.columns:
        return []
    if "rank" not in input_frame.columns:
        return ["output rank requires input rank to verify read-only Step 15 context"]

    key_columns = [column for column in ("ticker", "date") if column in input_frame.columns]
    if all(column in output_frame.columns for column in key_columns) and key_columns:
        left = input_frame.loc[:, [*key_columns, "rank"]].copy()
        right = output_frame.loc[:, [*key_columns, "rank"]].copy()
        for column in key_columns:
            left[column] = left[column].astype("string")
            right[column] = right[column].astype("string")
        merged = right.merge(left, on=key_columns, how="left", suffixes=("_output", "_input"))
        missing = merged["rank_input"].isna() & merged["rank_output"].notna()
        changed = merged["rank_input"].astype("string") != merged["rank_output"].astype("string")
        if (missing | changed).any():
            return ["output rank must match the read-only Step 15 input rank"]
        return []

    if len(input_frame) != len(output_frame):
        return ["output rank cannot be verified as read-only without matching rows"]
    input_ranks = input_frame["rank"].astype("string").reset_index(drop=True)
    output_ranks = output_frame["rank"].astype("string").reset_index(drop=True)
    if not input_ranks.equals(output_ranks):
        return ["output rank must match the read-only Step 15 input rank"]
    return []


def _read_only_fields(columns: Iterable[str]) -> list[str]:
    return ["rank"] if "rank" in set(columns) else []


def _coerce_frame(
    data: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, Mapping):
        return pd.DataFrame([dict(data)])
    return pd.DataFrame(list(data))


def _column_names(columns: pd.DataFrame | Iterable[str]) -> tuple[str, ...]:
    if isinstance(columns, pd.DataFrame):
        return tuple(str(column) for column in columns.columns)
    return tuple(str(column) for column in columns)


def _extract_report_text(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    parts: list[str] = []
    for column in frame.columns:
        normalized = str(column).lower()
        if normalized not in STEP16_REPORT_TEXT_FIELDS and not any(
            token in normalized
            for token in ("summary", "narrative", "explanation", "notice", "reason", "note")
        ):
            continue
        values = frame[column].dropna().tolist()
        parts.extend(_stringify_text_value(value) for value in values)
    return "\n".join(parts)


def _stringify_text_value(value: object) -> str:
    if isinstance(value, (list, tuple, set, frozenset)):
        return " ".join(str(item) for item in value)
    return str(value)


def _is_status_or_flag_column(normalized: str) -> bool:
    return normalized.endswith(STEP16_ALLOWED_STATUS_SUFFIXES)


def _is_score_like_column(normalized: str) -> bool:
    return (
        normalized.endswith("_score")
        or normalized.endswith("_robust_z")
        or normalized.endswith("_robust_zscore")
        or normalized.endswith("_normalized")
        or "composite" in normalized
    )


def _contains_forbidden_term(lowered: str, term: str) -> bool:
    term = term.lower()
    if " " in term or "-" in term or "_" in term:
        return term in lowered
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", lowered) is not None


__all__ = (
    "STEP16_DETAIL_REPORT_NOTICE",
    "Step16DetailReportValidationResult",
    "build_allowed_step16_technical_columns",
    "find_step16_context_only_fields",
    "find_step16_forbidden_fields",
    "find_step16_forbidden_report_language",
    "find_step16_rank_mutation_fields",
    "find_unknown_step16_score_like_columns",
    "validate_step16_detail_report_input",
    "validate_step16_detail_report_output",
    "validate_step16_report_boundary",
)
