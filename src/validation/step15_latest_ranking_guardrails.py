"""Step 15 latest ranking validation guardrails.

This module validates Step 15 inputs and output tables. It does not generate
rankings, calculate scores, run backtests, or perform valuation/fundamental
scoring.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
import pandas as pd

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY, CompositeInputSpec
from src.preprocess.schema_validator import KOSPI200_SYMBOL_POLICY, SymbolPolicy
from src.scores.schema import find_missing_columns, find_valuation_fundamental_columns
from src.validation.common import column_names
from src.validation.field_guardrails import find_forbidden_columns_by_rules


STEP15_LATEST_RANKING_NOTICE = "latest ranking output technical/statistical only"

STEP15_REQUIRED_LATEST_RANKING_COLUMNS: tuple[str, ...] = (
    "ticker",
    "date",
    "rank",
    "technical_composite_score",
    "final_composite_score",
    "coverage_metric",
    "data_quality_flag",
)

STEP15_INPUT_PLAN_COLUMNS: tuple[str, ...] = (
    "score_name",
    "branch",
    "role",
    "eligibility",
    "adoption_state",
    "input_column",
    "step15_usage",
    "manual_review_required",
)

STEP15_DIRECT_ADOPTION_STATES = frozenset(
    {
        "core_adopted",
        "technical_only",
    }
)

STEP15_REVIEW_OR_EXCLUDED_STATES = frozenset(
    {
        "conditional_adopted",
        "regime_only",
        "diagnostic_only",
        "research_only",
        "rejected",
        "blocked_by_data",
        "needs_manual_review",
    }
)

STEP15_ALLOWED_ADOPTION_STATES = frozenset(
    set(STEP15_DIRECT_ADOPTION_STATES).union(STEP15_REVIEW_OR_EXCLUDED_STATES)
)


class Step15Usage(str, Enum):
    """Allowed Step 15 routing labels for candidate input plans."""

    DIRECT_SCORE_INPUT = "direct_score_input"
    CONTEXT_DIAGNOSTIC = "context_diagnostic"
    REVIEW_REQUIRED = "review_required"
    EXCLUDED = "excluded"


ALLOWED_STEP15_USAGES = frozenset(usage.value for usage in Step15Usage)

STEP15_ALLOWED_CONTEXT_ROLES = frozenset(
    {
        "confirmation",
        "setup_context",
        "diagnostic_context",
    }
)

STEP15_FORBIDDEN_EXACT_COLUMNS = frozenset(
    {
        "ranking",
        "latest_rank",
        "latest_ranking",
        "alpha",
        "alpha_signal",
        "signal",
        "buy",
        "sell",
        "buy_signal",
        "sell_signal",
        "trading_signal",
        "recommendation",
        "valuation_score",
        "fundamental_score",
        "undervalued",
        "cheap",
        "bargain",
        "target_price",
        "expected_return",
        "position_size",
    }
)

STEP15_FORBIDDEN_PREFIXES = (
    "alpha_",
    "signal_",
    "buy_",
    "sell_",
    "valuation_",
    "fundamental_",
    "financial_",
    "target_price",
    "expected_return",
    "position_size",
)

STEP15_FORBIDDEN_SUFFIXES = (
    "_alpha",
    "_signal",
    "_buy",
    "_sell",
    "_target_price",
    "_expected_return",
    "_position_size",
)

STEP15_FORBIDDEN_TERMINOLOGY_TOKENS = frozenset(
    {
        "alpha",
        "signal",
        "buy",
        "sell",
        "cheap",
        "bargain",
        "undervalued",
    }
)

STEP15_FUTURE_OR_PERFORMANCE_SUBSTRINGS = (
    "forward_return",
    "future_return",
    "next_day_return",
    "next_month_return",
    "next_period_return",
    "label_return",
    "target_return",
    "realized_return",
    "realized_alpha",
    "backtest_return",
    "sharpe",
    "mdd",
    "max_drawdown",
    "win_rate",
    "profit_factor",
)

STEP15_EXTRA_FINANCIAL_EXACT_COLUMNS = frozenset(
    {
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

STEP15_EXTRA_FINANCIAL_PREFIXES = (
    "analyst_",
    "earnings_",
    "revenue_",
    "sales_",
    "cash_flow_",
    "dividend_",
    "market_cap_",
)

STEP15_ALLOWED_BASE_OUTPUT_COLUMNS = frozenset(STEP15_REQUIRED_LATEST_RANKING_COLUMNS)
STEP15_ALLOWED_DIAGNOSTIC_OUTPUT_COLUMNS = frozenset(
    {
        "coverage_status",
        "validity_flag",
        "review_route",
        "manual_review_required",
        "diagnostic_note",
        "ranking_reason_code",
    }
)


@dataclass(frozen=True)
class Step15InputPlanRow:
    """A Step 15 input routing row used by validation and review checks."""

    score_name: str
    branch: str
    role: str
    eligibility: str
    adoption_state: str
    input_column: str
    step15_usage: str
    manual_review_required: bool
    schema_columns: tuple[str, ...] = field(
        default=STEP15_INPUT_PLAN_COLUMNS,
        init=False,
        repr=False,
        compare=False,
    )


def validate_step15_latest_ranking_output(
    frame: pd.DataFrame,
    *,
    as_of_date: str | pd.Timestamp | None = None,
    registry: Iterable[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
    context: str = "Step 15 latest ranking output",
) -> None:
    """Validate a Step 15 latest ranking table without calculating rankings."""

    validate_step15_output_columns(frame, registry=registry, context=context)
    _assert_required_prefix(frame.columns, context=context)
    _assert_single_latest_date(frame, as_of_date=as_of_date, context=context)
    _assert_tickers_are_safe_strings(frame, symbol_policy=symbol_policy, context=context)
    _assert_no_duplicate_ticker_date(frame, context=context)
    _assert_rank_values_are_stable(frame, context=context)
    _assert_score_columns_are_finite(
        frame,
        ("technical_composite_score", "final_composite_score"),
        context=context,
    )


def validate_step15_output_columns(
    columns: pd.DataFrame | Iterable[str],
    *,
    registry: Iterable[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
    context: str = "Step 15 latest ranking output",
) -> None:
    """Validate required Step 15 columns and forbidden boundary columns."""

    names = column_names(columns)
    missing = find_missing_columns(names, STEP15_REQUIRED_LATEST_RANKING_COLUMNS)
    if missing:
        raise ValueError(f"{context} missing required columns: {', '.join(missing)}")
    forbidden = find_step15_forbidden_columns(names)
    if forbidden:
        raise ValueError(
            f"{context} contains forbidden Step 15 columns: {', '.join(forbidden)}"
        )
    unknown_score_columns = find_unknown_step15_score_like_columns(
        names,
        registry=registry,
    )
    if unknown_score_columns:
        raise ValueError(
            f"{context} contains unsupported score-like columns: "
            f"{', '.join(unknown_score_columns)}"
        )


def validate_step15_input_plan(
    frame: pd.DataFrame,
    *,
    registry: Iterable[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
    context: str = "Step 15 input plan",
) -> None:
    """Validate Step 15 input routing without generating ranking behavior."""

    column_names = tuple(str(column) for column in frame.columns)
    missing = find_missing_columns(column_names, STEP15_INPUT_PLAN_COLUMNS)
    if missing:
        raise ValueError(f"{context} missing required columns: {', '.join(missing)}")

    registry_by_name = {spec.score_name: spec for spec in registry}
    _assert_allowed_values(frame, "adoption_state", STEP15_ALLOWED_ADOPTION_STATES, context=context)
    _assert_allowed_values(frame, "step15_usage", ALLOWED_STEP15_USAGES, context=context)
    _assert_manual_review_required_is_boolean(frame, context=context)

    for _, row in frame.iterrows():
        _validate_step15_input_plan_row(row, registry_by_name=registry_by_name, context=context)


def find_step15_forbidden_columns(columns: pd.DataFrame | Iterable[str]) -> list[str]:
    """Return Step 15 columns that violate valuation, future, or trading guardrails."""

    names = column_names(columns)
    forbidden: set[str] = set(
        find_forbidden_columns_by_rules(
            names,
            exact=STEP15_FORBIDDEN_EXACT_COLUMNS,
            prefixes=STEP15_FORBIDDEN_PREFIXES,
            suffixes=STEP15_FORBIDDEN_SUFFIXES,
            tokens=STEP15_FORBIDDEN_TERMINOLOGY_TOKENS,
            extra_predicates=(
                _is_future_or_performance_column,
                _is_financial_or_fundamental_column,
            ),
        )
    )
    forbidden.update(find_valuation_fundamental_columns(names))
    return sorted(forbidden)


def find_unknown_step15_score_like_columns(
    columns: pd.DataFrame | Iterable[str],
    *,
    registry: Iterable[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
) -> list[str]:
    """Return score-like columns that are not known technical/statistical outputs."""

    allowed = build_allowed_step15_score_like_columns(registry=registry)
    unknown: list[str] = []
    for column in column_names(columns):
        if column in allowed:
            continue
        if column in STEP15_ALLOWED_BASE_OUTPUT_COLUMNS:
            continue
        if column in STEP15_ALLOWED_DIAGNOSTIC_OUTPUT_COLUMNS:
            continue
        if _is_status_or_flag_column(column):
            continue
        if _is_score_like_column(column):
            unknown.append(column)
    return sorted(unknown)


def build_allowed_step15_score_like_columns(
    *,
    registry: Iterable[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
) -> frozenset[str]:
    """Build the allowed Step 15 technical/statistical score-like column set."""

    specs = tuple(registry)
    families = sorted({spec.family for spec in specs})
    columns: set[str] = {
        "technical_composite_score",
        "final_composite_score",
    }
    for spec in specs:
        columns.add(spec.normalized_column)
        columns.add(spec.status_column)
        columns.add(spec.quality_flag_column)
        columns.add(spec.coverage_column)
        columns.add(spec.count_column)
    for family in families:
        columns.add(f"{family}_family_score")
        columns.add(f"family_{family}_score")
        columns.add(f"{family}_family_coverage_metric")
    return frozenset(columns)


def _validate_step15_input_plan_row(
    row: pd.Series,
    *,
    registry_by_name: dict[str, CompositeInputSpec],
    context: str,
) -> None:
    score_name = str(row["score_name"])
    branch = str(row["branch"])
    role = str(row["role"])
    eligibility = str(row["eligibility"])
    adoption_state = str(row["adoption_state"])
    input_column = str(row["input_column"])
    usage = str(row["step15_usage"])
    manual_review_required = bool(row["manual_review_required"])

    if _is_future_or_performance_column(input_column.lower()):
        raise ValueError(f"{context} contains future/performance leakage: {input_column}")

    financial = _is_financial_or_fundamental_column(input_column.lower()) or bool(
        find_valuation_fundamental_columns((input_column,))
    )
    if financial and usage not in {Step15Usage.REVIEW_REQUIRED.value, Step15Usage.EXCLUDED.value}:
        raise ValueError(
            f"{context} financial/fundamental input must be review_required or excluded: "
            f"{score_name}"
        )
    if financial:
        return

    known_spec = registry_by_name.get(score_name)
    if known_spec is None:
        if usage in {Step15Usage.REVIEW_REQUIRED.value, Step15Usage.EXCLUDED.value}:
            if usage == Step15Usage.REVIEW_REQUIRED.value and not manual_review_required:
                raise ValueError(f"{context} review_required rows must set manual_review_required.")
            return
        raise ValueError(f"{context} unknown score cannot be direct Step 15 input: {score_name}")

    if usage == Step15Usage.DIRECT_SCORE_INPUT.value:
        _assert_direct_score_input_row(
            score_name=score_name,
            branch=branch,
            role=role,
            eligibility=eligibility,
            adoption_state=adoption_state,
            input_column=input_column,
            manual_review_required=manual_review_required,
            spec=known_spec,
            context=context,
        )
        return

    if usage == Step15Usage.CONTEXT_DIAGNOSTIC.value:
        if role not in STEP15_ALLOWED_CONTEXT_ROLES:
            raise ValueError(f"{context} context_diagnostic row has unsupported role: {score_name}")
        if input_column != known_spec.normalized_column:
            raise ValueError(
                f"{context} context_diagnostic rows must use known normalized columns: "
                f"{score_name}"
            )
        return

    if usage == Step15Usage.REVIEW_REQUIRED.value and not manual_review_required:
        raise ValueError(f"{context} review_required rows must set manual_review_required.")


def _assert_direct_score_input_row(
    *,
    score_name: str,
    branch: str,
    role: str,
    eligibility: str,
    adoption_state: str,
    input_column: str,
    manual_review_required: bool,
    spec: CompositeInputSpec,
    context: str,
) -> None:
    if manual_review_required:
        raise ValueError(f"{context} manual-review rows cannot be direct inputs: {score_name}")
    if branch != "technical":
        raise ValueError(f"{context} direct inputs must stay in technical branch: {score_name}")
    if role != "candidate_signal":
        raise ValueError(f"{context} direct inputs must be candidate_signal rows: {score_name}")
    if eligibility not in {"eligible", "conditional"}:
        raise ValueError(f"{context} direct inputs have unsupported eligibility: {score_name}")
    if adoption_state not in STEP15_DIRECT_ADOPTION_STATES:
        raise ValueError(f"{context} adoption_state cannot be direct input: {score_name}")
    expected = (
        spec.branch,
        spec.role.value,
        spec.eligibility.value,
        spec.normalized_column,
    )
    observed = (branch, role, eligibility, input_column)
    if observed != expected:
        raise ValueError(
            f"{context} direct input must preserve Step 11 metadata and normalized column: "
            f"{score_name}"
        )


def _assert_required_prefix(columns: Iterable[str], *, context: str) -> None:
    observed = tuple(str(column) for column in columns)[: len(STEP15_REQUIRED_LATEST_RANKING_COLUMNS)]
    if observed != STEP15_REQUIRED_LATEST_RANKING_COLUMNS:
        raise ValueError(
            f"{context} must start with stable Step 15 columns: "
            f"{', '.join(STEP15_REQUIRED_LATEST_RANKING_COLUMNS)}"
        )


def _assert_single_latest_date(
    frame: pd.DataFrame,
    *,
    as_of_date: str | pd.Timestamp | None,
    context: str,
) -> None:
    dates = pd.to_datetime(frame["date"], errors="coerce")
    if dates.isna().any():
        raise ValueError(f"{context} contains unparseable date values.")
    if dates.nunique() != 1:
        raise ValueError(f"{context} must contain exactly one latest date snapshot.")
    if as_of_date is not None:
        as_of = pd.Timestamp(as_of_date)
        if (dates > as_of).any():
            raise ValueError(f"{context} contains future dates beyond as_of_date.")


def _assert_tickers_are_safe_strings(
    frame: pd.DataFrame,
    *,
    symbol_policy: SymbolPolicy,
    context: str,
) -> None:
    invalid = frame["ticker"].map(lambda value: not isinstance(value, str) or value.strip() == "")
    if invalid.any():
        raise ValueError(f"{context} ticker values must be non-empty strings.")
    unsafe = frame["ticker"].map(lambda value: not symbol_policy.is_valid(value))
    if unsafe.any():
        raise ValueError(f"{context} ticker values must preserve {symbol_policy.display_rule}.")


def _assert_no_duplicate_ticker_date(frame: pd.DataFrame, *, context: str) -> None:
    if frame.duplicated(["ticker", "date"]).any():
        raise ValueError(f"{context} contains duplicate ticker/date rows.")


def _assert_rank_values_are_stable(frame: pd.DataFrame, *, context: str) -> None:
    ranks = frame["rank"]
    numeric = pd.to_numeric(ranks, errors="coerce")
    blocked = _blocked_output_rows(frame)
    if (numeric.isna() & ~blocked).any():
        raise ValueError(f"{context} rank values must be numeric.")
    if (numeric.notna() & blocked).any():
        raise ValueError(f"{context} blocked rows must not receive rank values.")

    rankable = numeric.loc[~blocked]
    if (rankable <= 0).any():
        raise ValueError(f"{context} rank values must be positive.")
    if not _is_integer_like_series(rankable):
        raise ValueError(f"{context} rank values must be integer-like.")
    if rankable.duplicated().any():
        raise ValueError(f"{context} rank values must be unique.")


def _assert_score_columns_are_finite(
    frame: pd.DataFrame,
    columns: Iterable[str],
    *,
    context: str,
) -> None:
    blocked = _blocked_output_rows(frame)
    for column in columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        finite = pd.Series(np.isfinite(values), index=values.index)
        if (values.isna() & ~blocked).any() or (values.notna() & ~finite).any():
            raise ValueError(f"{context} {column} must contain finite numeric values.")


def _blocked_output_rows(frame: pd.DataFrame) -> pd.Series:
    blocked = pd.Series(False, index=frame.index)
    for column in ("coverage_status", "ranking_validity_flag", "validity_flag"):
        if column in frame.columns:
            blocked |= frame[column].astype("string").str.strip().str.lower().eq("blocked")
    return blocked


def _assert_allowed_values(
    frame: pd.DataFrame,
    column: str,
    allowed: frozenset[str],
    *,
    context: str,
) -> None:
    values = frame[column].astype("string").fillna("")
    invalid = sorted(set(values).difference(allowed))
    if invalid:
        raise ValueError(f"{context} contains unsupported {column} values: {', '.join(invalid)}")


def _assert_manual_review_required_is_boolean(frame: pd.DataFrame, *, context: str) -> None:
    invalid = [
        index
        for index, value in frame["manual_review_required"].items()
        if not isinstance(value, (bool, np.bool_))
    ]
    if invalid:
        raise ValueError(f"{context} manual_review_required must contain boolean values.")


def _is_integer_like_series(series: pd.Series) -> bool:
    return bool(((series % 1) == 0).all())


def _is_status_or_flag_column(column: str) -> bool:
    normalized = column.lower()
    return normalized.endswith(("_status", "_flag", "_count", "_metric", "_note", "_reason_code"))


def _is_score_like_column(column: str) -> bool:
    normalized = column.lower()
    return (
        normalized.endswith("_score")
        or normalized.endswith("_robust_z")
        or normalized.endswith("_robust_zscore")
        or "composite" in normalized
        or normalized.endswith("_normalized")
    )


def _is_future_or_performance_column(normalized: str) -> bool:
    return any(term in normalized for term in STEP15_FUTURE_OR_PERFORMANCE_SUBSTRINGS)


def _is_financial_or_fundamental_column(normalized: str) -> bool:
    return (
        normalized in STEP15_EXTRA_FINANCIAL_EXACT_COLUMNS
        or normalized.startswith(STEP15_EXTRA_FINANCIAL_PREFIXES)
    )


__all__ = (
    "ALLOWED_STEP15_USAGES",
    "STEP15_ALLOWED_ADOPTION_STATES",
    "STEP15_DIRECT_ADOPTION_STATES",
    "STEP15_INPUT_PLAN_COLUMNS",
    "STEP15_LATEST_RANKING_NOTICE",
    "STEP15_REQUIRED_LATEST_RANKING_COLUMNS",
    "Step15InputPlanRow",
    "Step15Usage",
    "build_allowed_step15_score_like_columns",
    "find_step15_forbidden_columns",
    "find_unknown_step15_score_like_columns",
    "validate_step15_input_plan",
    "validate_step15_latest_ranking_output",
    "validate_step15_output_columns",
)
