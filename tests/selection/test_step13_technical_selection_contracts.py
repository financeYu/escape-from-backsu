from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY  # noqa: E402
from src.selection.technical_selection_contracts import (  # noqa: E402
    ALLOWED_STEP13_REVIEW_STATUSES,
    STEP13_REVIEW_MATERIAL_NOTICE,
    Step13ReviewBundle,
    find_forbidden_step13_output_columns,
    reject_step13_forbidden_columns,
    validate_step13_review_bundle,
    validate_step13_review_language,
    validate_step13_review_table,
    validate_step13_status_values,
)


def review_table(review_statuses: tuple[str, ...] = ("adopt_candidate",)) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index, review_status in enumerate(review_statuses):
        spec = DEFAULT_COMPOSITE_INPUT_REGISTRY[index]
        rows.append(
            {
                "score_name": spec.score_name,
                "family": spec.family,
                "branch": spec.branch,
                "role": spec.role.value,
                "eligibility": spec.eligibility.value,
                "normalized_score_column": spec.normalized_column,
                "score_input_column": spec.raw_column,
                "coverage_status": "ok",
                "redundancy_status": "ok",
                "complexity_status": "simple",
                "regime_fit_status": "broad",
                "review_status": review_status,
                "review_reason": "Step 13 technical review recommendation from Step 9-12 material.",
                "evidence_sources": "Step 9 raw score; Step 10 normalized score; Step 11 metadata; Step 12 diagnostics.",
                "manual_review_required": review_status == "needs_manual_review",
            }
        )
    return pd.DataFrame(rows)


def full_review_table() -> pd.DataFrame:
    statuses = (
        "adopt_candidate",
        "conditional_candidate",
        "research_only",
        "diagnostic_only",
        "reject_candidate",
        "blocked_by_data",
        "needs_manual_review",
        "conditional_candidate",
    )
    return review_table(statuses)


def test_allowed_review_status_values_pass_without_final_adoption_state() -> None:
    frame = review_table(tuple(sorted(ALLOWED_STEP13_REVIEW_STATUSES)))

    validate_step13_status_values(frame)
    validate_step13_review_table(frame)


def test_invalid_review_status_and_step14_final_state_fail() -> None:
    frame = review_table(("adopt",))
    with pytest.raises(ValueError, match="unsupported review_status"):
        validate_step13_status_values(frame)

    final_state = review_table(("core_adopted",))
    with pytest.raises(ValueError, match="unsupported review_status"):
        validate_step13_review_table(final_state)


def test_required_column_missing_fails() -> None:
    frame = review_table().drop(columns=["review_reason"])

    with pytest.raises(ValueError, match="missing required columns"):
        validate_step13_review_table(frame)


@pytest.mark.parametrize(
    "column",
    (
        "technical_composite_score",
        "final_composite_score",
        "rank",
        "latest_rank",
        "forward_return",
        "future_return",
        "backtest_return",
        "valuation_score",
        "target_price",
        "expected_return",
        "position_size",
        "recommendation",
    ),
)
def test_forbidden_columns_are_rejected(column: str) -> None:
    frame = review_table()
    frame[column] = 1.0

    with pytest.raises(ValueError, match="forbidden Step 13 output columns"):
        validate_step13_review_table(frame)


def test_guardrail_blocks_ranking_or_final_adoption_shaped_output() -> None:
    assert find_forbidden_step13_output_columns(
        [
            "score_name",
            "review_status",
            "score_rank",
            "adoption_status",
            "final_adoption_decision",
        ]
    ) == ["adoption_status", "final_adoption_decision", "score_rank"]

    frame = review_table()
    frame["adoption_status"] = "core_adopted"
    with pytest.raises(ValueError, match="forbidden Step 13 output columns"):
        reject_step13_forbidden_columns(frame)


def test_review_table_requires_normalized_or_input_column() -> None:
    frame = review_table()
    frame["normalized_score_column"] = ""
    frame["score_input_column"] = ""

    with pytest.raises(ValueError, match="normalized_score_column or score_input_column"):
        validate_step13_review_table(frame)

    raw_as_normalized = review_table()
    raw_as_normalized["normalized_score_column"] = "short_term_overreaction_raw"
    with pytest.raises(ValueError, match="must not point to raw score"):
        validate_step13_review_table(raw_as_normalized)


def test_step13_review_language_guardrail_blocks_alpha_trading_and_valuation_language() -> None:
    allowed = (
        f"{STEP13_REVIEW_MATERIAL_NOTICE}\n"
        "This generated note is a conservative technical review recommendation."
    )
    validate_step13_review_language(allowed)

    for term in ("alpha", "signal", "ranking", "backtest", "valuation", "cheap", "buy"):
        blocked = f"{STEP13_REVIEW_MATERIAL_NOTICE}\nThis generated note mentions {term}."
        with pytest.raises(ValueError, match="forbidden Step 13 language"):
            validate_step13_review_language(blocked)

    table = review_table()
    table.loc[0, "review_reason"] = "This looks like alpha evidence."
    with pytest.raises(ValueError, match="forbidden Step 13 language"):
        validate_step13_review_table(table)


def test_review_bundle_requires_all_eight_scores_and_screens_source_tables() -> None:
    validate_step13_review_bundle(
        Step13ReviewBundle(review_table=full_review_table()),
        require_all_scores=True,
    )

    partial = Step13ReviewBundle(review_table=review_table())
    with pytest.raises(ValueError, match="all eight Step 9 MVP scores"):
        validate_step13_review_bundle(partial)

    source_with_future_return = pd.DataFrame({"score_name": ["x"], "forward_return": [0.01]})
    with pytest.raises(ValueError, match="forbidden Step 13 output columns"):
        validate_step13_review_bundle(
            {
                "review_table": full_review_table(),
                "step12_source": source_with_future_return,
            }
        )
