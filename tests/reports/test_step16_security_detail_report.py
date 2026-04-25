from __future__ import annotations

from collections.abc import Mapping
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY  # noqa: E402
from src.reports.security_detail_report import (  # noqa: E402
    FINAL_COMPOSITE_TECHNICAL_ONLY_NOTE,
    build_security_detail_report,
    build_security_detail_report_records,
    build_security_detail_reports,
)
from src.reports.security_detail_report_contracts import (  # noqa: E402
    STEP16_SECURITY_DETAIL_REPORT_NOTICE,
    SecurityReportDisplayRole,
)
from src.selection.adoption_synthesis_contracts import Step14AdoptionState  # noqa: E402


FORBIDDEN_EXACT_TERMS = (
    "buy",
    "sell",
    "target_price",
    "expected_return",
    "forward_return",
    "future_return",
    "backtest",
    "backtest_return",
    "valuation",
    "valuation_score",
    "fundamental",
    "undervalued",
    "cheap",
    "bargain",
    "hold",
    "position_size",
    "per",
    "pbr",
    "roe",
)


def latest_ranking_frame() -> pd.DataFrame:
    direct_values = {
        "005930": {
            "short_term_overreaction": 2.0,
            "donchian_breakout_distance": 1.0,
            "efficiency_ratio_trend": 1.5,
        },
        "000660": {
            "short_term_overreaction": 1.0,
            "donchian_breakout_distance": 0.5,
            "efficiency_ratio_trend": 0.75,
        },
        "035420": {
            "short_term_overreaction": pd.NA,
            "donchian_breakout_distance": pd.NA,
            "efficiency_ratio_trend": pd.NA,
        },
    }
    rows: list[dict[str, object]] = []
    for ticker, rank, score, status, validity in (
        ("005930", 1, 1.5, "adequate", "valid"),
        ("000660", 2, 0.75, "adequate", "valid"),
        ("035420", pd.NA, pd.NA, "blocked", "blocked"),
    ):
        row: dict[str, object] = {
            "ticker": ticker,
            "date": "2026-04-24",
            "rank": rank,
            "technical_composite_score": score,
            "final_composite_score": score,
            "coverage_metric": 1.0 if status == "adequate" else 0.0,
            "data_quality_flag": "valid" if status == "adequate" else "invalid",
            "coverage_status": status,
            "ranking_validity_flag": validity,
            "valid_score_count": 3 if status == "adequate" else 0,
            "expected_score_count": 3,
            "review_routed_score_count": 5,
            "final_score_policy": "technical_only_no_valuation",
            "mean_reversion_family_score": score,
            "trend_breakout_family_score": score,
        }
        for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY:
            if spec.score_name not in direct_values[ticker]:
                continue
            row[spec.normalized_column] = direct_values[ticker][spec.score_name]
            row[spec.status_column] = "adequate" if status == "adequate" else "blocked"
            row[spec.quality_flag_column] = "valid" if status == "adequate" else "invalid"
            row[spec.count_column] = 3 if status == "adequate" else 0
        rows.append(row)
    return pd.DataFrame(rows)


def adoption_synthesis_table() -> pd.DataFrame:
    states = {
        "short_term_overreaction": (Step14AdoptionState.CORE_ADOPTED.value, False),
        "atr_adjusted_oversold_distance": (
            Step14AdoptionState.CONDITIONAL_ADOPTED.value,
            True,
        ),
        "donchian_breakout_distance": (Step14AdoptionState.CORE_ADOPTED.value, False),
        "bollinger_width_squeeze": (Step14AdoptionState.REGIME_ONLY.value, False),
        "cmf_confirmation": (Step14AdoptionState.CONDITIONAL_ADOPTED.value, True),
        "rsi_price_divergence": (Step14AdoptionState.NEEDS_MANUAL_REVIEW.value, True),
        "realized_vol_percentile": (Step14AdoptionState.DIAGNOSTIC_ONLY.value, False),
        "efficiency_ratio_trend": (Step14AdoptionState.TECHNICAL_ONLY.value, False),
    }
    rows: list[dict[str, object]] = []
    for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY:
        adoption_state, manual_review_required = states[spec.score_name]
        rows.append(
            {
                "score_name": spec.score_name,
                "family": spec.family,
                "branch": spec.branch,
                "role": spec.role.value,
                "eligibility": spec.eligibility.value,
                "source_review_status": "diagnostic_only"
                if adoption_state == Step14AdoptionState.DIAGNOSTIC_ONLY.value
                else "conditional_candidate"
                if manual_review_required
                else "adopt_candidate",
                "adoption_state": adoption_state,
                "adoption_reason": "Technical review material remains conservative.",
                "evidence_sources": "toy_step13_review_table",
                "limitations": "Context limitations remain visible.",
                "manual_review_required": manual_review_required,
                "normalized_score_column": spec.normalized_column,
                "score_input_column": spec.raw_column,
                "coverage_status": "ok",
                "redundancy_status": "ok",
                "complexity_status": "simple",
                "regime_fit_status": "broad"
                if spec.role.value == "candidate_signal"
                else "diagnostic_context",
                "downstream_usage_note": "Step 16 display context only.",
            }
        )
    return pd.DataFrame(rows)


def test_single_ticker_report_generation() -> None:
    report = build_security_detail_report(
        latest_ranking_frame(),
        "005930",
        report_date="2026-04-25",
        adoption_synthesis=adoption_synthesis_table(),
    )
    record = report.to_dict()

    assert record["ticker"] == "005930"
    assert record["snapshot_date"] == "2026-04-24"
    assert record["report_date"] == "2026-04-25"
    assert record["source_latest_ranking_date"] == "2026-04-24"
    assert record["technical_composite_score"] == pytest.approx(1.5)
    assert record["final_composite_score"] == pytest.approx(1.5)
    assert record["final_composite_score_note"] == FINAL_COMPOSITE_TECHNICAL_ONLY_NOTE
    assert record["boundary_notice"]["scope"] == STEP16_SECURITY_DETAIL_REPORT_NOTICE
    assert len(record["score_breakdown"]) == 3


def test_multiple_ticker_report_generation_preserves_requested_order() -> None:
    reports = build_security_detail_reports(
        latest_ranking_frame(),
        tickers=["000660", "005930"],
        adoption_synthesis=adoption_synthesis_table(),
    )

    assert [report.ticker for report in reports] == ["000660", "005930"]
    assert [report.readonly_rank_fields["rank"] for report in reports] == [2, 1]


def test_missing_ticker_handling() -> None:
    with pytest.raises(ValueError, match="does not contain ticker"):
        build_security_detail_report(latest_ranking_frame(), "123456")


def test_blocked_or_low_quality_input_row_explanation() -> None:
    report = build_security_detail_report(
        latest_ranking_frame(),
        "035420",
        adoption_synthesis=adoption_synthesis_table(),
    )
    record = report.to_dict()

    assert record["readonly_rank_fields"]["rank"] is None
    assert record["technical_composite_score"] is None
    assert record["final_composite_score"] is None
    assert any("coverage_status is blocked" in text for text in record["explanations"])
    assert any("ranking_validity_flag is blocked" in text for text in record["explanations"])
    assert any("Step 15 rank is unavailable" in text for text in record["explanations"])


def test_diagnostic_only_score_is_context_not_ranking_driver() -> None:
    report = build_security_detail_report(
        latest_ranking_frame(),
        "005930",
        adoption_synthesis=adoption_synthesis_table(),
    )
    contexts = {
        item.score_name: item
        for item in report.diagnostic_context
    }
    diagnostic = contexts["realized_vol_percentile"]

    assert diagnostic.context_only is True
    assert diagnostic.readonly_step15_component is False
    assert diagnostic.score_value is None
    assert diagnostic.display_role == (
        SecurityReportDisplayRole.DIAGNOSTIC_CONTEXT_NOT_RANK_DRIVER.value
    )


def test_step15_rank_is_displayed_readonly() -> None:
    report = build_security_detail_report(
        latest_ranking_frame(),
        "000660",
        adoption_synthesis=adoption_synthesis_table(),
    )

    assert report.rank_fields_are_readonly is True
    assert report.readonly_rank_fields["rank"] == 2
    assert report.readonly_rank_fields["final_score_policy"] == "technical_only_no_valuation"


def test_no_forbidden_backtest_valuation_or_trading_fields_in_output() -> None:
    record = build_security_detail_report_records(
        latest_ranking_frame(),
        "005930",
        adoption_synthesis=adoption_synthesis_table(),
    )[0]

    found = _find_forbidden_exact_terms(record)

    assert found == []


def test_forbidden_input_fields_are_rejected_before_report_generation() -> None:
    for column in (
        "buy",
        "sell",
        "target_price",
        "expected_return",
        "forward_return",
        "future_return",
        "backtest_return",
        "valuation_score",
        "PER",
        "PBR",
        "ROE",
    ):
        frame = latest_ranking_frame()
        frame[column] = 1
        with pytest.raises(ValueError, match="forbidden Step 16 report columns"):
            build_security_detail_report(
                frame,
                "005930",
                adoption_synthesis=adoption_synthesis_table(),
            )


@pytest.mark.parametrize(
    ("column", "text"),
    (
        ("limitations", "A backtest supports this report."),
        ("adoption_reason", "The valuation case is strong."),
        ("limitations", "Fundamental evidence is supportive."),
        ("adoption_reason", "This looks cheap."),
        ("limitations", "forward_return supports the view."),
    ),
)
def test_forbidden_metadata_language_is_rejected_before_report_generation(
    column: str,
    text: str,
) -> None:
    metadata = adoption_synthesis_table()
    metadata.loc[0, column] = text

    with pytest.raises(ValueError, match="forbidden Step 16 report language"):
        build_security_detail_report(
            latest_ranking_frame(),
            "005930",
            adoption_synthesis=metadata,
        )


def test_deterministic_repeated_output() -> None:
    kwargs = {
        "report_date": "2026-04-25",
        "adoption_synthesis": adoption_synthesis_table(),
    }

    first = build_security_detail_report(latest_ranking_frame(), "005930", **kwargs).to_dict()
    second = build_security_detail_report(latest_ranking_frame(), "005930", **kwargs).to_dict()

    assert first == second


def _find_forbidden_exact_terms(value: Any) -> list[str]:
    found: list[str] = []

    def walk(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                _check_text(str(key))
                walk(child)
            return
        if isinstance(item, (tuple, list)):
            for child in item:
                walk(child)
            return
        if isinstance(item, str):
            _check_text(item)

    def _check_text(text: str) -> None:
        lowered = text.lower()
        for term in FORBIDDEN_EXACT_TERMS:
            if "_" in term:
                if term in lowered:
                    found.append(term)
            elif re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", lowered):
                found.append(term)

    walk(value)
    return sorted(set(found))
