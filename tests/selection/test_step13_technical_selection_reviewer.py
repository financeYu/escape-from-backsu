from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY  # noqa: E402
from src.diagnostics.diagnostic_contracts import (  # noqa: E402
    STEP12_COVERAGE_SUMMARY_COLUMNS,
    STEP12_PAIR_DIAGNOSTIC_COLUMNS,
)
from src.selection.technical_selection_reviewer import (  # noqa: E402
    TechnicalReviewStatus,
    assert_no_forbidden_step13_output_columns,
    build_step13_review_bundle,
    build_technical_selection_review,
    validate_step13_review_table,
)


def coverage_summary_frame(status_overrides: dict[str, str] | None = None) -> pd.DataFrame:
    overrides = status_overrides or {}
    rows = []
    for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY:
        status = overrides.get(spec.score_name, "ok")
        rows.append(
            {
                "diagnostic_name": "coverage_summary",
                "score_name": spec.score_name,
                "score_family": spec.family,
                "normalization_scope": spec.normalization_scope.value,
                "date": "",
                "ticker_count": 200,
                "observation_count": 200,
                "non_nan_observation_count": 180 if status == "ok" else 12,
                "coverage_ratio": 0.90 if status == "ok" else 0.06,
                "min_required_observations": 60,
                "min_cross_section_count": 20,
                "diagnostic_status": status,
                "insufficient_data_reason": "" if status == "ok" else "toy coverage gap",
                "implementation_deviation_id": "",
                "notes": "diagnostic_only_review_material",
            }
        )
    return pd.DataFrame(rows, columns=STEP12_COVERAGE_SUMMARY_COLUMNS)


def pair_diagnostics_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=STEP12_PAIR_DIAGNOSTIC_COLUMNS)


def pair_row(
    left: str,
    right: str,
    *,
    status: str = "ok",
    abs_spearman: object = 0.25,
    threshold_flag: str = "none",
) -> dict[str, object]:
    left_spec = _spec(left)
    right_spec = _spec(right)
    return {
        "diagnostic_name": "score_pair_correlation",
        "score_left": left,
        "score_right": right,
        "normalization_scope": "cross_sectional",
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
        "observation_count": 120,
        "cross_section_count": 24,
        "spearman_correlation": abs_spearman,
        "abs_spearman_correlation": abs_spearman,
        "threshold_flag": threshold_flag,
        "diagnostic_status": status,
        "insufficient_data_reason": "" if status in {"ok", "warn", "block_candidate"} else "toy issue",
        "score_left_family": left_spec.family,
        "score_right_family": right_spec.family,
        "score_left_role": left_spec.role.value,
        "score_right_role": right_spec.role.value,
        "implementation_deviation_id": "",
        "notes": "diagnostic_only_review_material",
    }


def _spec(score_name: str):
    return next(spec for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY if spec.score_name == score_name)


def row_for(review: pd.DataFrame, score_name: str) -> pd.Series:
    return review.loc[review["score_name"].eq(score_name)].iloc[0]


def test_eligible_good_coverage_low_redundancy_becomes_adopt_candidate() -> None:
    review = build_technical_selection_review(
        pair_diagnostics=pair_diagnostics_frame(
            [
                pair_row(
                    "short_term_overreaction",
                    "donchian_breakout_distance",
                    status="ok",
                    abs_spearman=0.22,
                )
            ]
        ),
        coverage_summary=coverage_summary_frame(),
    )

    target = row_for(review, "short_term_overreaction")
    assert target["review_status"] == TechnicalReviewStatus.ADOPT_CANDIDATE.value
    assert not bool(target["manual_review_required"])


def test_diagnostic_context_remains_diagnostic_only() -> None:
    review = build_technical_selection_review(
        pair_diagnostics=pair_diagnostics_frame(
            [
                pair_row(
                    "realized_vol_percentile",
                    "bollinger_width_squeeze",
                    status="ok",
                    abs_spearman=0.31,
                )
            ]
        ),
        coverage_summary=coverage_summary_frame(),
    )

    target = row_for(review, "realized_vol_percentile")
    assert target["review_status"] == TechnicalReviewStatus.DIAGNOSTIC_ONLY.value
    assert target["role"] == "diagnostic_context"


def test_insufficient_coverage_is_not_interpreted_optimistically() -> None:
    review = build_technical_selection_review(
        pair_diagnostics=pair_diagnostics_frame(
            [
                pair_row(
                    "donchian_breakout_distance",
                    "efficiency_ratio_trend",
                    status="ok",
                    abs_spearman=0.19,
                )
            ]
        ),
        coverage_summary=coverage_summary_frame(
            {"donchian_breakout_distance": "insufficient_data"}
        ),
    )

    target = row_for(review, "donchian_breakout_distance")
    assert target["review_status"] in {
        TechnicalReviewStatus.BLOCKED_BY_DATA.value,
        TechnicalReviewStatus.NEEDS_MANUAL_REVIEW.value,
    }
    assert bool(target["manual_review_required"])


def test_severe_redundancy_blocks_unconditional_adopt_candidate() -> None:
    review = build_technical_selection_review(
        pair_diagnostics=pair_diagnostics_frame(
            [
                pair_row(
                    "short_term_overreaction",
                    "atr_adjusted_oversold_distance",
                    status="block_candidate",
                    abs_spearman=0.94,
                    threshold_flag="spearman_block",
                )
            ]
        ),
        coverage_summary=coverage_summary_frame(),
    )

    target = row_for(review, "short_term_overreaction")
    assert target["review_status"] != TechnicalReviewStatus.ADOPT_CANDIDATE.value
    assert target["redundancy_status"] == "severe_redundancy"
    assert target["strongest_redundant_peer"] == "atr_adjusted_oversold_distance"


def test_confirmation_and_setup_context_do_not_unconditionally_adopt() -> None:
    review = build_technical_selection_review(
        pair_diagnostics=pair_diagnostics_frame(
            [
                pair_row("cmf_confirmation", "donchian_breakout_distance"),
                pair_row("bollinger_width_squeeze", "realized_vol_percentile"),
            ]
        ),
        coverage_summary=coverage_summary_frame(),
    )

    assert row_for(review, "cmf_confirmation")["review_status"] == (
        TechnicalReviewStatus.CONDITIONAL_CANDIDATE.value
    )
    assert row_for(review, "bollinger_width_squeeze")["review_status"] == (
        TechnicalReviewStatus.CONDITIONAL_CANDIDATE.value
    )


def test_step13_review_table_blocks_forbidden_output_columns() -> None:
    review = build_technical_selection_review(
        pair_diagnostics=pair_diagnostics_frame(
            [pair_row("short_term_overreaction", "donchian_breakout_distance")]
        ),
        coverage_summary=coverage_summary_frame(),
    )
    validate_step13_review_table(review)

    for column in (
        "rank",
        "score_rank",
        "technical_composite_score",
        "target_price",
        "expected_return",
        "position_size",
        "adoption_status",
        "recommendation",
        "alpha",
        "cheap",
        "valuation_score",
    ):
        bad = review.copy()
        bad[column] = 1
        with pytest.raises(ValueError, match="forbidden Step 13 output columns"):
            assert_no_forbidden_step13_output_columns(bad)


def test_step13_bundle_contains_review_and_count_tables() -> None:
    bundle = build_step13_review_bundle(
        pair_diagnostics=pair_diagnostics_frame(
            [pair_row("short_term_overreaction", "donchian_breakout_distance")]
        ),
        coverage_summary=coverage_summary_frame(),
    )

    assert set(bundle) == {
        "review_table",
        "status_counts",
        "coverage_counts",
        "redundancy_counts",
    }
    validate_step13_review_table(bundle["review_table"])
