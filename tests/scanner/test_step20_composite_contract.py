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

from src.scanner.latest_ranking import build_latest_ranking_output  # noqa: E402
from step20_fixtures import (  # noqa: E402
    adoption_synthesis_table,
    normalized_score_frame,
)


def test_final_composite_score_is_technical_only_alias_for_mvp() -> None:
    output = build_latest_ranking_output(normalized_score_frame(), adoption_synthesis_table())

    assert output["final_score_policy"].eq("technical_only_no_valuation").all()
    assert output["technical_only_notice"].str.contains("kospi200_technical_only").all()
    assert output["technical_composite_score"].equals(output["final_composite_score"])


def test_missing_direct_score_uses_neutral_shrinkage_not_skip_average() -> None:
    frame = normalized_score_frame()
    mask = frame["ticker"].eq("000660") & frame["date"].eq("2026-04-24")
    frame.loc[mask, "efficiency_ratio_trend_cross_sectional_status"] = "blocked"
    frame.loc[mask, "efficiency_ratio_trend_cross_sectional_quality_flag"] = "invalid"

    output = build_latest_ranking_output(
        frame,
        adoption_synthesis_table(),
        as_of_date="2026-04-24",
    )
    row = output.loc[output["ticker"].eq("000660")].iloc[0]

    assert row["neutral_shrinkage_count"] == 1
    assert row["valid_score_count"] == 2
    assert row["coverage_metric"] == pytest.approx(2 / 3)
    assert row["trend_breakout_family_score"] == pytest.approx(1.0)
    assert row["technical_composite_score"] == pytest.approx(1.0)


def test_warmup_insufficient_rows_are_blocked_conservatively() -> None:
    frame = normalized_score_frame()
    mask = frame["ticker"].eq("035420") & frame["date"].eq("2026-04-24")
    frame.loc[mask, "score_warmup_state"] = "warmup"

    output = build_latest_ranking_output(
        frame,
        adoption_synthesis_table(),
        as_of_date="2026-04-24",
    )
    row = output.loc[output["ticker"].eq("035420")].iloc[0]

    assert row["warmup_status"] == "blocked"
    assert row["ranking_validity_flag"] == "blocked"
    assert pd.isna(row["rank"])
    assert row["neutral_shrinkage_count"] == 3
