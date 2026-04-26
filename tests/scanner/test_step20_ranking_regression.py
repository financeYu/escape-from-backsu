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

from src.scanner.latest_ranking import (  # noqa: E402
    build_latest_ranking_output,
    validate_step15_latest_ranking_output,
)
from src.validation.step15_latest_ranking_guardrails import (  # noqa: E402
    validate_step15_latest_ranking_output as validate_guardrail_output,
)
from step20_fixtures import (  # noqa: E402
    adoption_synthesis_table,
    normalized_score_frame,
)


def test_ranking_date_selection_uses_latest_eligible_single_snapshot() -> None:
    output = build_latest_ranking_output(normalized_score_frame(), adoption_synthesis_table())

    assert output["date"].tolist() == ["2026-04-24"] * 4
    validate_step15_latest_ranking_output(output)
    validate_guardrail_output(output, as_of_date="2026-04-24")


def test_tie_handling_uses_ticker_as_deterministic_second_key() -> None:
    output = build_latest_ranking_output(
        normalized_score_frame(),
        adoption_synthesis_table(),
        as_of_date="2026-04-24",
    )

    tied = output.loc[output["final_composite_score"].eq(1.0)]
    assert tied["ticker"].tolist() == ["005930", "051910"]
    assert tied["rank"].tolist() == [2, 3]


def test_forbidden_columns_are_rejected_or_absent() -> None:
    frame = normalized_score_frame()
    frame["future_return"] = 0.1

    with pytest.raises(ValueError, match="forbidden|valuation/fundamental"):
        build_latest_ranking_output(frame, adoption_synthesis_table())

    output = build_latest_ranking_output(normalized_score_frame(), adoption_synthesis_table())
    forbidden = {
        "future_return",
        "forward_return",
        "expected_return",
        "valuation_score",
        "fundamental_score",
        "target_price",
    }
    assert forbidden.isdisjoint(output.columns)


def test_output_supports_dataframe_roundtrip_without_generated_cache_dependency() -> None:
    output = build_latest_ranking_output(normalized_score_frame(), adoption_synthesis_table())
    roundtrip = pd.DataFrame(output.to_dict(orient="records"))

    pd.testing.assert_frame_equal(output, roundtrip, check_dtype=False)
