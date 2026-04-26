"""Coverage summary helpers for Step 12 score redundancy diagnostics."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from .diagnostic_contracts import (
    STEP12_COVERAGE_SUMMARY_COLUMNS,
    Step12DiagnosticStatus,
    assert_no_forbidden_diagnostic_output_columns,
    validate_step12_coverage_summary,
)
from .score_redundancy_config import ScoreRedundancyConfig
from .score_redundancy_inputs import (
    RedundancyScoreInput,
    _finite_mask,
    _numeric_score_values,
    prepare_redundancy_input_frame,
)


def _build_coverage_summary(
    frame: pd.DataFrame,
    *,
    score_inputs: Sequence[RedundancyScoreInput],
    config: ScoreRedundancyConfig,
    as_of_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    prepared = prepare_redundancy_input_frame(
        frame,
        score_inputs=score_inputs,
        as_of_date=as_of_date,
    )
    rows: list[dict[str, object]] = []
    ticker_count = int(prepared["ticker"].nunique())
    observation_count = int(len(prepared))
    for score_input in score_inputs:
        if score_input.normalized_column not in prepared.columns:
            rows.append(
                _coverage_row(
                    score_input,
                    ticker_count=ticker_count,
                    observation_count=observation_count,
                    non_nan_observation_count=0,
                    coverage_ratio=0.0,
                    config=config,
                    status=Step12DiagnosticStatus.INSUFFICIENT_INPUT.value,
                    reason="upstream_missing_normalized_score_column:"
                    + score_input.normalized_column,
                )
            )
            continue
        values = _numeric_score_values(prepared, score_input)
        non_nan_observation_count = int(_finite_mask(values).sum())
        coverage_ratio = (
            non_nan_observation_count / observation_count if observation_count else 0.0
        )
        same_date_usable_cross_sections = _same_date_usable_cross_section_count(
            prepared,
            score_input,
            config,
        )
        status, reason = _coverage_status_and_reason(
            non_nan_observation_count,
            same_date_usable_cross_sections,
            config,
        )
        rows.append(
            _coverage_row(
                score_input,
                ticker_count=ticker_count,
                observation_count=observation_count,
                non_nan_observation_count=non_nan_observation_count,
                coverage_ratio=coverage_ratio,
                config=config,
                status=status,
                reason=reason,
                same_date_usable_cross_sections=same_date_usable_cross_sections,
            )
        )
    output = pd.DataFrame(rows, columns=STEP12_COVERAGE_SUMMARY_COLUMNS)
    assert_no_forbidden_diagnostic_output_columns(output)
    return output


def _config_missing_coverage_summary(
    score_inputs: Sequence[RedundancyScoreInput], reason: str
) -> pd.DataFrame:
    rows = [
        {
            "diagnostic_name": "coverage_summary",
            "score_name": score_input.score_name,
            "score_family": score_input.score_family,
            "normalization_scope": score_input.normalization_scope,
            "date": "",
            "ticker_count": 0,
            "observation_count": 0,
            "non_nan_observation_count": 0,
            "coverage_ratio": 0.0,
            "min_required_observations": 0,
            "min_cross_section_count": 0,
            "diagnostic_status": Step12DiagnosticStatus.CONFIG_MISSING.value,
            "insufficient_data_reason": reason,
            "implementation_deviation_id": "",
            "notes": "diagnostic_only_review_material",
        }
        for score_input in score_inputs
    ]
    output = pd.DataFrame(rows, columns=STEP12_COVERAGE_SUMMARY_COLUMNS)
    validate_step12_coverage_summary(output)
    return output


def _coverage_row(
    score_input: RedundancyScoreInput,
    *,
    ticker_count: int,
    observation_count: int,
    non_nan_observation_count: int,
    coverage_ratio: float,
    config: ScoreRedundancyConfig,
    status: str,
    reason: str,
    same_date_usable_cross_sections: int = 0,
) -> dict[str, object]:
    return {
        "diagnostic_name": "coverage_summary",
        "score_name": score_input.score_name,
        "score_family": score_input.score_family,
        "normalization_scope": score_input.normalization_scope,
        "date": "",
        "ticker_count": ticker_count,
        "observation_count": observation_count,
        "non_nan_observation_count": non_nan_observation_count,
        "coverage_ratio": coverage_ratio,
        "min_required_observations": config.min_non_nan_observations,
        "min_cross_section_count": config.min_cross_section_count,
        "diagnostic_status": status,
        "insufficient_data_reason": reason,
        "implementation_deviation_id": "",
        "notes": (
            "diagnostic_only_review_material;"
            f"same_date_usable_cross_sections={same_date_usable_cross_sections}"
        ),
    }


def _same_date_usable_cross_section_count(
    prepared: pd.DataFrame,
    score_input: RedundancyScoreInput,
    config: ScoreRedundancyConfig,
) -> int:
    values = _numeric_score_values(prepared, score_input)
    finite = _finite_mask(values)
    finite_by_date = finite.groupby(prepared["date"]).sum()
    return int(finite_by_date.ge(config.min_cross_section_count).sum())


def _coverage_status_and_reason(
    non_nan_observation_count: int,
    same_date_usable_cross_sections: int,
    config: ScoreRedundancyConfig,
) -> tuple[str, str]:
    reasons: list[str] = []
    if non_nan_observation_count < config.min_non_nan_observations:
        reasons.append("non_nan_observation_count_below_min_required_observations")
    if same_date_usable_cross_sections < 1:
        reasons.append("no_same_date_cross_section_met_min_cross_section_count")
    if reasons:
        return Step12DiagnosticStatus.INSUFFICIENT_DATA.value, ";".join(reasons)
    return Step12DiagnosticStatus.OK.value, ""
