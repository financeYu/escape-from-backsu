from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY  # noqa: E402
from src.preprocess.schema_validator import GENERIC_EXCHANGE_SYMBOL_POLICY  # noqa: E402
from src.selection.adoption_synthesis_contracts import (  # noqa: E402
    assert_no_forbidden_adoption_columns,
)
from src.validation.step15_latest_ranking_guardrails import (  # noqa: E402
    STEP15_INPUT_PLAN_COLUMNS,
    STEP15_REQUIRED_LATEST_RANKING_COLUMNS,
    Step15Usage,
    find_step15_forbidden_columns,
    find_unknown_step15_score_like_columns,
    validate_step15_input_plan,
    validate_step15_latest_ranking_output,
    validate_step15_output_columns,
)


def latest_ranking_frame() -> pd.DataFrame:
    spec = next(iter(DEFAULT_COMPOSITE_INPUT_REGISTRY))
    return pd.DataFrame(
        [
            {
                "ticker": "005930",
                "date": "2026-04-24",
                "rank": 1,
                "technical_composite_score": 1.25,
                "final_composite_score": 1.25,
                "coverage_metric": 1.0,
                "data_quality_flag": "ok",
                spec.normalized_column: 0.75,
                "mean_reversion_family_score": 0.75,
                spec.status_column: "adequate",
                spec.quality_flag_column: "ok",
                spec.count_column: 190,
            },
            {
                "ticker": "000660",
                "date": "2026-04-24",
                "rank": 2,
                "technical_composite_score": 0.65,
                "final_composite_score": 0.65,
                "coverage_metric": 1.0,
                "data_quality_flag": "ok",
                spec.normalized_column: 0.25,
                "mean_reversion_family_score": 0.25,
                spec.status_column: "adequate",
                spec.quality_flag_column: "ok",
                spec.count_column: 188,
            },
        ],
        columns=(
            *STEP15_REQUIRED_LATEST_RANKING_COLUMNS,
            spec.normalized_column,
            "mean_reversion_family_score",
            spec.status_column,
            spec.quality_flag_column,
            spec.count_column,
        ),
    )


def input_plan_row(
    score_name: str = "short_term_overreaction",
    *,
    step15_usage: str = Step15Usage.DIRECT_SCORE_INPUT.value,
    adoption_state: str = "core_adopted",
    manual_review_required: bool = False,
    input_column: str | None = None,
    branch: str | None = None,
    role: str | None = None,
    eligibility: str | None = None,
) -> dict[str, object]:
    spec = next(
        candidate
        for candidate in DEFAULT_COMPOSITE_INPUT_REGISTRY
        if candidate.score_name == score_name
    )
    return {
        "score_name": score_name,
        "branch": branch or spec.branch,
        "role": role or spec.role.value,
        "eligibility": eligibility or spec.eligibility.value,
        "adoption_state": adoption_state,
        "input_column": input_column or spec.normalized_column,
        "step15_usage": step15_usage,
        "manual_review_required": manual_review_required,
    }


def input_plan(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=STEP15_INPUT_PLAN_COLUMNS)


def test_valid_latest_ranking_output_allows_only_known_technical_statistical_scores() -> None:
    frame = latest_ranking_frame()

    validate_step15_latest_ranking_output(frame, as_of_date="2026-04-25")
    validate_step15_output_columns(frame)


@pytest.mark.parametrize(
    "column",
    (
        "PER",
        "PBR",
        "ROE",
        "market_cap",
        "financial_revenue",
        "fundamental_score",
        "valuation_score",
        "analyst_rating",
        "analyst_score",
    ),
)
def test_financial_or_fundamental_output_columns_are_rejected(column: str) -> None:
    frame = latest_ranking_frame()
    frame[column] = 1

    with pytest.raises(ValueError, match="forbidden Step 15 columns"):
        validate_step15_latest_ranking_output(frame)

    assert column in find_step15_forbidden_columns(frame.columns)


@pytest.mark.parametrize(
    "column",
    (
        "forward_return",
        "future_return_20d",
        "next_day_return",
        "label_return",
        "target_return",
        "backtest_return",
        "sharpe_ratio",
        "mdd",
        "win_rate",
    ),
)
def test_future_return_and_performance_columns_are_rejected(column: str) -> None:
    frame = latest_ranking_frame()
    frame[column] = 0.10

    with pytest.raises(ValueError, match="forbidden Step 15 columns"):
        validate_step15_latest_ranking_output(frame)


@pytest.mark.parametrize(
    "column",
        (
            "sentiment_score",
            "custom_ml_score",
            "mystery_normalized",
        ),
)
def test_unknown_score_like_output_columns_are_rejected(column: str) -> None:
    frame = latest_ranking_frame()
    frame[column] = 0.5

    with pytest.raises(ValueError, match="unsupported score-like columns"):
        validate_step15_latest_ranking_output(frame)

    assert column in find_unknown_step15_score_like_columns(frame.columns)


@pytest.mark.parametrize("column", ("ranking", "latest_rank", "latest_ranking"))
def test_rank_synonyms_are_rejected_to_keep_schema_stable(column: str) -> None:
    frame = latest_ranking_frame()
    frame[column] = frame["rank"]

    with pytest.raises(ValueError, match="forbidden Step 15 columns"):
        validate_step15_latest_ranking_output(frame)


def test_output_schema_requires_stable_required_column_prefix() -> None:
    frame = latest_ranking_frame()
    reordered = frame[["date", "ticker", *frame.columns[2:]]]

    with pytest.raises(ValueError, match="must start with stable Step 15 columns"):
        validate_step15_latest_ranking_output(reordered)


def test_output_rejects_multiple_dates_future_dates_and_duplicate_tickers() -> None:
    multiple_dates = latest_ranking_frame()
    multiple_dates.loc[1, "date"] = "2026-04-23"
    with pytest.raises(ValueError, match="exactly one latest date"):
        validate_step15_latest_ranking_output(multiple_dates)

    future_date = latest_ranking_frame()
    with pytest.raises(ValueError, match="future dates"):
        validate_step15_latest_ranking_output(future_date, as_of_date="2026-04-23")

    duplicate = latest_ranking_frame()
    duplicate.loc[1, "ticker"] = "005930"
    with pytest.raises(ValueError, match="duplicate ticker/date"):
        validate_step15_latest_ranking_output(duplicate)


def test_output_rank_and_ticker_values_must_be_stable() -> None:
    duplicate_rank = latest_ranking_frame()
    duplicate_rank.loc[1, "rank"] = 1
    with pytest.raises(ValueError, match="rank values must be unique"):
        validate_step15_latest_ranking_output(duplicate_rank)

    invalid_rank = latest_ranking_frame()
    invalid_rank.loc[0, "rank"] = 0
    with pytest.raises(ValueError, match="rank values must be positive"):
        validate_step15_latest_ranking_output(invalid_rank)

    lost_leading_zero = latest_ranking_frame()
    lost_leading_zero.loc[0, "ticker"] = "5930"
    with pytest.raises(ValueError, match="six-character uppercase alphanumeric string"):
        validate_step15_latest_ranking_output(lost_leading_zero)


def test_output_accepts_kospi200_alphanumeric_ticker_by_default() -> None:
    frame = latest_ranking_frame()
    frame.loc[0, "ticker"] = "0126Z0"

    validate_step15_latest_ranking_output(frame)


def test_output_ticker_policy_can_be_supplied_for_future_extension_contracts() -> None:
    frame = latest_ranking_frame()
    frame.loc[0, "ticker"] = "AAPL"
    frame.loc[1, "ticker"] = "MSFT"

    validate_step15_latest_ranking_output(
        frame,
        symbol_policy=GENERIC_EXCHANGE_SYMBOL_POLICY,
    )


def test_blocked_output_rows_may_omit_rank_and_composite_scores() -> None:
    frame = latest_ranking_frame()
    frame["coverage_status"] = ["adequate", "blocked"]
    frame["ranking_validity_flag"] = ["valid", "blocked"]
    frame.loc[1, "rank"] = pd.NA
    frame.loc[1, "technical_composite_score"] = pd.NA
    frame.loc[1, "final_composite_score"] = pd.NA

    validate_step15_latest_ranking_output(frame)

    blocked_with_rank = frame.copy()
    blocked_with_rank.loc[1, "rank"] = 2
    with pytest.raises(ValueError, match="blocked rows must not receive rank"):
        validate_step15_latest_ranking_output(blocked_with_rank)


def test_direct_input_plan_allows_known_technical_candidate_signal_normalized_column() -> None:
    frame = input_plan([input_plan_row()])

    validate_step15_input_plan(frame)


def test_conditional_adopted_rows_are_not_direct_step15_inputs() -> None:
    frame = input_plan(
        [
            input_plan_row(
                adoption_state="conditional_adopted",
                step15_usage=Step15Usage.DIRECT_SCORE_INPUT.value,
            )
        ]
    )

    with pytest.raises(ValueError, match="adoption_state cannot be direct"):
        validate_step15_input_plan(frame)


def test_direct_input_plan_rejects_context_diagnostic_or_manual_review_rows() -> None:
    diagnostic_direct = input_plan(
        [
            input_plan_row(
                "realized_vol_percentile",
                adoption_state="technical_only",
                step15_usage=Step15Usage.DIRECT_SCORE_INPUT.value,
            )
        ]
    )
    with pytest.raises(ValueError, match="direct inputs must stay in technical branch"):
        validate_step15_input_plan(diagnostic_direct)

    confirmation_direct = input_plan(
        [
            input_plan_row(
                "cmf_confirmation",
                adoption_state="conditional_adopted",
                step15_usage=Step15Usage.DIRECT_SCORE_INPUT.value,
            )
        ]
    )
    with pytest.raises(ValueError, match="direct inputs must be candidate_signal"):
        validate_step15_input_plan(confirmation_direct)

    manual_review = input_plan(
        [
            input_plan_row(
                manual_review_required=True,
                adoption_state="needs_manual_review",
                step15_usage=Step15Usage.DIRECT_SCORE_INPUT.value,
            )
        ]
    )
    with pytest.raises(ValueError, match="manual-review rows cannot be direct inputs"):
        validate_step15_input_plan(manual_review)


def test_ambiguous_or_hybrid_items_must_route_to_review_or_excluded() -> None:
    hybrid_direct = input_plan(
        [
            {
                "score_name": "hybrid_value_momentum",
                "branch": "hybrid",
                "role": "candidate_signal",
                "eligibility": "conditional",
                "adoption_state": "conditional_adopted",
                "input_column": "hybrid_value_momentum_score",
                "step15_usage": Step15Usage.DIRECT_SCORE_INPUT.value,
                "manual_review_required": False,
            }
        ]
    )
    with pytest.raises(ValueError, match="unknown score cannot be direct"):
        validate_step15_input_plan(hybrid_direct)

    hybrid_review = hybrid_direct.copy()
    hybrid_review.loc[0, "step15_usage"] = Step15Usage.REVIEW_REQUIRED.value
    hybrid_review.loc[0, "manual_review_required"] = True
    validate_step15_input_plan(hybrid_review)


def test_financial_columns_may_only_be_routed_to_review_or_excluded() -> None:
    direct_financial = input_plan(
        [input_plan_row(input_column="PER", step15_usage=Step15Usage.DIRECT_SCORE_INPUT.value)]
    )
    with pytest.raises(ValueError, match="financial/fundamental input"):
        validate_step15_input_plan(direct_financial)

    review_financial = input_plan(
        [
            input_plan_row(
                input_column="PER",
                step15_usage=Step15Usage.REVIEW_REQUIRED.value,
                manual_review_required=True,
                adoption_state="needs_manual_review",
            )
        ]
    )
    validate_step15_input_plan(review_financial)

    excluded_financial = input_plan(
        [
            input_plan_row(
                input_column="PBR",
                step15_usage=Step15Usage.EXCLUDED.value,
                adoption_state="blocked_by_data",
            )
        ]
    )
    validate_step15_input_plan(excluded_financial)


def test_future_return_input_is_rejected_even_when_marked_for_review() -> None:
    future_review = input_plan(
        [
            input_plan_row(
                input_column="future_return_20d",
                step15_usage=Step15Usage.REVIEW_REQUIRED.value,
                manual_review_required=True,
                adoption_state="needs_manual_review",
            )
        ]
    )

    with pytest.raises(ValueError, match="future/performance leakage"):
        validate_step15_input_plan(future_review)


def test_step15_guardrails_do_not_weaken_step14_forbidden_column_contract() -> None:
    with pytest.raises(ValueError, match="forbidden Step 14 adoption columns"):
        assert_no_forbidden_adoption_columns(["score_name", "rank"])
