from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY  # noqa: E402
from src.validation.step16_detail_report_guardrails import (  # noqa: E402
    STEP16_DETAIL_REPORT_NOTICE,
    find_step16_forbidden_fields,
    validate_step16_detail_report_input,
    validate_step16_detail_report_output,
    validate_step16_report_boundary,
)


def step15_report_input() -> pd.DataFrame:
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
                "data_quality_flag": "valid",
                "coverage_status": "adequate",
                "ranking_validity_flag": "valid",
                "valid_score_count": 3,
                "expected_score_count": 3,
                "review_routed_score_count": 1,
                "final_score_policy": "technical_only_no_valuation",
                spec.normalized_column: 0.75,
                "mean_reversion_family_score": 0.75,
                spec.status_column: "adequate",
                spec.quality_flag_column: "valid",
                spec.count_column: 190,
            }
        ]
    )


def report_output(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "ticker": "005930",
        "date": "2026-04-24",
        "rank": 1,
        "technical_composite_score": 1.25,
        "final_composite_score": 1.25,
        "coverage_metric": 1.0,
        "data_quality_flag": "valid",
        "report_notice": STEP16_DETAIL_REPORT_NOTICE,
        "summary": "Per-security technical context is explanatory only.",
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "column",
    (
        "forward_return",
        "future_return",
        "next_return",
        "backtest_return",
        "realized_return",
        "sharpe_ratio",
    ),
)
def test_forbidden_forward_future_and_backtest_columns_rejected(column: str) -> None:
    frame = step15_report_input()
    frame[column] = 0.12

    with pytest.raises(ValueError, match="forbidden columns"):
        validate_step16_detail_report_input(frame)

    assert column in find_step16_forbidden_fields(frame.columns)


@pytest.mark.parametrize(
    "column",
    (
        "PER",
        "PBR",
        "ROE",
        "financial_revenue",
        "fundamental_score",
        "valuation_score",
        "undervalued",
        "cheap",
        "bargain",
    ),
)
def test_forbidden_valuation_and_fundamental_columns_rejected(column: str) -> None:
    frame = step15_report_input()
    frame[column] = 1

    with pytest.raises(ValueError, match="forbidden columns"):
        validate_step16_detail_report_input(frame)


@pytest.mark.parametrize(
    "column",
    (
        "signal",
        "buy",
        "sell",
        "target_price",
        "expected_return",
        "position_size",
    ),
)
def test_forbidden_trading_signal_fields_rejected(column: str) -> None:
    frame = step15_report_input()
    frame[column] = 1

    with pytest.raises(ValueError, match="forbidden columns"):
        validate_step16_detail_report_input(frame)


def test_allowed_step15_technical_fields_are_accepted() -> None:
    result = validate_step16_detail_report_input(step15_report_input())

    assert result.is_valid
    assert "rank" in result.read_only_fields


def test_diagnostic_only_fields_are_accepted_only_as_context() -> None:
    frame = step15_report_input()
    frame["diagnostic_context_score"] = 0.42
    frame["diagnostic_note"] = "Coverage context for explanation."

    result = validate_step16_detail_report_input(frame)

    assert result.is_valid
    assert "diagnostic_context_score" in result.context_only_fields
    assert any("context-only" in warning for warning in result.warnings)


def test_technical_only_boundary_notice_required() -> None:
    result = validate_step16_detail_report_output(report_output())

    assert result.is_valid


def test_missing_boundary_notice_fails_validation() -> None:
    payload = report_output()
    payload.pop("report_notice")

    with pytest.raises(ValueError, match="missing required notice"):
        validate_step16_detail_report_output(payload)


def test_rank_field_is_accepted_only_as_read_only_display_context() -> None:
    source = step15_report_input()

    result = validate_step16_report_boundary(source, report_output())

    assert result.is_valid
    assert "rank" in result.read_only_fields

    changed_rank = report_output(rank=2)
    with pytest.raises(ValueError, match="read-only Step 15 input rank"):
        validate_step16_report_boundary(source, changed_rank)


@pytest.mark.parametrize(
    "text",
    (
        f"{STEP16_DETAIL_REPORT_NOTICE}\nThis looks cheap.",
        f"{STEP16_DETAIL_REPORT_NOTICE}\nThe security is undervalued.",
        f"{STEP16_DETAIL_REPORT_NOTICE}\nThis is a buy setup.",
        f"{STEP16_DETAIL_REPORT_NOTICE}\nThis is a sell setup.",
        f"{STEP16_DETAIL_REPORT_NOTICE}\nA backtest supports this report.",
    ),
)
def test_output_text_with_valuation_trading_or_backtest_language_fails(text: str) -> None:
    with pytest.raises(ValueError, match="forbidden report language"):
        validate_step16_detail_report_output(text)
