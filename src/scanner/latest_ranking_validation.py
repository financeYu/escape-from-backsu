"""Validation and forbidden-column checks for Step 15 latest ranking output."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import pandas as pd

from src.composite.contracts import (
    DEFAULT_COMPOSITE_INPUT_REGISTRY,
    CompositeInputSpec,
)
from src.composite.schema import validate_normalized_score_columns
from src.scanner.latest_ranking_policy import (
    DEFAULT_STEP15_RANKING_POLICY,
    STEP15_ALLOWED_COVERAGE_STATUSES,
    STEP15_ALLOWED_VALIDITY_FLAGS,
    STEP15_BASE_OUTPUT_COLUMNS,
    STEP15_DIRECT_RANKING_STATES,
    Step15RankingPolicy,
)
from src.scores.schema import (
    IDENTITY_COLUMNS,
    find_valuation_fundamental_columns,
    require_columns,
)
from src.selection.adoption_synthesis_contracts import validate_adoption_synthesis_table


STEP15_FORBIDDEN_EXACT_COLUMNS = frozenset(
    {
        "forward_return",
        "future_return",
        "next_return",
        "next_period_return",
        "backtest_return",
        "alpha",
        "alpha_label",
        "signal",
        "buy",
        "sell",
        "buy_signal",
        "sell_signal",
        "trading_signal",
        "valuation_score",
        "fundamental_score",
        "undervalued",
        "cheap",
        "bargain",
        "target_price",
        "expected_return",
        "position_size",
        "per",
        "pbr",
        "roe",
    }
)

STEP15_FORBIDDEN_PREFIXES = (
    "forward_return",
    "future_return",
    "next_return",
    "next_period_return",
    "backtest_",
    "alpha_",
    "signal_",
    "buy_",
    "sell_",
    "trading_signal",
    "valuation_",
    "fundamental_",
    "target_price",
    "expected_return",
    "position_size",
    "financial_",
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


def validate_step15_inputs(
    normalized_scores: pd.DataFrame,
    adoption_synthesis: pd.DataFrame,
    *,
    registry: Sequence[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
    policy: Step15RankingPolicy = DEFAULT_STEP15_RANKING_POLICY,
) -> None:
    """Validate Step 15 inputs before any ranking calculation."""

    assert_no_forbidden_step15_columns(
        normalized_scores.columns,
        context="Step 15 normalized input",
    )
    validate_normalized_score_columns(
        normalized_scores,
        registry=registry,
        context="Step 15 normalized input",
    )
    validate_adoption_synthesis_table(
        adoption_synthesis,
        registry=registry,
        require_all_scores=True,
        context="Step 15 adoption synthesis input",
    )
    invalid_states = sorted(
        set(policy.direct_ranking_states).difference(STEP15_DIRECT_RANKING_STATES)
    )
    if invalid_states:
        raise ValueError(
            "Step 15 direct_ranking_states may only include conservative direct "
            f"technical states: {', '.join(invalid_states)}"
        )


def validate_step15_latest_ranking_output(frame: pd.DataFrame) -> None:
    """Validate Step 15 latest ranking output boundaries."""

    require_columns(frame, STEP15_BASE_OUTPUT_COLUMNS, context="Step 15 latest ranking output")
    assert_no_forbidden_step15_columns(frame.columns, context="Step 15 latest ranking output")
    _assert_single_latest_date(frame)
    _assert_tickers_are_safe_strings(frame)
    _assert_unique_ticker_date(frame)
    _assert_allowed_output_status_values(frame)
    _assert_rank_order(frame)


def find_forbidden_step15_columns(
    columns: Iterable[str],
) -> list[str]:
    """Return forbidden Step 15 columns."""

    forbidden: set[str] = set(find_valuation_fundamental_columns(columns))
    for column in columns:
        normalized = str(column).lower()
        if (
            normalized in STEP15_FORBIDDEN_EXACT_COLUMNS
            or normalized.startswith(STEP15_FORBIDDEN_PREFIXES)
            or normalized.endswith(STEP15_FORBIDDEN_SUFFIXES)
        ):
            forbidden.add(str(column))
    return sorted(forbidden)


def assert_no_forbidden_step15_columns(
    columns: Iterable[str],
    *,
    context: str = "Step 15 output",
) -> None:
    """Reject Step 15 columns that imply leakage, trading, or valuation."""

    forbidden = find_forbidden_step15_columns(columns)
    if forbidden:
        raise ValueError(f"{context} contains forbidden Step 15 columns: {', '.join(forbidden)}")


def _assert_single_latest_date(frame: pd.DataFrame) -> None:
    dates = pd.to_datetime(frame["date"], errors="raise")
    if dates.nunique(dropna=False) != 1:
        raise ValueError("Step 15 latest ranking output must contain one latest date.")


def _assert_unique_ticker_date(frame: pd.DataFrame) -> None:
    duplicate_keys = frame.duplicated(list(IDENTITY_COLUMNS))
    if duplicate_keys.any():
        raise ValueError("Step 15 latest ranking output contains duplicate ticker/date rows.")


def _assert_tickers_are_safe_strings(frame: pd.DataFrame) -> None:
    invalid = frame["ticker"].map(lambda value: not isinstance(value, str) or value.strip() == "")
    if invalid.any():
        raise ValueError("Step 15 ticker values must be non-empty strings.")
    unsafe = frame["ticker"].map(lambda value: len(value) != 6 or not value.isdigit())
    if unsafe.any():
        raise ValueError("Step 15 ticker values must preserve six-digit string format.")


def _assert_allowed_output_status_values(frame: pd.DataFrame) -> None:
    invalid_coverage = sorted(
        set(frame["coverage_status"].astype("string")).difference(
            STEP15_ALLOWED_COVERAGE_STATUSES
        )
    )
    if invalid_coverage:
        raise ValueError(
            "Step 15 latest ranking output contains unsupported coverage_status "
            f"values: {', '.join(invalid_coverage)}"
        )
    invalid_flags = sorted(
        set(frame["ranking_validity_flag"].astype("string")).difference(
            STEP15_ALLOWED_VALIDITY_FLAGS
        )
    )
    if invalid_flags:
        raise ValueError(
            "Step 15 latest ranking output contains unsupported ranking_validity_flag "
            f"values: {', '.join(invalid_flags)}"
        )


def _assert_rank_order(frame: pd.DataFrame) -> None:
    scores = frame["final_composite_score"]
    ranks = frame["rank"]
    valid = scores.notna()
    if valid.any():
        expected_ranks = list(range(1, int(valid.sum()) + 1))
        observed_ranks = [int(value) for value in ranks.loc[valid].tolist()]
        if observed_ranks != expected_ranks:
            raise ValueError("Step 15 rank values must be consecutive for rankable rows.")
        ordered = frame.loc[valid, "final_composite_score"].tolist()
        if ordered != sorted(ordered, reverse=True):
            raise ValueError(
                "Step 15 latest ranking output is not sorted by final_composite_score."
            )
    if ranks.loc[~valid].notna().any():
        raise ValueError("Step 15 blocked rows must not receive rank values.")


__all__ = (
    "STEP15_FORBIDDEN_EXACT_COLUMNS",
    "STEP15_FORBIDDEN_PREFIXES",
    "STEP15_FORBIDDEN_SUFFIXES",
    "assert_no_forbidden_step15_columns",
    "find_forbidden_step15_columns",
    "validate_step15_inputs",
    "validate_step15_latest_ranking_output",
)
