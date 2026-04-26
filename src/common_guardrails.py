"""Shared constants for roadmap-gated guardrail validators.

The values here are inert boundary lists. Importing them must not enable
scoring, ranking, backtests, valuation/fundamental scoring, or trading outputs.
"""

from __future__ import annotations


COMMON_FORBIDDEN_OUTPUT_COLUMNS = frozenset(
    {
        "rank",
        "ranking",
        "latest_rank",
        "latest_ranking",
        "composite_score",
        "family_weighted_score",
        "technical_composite_score",
        "final_composite_score",
        "forward_return",
        "future_return",
        "next_return",
        "next_period_return",
        "backtest_return",
        "alpha",
        "signal",
        "buy",
        "sell",
        "buy_signal",
        "sell_signal",
        "alpha_signal",
        "recommendation",
        "fundamental_score",
        "valuation_score",
    }
)

NORMALIZED_SCORE_OUTPUT_COLUMNS = frozenset(
    {
        "normalized_score",
        "normalized_score_time_series",
        "normalized_score_cross_sectional",
    }
)

FORBIDDEN_VALUATION_INPUT_COLUMNS = frozenset(
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
        "market_cap",
        "shares_outstanding",
        "fundamental_score",
        "valuation_score",
    }
)

FORBIDDEN_VALUATION_INPUT_PREFIXES = (
    "financial_",
    "fundamental_",
    "valuation_",
)

VALUATION_FIELD_TOKENS = frozenset(
    {
        "per",
        "pbr",
        "roe",
        "eps",
        "bps",
        "book",
        "earnings",
        "revenue",
        "sales",
        "income",
        "financial",
        "fundamental",
        "valuation",
    }
)


__all__ = (
    "COMMON_FORBIDDEN_OUTPUT_COLUMNS",
    "FORBIDDEN_VALUATION_INPUT_COLUMNS",
    "FORBIDDEN_VALUATION_INPUT_PREFIXES",
    "NORMALIZED_SCORE_OUTPUT_COLUMNS",
    "VALUATION_FIELD_TOKENS",
)
