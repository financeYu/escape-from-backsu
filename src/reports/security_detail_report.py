"""Step 16 deterministic technical-only per-security detail report builder."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import pandas as pd

from src.composite.contracts import (
    DEFAULT_COMPOSITE_INPUT_REGISTRY,
    CompositeInputSpec,
)
from src.reports.security_detail_breakdown import (
    build_component_breakdown,
    build_diagnostic_context,
    build_score_breakdown,
    extract_quality_flags,
    extract_readonly_rank_fields,
)
from src.reports.security_detail_explanations import build_security_explanations
from src.reports.security_detail_metadata import (
    coerce_optional_metadata_frame,
    merge_security_detail_metadata,
    safe_float,
    source_adoption_metadata,
)
from src.reports.security_detail_report_contracts import (
    STEP16_SECURITY_DETAIL_REPORT_NOTICE,
    SecurityDetailReport,
    SecurityReportBoundaryNotice,
    validate_security_detail_report_content,
    validate_step16_latest_ranking_input,
    validate_step16_metadata_table,
)


FINAL_COMPOSITE_TECHNICAL_ONLY_NOTE = (
    "final_composite_score is displayed as existing Step 15 technical-only "
    "context; it is not a separate non-technical result."
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

    metadata_by_score = _prepare_metadata_by_score(
        adoption_synthesis=adoption_synthesis,
        score_metadata=score_metadata,
        diagnostic_metadata=diagnostic_metadata,
        registry=registry,
    )
    return _build_security_detail_report_from_row(
        matches.iloc[0],
        ticker=ticker,
        report_date=report_date,
        metadata_by_score=metadata_by_score,
        registry=registry,
        boundary_notice=boundary_notice,
    )


def _build_security_detail_report_from_row(
    row: pd.Series,
    *,
    ticker: str,
    report_date: object | None,
    metadata_by_score: Mapping[str, Mapping[str, Any]],
    registry: Sequence[CompositeInputSpec],
    boundary_notice: SecurityReportBoundaryNotice | None,
) -> SecurityDetailReport:
    """Build a report from already validated latest-ranking and metadata inputs."""

    snapshot_date = _date_string(row["date"])
    source_latest_ranking_date = _date_string(
        row.get("source_latest_ranking_date", row["date"])
    )
    resolved_report_date = _date_string(report_date if report_date is not None else snapshot_date)

    score_breakdown = build_score_breakdown(
        row,
        metadata_by_score=metadata_by_score,
        registry=registry,
    )
    diagnostic_context = build_diagnostic_context(
        metadata_by_score=metadata_by_score,
        score_breakdown=score_breakdown,
        registry=registry,
    )
    component_breakdown = build_component_breakdown(row)
    explanations = build_security_explanations(row, metadata_by_score=metadata_by_score)
    report = SecurityDetailReport(
        ticker=ticker,
        snapshot_date=snapshot_date,
        report_date=resolved_report_date,
        source_latest_ranking_date=source_latest_ranking_date,
        rank_fields_are_readonly=True,
        readonly_rank_fields=extract_readonly_rank_fields(row),
        technical_composite_score=safe_float(row.get("technical_composite_score")),
        final_composite_score=safe_float(row.get("final_composite_score")),
        final_composite_score_note=FINAL_COMPOSITE_TECHNICAL_ONLY_NOTE,
        score_breakdown=score_breakdown,
        component_breakdown=component_breakdown,
        diagnostic_context=diagnostic_context,
        source_adoption_metadata=source_adoption_metadata(metadata_by_score),
        quality_flags=extract_quality_flags(row),
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
    metadata_by_score = _prepare_metadata_by_score(
        adoption_synthesis=adoption_synthesis,
        score_metadata=score_metadata,
        diagnostic_metadata=diagnostic_metadata,
        registry=registry,
    )
    rows_by_ticker = frame.set_index("ticker", drop=False)
    return tuple(
        _build_security_detail_report_from_row(
            rows_by_ticker.loc[ticker],
            ticker=ticker,
            report_date=report_date,
            metadata_by_score=metadata_by_score,
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


def _prepare_metadata_by_score(
    *,
    adoption_synthesis: pd.DataFrame | Iterable[Mapping[str, Any]] | None,
    score_metadata: pd.DataFrame | Iterable[Mapping[str, Any]] | None,
    diagnostic_metadata: pd.DataFrame | Iterable[Mapping[str, Any]] | None,
    registry: Sequence[CompositeInputSpec],
) -> Mapping[str, Mapping[str, Any]]:
    metadata_frames = tuple(
        coerce_optional_metadata_frame(item)
        for item in (adoption_synthesis, score_metadata, diagnostic_metadata)
    )
    for index, metadata_frame in enumerate(metadata_frames, start=1):
        validate_step16_metadata_table(
            metadata_frame,
            context=f"Step 16 metadata input {index}",
        )
    return merge_security_detail_metadata(metadata_frames, registry=registry)


def _date_string(value: object) -> str:
    timestamp = pd.to_datetime(value, errors="raise")
    if isinstance(timestamp, pd.Series):
        raise ValueError("Step 16 date value must be scalar.")
    return pd.Timestamp(timestamp).date().isoformat()


__all__ = (
    "FINAL_COMPOSITE_TECHNICAL_ONLY_NOTE",
    "build_security_detail_report",
    "build_security_detail_report_records",
    "build_security_detail_reports",
    "STEP16_SECURITY_DETAIL_REPORT_NOTICE",
)
