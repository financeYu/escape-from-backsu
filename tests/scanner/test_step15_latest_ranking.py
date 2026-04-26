from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY  # noqa: E402
from src.scanner.latest_ranking import (  # noqa: E402
    Step15CoverageStatus,
    Step15ValidityFlag,
    build_latest_ranking_output,
    validate_step15_latest_ranking_output,
)
from src.selection.adoption_synthesis_contracts import Step14AdoptionState  # noqa: E402
from src.validation.step15_latest_ranking_guardrails import (  # noqa: E402
    validate_step15_latest_ranking_output as validate_step15_guardrail_output,
)


def normalized_score_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    latest_values = {
        "005930": {
            "short_term_overreaction": 3.0,
            "donchian_breakout_distance": 0.0,
            "efficiency_ratio_trend": 1.0,
            "atr_adjusted_oversold_distance": 999.0,
        },
        "000660": {
            "short_term_overreaction": 1.0,
            "donchian_breakout_distance": 2.0,
            "efficiency_ratio_trend": 1.0,
            "atr_adjusted_oversold_distance": 999.0,
        },
        "035420": {
            "short_term_overreaction": 1.0,
            "donchian_breakout_distance": 1.0,
            "efficiency_ratio_trend": 1.0,
            "atr_adjusted_oversold_distance": 999.0,
        },
    }
    for ticker, date_value in (
        ("005930", "2026-01-02"),
        ("000660", "2026-01-02"),
        ("035420", "2026-01-02"),
        ("005930", "2026-01-03"),
        ("000660", "2026-01-03"),
        ("035420", "2026-01-03"),
    ):
        row: dict[str, object] = {
            "ticker": ticker,
            "date": date_value,
            "score_warmup_state": "ready",
            "score_coverage_status": "adequate",
            "score_data_quality_flag": "valid",
            "minimum_history_required": 60,
        }
        for index, spec in enumerate(DEFAULT_COMPOSITE_INPUT_REGISTRY, start=1):
            score_value = latest_values.get(ticker, {}).get(spec.score_name, 0.0)
            if date_value == "2026-01-02":
                score_value = -100.0 + index
            row[spec.raw_column] = float(index)
            row[spec.normalized_column] = float(score_value)
            row[spec.status_column] = "adequate"
            row[spec.quality_flag_column] = "valid"
            row[spec.count_column] = 3
        rows.append(row)
    return pd.DataFrame(rows)


def adoption_synthesis_table() -> pd.DataFrame:
    states = {
        "short_term_overreaction": (
            Step14AdoptionState.CORE_ADOPTED.value,
            "adopt_candidate",
            False,
        ),
        "atr_adjusted_oversold_distance": (
            Step14AdoptionState.CONDITIONAL_ADOPTED.value,
            "conditional_candidate",
            True,
        ),
        "donchian_breakout_distance": (
            Step14AdoptionState.CORE_ADOPTED.value,
            "adopt_candidate",
            False,
        ),
        "bollinger_width_squeeze": (
            Step14AdoptionState.REGIME_ONLY.value,
            "conditional_candidate",
            False,
        ),
        "cmf_confirmation": (
            Step14AdoptionState.CONDITIONAL_ADOPTED.value,
            "adopt_candidate",
            True,
        ),
        "rsi_price_divergence": (
            Step14AdoptionState.CONDITIONAL_ADOPTED.value,
            "conditional_candidate",
            True,
        ),
        "realized_vol_percentile": (
            Step14AdoptionState.DIAGNOSTIC_ONLY.value,
            "diagnostic_only",
            False,
        ),
        "efficiency_ratio_trend": (
            Step14AdoptionState.CORE_ADOPTED.value,
            "adopt_candidate",
            False,
        ),
    }
    rows: list[dict[str, object]] = []
    for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY:
        adoption_state, source_review_status, manual_review_required = states[spec.score_name]
        rows.append(
            {
                "score_name": spec.score_name,
                "family": spec.family,
                "branch": spec.branch,
                "role": spec.role.value,
                "eligibility": spec.eligibility.value,
                "source_review_status": source_review_status,
                "adoption_state": adoption_state,
                "adoption_reason": "Technical review material is conservatively synthesized.",
                "evidence_sources": "step13_review_table",
                "limitations": "Review constraints remain visible.",
                "manual_review_required": manual_review_required,
                "normalized_score_column": spec.normalized_column,
                "score_input_column": spec.raw_column,
                "coverage_status": "ok",
                "redundancy_status": "ok",
                "complexity_status": "simple",
                "regime_fit_status": "broad",
                "downstream_usage_note": "Step 15 contract required before use.",
            }
        )
    return pd.DataFrame(rows)


def test_latest_ranking_uses_latest_date_and_direct_adopted_scores_only() -> None:
    output = build_latest_ranking_output(
        normalized_score_frame(),
        adoption_synthesis_table(),
    )

    assert output["ticker"].tolist() == ["005930", "000660", "035420"]
    assert output["rank"].tolist() == [1, 2, 3]
    assert output["date"].tolist() == ["2026-01-03", "2026-01-03", "2026-01-03"]
    assert output.columns[:7].tolist() == [
        "ticker",
        "date",
        "rank",
        "technical_composite_score",
        "final_composite_score",
        "coverage_metric",
        "data_quality_flag",
    ]
    assert "atr_adjusted_oversold_distance_cross_sectional_robust_z" not in output.columns
    assert output.loc[0, "mean_reversion_family_score"] == pytest.approx(3.0)
    assert output.loc[0, "trend_breakout_family_score"] == pytest.approx(0.5)
    assert output.loc[0, "technical_composite_score"] == pytest.approx(1.75)
    assert output.loc[0, "final_composite_score"] == pytest.approx(1.75)
    assert output["coverage_status"].tolist() == [Step15CoverageStatus.ADEQUATE.value] * 3
    assert output["ranking_validity_flag"].tolist() == [Step15ValidityFlag.VALID.value] * 3
    assert output["warmup_status"].tolist() == ["ready", "ready", "ready"]
    assert output["neutral_shrinkage_count"].tolist() == [0, 0, 0]
    assert output["review_routed_score_count"].tolist() == [5, 5, 5]
    assert output["technical_only_notice"].str.contains("kospi200_technical_only").all()


def test_as_of_date_and_top_n_are_explicit_and_deterministic() -> None:
    output = build_latest_ranking_output(
        normalized_score_frame(),
        adoption_synthesis_table(),
        as_of_date="2026-01-03",
        top_n=2,
    )

    assert output["ticker"].tolist() == ["005930", "000660"]
    assert output["rank"].tolist() == [1, 2]

    with pytest.raises(ValueError, match="as_of_date is not present"):
        build_latest_ranking_output(
            normalized_score_frame(),
            adoption_synthesis_table(),
            as_of_date="2026-01-04",
        )


def test_invalid_score_status_is_routed_to_partial_coverage_not_silent_acceptance() -> None:
    frame = normalized_score_frame()
    mask = (frame["ticker"] == "000660") & (frame["date"] == "2026-01-03")
    frame.loc[mask, "efficiency_ratio_trend_cross_sectional_status"] = "insufficient_cross_section"

    output = build_latest_ranking_output(frame, adoption_synthesis_table())
    row = output.loc[output["ticker"] == "000660"].iloc[0]

    assert row["valid_score_count"] == 2
    assert row["expected_score_count"] == 3
    assert row["coverage_status"] == Step15CoverageStatus.PARTIAL.value
    assert row["ranking_validity_flag"] == Step15ValidityFlag.PARTIAL.value
    assert row["coverage_metric"] == pytest.approx(2 / 3)
    assert row["neutral_shrinkage_count"] == 1
    assert row["trend_breakout_family_score"] == pytest.approx(1.0)


def test_no_direct_adopted_technical_score_blocks_ranking() -> None:
    adoption = adoption_synthesis_table()
    direct_names = {
        "short_term_overreaction",
        "donchian_breakout_distance",
        "efficiency_ratio_trend",
    }
    mask = adoption["score_name"].isin(direct_names)
    adoption.loc[mask, "adoption_state"] = Step14AdoptionState.CONDITIONAL_ADOPTED.value
    adoption.loc[mask, "manual_review_required"] = True

    with pytest.raises(ValueError, match="at least one direct technical adoption"):
        build_latest_ranking_output(normalized_score_frame(), adoption)


def test_forbidden_future_return_trading_and_valuation_columns_are_rejected() -> None:
    for column in ("future_return_5d", "buy_signal", "PER", "valuation_score"):
        frame = normalized_score_frame()
        frame[column] = 1.0
        with pytest.raises(ValueError, match="forbidden|valuation/fundamental"):
            build_latest_ranking_output(frame, adoption_synthesis_table())


def test_output_validator_rejects_non_step15_boundary_columns() -> None:
    output = build_latest_ranking_output(normalized_score_frame(), adoption_synthesis_table())
    bad = output.copy()
    bad["target_price"] = 100000

    with pytest.raises(ValueError, match="forbidden Step 15 columns"):
        validate_step15_latest_ranking_output(bad)


def test_latest_ranking_output_satisfies_step15_guardrail_validator() -> None:
    output = build_latest_ranking_output(normalized_score_frame(), adoption_synthesis_table())

    validate_step15_guardrail_output(output, as_of_date="2026-01-03")


def test_future_dates_and_unsafe_tickers_are_rejected() -> None:
    future = normalized_score_frame()
    future.loc[future["date"] == "2026-01-03", "date"] = "2026-01-04"
    with pytest.raises(ValueError, match="future dates"):
        build_latest_ranking_output(
            future,
            adoption_synthesis_table(),
            max_allowed_date="2026-01-03",
        )

    unsafe_ticker = normalized_score_frame()
    unsafe_ticker.loc[unsafe_ticker["ticker"] == "005930", "ticker"] = "5930"
    with pytest.raises(ValueError, match="six-digit string"):
        build_latest_ranking_output(unsafe_ticker, adoption_synthesis_table())
