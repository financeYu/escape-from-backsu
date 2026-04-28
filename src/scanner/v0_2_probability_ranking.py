"""v0.2 probability ranking contract helpers.

This module ranks only validated v0.2 `final_composite_score` probability
outputs. It does not rank `prob_up_1d_candidate` directly and does not alter
the frozen v0.1 technical ranking path.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.scores.prob_up_1d_candidate import PROBABILITY_COLUMN
from src.scores.schema import IDENTITY_COLUMNS, require_columns
from src.scores.v0_2_final_score import (
    FINAL_COMPOSITE_SCORE_COLUMN,
    FINAL_SCORE_RANKING_ELIGIBLE_COLUMN,
    FINAL_SCORE_SOURCE_COLUMN,
    SCORE_SEMANTIC_VERSION_COLUMN,
    TECHNICAL_COMPOSITE_SCORE_COLUMN,
    V0_2_FINAL_SCORE_SEMANTIC_VERSION,
    V0_2_FINAL_SCORE_SOURCE,
    validate_v0_2_final_score_output,
)


CALIBRATION_GATE_PASS_COLUMN = "calibration_gate_pass"
LEAKAGE_NO_LOOKAHEAD_GATE_PASS_COLUMN = "leakage_no_lookahead_gate_pass"
V0_2_PROBABILITY_RANK_COLUMN = "rank"
V0_2_RANKING_NOTICE = "v0.2 probability ranking for research/scanning use only"

V0_2_PROBABILITY_RANKING_COLUMNS = (
    "ticker",
    "date",
    V0_2_PROBABILITY_RANK_COLUMN,
    FINAL_COMPOSITE_SCORE_COLUMN,
    SCORE_SEMANTIC_VERSION_COLUMN,
    FINAL_SCORE_SOURCE_COLUMN,
    CALIBRATION_GATE_PASS_COLUMN,
    LEAKAGE_NO_LOOKAHEAD_GATE_PASS_COLUMN,
    FINAL_SCORE_RANKING_ELIGIBLE_COLUMN,
    "ranking_notice",
)


def build_v0_2_probability_ranking(final_score_output: pd.DataFrame) -> pd.DataFrame:
    """Build v0.2 probability ranking from final-score contract output."""

    validate_v0_2_probability_ranking_input(final_score_output)
    working = final_score_output.copy()
    eligible = working[FINAL_SCORE_RANKING_ELIGIBLE_COLUMN].astype("boolean").fillna(False)
    working = working.loc[eligible].copy()
    working = working.sort_values(
        [FINAL_COMPOSITE_SCORE_COLUMN, "ticker"],
        ascending=[False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    working[V0_2_PROBABILITY_RANK_COLUMN] = pd.Series(range(1, len(working) + 1), dtype="Int64")
    working["ranking_notice"] = V0_2_RANKING_NOTICE
    ranking = working.loc[:, list(V0_2_PROBABILITY_RANKING_COLUMNS)]
    validate_v0_2_probability_ranking_output(ranking)
    return ranking


def validate_v0_2_probability_ranking_input(frame: pd.DataFrame) -> None:
    """Validate inputs before v0.2 probability ranking."""

    require_columns(
        frame,
        (
            *IDENTITY_COLUMNS,
            FINAL_COMPOSITE_SCORE_COLUMN,
            SCORE_SEMANTIC_VERSION_COLUMN,
            FINAL_SCORE_SOURCE_COLUMN,
            FINAL_SCORE_RANKING_ELIGIBLE_COLUMN,
            CALIBRATION_GATE_PASS_COLUMN,
            LEAKAGE_NO_LOOKAHEAD_GATE_PASS_COLUMN,
        ),
        context="v0.2 probability ranking input",
    )
    validate_v0_2_final_score_output(frame)
    _assert_true_gate(frame[CALIBRATION_GATE_PASS_COLUMN], CALIBRATION_GATE_PASS_COLUMN)
    _assert_true_gate(
        frame[LEAKAGE_NO_LOOKAHEAD_GATE_PASS_COLUMN],
        LEAKAGE_NO_LOOKAHEAD_GATE_PASS_COLUMN,
    )
    if not frame[SCORE_SEMANTIC_VERSION_COLUMN].astype("string").eq(
        V0_2_FINAL_SCORE_SEMANTIC_VERSION
    ).all():
        raise ValueError("v0.2 probability ranking requires score_semantic_version v0_2_prob_up_1d.")
    if not frame[FINAL_SCORE_SOURCE_COLUMN].astype("string").eq(V0_2_FINAL_SCORE_SOURCE).all():
        raise ValueError("v0.2 probability ranking requires final_score_source prob_up_1d_candidate.")
    _assert_no_direct_candidate_ranking(frame)
    _assert_no_technical_fallback(frame)


def validate_v0_2_probability_ranking_output(frame: pd.DataFrame) -> None:
    """Validate v0.2 probability ranking output."""

    require_columns(frame, V0_2_PROBABILITY_RANKING_COLUMNS, context="v0.2 probability ranking output")
    scores = pd.to_numeric(frame[FINAL_COMPOSITE_SCORE_COLUMN], errors="coerce")
    if scores.isna().any() or (~np.isfinite(scores)).any():
        raise ValueError("v0.2 probability ranking output final scores must be finite.")
    if (~scores.between(0.0, 1.0)).any():
        raise ValueError("v0.2 probability ranking output final scores must be in [0, 1].")
    if not frame[SCORE_SEMANTIC_VERSION_COLUMN].astype("string").eq(
        V0_2_FINAL_SCORE_SEMANTIC_VERSION
    ).all():
        raise ValueError("v0.2 probability ranking output has wrong score_semantic_version.")
    if frame[V0_2_PROBABILITY_RANK_COLUMN].isna().any():
        raise ValueError("v0.2 probability ranking output cannot contain missing ranks.")
    ordered = scores.tolist()
    if ordered != sorted(ordered, reverse=True):
        raise ValueError("v0.2 probability ranking output must sort final_composite_score descending.")
    expected = list(range(1, len(frame) + 1))
    observed = [int(value) for value in frame[V0_2_PROBABILITY_RANK_COLUMN].tolist()]
    if observed != expected:
        raise ValueError("v0.2 probability ranking output ranks must be consecutive.")


def _assert_true_gate(values: pd.Series, column: str) -> None:
    normalized = values.map(lambda value: bool(value) if pd.notna(value) else False)
    if not normalized.all():
        raise ValueError(f"v0.2 probability ranking requires {column} PASS.")


def _assert_no_direct_candidate_ranking(frame: pd.DataFrame) -> None:
    if PROBABILITY_COLUMN in frame.columns and FINAL_COMPOSITE_SCORE_COLUMN not in frame.columns:
        raise ValueError("v0.2 probability ranking must not rank prob_up_1d_candidate directly.")


def _assert_no_technical_fallback(frame: pd.DataFrame) -> None:
    if TECHNICAL_COMPOSITE_SCORE_COLUMN not in frame.columns or PROBABILITY_COLUMN not in frame.columns:
        return
    candidate = pd.to_numeric(frame[PROBABILITY_COLUMN], errors="coerce")
    final = pd.to_numeric(frame[FINAL_COMPOSITE_SCORE_COLUMN], errors="coerce")
    technical = pd.to_numeric(frame[TECHNICAL_COMPOSITE_SCORE_COLUMN], errors="coerce")
    candidate_invalid = candidate.isna() | ~pd.Series(np.isfinite(candidate), index=candidate.index)
    fallback_like = candidate_invalid & final.notna() & np.isclose(
        final.astype(float),
        technical.astype(float),
        equal_nan=False,
    )
    if fallback_like.any():
        raise ValueError("v0.2 probability ranking must not use technical_composite_score fallback.")


__all__ = (
    "CALIBRATION_GATE_PASS_COLUMN",
    "LEAKAGE_NO_LOOKAHEAD_GATE_PASS_COLUMN",
    "V0_2_PROBABILITY_RANKING_COLUMNS",
    "V0_2_PROBABILITY_RANK_COLUMN",
    "V0_2_RANKING_NOTICE",
    "build_v0_2_probability_ranking",
    "validate_v0_2_probability_ranking_input",
    "validate_v0_2_probability_ranking_output",
)
