from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY  # noqa: E402
from src.selection.adoption_synthesis_contracts import (  # noqa: E402
    ALLOWED_STEP14_ADOPTION_STATES,
    STEP14_ADOPTION_SYNTHESIS_COLUMNS,
    STEP14_FORBIDDEN_REPORT_LANGUAGE,
    STEP14_REQUIRED_ADOPTION_SYNTHESIS_COLUMNS,
    Step14AdoptionSynthesisRow,
    assert_no_forbidden_adoption_columns,
    validate_adoption_report_text,
    validate_adoption_state,
    validate_adoption_synthesis_columns,
    validate_adoption_synthesis_table,
)


def adoption_table(
    *,
    adoption_state: str = "core_adopted",
    source_review_status: str = "adopt_candidate",
    manual_review_required: bool = False,
) -> pd.DataFrame:
    spec = DEFAULT_COMPOSITE_INPUT_REGISTRY[0]
    return pd.DataFrame(
        [
            {
                "score_name": spec.score_name,
                "family": spec.family,
                "branch": spec.branch,
                "role": spec.role.value,
                "eligibility": spec.eligibility.value,
                "source_review_status": source_review_status,
                "adoption_state": adoption_state,
                "adoption_reason": "Conservative Step 14 synthesis from Step 13 review material.",
                "evidence_sources": "Step 13 review table; Step 11 metadata.",
                "limitations": "Bounded to score-level synthesis material.",
                "manual_review_required": manual_review_required,
                "normalized_score_column": spec.normalized_column,
                "score_input_column": spec.raw_column,
                "coverage_status": "ok",
                "redundancy_status": "ok",
                "complexity_status": "simple",
                "regime_fit_status": "broad",
                "downstream_usage_note": "Step 15 may consume this only after its own contract.",
            }
        ],
        columns=STEP14_ADOPTION_SYNTHESIS_COLUMNS,
    )


def test_allowed_adoption_states_pass() -> None:
    for state in sorted(ALLOWED_STEP14_ADOPTION_STATES):
        assert validate_adoption_state(state) == state


def test_unknown_adoption_state_fails() -> None:
    with pytest.raises(ValueError, match="unsupported adoption_state"):
        validate_adoption_state("approved")

    frame = adoption_table(adoption_state="approved")
    with pytest.raises(ValueError, match="unsupported adoption_state"):
        validate_adoption_synthesis_table(frame)


@pytest.mark.parametrize(
    "column",
    (
        "rank",
        "ranking",
        "latest_rank",
        "technical_composite_score",
        "final_composite_score",
        "forward_return",
        "future_return",
        "backtest_return",
        "alpha",
        "signal",
        "buy",
        "sell",
        "valuation_score",
        "undervalued",
        "cheap",
        "bargain",
        "target_price",
        "expected_return",
        "position_size",
        "PER",
        "PBR",
        "ROE",
    ),
)
def test_forbidden_output_columns_fail(column: str) -> None:
    frame = adoption_table()
    frame[column] = 1

    with pytest.raises(ValueError, match="forbidden Step 14 adoption columns"):
        validate_adoption_synthesis_table(frame)

    with pytest.raises(ValueError, match="forbidden Step 14 adoption columns"):
        assert_no_forbidden_adoption_columns(["score_name", column])


@pytest.mark.parametrize(
    "phrase",
    tuple(sorted(STEP14_FORBIDDEN_REPORT_LANGUAGE)),
)
def test_forbidden_report_language_fails(phrase: str) -> None:
    with pytest.raises(ValueError, match="forbidden Step 14 adoption language"):
        validate_adoption_report_text(f"This report says {phrase}.")


def test_required_schema_fields_exist() -> None:
    dataclass_fields = set(Step14AdoptionSynthesisRow.__dataclass_fields__)

    for column in STEP14_REQUIRED_ADOPTION_SYNTHESIS_COLUMNS:
        assert column in STEP14_ADOPTION_SYNTHESIS_COLUMNS
        assert column in dataclass_fields

    validate_adoption_synthesis_columns(STEP14_ADOPTION_SYNTHESIS_COLUMNS)
    validate_adoption_synthesis_table(adoption_table())


def test_required_schema_fields_must_not_be_empty() -> None:
    frame = adoption_table()
    frame.loc[0, "adoption_reason"] = ""

    with pytest.raises(ValueError, match="adoption_reason must be non-empty"):
        validate_adoption_synthesis_table(frame)


def test_step14_contract_does_not_allow_ranking_composite_backtest_or_valuation_columns() -> None:
    blocked_columns = [
        "score_rank",
        "latest_ranking_snapshot",
        "technical_composite_score",
        "family_weighted_score",
        "backtest_return_20d",
        "future_return_5d",
        "target_price_krw",
        "position_size_pct",
        "valuation_status",
        "financial_metric",
    ]

    for column in blocked_columns:
        frame = adoption_table()
        frame[column] = "blocked"
        with pytest.raises(ValueError, match="forbidden Step 14 adoption columns"):
            validate_adoption_synthesis_table(frame)


def test_needs_manual_review_is_allowed_as_adoption_synthesis_state() -> None:
    frame = adoption_table(
        adoption_state="needs_manual_review",
        source_review_status="needs_manual_review",
        manual_review_required=True,
    )

    validate_adoption_synthesis_table(frame)


def test_review_status_and_adoption_state_remain_separate() -> None:
    frame = adoption_table()
    frame["review_status"] = "adopt_candidate"

    with pytest.raises(ValueError, match="forbidden Step 14 adoption columns"):
        validate_adoption_synthesis_table(frame)

    final_state_as_source = adoption_table(source_review_status="core_adopted")
    with pytest.raises(ValueError, match="unsupported source_review_status"):
        validate_adoption_synthesis_table(final_state_as_source)
