"""Step 12 diagnostic report writer and language guardrails.

Generated reports are runtime review artifacts. They are not canonical source
documents and they do not make downstream score decisions.
"""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

from .diagnostic_contracts import (
    STEP12_REVIEW_MATERIAL_NOTICE,
    Step12ThresholdPolicy,
    load_step12_threshold_policy,
    validate_step12_diagnostics_bundle,
)


REPORT_FORBIDDEN_LANGUAGE = frozenset(
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


def validate_step12_report_language(
    text: str,
    *,
    context: str = "Step 12 diagnostic report",
) -> None:
    """Reject generated report language that crosses Step 12 boundaries."""

    lowered = text.lower()
    violations = [
        term for term in sorted(REPORT_FORBIDDEN_LANGUAGE) if _contains_forbidden_term(lowered, term)
    ]
    if violations:
        raise ValueError(f"{context} contains forbidden language: {', '.join(violations)}")
    if STEP12_REVIEW_MATERIAL_NOTICE not in lowered:
        raise ValueError(f"{context} must include: {STEP12_REVIEW_MATERIAL_NOTICE}")


def write_step12_markdown_report(
    *,
    pair_diagnostics: pd.DataFrame,
    coverage_summary: pd.DataFrame,
    output_path: str | Path,
    threshold_policy: Step12ThresholdPolicy | None = None,
    deviation_log: pd.DataFrame | None = None,
) -> Path:
    """Write a generated Step 12 diagnostic report under a runtime report path."""

    validate_step12_diagnostics_bundle(
        pair_diagnostics=pair_diagnostics,
        coverage_summary=coverage_summary,
        deviation_log=deviation_log,
    )
    policy = threshold_policy or load_step12_threshold_policy()
    path = _validate_generated_report_path(output_path)
    text = render_step12_markdown_report(
        pair_diagnostics=pair_diagnostics,
        coverage_summary=coverage_summary,
        threshold_policy=policy,
        deviation_log=deviation_log,
    )
    validate_step12_report_language(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def render_step12_markdown_report(
    *,
    pair_diagnostics: pd.DataFrame,
    coverage_summary: pd.DataFrame,
    threshold_policy: Step12ThresholdPolicy,
    deviation_log: pd.DataFrame | None = None,
) -> str:
    """Render a compact Step 12 report that avoids downstream-output wording."""

    pair_counts = pair_diagnostics["diagnostic_status"].value_counts().sort_index()
    coverage_counts = coverage_summary["diagnostic_status"].value_counts().sort_index()
    lines = [
        "# Step 12 Redundancy Correlation Diagnostics",
        "",
        f"Scope: {STEP12_REVIEW_MATERIAL_NOTICE}.",
        "Generated report is runtime output, not source-controlled canonical state.",
        "",
        "## Threshold Policy",
        "",
        f"- spearman_warn: {threshold_policy.spearman_warn}",
        f"- spearman_block: {threshold_policy.spearman_block}",
        f"- min_cross_section_count: {threshold_policy.min_cross_section_count}",
        f"- min_non_nan_observations: {threshold_policy.min_non_nan_observations}",
        "",
        "## Pair Diagnostics",
        "",
        *_format_counts(pair_counts),
        "",
        "## Coverage Summary",
        "",
        *_format_counts(coverage_counts),
    ]
    if deviation_log is not None and not deviation_log.empty:
        lines.extend(
            [
                "",
                "## Implementation Deviation Log",
                "",
                f"- rows: {len(deviation_log)}",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _format_counts(counts: pd.Series) -> list[str]:
    if counts.empty:
        return ["- rows: 0"]
    lines = [f"- rows: {int(counts.sum())}"]
    lines.extend(f"- {status}: {int(count)}" for status, count in counts.items())
    return lines


def _contains_forbidden_term(lowered: str, term: str) -> bool:
    if " " in term or "_" in term:
        return term in lowered
    return re.search(rf"\b{re.escape(term)}\b", lowered) is not None


def _validate_generated_report_path(output_path: str | Path) -> Path:
    path = Path(output_path)
    lowered_parts = {part.lower() for part in path.parts}
    if "docs" in lowered_parts:
        raise ValueError("Generated Step 12 reports must not be written under docs/.")
    if path.suffix.lower() not in {".md", ".markdown"}:
        raise ValueError("Step 12 generated report path must be a Markdown file.")
    return path


__all__ = (
    "REPORT_FORBIDDEN_LANGUAGE",
    "render_step12_markdown_report",
    "validate_step12_report_language",
    "write_step12_markdown_report",
)
