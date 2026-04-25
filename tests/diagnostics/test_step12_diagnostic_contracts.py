from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.diagnostics.diagnostic_contracts import (  # noqa: E402
    FORBIDDEN_DIAGNOSTIC_OUTPUT_COLUMNS,
    STEP12_COVERAGE_SUMMARY_COLUMNS,
    STEP12_DEVIATION_LOG_COLUMNS,
    STEP12_PAIR_DIAGNOSTIC_COLUMNS,
    Step12DiagnosticStatus,
    Step12ThresholdPolicy,
    assert_no_forbidden_diagnostic_output_columns,
    classify_spearman_diagnostic_status,
    load_step12_threshold_policy,
    threshold_flag_for_status,
    validate_step12_coverage_summary,
    validate_step12_deviation_log,
    validate_step12_diagnostics_bundle,
    validate_step12_pair_diagnostics,
)


def pair_diagnostics_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "diagnostic_name": "score_pair_correlation",
                "score_left": "short_term_overreaction",
                "score_right": "atr_adjusted_oversold_distance",
                "normalization_scope": "cross_sectional",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "observation_count": 120,
                "cross_section_count": 24,
                "spearman_correlation": 0.83,
                "abs_spearman_correlation": 0.83,
                "threshold_flag": "spearman_warn",
                "diagnostic_status": "warn",
                "insufficient_data_reason": "",
                "score_left_family": "mean_reversion",
                "score_right_family": "mean_reversion",
                "score_left_role": "candidate_signal",
                "score_right_role": "candidate_signal",
                "implementation_deviation_id": "",
                "notes": "diagnostic_only_review_material",
            },
            {
                "diagnostic_name": "score_pair_correlation",
                "score_left": "donchian_breakout_distance",
                "score_right": "efficiency_ratio_trend",
                "normalization_scope": "cross_sectional",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "observation_count": 12,
                "cross_section_count": 8,
                "spearman_correlation": pd.NA,
                "abs_spearman_correlation": pd.NA,
                "threshold_flag": "insufficient_data",
                "diagnostic_status": "insufficient_data",
                "insufficient_data_reason": "below configured minimums",
                "score_left_family": "trend_breakout",
                "score_right_family": "trend_breakout",
                "score_left_role": "candidate_signal",
                "score_right_role": "candidate_signal",
                "implementation_deviation_id": "",
                "notes": "diagnostic_only_review_material",
            },
        ],
        columns=STEP12_PAIR_DIAGNOSTIC_COLUMNS,
    )


def coverage_summary_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "diagnostic_name": "coverage_summary",
                "score_name": "short_term_overreaction",
                "score_family": "mean_reversion",
                "normalization_scope": "cross_sectional",
                "date": "2026-01-31",
                "ticker_count": 200,
                "observation_count": 200,
                "non_nan_observation_count": 180,
                "coverage_ratio": 0.90,
                "min_required_observations": 60,
                "min_cross_section_count": 20,
                "diagnostic_status": "ok",
                "insufficient_data_reason": "",
                "implementation_deviation_id": "",
                "notes": "diagnostic_only_review_material",
            }
        ],
        columns=STEP12_COVERAGE_SUMMARY_COLUMNS,
    )


def deviation_log_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "deviation_id": "STEP12-DEV-001",
                "step": "Step 12",
                "affected_field": "threshold",
                "expected_behavior": "load required threshold from config",
                "actual_behavior": "config key was missing and output was blocked",
                "reason": "missing required key",
                "risk": "review material incomplete until config is fixed",
                "review_required": True,
                "created_at_utc": "2026-04-25T00:00:00Z",
            }
        ],
        columns=STEP12_DEVIATION_LOG_COLUMNS,
    )


def test_step12_pair_coverage_and_deviation_contracts_validate() -> None:
    pair = pair_diagnostics_frame()
    coverage = coverage_summary_frame()
    deviation = deviation_log_frame()

    validate_step12_pair_diagnostics(pair)
    validate_step12_coverage_summary(coverage)
    validate_step12_deviation_log(deviation)
    validate_step12_diagnostics_bundle(
        pair_diagnostics=pair,
        coverage_summary=coverage,
        deviation_log=deviation,
    )


def test_forbidden_output_columns_are_detected_independently_of_engine() -> None:
    for column in FORBIDDEN_DIAGNOSTIC_OUTPUT_COLUMNS:
        frame = pd.DataFrame({"diagnostic_name": ["x"], column: [1]})
        with pytest.raises(ValueError, match="forbidden diagnostic output columns"):
            assert_no_forbidden_diagnostic_output_columns(frame)

    for column in ("score_rank", "redundancy_signal", "future_return_20d", "backtest_metric"):
        frame = pd.DataFrame({"diagnostic_name": ["x"], column: [1]})
        with pytest.raises(ValueError, match="forbidden diagnostic output columns"):
            assert_no_forbidden_diagnostic_output_columns(frame)


def test_pair_diagnostics_do_not_allow_row_identity_or_invalid_status() -> None:
    pair = pair_diagnostics_frame()
    with_identity = pair.copy()
    with_identity["ticker"] = "005930"
    with pytest.raises(ValueError, match="pair-level output"):
        validate_step12_pair_diagnostics(with_identity)

    invalid_status = pair.copy()
    invalid_status.loc[0, "diagnostic_status"] = "adopt"
    with pytest.raises(ValueError, match="unsupported diagnostic_status"):
        validate_step12_pair_diagnostics(invalid_status)


def test_threshold_policy_loads_required_config_keys_without_defaults() -> None:
    policy = load_step12_threshold_policy(PROJECT_ROOT / "Quant_mvp" / "config" / "thresholds.toml")

    assert policy == Step12ThresholdPolicy(
        spearman_warn=0.80,
        spearman_block=0.90,
        min_cross_section_count=20,
        min_non_nan_observations=60,
    )

    missing_config = {
        "redundancy": {"spearman_warn": 0.8},
        "quality": {"min_cross_section_count": 20, "min_non_nan_observations": 60},
    }
    with pytest.raises(ValueError, match="Missing required Step 12 config key"):
        load_step12_threshold_policy(missing_config)


def test_spearman_status_classification_is_threshold_only_not_decision() -> None:
    policy = Step12ThresholdPolicy(
        spearman_warn=0.8,
        spearman_block=0.9,
        min_cross_section_count=20,
        min_non_nan_observations=60,
    )

    assert (
        classify_spearman_diagnostic_status(
            0.2,
            observation_count=60,
            cross_section_count=20,
            policy=policy,
        )
        is Step12DiagnosticStatus.OK
    )
    assert (
        classify_spearman_diagnostic_status(
            -0.85,
            observation_count=60,
            cross_section_count=20,
            policy=policy,
        )
        is Step12DiagnosticStatus.WARN
    )
    block_status = classify_spearman_diagnostic_status(
        0.93,
        observation_count=60,
        cross_section_count=20,
        policy=policy,
    )
    assert block_status is Step12DiagnosticStatus.BLOCK_CANDIDATE
    assert threshold_flag_for_status(block_status) == "spearman_block"

    assert (
        classify_spearman_diagnostic_status(
            0.93,
            observation_count=59,
            cross_section_count=20,
            policy=policy,
        )
        is Step12DiagnosticStatus.INSUFFICIENT_DATA
    )
    assert (
        classify_spearman_diagnostic_status(
            pd.NA,
            observation_count=60,
            cross_section_count=20,
            policy=policy,
        )
        is Step12DiagnosticStatus.UNDEFINED_CORRELATION
    )
