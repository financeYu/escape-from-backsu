"""Step 16 deterministic technical-only per-security detail report builder."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import math
from typing import Any

import numpy as np
import pandas as pd

from src.composite.contracts import (
    DEFAULT_COMPOSITE_INPUT_REGISTRY,
    CompositeInputSpec,
)
from src.reports.security_detail_report_contracts import (
    STEP16_READONLY_RANK_FIELD_COLUMNS,
    STEP16_SECURITY_DETAIL_REPORT_NOTICE,
    SecurityComponentBreakdown,
    SecurityDetailReport,
    SecurityReportBoundaryNotice,
    SecurityReportDisplayRole,
    SecurityScoreBreakdown,
    validate_security_detail_report_content,
    validate_step16_latest_ranking_input,
    validate_step16_metadata_table,
    validate_step16_report_text,
)


FINAL_COMPOSITE_TECHNICAL_ONLY_NOTE = (
    "final_composite_score is displayed as existing Step 15 technical-only "
    "context; it is not a separate valuation or fundamental result."
)

DIRECT_ADOPTION_STATES = frozenset({"core_adopted", "technical_only"})
CONTEXT_ADOPTION_STATES = frozenset(
    {
        "conditional_adopted",
        "regime_only",
        "diagnostic_only",
        "research_only",
    }
)
EXPLANATION_ADOPTION_STATES = frozenset(
    {
        "rejected",
        "blocked_by_data",
        "needs_manual_review",
    }
)
CONTEXT_ROLES = frozenset({"confirmation", "setup_context", "diagnostic_context"})
HEALTHY_STATUS_VALUES = frozenset({"", "ok", "valid", "adequate", "ready", "false"})

SOURCE_ADOPTION_METADATA_COLUMNS: tuple[str, ...] = (
    "score_name",
    "family",
    "branch",
    "role",
    "eligibility",
    "adoption_state",
    "source_review_status",
    "coverage_status",
    "redundancy_status",
    "complexity_status",
    "regime_fit_status",
    "manual_review_required",
    "limitations",
)

ROW_EXPLANATION_COLUMNS: tuple[str, ...] = (
    "diagnostic_note",
    "ranking_reason_code",
    "blocked_reason",
    "manual_review_reason",
    "limitations",
)


def build_security_detail_report(
    latest_ranking_output: pd.DataFrame | Iterable[Mapping[str, Any]],
    ticker: str,
    *,
    report_date: object | None = None,
    adoption_synthesis: pd.DataFrame | Iterable[Mapping[str, Any]] | None = None,
    score_metadata: pd.DataFrame | Iterable[Mapping[str, Any]] | None = None,
    diagnostic_metadata: pd.DataFrame | Iterable[Mapping[str, Any]] | None = None,
    registry: Sequence[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
    boundary_notice: SecurityReportBoundaryNotice | None = None,
) -> SecurityDetailReport:
    """Build one Step 16 per-security detail report from loaded Step 15 output.

    The function treats Step 15 rank and composite fields as read-only input
    context. It does not sort, recalculate rank, run a backtest, calculate
    future labels, or merge valuation/fundamental data.
    """

    frame = _coerce_frame(latest_ranking_output, context="Step 16 latest ranking input")
    validate_step16_latest_ranking_input(frame)
    ticker = _validate_ticker(ticker)
    matches = frame.loc[frame["ticker"].eq(ticker)]
    if matches.empty:
        raise ValueError(f"Step 16 latest ranking input does not contain ticker: {ticker}")
    if len(matches) > 1:
        raise ValueError(f"Step 16 latest ranking input has duplicate rows for ticker: {ticker}")

    metadata_frames = tuple(
        _coerce_optional_frame(item)
        for item in (adoption_synthesis, score_metadata, diagnostic_metadata)
    )
    for index, metadata_frame in enumerate(metadata_frames, start=1):
        validate_step16_metadata_table(
            metadata_frame,
            context=f"Step 16 metadata input {index}",
        )

    metadata_by_score = _metadata_by_score(metadata_frames, registry=registry)
    row = matches.iloc[0]
    snapshot_date = _date_string(row["date"])
    source_latest_ranking_date = _date_string(
        row.get("source_latest_ranking_date", row["date"])
    )
    resolved_report_date = _date_string(report_date if report_date is not None else snapshot_date)

    score_breakdown = _build_score_breakdown(
        row,
        metadata_by_score=metadata_by_score,
        registry=registry,
    )
    diagnostic_context = _build_diagnostic_context(
        metadata_by_score=metadata_by_score,
        score_breakdown=score_breakdown,
        registry=registry,
    )
    component_breakdown = _build_component_breakdown(row)
    explanations = _build_explanations(row, metadata_by_score=metadata_by_score)
    report = SecurityDetailReport(
        ticker=ticker,
        snapshot_date=snapshot_date,
        report_date=resolved_report_date,
        source_latest_ranking_date=source_latest_ranking_date,
        rank_fields_are_readonly=True,
        readonly_rank_fields=_extract_readonly_rank_fields(row),
        technical_composite_score=_safe_float(row.get("technical_composite_score")),
        final_composite_score=_safe_float(row.get("final_composite_score")),
        final_composite_score_note=FINAL_COMPOSITE_TECHNICAL_ONLY_NOTE,
        score_breakdown=score_breakdown,
        component_breakdown=component_breakdown,
        diagnostic_context=diagnostic_context,
        source_adoption_metadata=_source_adoption_metadata(metadata_by_score),
        quality_flags=_extract_quality_flags(row),
        explanations=explanations,
        boundary_notice=boundary_notice or SecurityReportBoundaryNotice(),
    )
    validate_security_detail_report_content(report.to_dict())
    return report


def build_security_detail_reports(
    latest_ranking_output: pd.DataFrame | Iterable[Mapping[str, Any]],
    tickers: Sequence[str] | str | None = None,
    *,
    report_date: object | None = None,
    adoption_synthesis: pd.DataFrame | Iterable[Mapping[str, Any]] | None = None,
    score_metadata: pd.DataFrame | Iterable[Mapping[str, Any]] | None = None,
    diagnostic_metadata: pd.DataFrame | Iterable[Mapping[str, Any]] | None = None,
    registry: Sequence[CompositeInputSpec] = DEFAULT_COMPOSITE_INPUT_REGISTRY,
    boundary_notice: SecurityReportBoundaryNotice | None = None,
) -> tuple[SecurityDetailReport, ...]:
    """Build Step 16 reports for one or more tickers without reordering by score."""

    frame = _coerce_frame(latest_ranking_output, context="Step 16 latest ranking input")
    validate_step16_latest_ranking_input(frame)
    selected_tickers = _selected_tickers(frame, tickers)
    present = set(frame["ticker"].astype("string"))
    missing = [ticker for ticker in selected_tickers if ticker not in present]
    if missing:
        raise ValueError(
            "Step 16 latest ranking input does not contain ticker(s): "
            f"{', '.join(missing)}"
        )
    return tuple(
        build_security_detail_report(
            frame,
            ticker,
            report_date=report_date,
            adoption_synthesis=adoption_synthesis,
            score_metadata=score_metadata,
            diagnostic_metadata=diagnostic_metadata,
            registry=registry,
            boundary_notice=boundary_notice,
        )
        for ticker in selected_tickers
    )


def build_security_detail_report_records(
    latest_ranking_output: pd.DataFrame | Iterable[Mapping[str, Any]],
    tickers: Sequence[str] | str | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Return JSON/DataFrame-friendly Step 16 report records."""

    reports = build_security_detail_reports(latest_ranking_output, tickers, **kwargs)
    return [report.to_record() for report in reports]


def _coerce_frame(
    rows: pd.DataFrame | Iterable[Mapping[str, Any]],
    *,
    context: str,
) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    frame = pd.DataFrame(list(rows))
    if frame.empty:
        raise ValueError(f"{context} must not be empty.")
    return frame


def _coerce_optional_frame(
    rows: pd.DataFrame | Iterable[Mapping[str, Any]] | None,
) -> pd.DataFrame | None:
    if rows is None:
        return None
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.DataFrame(list(rows))


def _validate_ticker(ticker: str) -> str:
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("Step 16 ticker must be a non-empty string.")
    if len(ticker) != 6 or not ticker.isdigit():
        raise ValueError("Step 16 ticker must preserve six-digit string format.")
    return ticker


def _selected_tickers(frame: pd.DataFrame, tickers: Sequence[str] | str | None) -> list[str]:
    if tickers is None:
        return frame["ticker"].astype("string").tolist()
    if isinstance(tickers, str):
        return [_validate_ticker(tickers)]
    return [_validate_ticker(ticker) for ticker in tickers]


def _metadata_by_score(
    metadata_frames: Sequence[pd.DataFrame | None],
    *,
    registry: Sequence[CompositeInputSpec],
) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {
        spec.score_name: {
            "score_name": spec.score_name,
            "family": spec.family,
            "branch": spec.branch,
            "role": spec.role.value,
            "eligibility": spec.eligibility.value,
            "normalized_score_column": spec.normalized_column,
        }
        for spec in registry
    }
    for frame in metadata_frames:
        if frame is None or frame.empty:
            continue
        if "score_name" not in frame.columns:
            raise ValueError("Step 16 metadata tables must include score_name.")
        for _, row in frame.iterrows():
            score_name = str(row["score_name"])
            target = metadata.setdefault(score_name, {"score_name": score_name})
            for column, value in row.items():
                if _is_present(value):
                    target[str(column)] = _safe_scalar(value)
    return metadata


def _build_score_breakdown(
    row: pd.Series,
    *,
    metadata_by_score: Mapping[str, Mapping[str, Any]],
    registry: Sequence[CompositeInputSpec],
) -> tuple[SecurityScoreBreakdown, ...]:
    breakdown: list[SecurityScoreBreakdown] = []
    for spec in registry:
        if spec.normalized_column not in row.index:
            continue
        metadata = metadata_by_score.get(spec.score_name, {})
        score = SecurityScoreBreakdown(
            score_name=spec.score_name,
            source_column=spec.normalized_column,
            score_value=_safe_float(row.get(spec.normalized_column)),
            score_family=str(metadata.get("family", spec.family)),
            score_role=str(metadata.get("role", spec.role.value)),
            score_branch=str(metadata.get("branch", spec.branch)),
            eligibility=str(metadata.get("eligibility", spec.eligibility.value)),
            adoption_state=str(metadata.get("adoption_state", "")),
            source_review_status=str(metadata.get("source_review_status", "")),
            readonly_step15_component=True,
            context_only=False,
            display_role=SecurityReportDisplayRole.READONLY_STEP15_SCORE_COMPONENT.value,
            status=str(_safe_scalar(row.get(spec.status_column, "")) or ""),
            quality_flag=str(_safe_scalar(row.get(spec.quality_flag_column, "")) or ""),
            valid_count=_safe_int(row.get(spec.count_column)),
            explanation=_score_explanation(spec.score_name, metadata),
        )
        breakdown.append(score)
    return tuple(breakdown)


def _build_diagnostic_context(
    *,
    metadata_by_score: Mapping[str, Mapping[str, Any]],
    score_breakdown: Sequence[SecurityScoreBreakdown],
    registry: Sequence[CompositeInputSpec],
) -> tuple[SecurityScoreBreakdown, ...]:
    displayed = {score.score_name for score in score_breakdown}
    registry_by_name = {spec.score_name: spec for spec in registry}
    context_rows: list[SecurityScoreBreakdown] = []
    for score_name in sorted(metadata_by_score):
        if score_name in displayed:
            continue
        metadata = metadata_by_score[score_name]
        spec = registry_by_name.get(score_name)
        role = str(metadata.get("role", spec.role.value if spec else ""))
        branch = str(metadata.get("branch", spec.branch if spec else ""))
        adoption_state = str(metadata.get("adoption_state", ""))
        if not _is_context_metadata(role=role, branch=branch, adoption_state=adoption_state):
            continue
        context_rows.append(
            SecurityScoreBreakdown(
                score_name=score_name,
                source_column=str(metadata.get("normalized_score_column", "")),
                score_value=None,
                score_family=str(metadata.get("family", spec.family if spec else "")),
                score_role=role,
                score_branch=branch,
                eligibility=str(metadata.get("eligibility", spec.eligibility.value if spec else "")),
                adoption_state=adoption_state,
                source_review_status=str(metadata.get("source_review_status", "")),
                readonly_step15_component=False,
                context_only=True,
                display_role=(
                    SecurityReportDisplayRole.DIAGNOSTIC_CONTEXT_NOT_RANK_DRIVER.value
                ),
                explanation=_score_explanation(score_name, metadata),
            )
        )
    return tuple(context_rows)


def _build_component_breakdown(row: pd.Series) -> tuple[SecurityComponentBreakdown, ...]:
    components: list[SecurityComponentBreakdown] = []
    for column in row.index:
        normalized = str(column)
        if not normalized.endswith("_family_score"):
            continue
        component_name = normalized.removesuffix("_family_score")
        components.append(
            SecurityComponentBreakdown(
                component_name=component_name,
                component_type="family_score",
                source_column=normalized,
                value=_safe_float(row.get(column)),
            )
        )
    return tuple(components)


def _source_adoption_metadata(
    metadata_by_score: Mapping[str, Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    rows: list[Mapping[str, Any]] = []
    for score_name in sorted(metadata_by_score):
        metadata = metadata_by_score[score_name]
        if "adoption_state" not in metadata and "source_review_status" not in metadata:
            continue
        row = {
            column: metadata[column]
            for column in SOURCE_ADOPTION_METADATA_COLUMNS
            if column in metadata and _is_present(metadata[column])
        }
        if row:
            rows.append(row)
    return tuple(rows)


def _extract_readonly_rank_fields(row: pd.Series) -> dict[str, Any]:
    return {
        column: _safe_scalar(row[column])
        for column in STEP16_READONLY_RANK_FIELD_COLUMNS
        if column in row.index
    }


def _extract_quality_flags(row: pd.Series) -> dict[str, Any]:
    quality: dict[str, Any] = {}
    for column in row.index:
        normalized = str(column)
        if (
            "warmup" in normalized
            or "coverage" in normalized
            or "quality" in normalized
            or "validity" in normalized
            or normalized.endswith(("_status", "_flag", "_metric", "_count"))
        ):
            quality[normalized] = _safe_scalar(row[column])
    return quality


def _build_explanations(
    row: pd.Series,
    *,
    metadata_by_score: Mapping[str, Mapping[str, Any]],
) -> tuple[str, ...]:
    explanations: list[str] = []
    for column in (
        "coverage_status",
        "ranking_validity_flag",
        "data_quality_flag",
        "score_warmup_state",
        "score_coverage_status",
        "score_data_quality_flag",
    ):
        if column not in row.index:
            continue
        value = _safe_scalar(row[column])
        if _status_value(value) not in HEALTHY_STATUS_VALUES:
            explanations.append(
                f"{column} is {value}; Step 16 keeps this row as technical context only."
            )
    if "rank" in row.index and not _is_present(row["rank"]):
        explanations.append("Step 15 rank is unavailable for this row.")
    for column in ROW_EXPLANATION_COLUMNS:
        if column in row.index and _is_present(row[column]):
            text = str(_safe_scalar(row[column]))
            validate_step16_report_text(text, context=f"Step 16 explanation column {column}")
            explanations.append(f"{column}: {text}")
    for score_name in sorted(metadata_by_score):
        metadata = metadata_by_score[score_name]
        adoption_state = str(metadata.get("adoption_state", ""))
        manual_review_required = bool(metadata.get("manual_review_required", False))
        if adoption_state not in EXPLANATION_ADOPTION_STATES and not manual_review_required:
            continue
        detail = _score_explanation(score_name, metadata)
        if detail:
            explanations.append(detail)
        else:
            explanations.append(f"{score_name} adoption_state is {adoption_state}.")
    return tuple(_dedupe(explanations))


def _score_explanation(score_name: str, metadata: Mapping[str, Any]) -> str:
    adoption_state = str(metadata.get("adoption_state", ""))
    manual_review_required = bool(metadata.get("manual_review_required", False))
    parts: list[str] = []
    if adoption_state:
        parts.append(f"{score_name} adoption_state is {adoption_state}.")
    if manual_review_required:
        parts.append(f"{score_name} requires manual review before stronger downstream use.")
    for column in ("adoption_reason", "limitations"):
        value = metadata.get(column)
        if _is_present(value):
            text = str(value)
            validate_step16_report_text(text, context=f"Step 16 {column}")
            parts.append(text)
    return " ".join(parts)


def _is_context_metadata(*, role: str, branch: str, adoption_state: str) -> bool:
    if role in CONTEXT_ROLES or branch == "diagnostic":
        return True
    if adoption_state in CONTEXT_ADOPTION_STATES:
        return True
    return adoption_state not in DIRECT_ADOPTION_STATES and adoption_state != ""


def _date_string(value: object) -> str:
    timestamp = pd.to_datetime(value, errors="raise")
    if isinstance(timestamp, pd.Series):
        raise ValueError("Step 16 date value must be scalar.")
    return pd.Timestamp(timestamp).date().isoformat()


def _safe_float(value: object) -> float | None:
    if not _is_present(value):
        return None
    numeric = pd.to_numeric(value, errors="coerce")
    try:
        parsed = float(numeric)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _safe_int(value: object) -> int | None:
    if not _is_present(value):
        return None
    numeric = pd.to_numeric(value, errors="coerce")
    try:
        parsed = float(numeric)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return int(parsed)


def _safe_scalar(value: object) -> Any:
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return _safe_float(value)
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _is_present(value: object) -> bool:
    if value is None or value is pd.NA or value is pd.NaT:
        return False
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return True
    if isinstance(missing, (bool, np.bool_)):
        return not bool(missing)
    return True


def _status_value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


__all__ = (
    "FINAL_COMPOSITE_TECHNICAL_ONLY_NOTE",
    "build_security_detail_report",
    "build_security_detail_report_records",
    "build_security_detail_reports",
    "STEP16_SECURITY_DETAIL_REPORT_NOTICE",
)
