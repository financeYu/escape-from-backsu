from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.reports.security_detail_report_contracts import (  # noqa: E402
    STEP16_SECURITY_DETAIL_REPORT_NOTICE,
    SecurityDetailReport,
    SecurityReportBoundaryNotice,
    find_forbidden_step16_report_columns,
    find_forbidden_step16_report_text,
    validate_security_detail_report_content,
    validate_step16_latest_ranking_input,
    validate_step16_metadata_table,
)


def valid_latest_ranking_frame() -> pd.DataFrame:
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
            }
        ]
    )


def test_boundary_notice_contains_required_conservative_meaning() -> None:
    notice = SecurityReportBoundaryNotice().to_dict()

    assert notice["scope"] == STEP16_SECURITY_DETAIL_REPORT_NOTICE
    assert notice["trading_notice"] == "display context only"
    assert notice["simulation_notice"] == "no outcome simulation"
    assert notice["analysis_notice"] == "technical context only"
    assert notice["data_timing_notice"] == "same-date snapshot only"


@pytest.mark.parametrize(
    "column",
    (
        "buy",
        "sell",
        "target_price",
        "expected_return",
        "forward_return",
        "future_return",
        "backtest_return",
        "valuation_score",
        "undervalued",
        "cheap",
        "bargain",
        "PER",
        "PBR",
        "ROE",
    ),
)
def test_forbidden_input_columns_are_rejected(column: str) -> None:
    frame = valid_latest_ranking_frame()
    frame[column] = 1

    with pytest.raises(ValueError, match="forbidden Step 16 report columns"):
        validate_step16_latest_ranking_input(frame)

    assert column in find_forbidden_step16_report_columns(frame.columns)


@pytest.mark.parametrize(
    "text",
    (
        "buy",
        "sell",
        "target_price",
        "expected_return",
        "forward_return",
        "future_return",
        "A backtest supports this report.",
        "backtest_return",
        "The valuation case is strong.",
        "Fundamental evidence is supportive.",
        "valuation_score",
        "undervalued",
        "cheap",
        "bargain",
        "This is a hold setup.",
        "position_size can increase.",
        "Sharpe is high.",
        "PER",
        "PBR",
        "ROE",
    ),
)
def test_forbidden_report_text_is_rejected(text: str) -> None:
    assert find_forbidden_step16_report_text(text)
    with pytest.raises(ValueError, match="forbidden Step 16 report content"):
        validate_security_detail_report_content({"note": text})


@pytest.mark.parametrize(
    "text",
    (
        "target_price is unavailable",
        "A backtest supports this report.",
        "The valuation case is strong.",
        "Fundamental evidence is supportive.",
    ),
)
def test_metadata_text_is_screened_before_it_can_enter_report(text: str) -> None:
    metadata = pd.DataFrame(
        [
            {
                "score_name": "short_term_overreaction",
                "adoption_state": "core_adopted",
                "limitations": text,
            }
        ]
    )

    with pytest.raises(ValueError, match="forbidden Step 16 report language"):
        validate_step16_metadata_table(metadata)


def test_security_detail_report_to_dict_validates_structured_content() -> None:
    report = SecurityDetailReport(
        ticker="005930",
        snapshot_date="2026-04-24",
        report_date="2026-04-24",
        source_latest_ranking_date="2026-04-24",
        rank_fields_are_readonly=True,
        readonly_rank_fields={"rank": 1},
        technical_composite_score=1.25,
        final_composite_score=1.25,
        final_composite_score_note="Displayed as existing Step 15 technical-only context.",
        score_breakdown=(),
        component_breakdown=(),
        diagnostic_context=(),
        source_adoption_metadata=(),
        quality_flags={"coverage_status": "adequate"},
        explanations=(),
    )

    record = report.to_dict()

    assert record["ticker"] == "005930"
    assert record["readonly_rank_fields"]["rank"] == 1
    assert record["boundary_notice"]["scope"] == STEP16_SECURITY_DETAIL_REPORT_NOTICE
