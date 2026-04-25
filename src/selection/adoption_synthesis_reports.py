"""Generated Step 14 adoption synthesis report builder."""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

from .adoption_synthesis import (
    STEP14_ADOPTION_MATERIAL_NOTICE,
    STEP14_ALLOWED_BOUNDARY_PHRASES,
    STEP14_FORBIDDEN_LANGUAGE_TERMS,
    build_adoption_synthesis_table,
    reject_step14_forbidden_columns,
    validate_step14_adoption_language,
    validate_step14_adoption_table,
)
from .adoption_synthesis_contracts import (
    STEP14_FORBIDDEN_REPORT_LANGUAGE as CONTRACT_STEP14_FORBIDDEN_REPORT_LANGUAGE,
    validate_adoption_report_text,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STEP14_REPORT_ROOT = PROJECT_ROOT / "reports" / "selection"
STEP14_REPORT_BOUNDARY_NOTICE = (
    "not ranking, not composite score, not backtest, not trading signal, and not valuation"
)


def write_step14_adoption_synthesis_report(
    *,
    adoption_table: pd.DataFrame | None = None,
    review_rows: pd.DataFrame | None = None,
    output_path: str | Path = "reports/selection/step14_adoption_synthesis.md",
) -> Path:
    """Write a generated Step 14 adoption synthesis report under reports/selection/."""

    if adoption_table is None:
        if review_rows is None:
            raise ValueError("Provide adoption_table or review_rows.")
        adoption_table = build_adoption_synthesis_table(review_rows)

    reject_step14_forbidden_columns(adoption_table, context="Step 14 generated report input")
    validate_step14_adoption_table(adoption_table, context="Step 14 generated report input")
    path = _validate_generated_report_path(output_path)
    text = render_step14_adoption_synthesis_report(adoption_table)
    validate_step14_report_language(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def render_step14_adoption_synthesis_report(adoption_table: pd.DataFrame) -> str:
    """Render compact Step 14 synthesis material for runtime review."""

    validate_step14_adoption_table(adoption_table, context="Step 14 report adoption table")
    state_counts = adoption_table["adoption_state"].value_counts().sort_index()
    manual_counts = adoption_table["manual_review_required"].value_counts().sort_index()
    lines = [
        "# Step 14 Adoption Synthesis",
        "",
        f"Scope: {STEP14_ADOPTION_MATERIAL_NOTICE}.",
        f"Boundary: {STEP14_REPORT_BOUNDARY_NOTICE}.",
        "Generated report is runtime output, not source-controlled canonical state.",
        "Rows preserve source review order and are not sorted by strength or return.",
        "",
        "## Adoption State Counts",
        "",
        *_format_counts(state_counts),
        "",
        "## Manual Review Counts",
        "",
        *_format_counts(manual_counts),
        "",
        "## Score Adoption Table",
        "",
        "| score_name | source_review_status | adoption_state | manual_review_required | limitations |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines.extend(_format_adoption_table_rows(adoption_table))
    return "\n".join(lines).strip() + "\n"


def validate_step14_report_language(
    text: str,
    *,
    context: str = "Step 14 adoption synthesis report",
) -> None:
    """Reject generated report language that crosses Step 14 boundaries."""

    validate_step14_adoption_language(text, context=context, require_notice=True)
    lowered = text.lower()
    if STEP14_REPORT_BOUNDARY_NOTICE not in lowered:
        raise ValueError(f"{context} must include: {STEP14_REPORT_BOUNDARY_NOTICE}")
    screened = _strip_allowed_report_phrases(lowered)
    violations = [
        term
        for term in sorted(STEP14_FORBIDDEN_LANGUAGE_TERMS)
        if _contains_forbidden_term(screened, term)
    ]
    violations.extend(
        term
        for term in sorted(CONTRACT_STEP14_FORBIDDEN_REPORT_LANGUAGE)
        if _contains_forbidden_term(screened, term.lower())
    )
    if violations:
        unique_violations = sorted(set(violations))
        raise ValueError(f"{context} contains forbidden language: {', '.join(unique_violations)}")
    validate_adoption_report_text(screened, context=context, require_notice=False)


def _format_adoption_table_rows(adoption_table: pd.DataFrame) -> list[str]:
    return [
        "| {score_name} | {source_review_status} | {adoption_state} | "
        "{manual_review_required} | {limitations} |".format(
            score_name=_escape_table_text(row["score_name"]),
            source_review_status=_escape_table_text(row["source_review_status"]),
            adoption_state=_escape_table_text(row["adoption_state"]),
            manual_review_required=str(bool(row["manual_review_required"])).lower(),
            limitations=_escape_table_text(row["limitations"]),
        )
        for _, row in adoption_table.iterrows()
    ]


def _format_counts(counts: pd.Series) -> list[str]:
    if counts.empty:
        return ["- rows: 0"]
    lines = [f"- rows: {int(counts.sum())}"]
    lines.extend(f"- {status}: {int(count)}" for status, count in counts.items())
    return lines


def _escape_table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _validate_generated_report_path(output_path: str | Path) -> Path:
    path = Path(output_path)
    lowered_parts = [part.lower() for part in path.parts]
    if "docs" in lowered_parts:
        raise ValueError("Generated Step 14 reports must not be written under docs/.")
    if path.suffix.lower() not in {".md", ".markdown"}:
        raise ValueError("Step 14 generated report path must be a Markdown file.")
    resolved_path = (path if path.is_absolute() else PROJECT_ROOT / path).resolve(strict=False)
    resolved_root = STEP14_REPORT_ROOT.resolve(strict=False)
    if not resolved_path.is_relative_to(resolved_root):
        raise ValueError("Generated Step 14 reports must be written under reports/selection/.")
    return resolved_path


def _strip_allowed_report_phrases(lowered: str) -> str:
    screened = lowered
    for phrase in STEP14_ALLOWED_BOUNDARY_PHRASES:
        screened = screened.replace(phrase, "")
    screened = screened.replace(STEP14_REPORT_BOUNDARY_NOTICE, "")
    return screened


def _contains_forbidden_term(lowered: str, term: str) -> bool:
    if " " in term or "_" in term:
        return term in lowered
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", lowered) is not None


__all__ = (
    "STEP14_REPORT_BOUNDARY_NOTICE",
    "render_step14_adoption_synthesis_report",
    "validate_step14_report_language",
    "write_step14_adoption_synthesis_report",
)
