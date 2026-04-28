"""v0.2 final score contract helpers.

This module connects the validated `prob_up_1d_candidate` output to the v0.2
`final_composite_score` contract only after calibration has passed. It does not
activate production ranking or report behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from pandas.api.types import is_float_dtype

from src.scores.prob_up_1d_candidate import PROBABILITY_COLUMN, PROBABILITY_STATUS_COLUMN
from src.scores.schema import IDENTITY_COLUMNS, require_columns


FINAL_COMPOSITE_SCORE_COLUMN = "final_composite_score"
TECHNICAL_COMPOSITE_SCORE_COLUMN = "technical_composite_score"
SCORE_SEMANTIC_VERSION_COLUMN = "score_semantic_version"
FINAL_SCORE_SOURCE_COLUMN = "final_score_source"
FINAL_SCORE_RANKING_ELIGIBLE_COLUMN = "final_score_ranking_eligible"
FINAL_SCORE_INVALID_REASON_COLUMN = "final_score_invalid_reason"

V0_2_FINAL_SCORE_SEMANTIC_VERSION = "v0_2_prob_up_1d"
V0_2_FINAL_SCORE_SOURCE = "prob_up_1d_candidate"


@dataclass(frozen=True)
class V02FinalScorePolicy:
    """Policy values for the v0.2 probability final-score contract."""

    semantic_version: str = V0_2_FINAL_SCORE_SEMANTIC_VERSION
    source: str = V0_2_FINAL_SCORE_SOURCE
    score_min: float = 0.0
    score_max: float = 1.0
    missing_policy: str = "exclude_from_ranking"


DEFAULT_V0_2_FINAL_SCORE_POLICY = V02FinalScorePolicy()


def build_v0_2_final_score_output(
    candidate_output: pd.DataFrame,
    *,
    calibration_gate_pass: bool,
    policy: V02FinalScorePolicy = DEFAULT_V0_2_FINAL_SCORE_POLICY,
) -> pd.DataFrame:
    """Return a v0.2 final-score contract frame from candidate probabilities.

    Missing, NaN, or infinite `prob_up_1d_candidate` values remain invalid for
    ranking eligibility and are not filled from `technical_composite_score`.
    """

    if not calibration_gate_pass:
        raise ValueError("v0.2 final_composite_score requires calibration gate PASS.")
    require_columns(
        candidate_output,
        (*IDENTITY_COLUMNS, PROBABILITY_COLUMN),
        context="v0.2 final score candidate output",
    )

    output = candidate_output.loc[:, list(IDENTITY_COLUMNS)].copy()
    candidate_values = _numeric_probability(candidate_output[PROBABILITY_COLUMN])
    valid_candidate = candidate_values.notna() & _finite_mask(candidate_values)
    in_range = candidate_values.between(policy.score_min, policy.score_max)
    eligible = valid_candidate & in_range

    final_scores = candidate_values.where(eligible)
    output[PROBABILITY_COLUMN] = candidate_values.astype("Float64")
    if PROBABILITY_STATUS_COLUMN in candidate_output.columns:
        output[PROBABILITY_STATUS_COLUMN] = candidate_output[PROBABILITY_STATUS_COLUMN].astype("string")
    output[FINAL_COMPOSITE_SCORE_COLUMN] = final_scores.astype("Float64")
    output[SCORE_SEMANTIC_VERSION_COLUMN] = policy.semantic_version
    output[FINAL_SCORE_SOURCE_COLUMN] = policy.source
    output[FINAL_SCORE_RANKING_ELIGIBLE_COLUMN] = eligible.astype("boolean")
    output[FINAL_SCORE_INVALID_REASON_COLUMN] = _invalid_reasons(candidate_values, eligible, policy)

    validate_v0_2_final_score_output(output, policy=policy)
    return output


def validate_v0_2_final_score_output(
    frame: pd.DataFrame,
    *,
    policy: V02FinalScorePolicy = DEFAULT_V0_2_FINAL_SCORE_POLICY,
) -> None:
    """Validate the v0.2 probability final-score output contract."""

    require_columns(
        frame,
        (
            *IDENTITY_COLUMNS,
            PROBABILITY_COLUMN,
            FINAL_COMPOSITE_SCORE_COLUMN,
            SCORE_SEMANTIC_VERSION_COLUMN,
            FINAL_SCORE_SOURCE_COLUMN,
            FINAL_SCORE_RANKING_ELIGIBLE_COLUMN,
        ),
        context="v0.2 final score output",
    )
    if not is_float_dtype(frame[FINAL_COMPOSITE_SCORE_COLUMN].dtype):
        raise ValueError("v0.2 final_composite_score must use a float dtype.")
    _assert_constant(frame[SCORE_SEMANTIC_VERSION_COLUMN], policy.semantic_version, SCORE_SEMANTIC_VERSION_COLUMN)
    _assert_constant(frame[FINAL_SCORE_SOURCE_COLUMN], policy.source, FINAL_SCORE_SOURCE_COLUMN)

    candidate_values = _numeric_probability(frame[PROBABILITY_COLUMN])
    final_scores = _numeric_probability(frame[FINAL_COMPOSITE_SCORE_COLUMN])
    eligible = frame[FINAL_SCORE_RANKING_ELIGIBLE_COLUMN].astype("boolean").fillna(False)
    finite_final = final_scores.notna() & _finite_mask(final_scores)
    valid_final = finite_final & final_scores.between(policy.score_min, policy.score_max)

    if (eligible & ~valid_final).any():
        raise ValueError("v0.2 rank-eligible rows must have finite final scores in [0, 1].")
    if (~eligible & final_scores.notna()).any():
        raise ValueError("v0.2 rank-ineligible rows must not display final_composite_score.")
    if (valid_final & ~np.isclose(final_scores.astype(float), candidate_values.astype(float), equal_nan=True)).any():
        raise ValueError("v0.2 final_composite_score must equal prob_up_1d_candidate.")
    if (candidate_values.isna() & eligible).any():
        raise ValueError("v0.2 missing prob_up_1d_candidate rows must be excluded from ranking eligibility.")

    if TECHNICAL_COMPOSITE_SCORE_COLUMN in frame.columns:
        candidate_missing = candidate_values.isna() | ~_finite_mask(candidate_values)
        technical_values = pd.to_numeric(frame[TECHNICAL_COMPOSITE_SCORE_COLUMN], errors="coerce")
        fallback_like = candidate_missing & final_scores.notna() & np.isclose(
            final_scores.astype(float),
            technical_values.astype(float),
            equal_nan=False,
        )
        if fallback_like.any():
            raise ValueError("v0.2 final_composite_score must not fall back to technical_composite_score.")


def validate_v0_1_final_score_contract(frame: pd.DataFrame) -> None:
    """Validate the frozen v0.1 technical-only final score contract."""

    require_columns(
        frame,
        (TECHNICAL_COMPOSITE_SCORE_COLUMN, FINAL_COMPOSITE_SCORE_COLUMN),
        context="v0.1 final score contract",
    )
    technical = pd.to_numeric(frame[TECHNICAL_COMPOSITE_SCORE_COLUMN], errors="coerce")
    final = pd.to_numeric(frame[FINAL_COMPOSITE_SCORE_COLUMN], errors="coerce")
    unequal = ~np.isclose(technical.astype(float), final.astype(float), equal_nan=True)
    if unequal.any():
        raise ValueError("v0.1 final_composite_score must equal technical_composite_score.")


def _numeric_probability(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    invalid = values.notna() & numeric.isna()
    if invalid.any():
        raise ValueError("v0.2 probability score columns must be numeric.")
    return numeric


def _finite_mask(values: pd.Series) -> pd.Series:
    finite = np.isfinite(values.to_numpy(dtype=float, na_value=np.nan))
    return pd.Series(finite, index=values.index)


def _invalid_reasons(
    candidate_values: pd.Series,
    eligible: pd.Series,
    policy: V02FinalScorePolicy,
) -> pd.Series:
    reasons = pd.Series("", index=candidate_values.index, dtype="string")
    missing = candidate_values.isna()
    non_finite = candidate_values.notna() & ~_finite_mask(candidate_values)
    out_of_range = _finite_mask(candidate_values) & ~candidate_values.between(policy.score_min, policy.score_max)
    reasons.loc[missing] = "missing_prob_up_1d_candidate"
    reasons.loc[non_finite] = "non_finite_prob_up_1d_candidate"
    reasons.loc[out_of_range] = "prob_up_1d_candidate_out_of_range"
    reasons.loc[eligible] = "eligible"
    return reasons


def _assert_constant(values: pd.Series, expected: str, column: str) -> None:
    observed = set(values.astype("string").dropna().tolist())
    if observed != {expected}:
        raise ValueError(f"v0.2 {column} must be {expected}.")


__all__ = (
    "DEFAULT_V0_2_FINAL_SCORE_POLICY",
    "FINAL_COMPOSITE_SCORE_COLUMN",
    "FINAL_SCORE_INVALID_REASON_COLUMN",
    "FINAL_SCORE_RANKING_ELIGIBLE_COLUMN",
    "FINAL_SCORE_SOURCE_COLUMN",
    "SCORE_SEMANTIC_VERSION_COLUMN",
    "TECHNICAL_COMPOSITE_SCORE_COLUMN",
    "V0_2_FINAL_SCORE_SEMANTIC_VERSION",
    "V0_2_FINAL_SCORE_SOURCE",
    "V02FinalScorePolicy",
    "build_v0_2_final_score_output",
    "validate_v0_1_final_score_contract",
    "validate_v0_2_final_score_output",
)
