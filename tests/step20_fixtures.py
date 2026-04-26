from __future__ import annotations

import pandas as pd

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY, CompositeInputSpec
from src.selection.adoption_synthesis_contracts import Step14AdoptionState


DIRECT_SCORE_VALUES: dict[str, dict[str, float]] = {
    "000660": {
        "short_term_overreaction": 1.0,
        "donchian_breakout_distance": 2.0,
        "efficiency_ratio_trend": 2.0,
    },
    "005930": {
        "short_term_overreaction": 1.0,
        "donchian_breakout_distance": 1.0,
        "efficiency_ratio_trend": 1.0,
    },
    "035420": {
        "short_term_overreaction": 0.5,
        "donchian_breakout_distance": 0.5,
        "efficiency_ratio_trend": 0.5,
    },
    "051910": {
        "short_term_overreaction": 1.0,
        "donchian_breakout_distance": 1.0,
        "efficiency_ratio_trend": 1.0,
    },
}

ADOPTION_SYNTHESIS_STATES = {
    "short_term_overreaction": (
        Step14AdoptionState.CORE_ADOPTED.value,
        "adopt_candidate",
        False,
    ),
    "atr_adjusted_oversold_distance": (
        Step14AdoptionState.CONDITIONAL_ADOPTED.value,
        "conditional_candidate",
        True,
    ),
    "donchian_breakout_distance": (
        Step14AdoptionState.CORE_ADOPTED.value,
        "adopt_candidate",
        False,
    ),
    "bollinger_width_squeeze": (
        Step14AdoptionState.REGIME_ONLY.value,
        "conditional_candidate",
        False,
    ),
    "cmf_confirmation": (
        Step14AdoptionState.CONDITIONAL_ADOPTED.value,
        "conditional_candidate",
        True,
    ),
    "rsi_price_divergence": (
        Step14AdoptionState.CONDITIONAL_ADOPTED.value,
        "conditional_candidate",
        True,
    ),
    "realized_vol_percentile": (
        Step14AdoptionState.DIAGNOSTIC_ONLY.value,
        "diagnostic_only",
        False,
    ),
    "efficiency_ratio_trend": (
        Step14AdoptionState.TECHNICAL_ONLY.value,
        "adopt_candidate",
        False,
    ),
}


def normalized_score_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for date_value in ("2026-04-23", "2026-04-24"):
        for ticker in ("000660", "005930", "035420", "051910"):
            row: dict[str, object] = {
                "ticker": ticker,
                "date": date_value,
                "score_warmup_state": "ready",
                "score_coverage_status": "adequate",
                "score_data_quality_flag": "valid",
                "minimum_history_required": 60,
            }
            for index, spec in enumerate(DEFAULT_COMPOSITE_INPUT_REGISTRY, start=1):
                value = DIRECT_SCORE_VALUES[ticker].get(spec.score_name, 0.0)
                if date_value == "2026-04-23":
                    value = -10.0 + index
                row[spec.raw_column] = float(index)
                row[spec.normalized_column] = float(value)
                row[spec.status_column] = "adequate"
                row[spec.quality_flag_column] = "valid"
                row[spec.count_column] = 4
            rows.append(row)
    return pd.DataFrame(rows)


def adoption_synthesis_table() -> pd.DataFrame:
    rows = [_adoption_synthesis_row(spec) for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY]
    return pd.DataFrame(rows)


def _adoption_synthesis_row(spec: CompositeInputSpec) -> dict[str, object]:
    adoption_state, source_review_status, manual_review_required = ADOPTION_SYNTHESIS_STATES[
        spec.score_name
    ]
    return {
        "score_name": spec.score_name,
        "family": spec.family,
        "branch": spec.branch,
        "role": spec.role.value,
        "eligibility": spec.eligibility.value,
        "source_review_status": source_review_status,
        "adoption_state": adoption_state,
        "adoption_reason": "Synthetic Step 20 lineage fixture.",
        "evidence_sources": "step20_fixture",
        "limitations": "Fixture keeps review-routed rows visible.",
        "manual_review_required": manual_review_required,
        "normalized_score_column": spec.normalized_column,
        "score_input_column": spec.raw_column,
        "coverage_status": "ok",
        "redundancy_status": "ok",
        "complexity_status": "simple",
        "regime_fit_status": _fixture_regime_fit_status(spec.role.value),
        "downstream_usage_note": "Step 20 KOSPI200 technical-only fixture.",
    }


def _fixture_regime_fit_status(role: str) -> str:
    return "broad" if role == "candidate_signal" else "diagnostic_context"
