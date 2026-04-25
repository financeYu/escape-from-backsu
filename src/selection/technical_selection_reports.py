"""Generated Step 13 technical selection review report builder."""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

from .technical_selection_reviewer import (
    STEP13_REVIEW_MATERIAL_NOTICE,
    build_technical_selection_review,
    validate_step13_review_table,
)
from .technical_selection_contracts import (
    STEP13_REVIEW_MATERIAL_NOTICE as CONTRACT_STEP13_REVIEW_MATERIAL_NOTICE,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STEP13_REPORT_ROOT = PROJECT_ROOT / "reports" / "selection"

STEP13_REPORT_FORBIDDEN_LANGUAGE = frozenset(
    {
        "rank",
        "ranking",
        "latest_rank",
        "latest ranking",
        "technical_composite_score",
        "final_composite_score",
        "forward_return",
        "future_return",
        "backtest",
        "backtest_return",
        "alpha",
        "signal",
        "buy",
        "sell",
        "valuation",
        "valuation_score",
        "undervalued",
        "cheap",
        "bargain",
    }
)


def write_step13_review_report(
    *,
    review_table: pd.DataFrame | None = None,
    pair_diagnostics: pd.DataFrame | None = None,
    coverage_summary: pd.DataFrame | None = None,
    output_path: str | Path = "reports/selection/step13_technical_selection_review.md",
) -> Path:
    """Write a generated Step 13 review report under reports/selection/."""

    if review_table is None:
        if pair_diagnostics is None or coverage_summary is None:
            raise ValueError("Provide review_table or both pair_diagnostics and coverage_summary.")
        review_table = build_technical_selection_review(
            pair_diagnostics=pair_diagnostics,
            coverage_summary=coverage_summary,
        )
    validate_step13_review_table(review_table)
    path = _validate_generated_report_path(output_path)
    text = render_step13_review_report(review_table)
    validate_step13_report_language(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def render_step13_review_report(review_table: pd.DataFrame) -> str:
    """Render compact generated Step 13 review material."""

    validate_step13_review_table(review_table)
    status_counts = review_table["review_status"].value_counts().sort_index()
    coverage_counts = review_table["coverage_status"].value_counts().sort_index()
    redundancy_counts = review_table["redundancy_status"].value_counts().sort_index()
    lines = [
        "# Step 13 Technical Selection Review",
        "",
        f"Scope: {STEP13_REVIEW_MATERIAL_NOTICE}; {CONTRACT_STEP13_REVIEW_MATERIAL_NOTICE}.",
        "Generated report is runtime output, not source-controlled canonical state.",
        "These statuses are Step 13 review material, not final Step 14 states.",
        "",
        "## Review Status Counts",
        "",
        *_format_counts(status_counts),
        "",
        "## Coverage Status Counts",
        "",
        *_format_counts(coverage_counts),
        "",
        "## Redundancy Status Counts",
        "",
        *_format_counts(redundancy_counts),
        "",
        "## Score Review Table",
        "",
        "| score_name | review_status | coverage_status | redundancy_status | strongest_redundant_peer | max_abs_spearman | manual_review_required |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines.extend(_format_review_table_rows(review_table))
    return "\n".join(lines).strip() + "\n"


def _format_review_table_rows(review_table: pd.DataFrame) -> list[str]:
    return [
        "| {score_name} | {review_status} | {coverage_status} | {redundancy_status} | "
        "{strongest_redundant_peer} | {max_abs_spearman} | {manual_review_required} |".format(
            score_name=row["score_name"],
            review_status=row["review_status"],
            coverage_status=row["coverage_status"],
            redundancy_status=row["redundancy_status"],
            strongest_redundant_peer=row["strongest_redundant_peer"],
            max_abs_spearman=_format_optional_number(row["max_abs_spearman"]),
            manual_review_required=str(bool(row["manual_review_required"])).lower(),
        )
        for _, row in review_table.iterrows()
    ]


def validate_step13_report_language(
    text: str,
    *,
    context: str = "Step 13 technical selection report",
) -> None:
    """Reject generated report language that crosses Step 13 boundaries."""

    lowered = text.lower()
    violations = [
        term
        for term in sorted(STEP13_REPORT_FORBIDDEN_LANGUAGE)
        if _contains_forbidden_term(lowered, term)
    ]
    if violations:
        raise ValueError(f"{context} contains forbidden language: {', '.join(violations)}")
    if STEP13_REVIEW_MATERIAL_NOTICE not in lowered:
        raise ValueError(f"{context} must include: {STEP13_REVIEW_MATERIAL_NOTICE}")
    if CONTRACT_STEP13_REVIEW_MATERIAL_NOTICE not in lowered:
        raise ValueError(f"{context} must include: {CONTRACT_STEP13_REVIEW_MATERIAL_NOTICE}")


def _format_counts(counts: pd.Series) -> list[str]:
    if counts.empty:
        return ["- rows: 0"]
    lines = [f"- rows: {int(counts.sum())}"]
    lines.extend(f"- {status}: {int(count)}" for status, count in counts.items())
    return lines


def _format_optional_number(value: object) -> str:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return ""
    if pd.isna(parsed):
        return ""
    return f"{parsed:.4f}"


def _contains_forbidden_term(lowered: str, term: str) -> bool:
    if " " in term or "_" in term:
        return term in lowered
    return re.search(rf"(^|[^a-z0-9]){re.escape(term)}([^a-z0-9]|$)", lowered) is not None


def _validate_generated_report_path(output_path: str | Path) -> Path:
    path = Path(output_path)
    lowered_parts = [part.lower() for part in path.parts]
    if "docs" in lowered_parts:
        raise ValueError("Generated Step 13 reports must not be written under docs/.")
    if path.suffix.lower() not in {".md", ".markdown"}:
        raise ValueError("Step 13 generated report path must be a Markdown file.")
    resolved_path = (path if path.is_absolute() else PROJECT_ROOT / path).resolve(strict=False)
    resolved_root = STEP13_REPORT_ROOT.resolve(strict=False)
    if not resolved_path.is_relative_to(resolved_root):
        raise ValueError("Generated Step 13 reports must be written under reports/selection/.")
    return resolved_path


__all__ = (
    "STEP13_REPORT_FORBIDDEN_LANGUAGE",
    "render_step13_review_report",
    "validate_step13_report_language",
    "write_step13_review_report",
)
