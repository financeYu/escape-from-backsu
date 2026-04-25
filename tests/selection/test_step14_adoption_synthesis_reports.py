from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.selection.adoption_synthesis import (  # noqa: E402
    STEP14_ADOPTION_MATERIAL_NOTICE,
    build_adoption_synthesis_table,
)
from src.selection.adoption_synthesis_contracts import STEP14_ADOPTION_SYNTHESIS_NOTICE  # noqa: E402
from src.selection.adoption_synthesis_reports import (  # noqa: E402
    STEP14_REPORT_BOUNDARY_NOTICE,
    render_step14_adoption_synthesis_report,
    validate_step14_report_language,
    write_step14_adoption_synthesis_report,
)
from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY  # noqa: E402


def review_row(score_name: str, *, review_status: str = "adopt_candidate") -> dict[str, object]:
    spec = _spec(score_name)
    return {
        "score_name": score_name,
        "family": spec.family,
        "branch": spec.branch,
        "role": spec.role.value,
        "eligibility": spec.eligibility.value,
        "normalized_score_column": spec.normalized_column,
        "score_input_column": spec.raw_column,
        "coverage_status": "ok",
        "redundancy_status": "ok",
        "complexity_status": "simple",
        "regime_fit_status": "broad",
        "review_status": review_status,
        "review_reason": "Step 13 technical review row.",
        "evidence_sources": "step13_review_table",
        "manual_review_required": review_status == "needs_manual_review",
    }


def _spec(score_name: str):
    return next(spec for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY if spec.score_name == score_name)


def adoption_table() -> pd.DataFrame:
    return build_adoption_synthesis_table(
        pd.DataFrame(
            [
                review_row("short_term_overreaction"),
                review_row("donchian_breakout_distance", review_status="research_only"),
            ]
        )
    )


def report_output_path(name: str) -> Path:
    path = PROJECT_ROOT / "reports" / "selection" / name
    path.unlink(missing_ok=True)
    return path


def test_rendered_report_includes_required_scope_and_boundary_notice() -> None:
    text = render_step14_adoption_synthesis_report(adoption_table())

    lowered = text.lower()
    assert STEP14_ADOPTION_MATERIAL_NOTICE in lowered
    assert STEP14_ADOPTION_SYNTHESIS_NOTICE in lowered
    assert STEP14_REPORT_BOUNDARY_NOTICE in lowered
    validate_step14_report_language(text)


def test_report_language_guardrail_accepts_canonical_contract_notice() -> None:
    text = (
        f"{STEP14_ADOPTION_SYNTHESIS_NOTICE}\n"
        f"Boundary: {STEP14_REPORT_BOUNDARY_NOTICE}.\n"
        "Rows are Step 14 synthesis material for later review."
    )

    validate_step14_report_language(text)


def test_report_does_not_use_forbidden_terms_outside_boundary_notice() -> None:
    text = render_step14_adoption_synthesis_report(adoption_table())
    screened = text.lower().replace(STEP14_REPORT_BOUNDARY_NOTICE, "")

    for term in (
        "ranking",
        "technical_composite_score",
        "final_composite_score",
        "backtest",
        "valuation",
        "cheap",
        "undervalued",
        "target_price",
        "expected_return",
        "position_size",
    ):
        assert term not in screened


def test_report_language_guardrail_blocks_forbidden_terms() -> None:
    for term in (
        "rank",
        "buy",
        "sell",
        "alpha",
        "backtest",
        "cheap",
        "undervalued",
        "value stock",
        "target price",
        "실전 매수 후보",
    ):
        text = (
            f"{STEP14_ADOPTION_MATERIAL_NOTICE}\n"
            f"Boundary: {STEP14_REPORT_BOUNDARY_NOTICE}.\n"
            f"This generated report mentions {term}."
        )
        with pytest.raises(ValueError, match="forbidden"):
            validate_step14_report_language(text)


def test_report_writer_writes_only_under_reports_selection() -> None:
    output_path = report_output_path("test_step14_adoption_synthesis.md")

    written = write_step14_adoption_synthesis_report(
        adoption_table=adoption_table(),
        output_path=output_path,
    )

    assert written == output_path
    text = written.read_text(encoding="utf-8")
    validate_step14_report_language(text)
    written.unlink(missing_ok=True)


def test_report_writer_rejects_docs_output_path() -> None:
    with pytest.raises(ValueError, match="must not be written under docs"):
        write_step14_adoption_synthesis_report(
            adoption_table=adoption_table(),
            output_path=PROJECT_ROOT / "docs" / "step14_generated_report.md",
        )


def test_report_writer_requires_reports_selection_path() -> None:
    with pytest.raises(ValueError, match="reports/selection"):
        write_step14_adoption_synthesis_report(
            adoption_table=adoption_table(),
            output_path=PROJECT_ROOT / "reports" / "diagnostics" / "step14_report.md",
        )


def test_report_writer_rejects_nested_noncanonical_reports_selection_path() -> None:
    with pytest.raises(ValueError, match="reports/selection"):
        write_step14_adoption_synthesis_report(
            adoption_table=adoption_table(),
            output_path=PROJECT_ROOT / "tmp" / "reports" / "selection" / "step14_report.md",
        )


def test_report_writer_rejects_forbidden_columns_before_writing() -> None:
    table = adoption_table()
    table["rank"] = 1
    output_path = report_output_path("test_step14_forbidden_report.md")

    with pytest.raises(ValueError, match="forbidden Step 14 output columns"):
        write_step14_adoption_synthesis_report(
            adoption_table=table,
            output_path=output_path,
        )

    assert not output_path.exists()
