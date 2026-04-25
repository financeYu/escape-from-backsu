from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.diagnostics.diagnostic_contracts import (  # noqa: E402
    STEP12_REVIEW_MATERIAL_NOTICE,
    Step12ThresholdPolicy,
)
from src.diagnostics.diagnostic_reports import (  # noqa: E402
    REPORT_FORBIDDEN_LANGUAGE,
    validate_step12_report_language,
    write_step12_markdown_report,
)


def policy() -> Step12ThresholdPolicy:
    return Step12ThresholdPolicy(
        spearman_warn=0.8,
        spearman_block=0.9,
        min_cross_section_count=20,
        min_non_nan_observations=60,
    )


def workspace_output_path(name: str) -> Path:
    output_dir = PROJECT_ROOT / "tests" / "_tmp" / "step12_report_guardrails"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / name
    if path.exists():
        path.unlink()
    return path


def pair_diagnostics_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "diagnostic_name": "score_pair_correlation",
                "score_left": "short_term_overreaction",
                "score_right": "atr_adjusted_oversold_distance",
                "normalization_scope": "cross_sectional",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "observation_count": 120,
                "cross_section_count": 24,
                "spearman_correlation": 0.83,
                "abs_spearman_correlation": 0.83,
                "threshold_flag": "spearman_warn",
                "diagnostic_status": "warn",
                "insufficient_data_reason": "",
                "score_left_family": "mean_reversion",
                "score_right_family": "mean_reversion",
                "score_left_role": "candidate_signal",
                "score_right_role": "candidate_signal",
                "implementation_deviation_id": "",
                "notes": "diagnostic_only_review_material",
            }
        ]
    )


def coverage_summary_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "diagnostic_name": "coverage_summary",
                "score_name": "short_term_overreaction",
                "score_family": "mean_reversion",
                "normalization_scope": "cross_sectional",
                "date": "2026-01-31",
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
        ]
    )


def test_step12_report_writer_creates_runtime_review_material_only() -> None:
    output_path = workspace_output_path("step12_report.md")

    written = write_step12_markdown_report(
        pair_diagnostics=pair_diagnostics_frame(),
        coverage_summary=coverage_summary_frame(),
        threshold_policy=policy(),
        output_path=output_path,
    )

    text = written.read_text(encoding="utf-8")
    assert STEP12_REVIEW_MATERIAL_NOTICE in text.lower()
    assert "runtime output, not source-controlled canonical state" in text
    validate_step12_report_language(text)
    lowered = text.lower()
    assert not [term for term in REPORT_FORBIDDEN_LANGUAGE if term in lowered]
    output_path.unlink(missing_ok=True)


def test_report_language_guardrail_blocks_forbidden_review_framing() -> None:
    for term in (
        "alpha",
        "signal",
        "ranking",
        "backtest",
        "valuation",
        "buy",
        "sell",
        "cheap",
    ):
        text = f"{STEP12_REVIEW_MATERIAL_NOTICE}\nThis report mentions {term}."
        with pytest.raises(ValueError, match="forbidden language"):
            validate_step12_report_language(text)


def test_report_writer_rejects_forbidden_columns_before_writing() -> None:
    pair = pair_diagnostics_frame()
    pair["alpha"] = 1.0
    output_path = workspace_output_path("blocked_step12_report.md")

    with pytest.raises(ValueError, match="forbidden diagnostic output columns"):
        write_step12_markdown_report(
            pair_diagnostics=pair,
            coverage_summary=coverage_summary_frame(),
            threshold_policy=policy(),
            output_path=output_path,
        )


def test_generated_reports_are_not_written_under_source_docs() -> None:
    docs_path = PROJECT_ROOT / "tests" / "_tmp" / "step12_report_guardrails" / "docs" / "step12_report.md"

    with pytest.raises(ValueError, match="must not be written under docs"):
        write_step12_markdown_report(
            pair_diagnostics=pair_diagnostics_frame(),
            coverage_summary=coverage_summary_frame(),
            threshold_policy=policy(),
            output_path=docs_path,
        )


def test_report_language_requires_review_material_notice() -> None:
    with pytest.raises(ValueError, match=STEP12_REVIEW_MATERIAL_NOTICE):
        validate_step12_report_language("Step 12 diagnostic report")
