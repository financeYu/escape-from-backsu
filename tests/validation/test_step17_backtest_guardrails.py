from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.validation.step17_backtest_guardrails import (  # noqa: E402
    STEP17_REQUIRED_LIMITATION_FLAGS,
    find_step17_forbidden_fields,
    find_step17_forbidden_report_language,
    validate_step17_backtest_input,
    validate_step17_backtest_output,
    validate_step17_backtest_report,
    validate_step17_no_feedback_loop,
    validate_step17_report_boundary,
)


def step15_snapshot_input() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "005930",
                "date": "2026-04-24",
                "rank": 1,
                "technical_composite_score": 1.25,
                "final_composite_score": 1.25,
                "coverage_metric": 1.0,
                "data_quality_flag": "valid",
            }
        ]
    )


def limitation_text() -> str:
    return (
        "Limitations: survivorship bias is disclosed when PIT constituent "
        "membership is unavailable; corporate action / adjusted price "
        "uncertainty is disclosed when applicable; missing execution or exit "
        "price handling is explicit; transaction cost and slippage assumptions "
        "are explicit; no valuation/fundamental data used; no return feedback "
        "into upstream scores."
    )


def valid_report_text() -> str:
    return (
        "evaluation-only conservative backtest artifact. "
        "This is not a trading recommendation. "
        "It does not redefine score or ranking formulas. "
        "It uses technical-only upstream ranking context. "
        "Valuation/fundamental scoring remains gated until Step 18. "
        f"{limitation_text()}"
    )


def valid_backtest_output(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "ticker": "005930",
        "evaluation_start_date": "2026-04-24",
        "evaluation_end_date": "2026-04-30",
        "execution_date": "2026-04-27",
        "exit_date": "2026-04-30",
        "realized_holding_return": 0.012,
        "backtest_period_return": 0.010,
        "evaluation_return": 0.010,
        "transaction_cost_bps": 10,
        "slippage_bps": 5,
        "limitation_flags": list(STEP17_REQUIRED_LIMITATION_FLAGS),
        "boundary_notice": valid_report_text(),
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "column",
    (
        "valuation_score",
        "fundamental_score",
        "PER",
        "PBR",
        "ROE",
        "EPS",
        "BPS",
        "market_cap",
        "cheap",
        "undervalued",
        "bargain",
    ),
)
def test_forbidden_valuation_columns_are_rejected(column: str) -> None:
    frame = step15_snapshot_input()
    frame[column] = 1

    with pytest.raises(ValueError, match="forbidden Step 17 fields"):
        validate_step17_backtest_input(frame)

    assert column in find_step17_forbidden_fields(frame.columns)


@pytest.mark.parametrize(
    "column",
    (
        "signal",
        "buy",
        "sell",
        "hold",
        "recommendation",
        "target_price",
        "expected_return",
        "alpha",
    ),
)
def test_forbidden_trading_columns_are_rejected(column: str) -> None:
    frame = step15_snapshot_input()
    frame[column] = 1

    with pytest.raises(ValueError, match="forbidden Step 17 fields"):
        validate_step17_backtest_input(frame)


@pytest.mark.parametrize("column", ("future_return", "forward_return", "future_return_20d"))
def test_future_and_forward_return_columns_are_rejected(column: str) -> None:
    frame = step15_snapshot_input()
    frame[column] = 0.12

    with pytest.raises(ValueError, match="forbidden Step 17 fields"):
        validate_step17_backtest_input(frame)


def test_realized_holding_return_is_allowed_only_in_step17_output_context() -> None:
    input_frame = step15_snapshot_input()
    input_frame["realized_holding_return"] = 0.02

    with pytest.raises(ValueError, match="allowed only in backtest output context"):
        validate_step17_backtest_input(input_frame)

    result = validate_step17_backtest_output(valid_backtest_output())

    assert result.is_valid
    assert "realized_holding_return" in result.evaluation_fields


@pytest.mark.parametrize(
    "forbidden_text",
    (
        "alpha is proven by this run.",
        "This is a profitable strategy.",
        "This is a buy recommendation.",
        "This is a sell recommendation.",
        "The target price is higher.",
        "The backtest is the score definition source.",
        "Automatic adoption follows from this backtest.",
    ),
)
def test_alpha_profitability_recommendation_and_adoption_language_is_rejected(
    forbidden_text: str,
) -> None:
    text = f"{valid_report_text()} {forbidden_text}"

    with pytest.raises(ValueError, match="forbidden report language"):
        validate_step17_backtest_report(text)

    assert find_step17_forbidden_report_language(forbidden_text)


def test_conservative_boundary_notice_is_required() -> None:
    text = valid_report_text().replace("evaluation-only ", "")

    with pytest.raises(ValueError, match="missing required notices"):
        validate_step17_backtest_report(text)


def test_missing_limitation_flags_are_caught() -> None:
    text = (
        "evaluation-only conservative backtest artifact. "
        "This is not a trading recommendation. "
        "It does not redefine score or ranking formulas. "
        "It uses technical-only upstream ranking context. "
        "Valuation/fundamental scoring remains gated until Step 18."
    )

    with pytest.raises(ValueError, match="missing limitation disclosures"):
        validate_step17_backtest_report(text)


def test_step18_valuation_leakage_is_caught_in_report_and_output() -> None:
    with pytest.raises(ValueError, match="forbidden report language"):
        validate_step17_backtest_report(f"{valid_report_text()} valuation_score improved.")

    output = valid_backtest_output(valuation_score=0.7)
    with pytest.raises(ValueError, match="forbidden Step 17 fields"):
        validate_step17_backtest_output(output)


@pytest.mark.parametrize(
    ("target_context", "protected_field"),
    (
        ("Step 13 review_status update", "review_status"),
        ("Step 14 adoption_state update", "adoption_state"),
        ("Step 15 ranking input update", "rank"),
        ("Step 16 detail report score update", "final_composite_score"),
    ),
)
def test_backtest_result_cannot_update_upstream_score_rank_or_adoption_fields(
    target_context: str,
    protected_field: str,
) -> None:
    update = {
        protected_field: "updated_from_backtest",
        "realized_holding_return": 0.03,
        "summary": "backtest output should remain evaluation-only",
    }

    with pytest.raises(ValueError, match="cannot update upstream context"):
        validate_step17_no_feedback_loop(update, target_context=target_context)


def test_report_boundary_accepts_clean_input_and_clean_evaluation_report() -> None:
    result = validate_step17_report_boundary(step15_snapshot_input(), valid_backtest_output())

    assert result.is_valid


def test_recursive_structured_output_language_check_exists() -> None:
    payload = valid_backtest_output(
        sections=[
            {
                "title": "nested note",
                "body": "This nested section says alpha is proven.",
            }
        ]
    )

    with pytest.raises(ValueError, match="forbidden report language"):
        validate_step17_backtest_report(payload)
