from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.diagnostics.diagnostic_contracts import (  # noqa: E402
    STEP12_COVERAGE_SUMMARY_COLUMNS,
    STEP12_PAIR_DIAGNOSTIC_COLUMNS,
)
from src.selection.technical_selection_reports import (  # noqa: E402
    STEP13_REPORT_FORBIDDEN_LANGUAGE,
    validate_step13_report_language,
    write_step13_review_report,
)
from src.selection.technical_selection_reviewer import (  # noqa: E402
    STEP13_REVIEW_MATERIAL_NOTICE,
    build_technical_selection_review,
)


def coverage_summary_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "diagnostic_name": "coverage_summary",
                "score_name": "short_term_overreaction",
                "score_family": "mean_reversion",
                "normalization_scope": "cross_sectional",
                "date": "",
                "ticker_count": 200,
                "observation_count": 200,
                "non_nan_observation_count": 180,
                "coverage_ratio": 0.90,
                "min_required_observations": 60,
                "min_cross_section_count": 20,
                "diagnostic_status": "ok",
                "insufficient_data_reason": "",
                "implementation_deviation_id": "",
                "notes": "diagnostic_only_review_material",
            }
        ],
        columns=STEP12_COVERAGE_SUMMARY_COLUMNS,
    )


def pair_diagnostics_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "diagnostic_name": "score_pair_correlation",
                "score_left": "short_term_overreaction",
                "score_right": "donchian_breakout_distance",
                "normalization_scope": "cross_sectional",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "observation_count": 120,
                "cross_section_count": 24,
                "spearman_correlation": 0.22,
                "abs_spearman_correlation": 0.22,
                "threshold_flag": "none",
                "diagnostic_status": "ok",
                "insufficient_data_reason": "",
                "score_left_family": "mean_reversion",
                "score_right_family": "trend_breakout",
                "score_left_role": "candidate_signal",
                "score_right_role": "candidate_signal",
                "implementation_deviation_id": "",
                "notes": "diagnostic_only_review_material",
            }
        ],
        columns=STEP12_PAIR_DIAGNOSTIC_COLUMNS,
    )


def report_output_path(name: str) -> Path:
    path = PROJECT_ROOT / "reports" / "selection" / name
    path.unlink(missing_ok=True)
    return path


def test_generated_report_includes_required_notice() -> None:
    review = build_technical_selection_review(
        pair_diagnostics=pair_diagnostics_frame(),
        coverage_summary=coverage_summary_frame(),
    )
    output_path = report_output_path("test_step13_selection_report.md")

    written = write_step13_review_report(review_table=review, output_path=output_path)

    text = written.read_text(encoding="utf-8")
    assert STEP13_REVIEW_MATERIAL_NOTICE in text.lower()
    validate_step13_report_language(text)
    lowered = text.lower()
    assert not [
        term
        for term in STEP13_REPORT_FORBIDDEN_LANGUAGE
        if term in lowered and term not in {"sell"}
    ]
    written.unlink(missing_ok=True)


def test_report_language_guardrail_blocks_forbidden_terms() -> None:
    for term in (
        "rank",
        "buy",
        "sell",
        "alpha",
        "backtest",
        "cheap",
        "undervalued",
    ):
        text = f"{STEP13_REVIEW_MATERIAL_NOTICE}\nThis generated report mentions {term}."
        with pytest.raises(ValueError, match="forbidden language"):
            validate_step13_report_language(text)


def test_report_writer_rejects_docs_output_path() -> None:
    review = build_technical_selection_review(
        pair_diagnostics=pair_diagnostics_frame(),
        coverage_summary=coverage_summary_frame(),
    )

    with pytest.raises(ValueError, match="must not be written under docs"):
        write_step13_review_report(
            review_table=review,
            output_path=PROJECT_ROOT / "docs" / "step13_generated_report.md",
        )


def test_report_writer_requires_reports_selection_path() -> None:
    review = build_technical_selection_review(
        pair_diagnostics=pair_diagnostics_frame(),
        coverage_summary=coverage_summary_frame(),
    )

    with pytest.raises(ValueError, match="reports/selection"):
        write_step13_review_report(
            review_table=review,
            output_path=PROJECT_ROOT / "reports" / "diagnostics" / "step13_report.md",
        )


def test_report_writer_rejects_nested_noncanonical_reports_selection_path() -> None:
    review = build_technical_selection_review(
        pair_diagnostics=pair_diagnostics_frame(),
        coverage_summary=coverage_summary_frame(),
    )

    with pytest.raises(ValueError, match="reports/selection"):
        write_step13_review_report(
            review_table=review,
            output_path=PROJECT_ROOT / "tmp" / "reports" / "selection" / "step13_report.md",
        )
