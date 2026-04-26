"""Step 14 adoption synthesis rule constants."""

from __future__ import annotations

STEP14_INPUT_REQUIRED_COLUMNS: tuple[str, ...] = (
    "score_name",
    "family",
    "branch",
    "role",
    "eligibility",
    "review_status",
    "evidence_sources",
    "manual_review_required",
)

STEP14_FORBIDDEN_EXACT_COLUMNS = frozenset(
    {
        "rank",
        "ranking",
        "latest_rank",
        "latest_ranking",
        "score_rank",
        "score_ranking",
        "technical_composite_score",
        "final_composite_score",
        "composite_score",
        "family_weighted_score",
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
        "valuation_score",
        "fundamental_score",
        "undervalued",
        "cheap",
        "bargain",
        "target_price",
        "expected_return",
        "position_size",
        "recommendation",
        "review_status",
        "selected_score",
        "selected_for_composite",
    }
)
STEP14_FORBIDDEN_PREFIXES = (
    "rank_",
    "ranking_",
    "latest_rank",
    "score_rank",
    "forward_return",
    "future_return",
    "next_period_return",
    "backtest_",
    "alpha_",
    "signal_",
    "buy_",
    "sell_",
    "valuation_",
    "fundamental_",
    "target_price",
    "expected_return",
    "position_size",
)
STEP14_FORBIDDEN_SUFFIXES = (
    "_rank",
    "_ranking",
    "_signal",
    "_alpha",
    "_target_price",
    "_expected_return",
    "_position_size",
)
STEP14_FORBIDDEN_SUBSTRINGS = (
    "technical_composite_score",
    "technical_composite",
    "final_composite_score",
    "final_composite",
    "composite_score",
    "family_weighted_score",
    "forward_return",
    "future_return",
    "backtest_return",
    "valuation_score",
    "target_price",
    "expected_return",
    "position_size",
    "latest_ranking",
    "latest_rank",
)
STEP14_FORBIDDEN_COLUMN_TOKENS = frozenset(
    {
        "rank",
        "ranking",
        "alpha",
        "signal",
        "buy",
        "sell",
        "cheap",
        "bargain",
        "undervalued",
    }
)

STEP14_FORBIDDEN_LANGUAGE_TERMS = frozenset(
    {
        "rank",
        "ranking",
        "latest rank",
        "latest_rank",
        "latest ranking",
        "latest_ranking",
        "technical_composite_score",
        "final_composite_score",
        "composite score",
        "forward return",
        "forward_return",
        "future return",
        "future_return",
        "backtest",
        "backtest_return",
        "alpha",
        "signal",
        "buy",
        "sell",
        "valuation",
        "valuation_score",
        "undervalued",
        "cheap",
        "bargain",
        "target price",
        "target_price",
        "expected return",
        "expected_return",
        "position size",
        "position_size",
    }
)

STEP14_ALLOWED_BOUNDARY_PHRASES = (
    "not ranking, not composite score, not backtest, not trading signal, and not valuation",
)
STEP14_TEXT_COLUMNS = ("adoption_reason", "evidence_sources", "limitations")
STEP14_OPTIONAL_TEXT_COLUMNS = ("downstream_usage_note",)

BLOCKING_COVERAGE_STATUSES = frozenset(
    {
        "blocked_by_data",
        "insufficient_input",
        "insufficient_data",
        "config_missing",
    }
)
BLOCKING_REDUNDANCY_STATUSES = frozenset(
    {
        "config_missing",
        "insufficient_input",
        "insufficient_data",
    }
)
UNCLEAR_REDUNDANCY_STATUSES = frozenset(
    {
        "undefined_correlation",
        "unknown",
    }
)
SEVERE_REDUNDANCY_STATUSES = frozenset(
    {
        "severe_redundancy",
        "block_candidate",
    }
)
ACCEPTABLE_COVERAGE_STATUSES = frozenset({"ok"})
ACCEPTABLE_REDUNDANCY_STATUSES = frozenset({"ok"})
CONTEXT_ROLES = frozenset({"setup_context", "confirmation"})
DIAGNOSTIC_ROLES = frozenset({"diagnostic_context"})

__all__ = (
    "ACCEPTABLE_COVERAGE_STATUSES",
    "ACCEPTABLE_REDUNDANCY_STATUSES",
    "BLOCKING_COVERAGE_STATUSES",
    "BLOCKING_REDUNDANCY_STATUSES",
    "CONTEXT_ROLES",
    "DIAGNOSTIC_ROLES",
    "SEVERE_REDUNDANCY_STATUSES",
    "STEP14_ALLOWED_BOUNDARY_PHRASES",
    "STEP14_FORBIDDEN_COLUMN_TOKENS",
    "STEP14_FORBIDDEN_EXACT_COLUMNS",
    "STEP14_FORBIDDEN_LANGUAGE_TERMS",
    "STEP14_FORBIDDEN_PREFIXES",
    "STEP14_FORBIDDEN_SUBSTRINGS",
    "STEP14_FORBIDDEN_SUFFIXES",
    "STEP14_INPUT_REQUIRED_COLUMNS",
    "STEP14_OPTIONAL_TEXT_COLUMNS",
    "STEP14_TEXT_COLUMNS",
    "UNCLEAR_REDUNDANCY_STATUSES",
)
