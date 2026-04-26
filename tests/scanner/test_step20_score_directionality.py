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


def test_higher_direct_normalized_scores_rank_better() -> None:
    output = build_latest_ranking_output(
        normalized_score_frame(),
        adoption_synthesis_table(),
        as_of_date="2026-04-24",
    )

    assert output["ticker"].tolist()[:3] == ["000660", "005930", "051910"]
    assert output.loc[0, "final_composite_score"] > output.loc[1, "final_composite_score"]
    assert output.loc[1, "final_composite_score"] == pytest.approx(
        output.loc[2, "final_composite_score"]
    )


def test_score_directionality_is_deterministic_for_repeated_runs() -> None:
    frame = normalized_score_frame()
    adoption = adoption_synthesis_table()

    first = build_latest_ranking_output(frame, adoption, as_of_date="2026-04-24")
    second = build_latest_ranking_output(frame.sample(frac=1.0, random_state=7), adoption)

    pd.testing.assert_frame_equal(first, second)


def test_context_and_diagnostic_scores_do_not_change_rank_when_extreme() -> None:
    baseline = build_latest_ranking_output(
        normalized_score_frame(),
        adoption_synthesis_table(),
        as_of_date="2026-04-24",
    )
    contaminated_context = normalized_score_frame()
    latest = contaminated_context["date"].eq("2026-04-24")
    contaminated_context.loc[latest, "realized_vol_percentile_cross_sectional_robust_z"] = 999.0
    contaminated_context.loc[latest, "bollinger_width_squeeze_cross_sectional_robust_z"] = -999.0
    contaminated_context.loc[latest, "cmf_confirmation_cross_sectional_robust_z"] = 999.0

    repeated = build_latest_ranking_output(
        contaminated_context,
        adoption_synthesis_table(),
        as_of_date="2026-04-24",
    )

    assert baseline["ticker"].tolist() == repeated["ticker"].tolist()
    assert baseline["final_composite_score"].tolist() == repeated["final_composite_score"].tolist()
