from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY  # noqa: E402
from src.scanner.latest_ranking import build_latest_ranking_output  # noqa: E402
from src.selection.adoption_synthesis_contracts import Step14AdoptionState  # noqa: E402
from src.validation.step15_latest_ranking_guardrails import (  # noqa: E402
    validate_step15_latest_ranking_output,
)
from src.validation.step18_valuation_fundamental_guardrails import (  # noqa: E402
    assert_step18_no_production_leakage,
    validate_step18_candidate_records,
)


def normalized_score_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    values = {
        "005930": {
            "short_term_overreaction": 3.0,
            "donchian_breakout_distance": 0.0,
            "efficiency_ratio_trend": 1.0,
        },
        "000660": {
            "short_term_overreaction": 1.0,
            "donchian_breakout_distance": 2.0,
            "efficiency_ratio_trend": 1.0,
        },
    }
    for ticker in ("005930", "000660"):
        row: dict[str, object] = {
            "ticker": ticker,
            "date": "2026-04-01",
            "score_warmup_state": "ready",
            "score_coverage_status": "adequate",
            "score_data_quality_flag": "valid",
            "minimum_history_required": 60,
        }
        for index, spec in enumerate(DEFAULT_COMPOSITE_INPUT_REGISTRY, start=1):
            row[spec.raw_column] = float(index)
            row[spec.normalized_column] = float(values[ticker].get(spec.score_name, 0.0))
            row[spec.status_column] = "adequate"
            row[spec.quality_flag_column] = "valid"
            row[spec.count_column] = 2
        rows.append(row)
    return pd.DataFrame(rows)


def adoption_synthesis_table() -> pd.DataFrame:
    direct = {
        "short_term_overreaction",
        "donchian_breakout_distance",
        "efficiency_ratio_trend",
    }
    rows: list[dict[str, object]] = []
    for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY:
        is_direct = spec.score_name in direct
        rows.append(
            {
                "score_name": spec.score_name,
                "family": spec.family,
                "branch": spec.branch,
                "role": spec.role.value,
                "eligibility": spec.eligibility.value,
                "source_review_status": "adopt_candidate" if is_direct else "diagnostic_only",
                "adoption_state": (
                    Step14AdoptionState.CORE_ADOPTED.value
                    if is_direct
                    else Step14AdoptionState.DIAGNOSTIC_ONLY.value
                ),
                "adoption_reason": "Synthetic Step 18 boundary fixture.",
                "evidence_sources": "synthetic_fixture",
                "limitations": "Candidate-only valuation sidecar is excluded.",
                "manual_review_required": False,
                "normalized_score_column": spec.normalized_column,
                "score_input_column": spec.raw_column,
                "coverage_status": "ok",
                "redundancy_status": "ok",
                "complexity_status": "simple",
                "regime_fit_status": "broad",
                "downstream_usage_note": "Technical-only Step 15 ranking input.",
            }
        )
    return pd.DataFrame(rows)


def candidate_sidecar() -> list[dict[str, object]]:
    return [
        {
            "ticker": "005930",
            "company_name": "Samsung Electronics",
            "metric": "per",
            "value": 12.5,
            "metric_unit": "ratio",
            "metric_category": "valuation",
            "period": "2025Q4",
            "report_date": "2026-03-15",
            "filing_date": "2026-03-20",
            "availability_date": "2026-03-31",
            "source_report_id": "SYN-2025Q4-005930",
            "source_vendor": "synthetic",
            "collected_at": "2026-04-01",
            "source": "synthetic_fixture",
            "quality_flags": ("synthetic", "candidate_only"),
        }
    ]


def test_candidate_sidecar_does_not_change_current_ranking_output() -> None:
    baseline = build_latest_ranking_output(normalized_score_frame(), adoption_synthesis_table())

    validate_step18_candidate_records(candidate_sidecar(), evaluation_date="2026-04-01")
    repeated = build_latest_ranking_output(normalized_score_frame(), adoption_synthesis_table())

    pd.testing.assert_frame_equal(baseline, repeated)
    assert baseline["technical_composite_score"].tolist() == repeated["technical_composite_score"].tolist()
    assert baseline["final_composite_score"].tolist() == repeated["final_composite_score"].tolist()


def test_valuation_fixture_columns_are_rejected_if_added_to_ranking_inputs() -> None:
    frame = normalized_score_frame()
    frame["per"] = [12.5, 8.1]

    with pytest.raises(ValueError, match="forbidden|valuation/fundamental"):
        build_latest_ranking_output(frame, adoption_synthesis_table())


def test_candidate_columns_are_rejected_if_appended_to_production_ranking_output() -> None:
    output = build_latest_ranking_output(normalized_score_frame(), adoption_synthesis_table())
    contaminated = output.copy()
    contaminated["roe"] = [9.5, 7.0]

    with pytest.raises(ValueError, match="forbidden Step 15 columns"):
        validate_step15_latest_ranking_output(contaminated)
    with pytest.raises(ValueError, match="candidate-only valuation/fundamental columns"):
        assert_step18_no_production_leakage(contaminated)
