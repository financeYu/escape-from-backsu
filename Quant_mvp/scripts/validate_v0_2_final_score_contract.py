"""Validate the v0.2 final score probability contract."""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.scores.v0_2_final_score import (  # noqa: E402
    FINAL_COMPOSITE_SCORE_COLUMN,
    FINAL_SCORE_RANKING_ELIGIBLE_COLUMN,
    SCORE_SEMANTIC_VERSION_COLUMN,
    TECHNICAL_COMPOSITE_SCORE_COLUMN,
    V0_2_FINAL_SCORE_SEMANTIC_VERSION,
    build_v0_2_final_score_output,
    validate_v0_1_final_score_contract,
    validate_v0_2_final_score_output,
)


def main() -> int:
    candidate = pd.DataFrame(
        {
            "ticker": ["000001", "000002", "000003", "000004"],
            "date": pd.to_datetime(["2026-04-27"] * 4),
            "prob_up_1d_candidate": [0.72, 0.41, np.nan, np.inf],
            "prob_up_1d_candidate_status": [
                "candidate_probability",
                "candidate_probability",
                "missing_features",
                "candidate_probability",
            ],
            TECHNICAL_COMPOSITE_SCORE_COLUMN: [12.0, 88.0, 55.0, 77.0],
        }
    )
    output = build_v0_2_final_score_output(candidate, calibration_gate_pass=True)
    validate_v0_2_final_score_output(output)

    assert FINAL_COMPOSITE_SCORE_COLUMN in output.columns
    assert str(output[FINAL_COMPOSITE_SCORE_COLUMN].dtype) == "Float64"
    assert output[SCORE_SEMANTIC_VERSION_COLUMN].eq(V0_2_FINAL_SCORE_SEMANTIC_VERSION).all()
    assert output.loc[0, FINAL_COMPOSITE_SCORE_COLUMN] == candidate.loc[0, "prob_up_1d_candidate"]
    assert output.loc[1, FINAL_COMPOSITE_SCORE_COLUMN] == candidate.loc[1, "prob_up_1d_candidate"]
    assert bool(output.loc[2, FINAL_SCORE_RANKING_ELIGIBLE_COLUMN]) is False
    assert bool(output.loc[3, FINAL_SCORE_RANKING_ELIGIBLE_COLUMN]) is False
    assert pd.isna(output.loc[2, FINAL_COMPOSITE_SCORE_COLUMN])
    assert pd.isna(output.loc[3, FINAL_COMPOSITE_SCORE_COLUMN])

    try:
        build_v0_2_final_score_output(candidate, calibration_gate_pass=False)
    except ValueError as exc:
        assert "calibration gate PASS" in str(exc)
    else:
        raise AssertionError("calibration gate failure did not block final score output")

    fallback = output.copy()
    fallback[TECHNICAL_COMPOSITE_SCORE_COLUMN] = candidate[TECHNICAL_COMPOSITE_SCORE_COLUMN]
    fallback.loc[2, FINAL_COMPOSITE_SCORE_COLUMN] = fallback.loc[2, TECHNICAL_COMPOSITE_SCORE_COLUMN]
    try:
        validate_v0_2_final_score_output(fallback)
    except ValueError as exc:
        assert "technical_composite_score" in str(exc) or "rank-ineligible" in str(exc)
    else:
        raise AssertionError("technical fallback was not rejected")

    v0_1 = pd.DataFrame(
        {
            TECHNICAL_COMPOSITE_SCORE_COLUMN: [10.0, 20.0, np.nan],
            FINAL_COMPOSITE_SCORE_COLUMN: [10.0, 20.0, np.nan],
        }
    )
    validate_v0_1_final_score_contract(v0_1)

    print("PASS: v0.2 final score prob_up_1d contract is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
