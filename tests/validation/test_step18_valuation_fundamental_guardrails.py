from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.validation.step18_valuation_fundamental_guardrails import (  # noqa: E402
    assert_step18_no_production_leakage,
    assert_step18_no_score_contamination,
    find_step18_candidate_columns,
    validate_step18_backtest_candidate_availability,
    validate_step18_candidate_records,
    validate_step18_candidate_report_text,
)


def candidate_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "symbol": "005930",
        "company_name": "Samsung Electronics",
        "metric_name": "roe",
        "metric_value": 9.5,
        "metric_unit": "percent",
        "metric_category": "profitability",
        "fiscal_period": "2025Q4",
        "report_date": "2026-03-15",
        "available_date": "2026-03-31",
        "source": "synthetic_fixture",
        "quality_flags": ("synthetic", "candidate_only"),
    }
    record.update(overrides)
    return record


def test_guardrail_entrypoint_validates_candidate_records() -> None:
    records = validate_step18_candidate_records(
        [candidate_record()],
        evaluation_date="2026-04-01",
    )

    assert records[0].metric_name == "roe"


def test_fundamental_columns_next_to_composite_scores_are_blocked() -> None:
    columns = [
        "ticker",
        "date",
        "technical_composite_score",
        "final_composite_score",
        "roe",
    ]

    with pytest.raises(ValueError, match="protected production columns"):
        assert_step18_no_score_contamination(columns)


def test_candidate_columns_are_not_allowed_in_production_outputs() -> None:
    frame = pd.DataFrame(
        [
            {
                "ticker": "005930",
                "date": "2026-04-01",
                "rank": 1,
                "per": 12.5,
            }
        ]
    )

    with pytest.raises(ValueError, match="candidate-only valuation/fundamental columns"):
        assert_step18_no_production_leakage(frame)


def test_candidate_only_score_placeholders_are_blocked_from_production_outputs() -> None:
    with pytest.raises(ValueError, match="candidate-only valuation/fundamental columns"):
        assert_step18_no_production_leakage(["ticker", "date", "valuation_candidate_score"])


def test_candidate_column_finder_covers_registry_and_metadata_fields() -> None:
    columns = ["ticker", "date", "per", "source_report_id", "fundamental_margin"]

    assert find_step18_candidate_columns(columns) == [
        "fundamental_margin",
        "per",
        "source_report_id",
    ]


def test_backtest_availability_guardrail_rejects_before_available_date() -> None:
    with pytest.raises(ValueError, match="not available for evaluation_date"):
        validate_step18_backtest_candidate_availability(
            [candidate_record(available_date="2026-04-10")],
            decision_date="2026-04-01",
        )


def test_candidate_report_notices_are_required() -> None:
    text = (
        "Step 18 candidate valuation/fundamental expansion. "
        "These fields are not activated in final ranking. "
        "These fields are not validated alpha signals. "
        "These fields must not be used in backtests unless availability-date rules are enforced."
    )
    validate_step18_candidate_report_text(text)

    with pytest.raises(ValueError, match="missing required notices"):
        validate_step18_candidate_report_text(text.replace("not validated alpha signals", "unreviewed"))
