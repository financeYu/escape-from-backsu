"""Contract-facing adapter for Step 12 score redundancy diagnostics."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd

from .diagnostic_contracts import (
    STEP12_PAIR_DIAGNOSTIC_COLUMNS,
    Step12DiagnosticStatus,
    assert_no_forbidden_diagnostic_output_columns,
    threshold_flag_for_status,
    validate_step12_coverage_summary,
    validate_step12_pair_diagnostics,
)
from .score_redundancy_config import (
    ScoreRedundancyConfig,
    ScoreRedundancyConfigError,
    load_score_redundancy_config,
)
from .score_redundancy_coverage import (
    _build_coverage_summary,
    _config_missing_coverage_summary,
)
from .score_redundancy_engine import (
    PAIR_DATE_COLUMNS,
    _config_missing_summary,
    calculate_score_pair_correlations,
    summarize_score_redundancy,
)
from .score_redundancy_inputs import (
    RedundancyScoreInput,
    _resolve_score_inputs,
    prepare_redundancy_input_frame,
)


def build_score_redundancy_diagnostics(
    frame: pd.DataFrame,
    *,
    score_inputs: Sequence[RedundancyScoreInput] | None = None,
    score_columns: Sequence[str] | None = None,
    config: ScoreRedundancyConfig | None = None,
    thresholds_config_path: str | Path = "Quant_mvp/config/thresholds.toml",
    as_of_date: str | pd.Timestamp | None = None,
) -> dict[str, pd.DataFrame]:
    """Build Step 12 engine and contract-facing diagnostic tables."""

    active_inputs = _resolve_score_inputs(score_inputs, score_columns)
    prepared = prepare_redundancy_input_frame(
        frame,
        score_inputs=active_inputs,
        as_of_date=as_of_date,
    )
    try:
        active_config = config or load_score_redundancy_config(
            thresholds_config_path=thresholds_config_path
        )
    except ScoreRedundancyConfigError as exc:
        pair_summary = _config_missing_summary(active_inputs, str(exc))
        pair_diagnostics = _pair_summary_to_contract(
            pair_summary=pair_summary,
            pair_date_diagnostics=pd.DataFrame(columns=PAIR_DATE_COLUMNS),
            score_inputs=active_inputs,
        )
        return {
            "pair_summary": pair_summary,
            "pair_date_diagnostics": pd.DataFrame(columns=PAIR_DATE_COLUMNS),
            "pair_diagnostics": pair_diagnostics,
            "coverage_summary": _config_missing_coverage_summary(active_inputs, str(exc)),
        }

    pair_date = calculate_score_pair_correlations(
        prepared,
        score_inputs=active_inputs,
        config=active_config,
    )
    pair_summary = summarize_score_redundancy(
        prepared,
        score_inputs=active_inputs,
        config=active_config,
    )
    pair_diagnostics = _pair_summary_to_contract(
        pair_summary=pair_summary,
        pair_date_diagnostics=pair_date,
        score_inputs=active_inputs,
    )
    coverage_summary = _build_coverage_summary(
        prepared,
        score_inputs=active_inputs,
        config=active_config,
    )
    validate_step12_pair_diagnostics(pair_diagnostics)
    validate_step12_coverage_summary(coverage_summary)
    return {
        "pair_summary": pair_summary,
        "pair_date_diagnostics": pair_date,
        "pair_diagnostics": pair_diagnostics,
        "coverage_summary": coverage_summary,
    }


def _pair_summary_to_contract(
    *,
    pair_summary: pd.DataFrame,
    pair_date_diagnostics: pd.DataFrame,
    score_inputs: Sequence[RedundancyScoreInput],
) -> pd.DataFrame:
    lookup = {score_input.score_name: score_input for score_input in score_inputs}
    rows: list[dict[str, object]] = []
    for _, summary in pair_summary.iterrows():
        left_name = str(summary["score_a"])
        right_name = str(summary["score_b"])
        pair_dates = _pair_date_rows(pair_date_diagnostics, left_name, right_name)
        status = str(summary["redundancy_status"])
        contract_spearman = _contract_spearman_value(summary, pair_dates)
        rows.append(
            {
                "diagnostic_name": "score_pair_correlation",
                "score_left": left_name,
                "score_right": right_name,
                "normalization_scope": _pair_normalization_scope(
                    lookup.get(left_name),
                    lookup.get(right_name),
                ),
                "start_date": _date_bound(pair_dates, "min"),
                "end_date": _date_bound(pair_dates, "max"),
                "observation_count": _pair_observation_count(pair_dates),
                "cross_section_count": int(summary["dates_evaluated"]),
                "spearman_correlation": contract_spearman,
                "abs_spearman_correlation": _absolute_or_na(contract_spearman),
                "threshold_flag": threshold_flag_for_status(status),
                "diagnostic_status": status,
                "insufficient_data_reason": _insufficient_reason(status, summary),
                "score_left_family": _score_family(lookup.get(left_name)),
                "score_right_family": _score_family(lookup.get(right_name)),
                "score_left_role": _score_role(lookup.get(left_name)),
                "score_right_role": _score_role(lookup.get(right_name)),
                "implementation_deviation_id": "",
                "notes": "diagnostic_only_review_material",
            }
        )
    output = pd.DataFrame(rows, columns=STEP12_PAIR_DIAGNOSTIC_COLUMNS)
    assert_no_forbidden_diagnostic_output_columns(output)
    return output


def _pair_date_rows(
    pair_date_diagnostics: pd.DataFrame,
    left_name: str,
    right_name: str,
) -> pd.DataFrame:
    if pair_date_diagnostics.empty:
        return pair_date_diagnostics
    return pair_date_diagnostics[
        pair_date_diagnostics["score_a"].eq(left_name)
        & pair_date_diagnostics["score_b"].eq(right_name)
    ]


def _contract_spearman_value(summary: pd.Series, pair_dates: pd.DataFrame) -> object:
    """Return the signed Spearman value whose absolute value drives the contract row."""

    if pair_dates.empty or "spearman" not in pair_dates:
        return summary["median_spearman"]
    ok_spearman = pd.to_numeric(
        pair_dates.loc[pair_dates["diagnostic_status"].eq("ok"), "spearman"],
        errors="coerce",
    ).dropna()
    if ok_spearman.empty:
        return summary["median_spearman"]
    max_abs_index = ok_spearman.abs().idxmax()
    return float(ok_spearman.loc[max_abs_index])


def _absolute_or_na(value: object) -> object:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return pd.NA
    if not np.isfinite(numeric):
        return pd.NA
    return abs(numeric)


def _date_bound(pair_dates: pd.DataFrame, method: str) -> object:
    if pair_dates.empty or "date" not in pair_dates:
        return ""
    dates = pd.to_datetime(pair_dates["date"], errors="coerce").dropna()
    if dates.empty:
        return ""
    return dates.min() if method == "min" else dates.max()


def _pair_observation_count(pair_dates: pd.DataFrame) -> int:
    if pair_dates.empty or "pair_observations" not in pair_dates:
        return 0
    observations = pd.to_numeric(pair_dates["pair_observations"], errors="coerce")
    return int(observations.dropna().sum())


def _pair_normalization_scope(
    left: RedundancyScoreInput | None,
    right: RedundancyScoreInput | None,
) -> str:
    scopes = {
        score_input.normalization_scope
        for score_input in (left, right)
        if score_input is not None and score_input.normalization_scope != "unknown"
    }
    if len(scopes) == 1:
        return next(iter(scopes))
    if len(scopes) > 1:
        return "mixed"
    return "unknown"


def _score_family(score_input: RedundancyScoreInput | None) -> str:
    return score_input.score_family if score_input is not None else "unknown"


def _score_role(score_input: RedundancyScoreInput | None) -> str:
    return score_input.score_role if score_input is not None else "unknown"


def _insufficient_reason(status: str, summary: pd.Series) -> str:
    if status in {
        Step12DiagnosticStatus.OK.value,
        Step12DiagnosticStatus.WARN.value,
        Step12DiagnosticStatus.BLOCK_CANDIDATE.value,
        Step12DiagnosticStatus.SEVERE_REDUNDANCY.value,
    }:
        return ""
    return str(summary["redundancy_reason"])


__all__ = ("build_score_redundancy_diagnostics",)
