from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.selection.adoption_synthesis import (  # noqa: E402
    AdoptionState,
    build_adoption_synthesis_table,
    reject_step14_forbidden_columns,
    validate_step14_adoption_language,
    validate_step14_adoption_table,
)
from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY  # noqa: E402


def review_row(
    score_name: str,
    *,
    role: str = "candidate_signal",
    eligibility: str = "eligible",
    branch: str = "technical",
    review_status: str = "adopt_candidate",
    coverage_status: str = "ok",
    redundancy_status: str = "ok",
    manual_review_required: bool = False,
) -> dict[str, object]:
    spec = _spec(score_name)
    return {
        "score_name": score_name,
        "family": spec.family,
        "branch": branch if branch != "technical" else spec.branch,
        "role": role if role != "candidate_signal" else spec.role.value,
        "eligibility": eligibility if eligibility != "eligible" else spec.eligibility.value,
        "normalized_score_column": spec.normalized_column,
        "score_input_column": spec.raw_column,
        "coverage_status": coverage_status,
        "redundancy_status": redundancy_status,
        "complexity_status": "simple",
        "regime_fit_status": "broad",
        "review_status": review_status,
        "review_reason": "Step 13 technical review row.",
        "evidence_sources": "step13_review_table",
        "manual_review_required": manual_review_required,
    }


def _spec(score_name: str):
    return next(spec for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY if spec.score_name == score_name)


def synthesize_one(row: dict[str, object]) -> pd.Series:
    table = build_adoption_synthesis_table(pd.DataFrame([row]))
    return table.iloc[0]


def test_adopt_candidate_with_clean_technical_row_can_become_core_adopted() -> None:
    result = synthesize_one(review_row("short_term_overreaction"))

    assert result["adoption_state"] == AdoptionState.CORE_ADOPTED.value
    assert not bool(result["manual_review_required"])
    assert "acceptable coverage" in result["adoption_reason"]


def test_diagnostic_role_cannot_become_core_adopted() -> None:
    result = synthesize_one(
        review_row(
            "realized_vol_percentile",
            branch="diagnostic",
            role="diagnostic_context",
            eligibility="diagnostic_only",
        )
    )

    assert result["adoption_state"] == AdoptionState.DIAGNOSTIC_ONLY.value


@pytest.mark.parametrize(
    ("review_status", "expected_state"),
    (
        ("blocked_by_data", AdoptionState.BLOCKED_BY_DATA.value),
        ("reject_candidate", AdoptionState.REJECTED.value),
        ("research_only", AdoptionState.RESEARCH_ONLY.value),
        ("needs_manual_review", AdoptionState.NEEDS_MANUAL_REVIEW.value),
    ),
)
def test_explicit_step13_review_statuses_are_preserved_conservatively(
    review_status: str,
    expected_state: str,
) -> None:
    result = synthesize_one(
        review_row(
            "short_term_overreaction",
            review_status=review_status,
            manual_review_required=review_status == "needs_manual_review",
        )
    )

    assert result["adoption_state"] == expected_state


@pytest.mark.parametrize(
    ("review_status", "expected_state"),
    (
        ("reject_candidate", AdoptionState.REJECTED.value),
        ("research_only", AdoptionState.RESEARCH_ONLY.value),
        ("diagnostic_only", AdoptionState.DIAGNOSTIC_ONLY.value),
    ),
)
def test_explicit_step13_terminal_statuses_keep_state_even_with_manual_flag(
    review_status: str,
    expected_state: str,
) -> None:
    result = synthesize_one(
        review_row(
            "short_term_overreaction",
            review_status=review_status,
            manual_review_required=True,
        )
    )

    assert result["adoption_state"] == expected_state
    assert bool(result["manual_review_required"])


def test_conditional_setup_and_confirmation_roles_do_not_become_core_adopted() -> None:
    rows = [
        review_row(
            "bollinger_width_squeeze",
            role="setup_context",
            eligibility="conditional",
            review_status="conditional_candidate",
        ),
        review_row(
            "cmf_confirmation",
            role="confirmation",
            eligibility="conditional",
            review_status="adopt_candidate",
        ),
    ]

    table = build_adoption_synthesis_table(pd.DataFrame(rows))

    assert table["adoption_state"].tolist() == [
        AdoptionState.REGIME_ONLY.value,
        AdoptionState.CONDITIONAL_ADOPTED.value,
    ]
    assert AdoptionState.CORE_ADOPTED.value not in set(table["adoption_state"])


@pytest.mark.parametrize("redundancy_status", ("severe_redundancy", "block_candidate"))
def test_severe_redundancy_or_block_candidate_does_not_auto_promote(
    redundancy_status: str,
) -> None:
    result = synthesize_one(
        review_row(
            "short_term_overreaction",
            review_status="adopt_candidate",
            redundancy_status=redundancy_status,
        )
    )

    assert result["adoption_state"] != AdoptionState.CORE_ADOPTED.value
    assert result["adoption_state"] == AdoptionState.CONDITIONAL_ADOPTED.value
    assert bool(result["manual_review_required"])


@pytest.mark.parametrize("coverage_status", ("insufficient_input", "insufficient_data"))
def test_insufficient_coverage_blocks_automatic_adoption(coverage_status: str) -> None:
    result = synthesize_one(
        review_row(
            "short_term_overreaction",
            review_status="adopt_candidate",
            coverage_status=coverage_status,
        )
    )

    assert result["adoption_state"] == AdoptionState.BLOCKED_BY_DATA.value


def test_manual_review_flag_prevents_core_adoption() -> None:
    result = synthesize_one(
        review_row(
            "short_term_overreaction",
            review_status="adopt_candidate",
            manual_review_required=True,
        )
    )

    assert result["adoption_state"] == AdoptionState.NEEDS_MANUAL_REVIEW.value


def test_forbidden_columns_are_rejected() -> None:
    frame = pd.DataFrame([review_row("short_term_overreaction")])

    for column in (
        "rank",
        "score_rank",
        "technical_composite_score",
        "final_composite_score",
        "backtest_return",
        "valuation_score",
        "target_price",
        "expected_return",
        "position_size",
        "alpha",
        "buy_signal",
        "cheap",
        "adoption_decision",
        "final_adoption_status",
        "final_adoption_decision",
        "family_weighted_composite",
    ):
        bad = frame.copy()
        bad[column] = 1
        with pytest.raises(ValueError, match="forbidden Step 14 output columns"):
            build_adoption_synthesis_table(bad)

    output = build_adoption_synthesis_table(frame)
    output["rank"] = 1
    with pytest.raises(ValueError, match="forbidden Step 14 output columns"):
        reject_step14_forbidden_columns(output)


def test_contract_valid_minimal_adoption_table_does_not_require_optional_traceability() -> None:
    table = build_adoption_synthesis_table(pd.DataFrame([review_row("short_term_overreaction")]))
    minimal_table = table.drop(
        columns=[
            "normalized_score_column",
            "score_input_column",
            "coverage_status",
            "redundancy_status",
            "complexity_status",
            "regime_fit_status",
            "downstream_usage_note",
        ]
    )

    validate_step14_adoption_table(minimal_table)


def test_forbidden_language_is_rejected_in_text_fields() -> None:
    row = review_row("short_term_overreaction")
    row["evidence_sources"] = "This mentions cheap support."

    with pytest.raises(ValueError, match="forbidden Step 14 language"):
        build_adoption_synthesis_table(pd.DataFrame([row]))

    with pytest.raises(ValueError, match="forbidden Step 14 language"):
        validate_step14_adoption_language(
            "technical adoption synthesis material only\nThis mentions alpha.",
        )


def test_output_preserves_input_order_without_ranking_sort() -> None:
    rows = [
        review_row("donchian_breakout_distance"),
        review_row("short_term_overreaction"),
        review_row("efficiency_ratio_trend"),
    ]

    table = build_adoption_synthesis_table(pd.DataFrame(rows))

    assert table["score_name"].tolist() == [
        "donchian_breakout_distance",
        "short_term_overreaction",
        "efficiency_ratio_trend",
    ]
