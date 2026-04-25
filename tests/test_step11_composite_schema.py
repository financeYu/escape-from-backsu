from __future__ import annotations

from dataclasses import replace
import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.composite.contracts import (  # noqa: E402
    DEFAULT_COMPOSITE_INPUT_REGISTRY,
    MVP_SCORE_NAMES,
    CompositeEligibility,
    CompositeInputSpec,
    CompositeRole,
)
from src.composite.schema import (  # noqa: E402
    assert_no_forbidden_step11_output_columns,
    assert_ticker_date_identity_unchanged,
    candidate_signal_specs,
    validate_composite_input_registry,
    validate_normalized_score_columns,
    validate_step11_config_flags,
)


def normalized_contract_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for ticker, date_value in (
        ("005930", "2026-01-01"),
        ("000660", "2026-01-01"),
        ("035420", "2026-01-01"),
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
            row[spec.raw_column] = float(index)
            row[spec.normalized_column] = float(index) / 10.0
            row[spec.status_column] = "adequate"
            row[spec.quality_flag_column] = "valid"
            row[spec.count_column] = 3
        rows.append(row)
    return pd.DataFrame(rows)


def test_default_registry_contains_only_the_eight_step9_mvp_scores() -> None:
    validate_composite_input_registry()

    assert tuple(spec.score_name for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY) == MVP_SCORE_NAMES
    assert len(DEFAULT_COMPOSITE_INPUT_REGISTRY) == 8

    extra = CompositeInputSpec(
        score_name="new_unreviewed_score",
        raw_column="new_unreviewed_score_raw",
        family="novelty",
        branch="technical",
        role=CompositeRole.CANDIDATE_SIGNAL,
        eligibility=CompositeEligibility.ELIGIBLE,
    )
    with pytest.raises(ValueError, match="eight Step 9 MVP scores"):
        validate_composite_input_registry((*DEFAULT_COMPOSITE_INPUT_REGISTRY, extra))


def test_registry_matches_step11_family_role_and_eligibility_policy() -> None:
    by_name = {spec.score_name: spec for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY}

    assert by_name["short_term_overreaction"].family == "mean_reversion"
    assert by_name["short_term_overreaction"].role is CompositeRole.CANDIDATE_SIGNAL
    assert by_name["short_term_overreaction"].eligibility is CompositeEligibility.ELIGIBLE

    assert by_name["atr_adjusted_oversold_distance"].family == "mean_reversion"
    assert by_name["atr_adjusted_oversold_distance"].eligibility is CompositeEligibility.CONDITIONAL

    assert by_name["donchian_breakout_distance"].family == "trend_breakout"
    assert by_name["donchian_breakout_distance"].eligibility is CompositeEligibility.ELIGIBLE

    assert by_name["bollinger_width_squeeze"].family == "volatility_context"
    assert by_name["bollinger_width_squeeze"].role is CompositeRole.SETUP_CONTEXT
    assert by_name["bollinger_width_squeeze"].eligibility is CompositeEligibility.CONDITIONAL

    assert by_name["cmf_confirmation"].family == "volume_flow"
    assert by_name["cmf_confirmation"].role is CompositeRole.CONFIRMATION
    assert by_name["cmf_confirmation"].eligibility is CompositeEligibility.CONDITIONAL

    assert by_name["rsi_price_divergence"].family == "mean_reversion"
    assert by_name["rsi_price_divergence"].eligibility is CompositeEligibility.CONDITIONAL

    assert by_name["realized_vol_percentile"].family == "volatility_context"
    assert by_name["realized_vol_percentile"].role is CompositeRole.DIAGNOSTIC_CONTEXT
    assert by_name["realized_vol_percentile"].eligibility is CompositeEligibility.DIAGNOSTIC_ONLY

    assert by_name["efficiency_ratio_trend"].family == "trend_breakout"
    assert by_name["efficiency_ratio_trend"].eligibility is CompositeEligibility.ELIGIBLE


def test_diagnostic_and_context_only_scores_are_not_candidate_signals() -> None:
    by_name = {spec.score_name: spec for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY}

    assert by_name["realized_vol_percentile"].eligibility is CompositeEligibility.DIAGNOSTIC_ONLY
    assert by_name["bollinger_width_squeeze"].role is CompositeRole.SETUP_CONTEXT
    assert by_name["cmf_confirmation"].role is CompositeRole.CONFIRMATION
    assert {spec.score_name for spec in candidate_signal_specs()} == {
        "short_term_overreaction",
        "atr_adjusted_oversold_distance",
        "donchian_breakout_distance",
        "rsi_price_divergence",
        "efficiency_ratio_trend",
    }

    bad_registry = tuple(
        replace(spec, role=CompositeRole.CANDIDATE_SIGNAL, eligibility=CompositeEligibility.ELIGIBLE)
        if spec.score_name == "realized_vol_percentile"
        else spec
        for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY
    )
    with pytest.raises(ValueError, match="cannot be candidate_signal"):
        validate_composite_input_registry(bad_registry)

    over_open_confirmation = tuple(
        replace(spec, eligibility=CompositeEligibility.ELIGIBLE)
        if spec.score_name == "cmf_confirmation"
        else spec
        for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY
    )
    with pytest.raises(ValueError, match="family/role/eligibility policy"):
        validate_composite_input_registry(over_open_confirmation)


def test_step11_forbidden_composite_and_ranking_outputs_are_blocked() -> None:
    frame = normalized_contract_frame()
    validate_normalized_score_columns(frame)

    for column in (
        "technical_composite_score",
        "final_composite_score",
        "rank",
        "latest_rank",
        "latest_ranking",
        "buy_signal",
        "sell_signal",
        "alpha_signal",
    ):
        blocked = frame.copy()
        blocked[column] = 1.0
        with pytest.raises(ValueError, match="forbidden Step 11 output"):
            assert_no_forbidden_step11_output_columns(blocked)


def test_future_return_and_backtest_columns_are_blocked() -> None:
    frame = normalized_contract_frame()

    for column in (
        "forward_return",
        "forward_return_5d",
        "future_return",
        "future_return_20d",
        "next_period_return",
        "next_period_return_5d",
        "backtest_return",
    ):
        blocked = frame.copy()
        blocked[column] = 0.01
        with pytest.raises(ValueError, match="forbidden Step 11 output"):
            validate_normalized_score_columns(blocked)


def test_valuation_and_fundamental_columns_are_not_allowed_in_registry_or_frame() -> None:
    frame = normalized_contract_frame()
    frame["PER"] = 10.0
    with pytest.raises(ValueError, match="valuation/fundamental columns"):
        validate_normalized_score_columns(frame)

    bad_registry = (
        replace(DEFAULT_COMPOSITE_INPUT_REGISTRY[0], raw_column="per_raw"),
    ) + DEFAULT_COMPOSITE_INPUT_REGISTRY[1:]
    with pytest.raises(ValueError, match="valuation/fundamental columns"):
        validate_composite_input_registry(bad_registry)


def test_ticker_date_identity_is_required_and_preserved() -> None:
    source = normalized_contract_frame()
    candidate = source.copy()

    assert_ticker_date_identity_unchanged(source, candidate)

    changed = candidate.iloc[[1, 0, 2]].reset_index(drop=True)
    with pytest.raises(ValueError, match="identity changed"):
        assert_ticker_date_identity_unchanged(source, changed)

    duplicate = candidate.copy()
    duplicate.loc[1, "ticker"] = duplicate.loc[0, "ticker"]
    with pytest.raises(ValueError, match="duplicate ticker/date"):
        validate_normalized_score_columns(duplicate)


def test_step10_missing_warmup_and_coverage_metadata_must_be_preserved() -> None:
    frame = normalized_contract_frame()

    for column in (
        "score_warmup_state",
        "score_coverage_status",
        "score_data_quality_flag",
        "minimum_history_required",
        "short_term_overreaction_cross_sectional_status",
        "short_term_overreaction_cross_sectional_quality_flag",
        "short_term_overreaction_cross_sectional_valid_count",
    ):
        missing = frame.drop(columns=[column])
        with pytest.raises(ValueError, match="missing"):
            validate_normalized_score_columns(missing)

    empty_metadata = frame.copy()
    empty_metadata["score_warmup_state"] = pd.NA
    with pytest.raises(ValueError, match="preserve non-empty metadata"):
        validate_normalized_score_columns(empty_metadata)


def test_config_production_runtime_flags_remain_disabled() -> None:
    validate_step11_config_flags(
        quant_scores_config=PROJECT_ROOT / "Quant_mvp" / "config" / "scores.toml",
        root_scores_config=PROJECT_ROOT / "config" / "scores.toml",
    )

    bad_quant_config = {
        "registry_status": {
            "ranking_generation_enabled": False,
            "composite_scoring_enabled": True,
            "backtest_enabled": False,
            "valuation_branch_enabled": False,
        },
        "scores": [{"score_id": "short_term_overreaction", "runtime_enabled": False}],
    }
    with pytest.raises(ValueError, match="production flags"):
        validate_step11_config_flags(
            quant_scores_config=bad_quant_config,
            root_scores_config={"status": {}, "composite": {"enabled": False, "implemented": False}},
        )

    bad_runtime_config = {
        "registry_status": {
            "ranking_generation_enabled": False,
            "composite_scoring_enabled": False,
            "backtest_enabled": False,
            "valuation_branch_enabled": False,
        },
        "scores": [{"score_id": "short_term_overreaction", "runtime_enabled": True}],
    }
    with pytest.raises(ValueError, match="runtime_enabled"):
        validate_step11_config_flags(
            quant_scores_config=bad_runtime_config,
            root_scores_config={"status": {}, "composite": {"enabled": False, "implemented": False}},
        )
