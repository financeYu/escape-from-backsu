"""Tests for the v0.2 probability final-score contract."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.scores.v0_2_final_score import (
    FINAL_COMPOSITE_SCORE_COLUMN,
    FINAL_SCORE_RANKING_ELIGIBLE_COLUMN,
    SCORE_SEMANTIC_VERSION_COLUMN,
    TECHNICAL_COMPOSITE_SCORE_COLUMN,
    V0_2_FINAL_SCORE_SEMANTIC_VERSION,
    build_v0_2_final_score_output,
    validate_v0_1_final_score_contract,
    validate_v0_2_final_score_output,
)


def _candidate_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["000001", "000002", "000003"],
            "date": pd.to_datetime(["2026-04-27"] * 3),
            "prob_up_1d_candidate": [0.8, 0.2, np.nan],
            "technical_composite_score": [11.0, 22.0, 33.0],
        }
    )


def test_v0_2_final_score_equals_calibrated_prob_up_1d_candidate() -> None:
    output = build_v0_2_final_score_output(_candidate_frame(), calibration_gate_pass=True)

    assert output[SCORE_SEMANTIC_VERSION_COLUMN].eq(V0_2_FINAL_SCORE_SEMANTIC_VERSION).all()
    assert output.loc[0, FINAL_COMPOSITE_SCORE_COLUMN] == 0.8
    assert output.loc[1, FINAL_COMPOSITE_SCORE_COLUMN] == 0.2
    validate_v0_2_final_score_output(output)


def test_v0_2_final_score_requires_calibration_pass() -> None:
    with pytest.raises(ValueError, match="calibration gate PASS"):
        build_v0_2_final_score_output(_candidate_frame(), calibration_gate_pass=False)


def test_v0_2_final_score_missing_candidate_excluded_not_filled_from_technical() -> None:
    output = build_v0_2_final_score_output(_candidate_frame(), calibration_gate_pass=True)

    assert bool(output.loc[2, FINAL_SCORE_RANKING_ELIGIBLE_COLUMN]) is False
    assert pd.isna(output.loc[2, FINAL_COMPOSITE_SCORE_COLUMN])


def test_v0_2_final_score_rejects_technical_fallback() -> None:
    output = build_v0_2_final_score_output(_candidate_frame(), calibration_gate_pass=True)
    output[TECHNICAL_COMPOSITE_SCORE_COLUMN] = _candidate_frame()[TECHNICAL_COMPOSITE_SCORE_COLUMN]
    output.loc[2, FINAL_COMPOSITE_SCORE_COLUMN] = output.loc[2, TECHNICAL_COMPOSITE_SCORE_COLUMN]

    with pytest.raises(ValueError):
        validate_v0_2_final_score_output(output)


def test_v0_1_final_score_contract_unchanged() -> None:
    v0_1 = pd.DataFrame(
        {
            TECHNICAL_COMPOSITE_SCORE_COLUMN: [1.0, 2.0, np.nan],
            FINAL_COMPOSITE_SCORE_COLUMN: [1.0, 2.0, np.nan],
        }
    )

    validate_v0_1_final_score_contract(v0_1)
