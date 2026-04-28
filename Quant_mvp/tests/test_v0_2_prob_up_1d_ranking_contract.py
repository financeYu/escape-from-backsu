"""Tests for the v0.2 probability ranking contract."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.scanner.v0_2_probability_ranking import (
    CALIBRATION_GATE_PASS_COLUMN,
    LEAKAGE_NO_LOOKAHEAD_GATE_PASS_COLUMN,
    build_v0_2_probability_ranking,
)
from src.scores.v0_2_final_score import (
    FINAL_COMPOSITE_SCORE_COLUMN,
    FINAL_SCORE_RANKING_ELIGIBLE_COLUMN,
    SCORE_SEMANTIC_VERSION_COLUMN,
    TECHNICAL_COMPOSITE_SCORE_COLUMN,
    V0_2_FINAL_SCORE_SEMANTIC_VERSION,
    build_v0_2_final_score_output,
    validate_v0_2_final_score_output,
)


def _final_score_frame() -> pd.DataFrame:
    candidate = pd.DataFrame(
        {
            "ticker": ["000003", "000001", "000002"],
            "date": pd.to_datetime(["2026-04-27"] * 3),
            "prob_up_1d_candidate": [0.52, 0.91, 0.91],
            TECHNICAL_COMPOSITE_SCORE_COLUMN: [99.0, -10.0, 88.0],
        }
    )
    output = build_v0_2_final_score_output(candidate, calibration_gate_pass=True)
    output[CALIBRATION_GATE_PASS_COLUMN] = True
    output[LEAKAGE_NO_LOOKAHEAD_GATE_PASS_COLUMN] = True
    return output


def test_v0_2_ranking_sorts_by_final_score_desc() -> None:
    ranking = build_v0_2_probability_ranking(_final_score_frame())

    assert ranking["ticker"].tolist() == ["000001", "000002", "000003"]
    assert ranking[FINAL_COMPOSITE_SCORE_COLUMN].tolist() == [0.91, 0.91, 0.52]


def test_v0_2_ranking_requires_prob_up_1d_semantic_version() -> None:
    frame = _final_score_frame()
    frame[SCORE_SEMANTIC_VERSION_COLUMN] = "v0_1_technical"

    with pytest.raises(ValueError, match="score_semantic_version"):
        build_v0_2_probability_ranking(frame)


def test_v0_2_ranking_rejects_missing_final_score() -> None:
    frame = _final_score_frame()
    frame.loc[0, FINAL_SCORE_RANKING_ELIGIBLE_COLUMN] = True
    frame.loc[0, FINAL_COMPOSITE_SCORE_COLUMN] = np.nan

    with pytest.raises(ValueError):
        build_v0_2_probability_ranking(frame)


def test_v0_2_ranking_does_not_use_technical_fallback() -> None:
    frame = _final_score_frame()
    frame[TECHNICAL_COMPOSITE_SCORE_COLUMN] = [99.0, -10.0, 88.0]
    frame.loc[0, "prob_up_1d_candidate"] = np.nan
    frame.loc[0, FINAL_COMPOSITE_SCORE_COLUMN] = frame.loc[0, TECHNICAL_COMPOSITE_SCORE_COLUMN]

    with pytest.raises(ValueError):
        validate_v0_2_final_score_output(frame)


def test_v0_2_ranking_requires_calibration_pass() -> None:
    frame = _final_score_frame()
    frame[CALIBRATION_GATE_PASS_COLUMN] = False

    with pytest.raises(ValueError, match="calibration_gate_pass"):
        build_v0_2_probability_ranking(frame)


def test_v0_1_ranking_path_is_not_modified_by_v0_2_contract() -> None:
    frame = pd.DataFrame(
        {
            TECHNICAL_COMPOSITE_SCORE_COLUMN: [1.0, np.nan],
            FINAL_COMPOSITE_SCORE_COLUMN: [1.0, np.nan],
        }
    )

    assert frame[TECHNICAL_COMPOSITE_SCORE_COLUMN].equals(frame[FINAL_COMPOSITE_SCORE_COLUMN])
