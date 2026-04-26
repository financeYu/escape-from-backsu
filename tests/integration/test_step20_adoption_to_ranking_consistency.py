from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
TESTS_ROOT = PROJECT_ROOT / "tests"
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from src.reports.security_detail_report import build_security_detail_report  # noqa: E402
from src.scanner.latest_ranking import build_latest_ranking_output  # noqa: E402
from src.validation.step17_backtest_guardrails import validate_step17_no_feedback_loop  # noqa: E402
from step20_fixtures import (  # noqa: E402
    adoption_synthesis_table,
    normalized_score_frame,
)


def test_step20_ranking_output_feeds_step16_as_readonly_context() -> None:
    ranking = build_latest_ranking_output(normalized_score_frame(), adoption_synthesis_table())
    report = build_security_detail_report(
        ranking,
        "000660",
        report_date="2026-04-25",
        adoption_synthesis=adoption_synthesis_table(),
    )

    assert report.rank_fields_are_readonly is True
    assert report.readonly_rank_fields["rank"] == 1
    assert report.readonly_rank_fields["neutral_shrinkage_count"] == 0
    assert "technical_only_notice" in report.readonly_rank_fields
    assert report.final_composite_score == report.technical_composite_score


def test_step17_backtest_output_cannot_update_upstream_scoring_or_ranking() -> None:
    update = pd.DataFrame(
        [
            {
                "ticker": "000660",
                "realized_holding_return": 0.12,
                "technical_composite_score": 9.9,
                "notes": "backtest result updates score",
            }
        ]
    )

    with pytest.raises(ValueError, match="cannot update upstream"):
        validate_step17_no_feedback_loop(update, target_context="Step 15 ranking")
