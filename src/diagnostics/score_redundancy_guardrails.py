"""Input guardrails for Step 12 score redundancy diagnostics."""

from __future__ import annotations

import pandas as pd

from src.composite.schema import find_forbidden_step11_output_columns
from src.scores.schema import find_valuation_fundamental_columns


FORBIDDEN_INPUT_FRAGMENTS = (
    "rank",
    "ranking",
    "latest_rank",
    "technical_composite_score",
    "final_composite_score",
    "forward_return",
    "future_return",
    "backtest_return",
    "alpha",
    "signal",
    "buy",
    "sell",
)
BLOCKING_QUALITY_FLAGS = frozenset(
    {
        "invalid_ticker",
        "leading_zero_lost",
        "invalid_date",
        "future_date",
        "duplicate_ticker_date",
        "invalid_numeric",
    }
)


def _assert_no_forbidden_step12_input_columns(frame: pd.DataFrame) -> None:
    forbidden = set(find_forbidden_step11_output_columns(frame.columns))
    for column in frame.columns:
        normalized = column.lower()
        if any(fragment == normalized for fragment in FORBIDDEN_INPUT_FRAGMENTS):
            forbidden.add(column)
    if forbidden:
        raise ValueError(
            "Step 12 redundancy input contains forbidden columns: "
            + ", ".join(sorted(forbidden))
        )


def _assert_no_valuation_fundamental_columns(frame: pd.DataFrame) -> None:
    flagged = find_valuation_fundamental_columns(frame.columns)
    if flagged:
        raise ValueError(
            "Step 12 redundancy input contains valuation/fundamental columns: "
            + ", ".join(flagged)
        )


def _has_blocking_quality_flag(value: object) -> bool:
    if pd.isna(value):
        return False
    flags = {part.strip() for part in str(value).split(";") if part.strip()}
    return bool(flags.intersection(BLOCKING_QUALITY_FLAGS))


__all__ = ()
