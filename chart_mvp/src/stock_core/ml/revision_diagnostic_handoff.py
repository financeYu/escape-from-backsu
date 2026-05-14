"""Diagnostic v1.4 revision handoff from local chart financial caches.

This helper only repackages existing local financial statement cache rows into
v1.4 diagnostic records. It does not verify point-in-time revision safety and
does not activate valuation, scoring, ranking, or execution behavior.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


SCHEMA_VERSION = "v1_4_chart_financial_revision_diagnostic_handoff_v1_0"
BOUNDARY_NOTICE = (
    "diagnostic_only_existing_chart_financial_cache_not_pit_revision_source"
)
OUTPUT_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "source_ticker",
    "company_name",
    "revision_source_ref",
    "estimate_as_of_date",
    "available_at",
    "fiscal_period",
    "sector_id",
    "eps_estimate_current",
    "eps_estimate_1m_ago",
    "eps_estimate_3m_ago",
    "analyst_revision_up_count_1m",
    "analyst_revision_down_count_1m",
    "sector_revision_percentile",
    "diagnostic_sector_id",
    "diagnostic_sector_name",
    "diagnostic_sector_source_ref",
    "diagnostic_sector_source_date",
    "source_financial_cache_path",
    "source_metric",
    "source_period",
    "selection_reference_date",
    "selection_reason",
    "diagnostic_status",
    "diagnostic_reason_codes",
    "boundary_notice",
]


@dataclass(frozen=True)
class RevisionDiagnosticHandoffConfig:
    """Paths for building a diagnostic handoff from chart_mvp local caches."""

    candidate_handoff_path: Path
    financial_cache_dir: Path
    output_dir: Path
    sector_supplement_path: Path | None = None
    output_csv_name: str = "v1_4_candidate_revision_diagnostic_handoff_latest.csv"
    output_manifest_name: str = "v1_4_candidate_revision_diagnostic_manifest_latest.json"


def build_revision_diagnostic_handoff(
    config: RevisionDiagnosticHandoffConfig,
) -> dict[str, object]:
    """Build and write diagnostic v1.4 revision handoff rows."""

    config.output_dir.mkdir(parents=True, exist_ok=True)
    candidate_rows = _read_csv_rows(config.candidate_handoff_path)
    sector_supplement_path = config.sector_supplement_path or (
        config.output_dir / "v1_4_krx_sector_supplement_latest.csv"
    )
    sector_by_candidate = (
        _read_sector_supplement(sector_supplement_path)
        if sector_supplement_path.exists()
        else {}
    )
    rows = [
        _build_candidate_revision_row(
            candidate_row,
            financial_cache_dir=config.financial_cache_dir,
            sector_row=sector_by_candidate.get(str(candidate_row.get("candidate_id") or "").strip()),
        )
        for candidate_row in candidate_rows
    ]
    output_csv = config.output_dir / config.output_csv_name
    output_manifest = config.output_dir / config.output_manifest_name
    _write_csv(output_csv, rows)
    manifest = _build_manifest(
        rows,
        candidate_handoff_path=config.candidate_handoff_path,
        financial_cache_dir=config.financial_cache_dir,
        sector_supplement_path=sector_supplement_path,
        output_csv=output_csv,
    )
    output_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "rows": rows,
        "manifest": manifest,
        "output_csv": str(output_csv),
        "output_manifest": str(output_manifest),
    }


def _build_candidate_revision_row(
    candidate_row: dict[str, str],
    *,
    financial_cache_dir: Path,
    sector_row: dict[str, str] | None = None,
) -> dict[str, str]:
    ticker = str(candidate_row.get("candidate_ticker") or "").strip()
    cache_path = financial_cache_dir / f"{ticker}_financial_statements.csv"
    financial_rows = _read_csv_rows(cache_path) if cache_path.exists() else []
    selection_reference_date = _candidate_reference_date(candidate_row)
    eps_row = _select_eps_estimate_row(
        financial_rows,
        reference_date=selection_reference_date,
    )
    reasons = [
        "available_at_missing",
        "estimate_as_of_date_missing",
        "eps_estimate_1m_ago_missing",
        "eps_estimate_3m_ago_missing",
        "analyst_revision_up_count_1m_missing",
        "analyst_revision_down_count_1m_missing",
        "sector_id_missing",
        "sector_revision_percentile_missing",
        "chart_financial_cache_is_not_revision_history",
    ]
    status = "diagnostic_missing_pit_revision_fields"
    if not cache_path.exists():
        reasons.append("financial_cache_missing")
    if eps_row is None:
        reasons.append("eps_estimate_current_missing")
    if selection_reference_date is None:
        reasons.append("selection_reference_date_missing")
    source_ref = (
        f"chart_mvp_financial_statement_cache:{ticker}:{cache_path.name}"
        if ticker and cache_path.exists()
        else ""
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": str(candidate_row.get("candidate_id") or "").strip(),
        "evidence_id": str(candidate_row.get("evidence_id") or "").strip(),
        "source_ticker": ticker,
        "company_name": str(candidate_row.get("company_name") or "").strip(),
        "revision_source_ref": source_ref,
        "estimate_as_of_date": "",
        "available_at": "",
        "fiscal_period": str((eps_row or {}).get("period") or "").strip(),
        "sector_id": "",
        "eps_estimate_current": str((eps_row or {}).get("value") or "").strip(),
        "eps_estimate_1m_ago": "",
        "eps_estimate_3m_ago": "",
        "analyst_revision_up_count_1m": "",
        "analyst_revision_down_count_1m": "",
        "sector_revision_percentile": "",
        "diagnostic_sector_id": str((sector_row or {}).get("diagnostic_sector_id") or "").strip(),
        "diagnostic_sector_name": str((sector_row or {}).get("diagnostic_sector_name") or "").strip(),
        "diagnostic_sector_source_ref": str((sector_row or {}).get("sector_source_ref") or "").strip(),
        "diagnostic_sector_source_date": str((sector_row or {}).get("sector_source_date") or "").strip(),
        "source_financial_cache_path": str(cache_path),
        "source_metric": str((eps_row or {}).get("metric") or "").strip(),
        "source_period": str((eps_row or {}).get("period") or "").strip(),
        "selection_reference_date": selection_reference_date.isoformat()
        if selection_reference_date is not None
        else "",
        "selection_reason": "best_matching_eps_estimate_period_for_candidate_row_reference_date"
        if selection_reference_date is not None and eps_row is not None
        else "fallback_eps_estimate_row_selection",
        "diagnostic_status": status,
        "diagnostic_reason_codes": ";".join(reasons),
        "boundary_notice": BOUNDARY_NOTICE,
    }


def _select_eps_estimate_row(
    rows: Iterable[dict[str, str]],
    *,
    reference_date: date | None,
) -> dict[str, str] | None:
    candidates = [
        row
        for row in rows
        if "eps" in str(row.get("metric") or "").lower()
        and "(E)" in str(row.get("period") or "")
        and str(row.get("value") or "").strip()
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda row: _eps_estimate_sort_key(row, reference_date))[0]


def _eps_estimate_sort_key(row: dict[str, str], reference_date: date | None) -> tuple[int, int, int, int, str]:
    period = str(row.get("period") or "")
    period_range = _period_date_range(period)
    if reference_date is not None and period_range is not None:
        start, end = period_range
        contains_rank = 0 if start <= reference_date <= end else 1
        distance = 0 if contains_rank == 0 else min(abs((start - reference_date).days), abs((end - reference_date).days))
        span_days = (end - start).days
    else:
        contains_rank = 1
        distance = 999_999
        span_days = 999_999
    consolidated_rank = 0 if "연결" in period else 1
    return (contains_rank, distance, span_days, consolidated_rank, period)


def _candidate_reference_date(candidate_row: dict[str, str]) -> date | None:
    for key in ("as_of_date", "market_cap_as_of_date"):
        raw_value = str(candidate_row.get(key) or "").strip()
        if not raw_value:
            continue
        try:
            return date.fromisoformat(raw_value)
        except ValueError:
            continue
    return None


def _period_date_range(period: str) -> tuple[date, date] | None:
    match = re.search(r"(\d{4})[./-](\d{2})", period)
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        return None
    end = date(year, month, calendar.monthrange(year, month)[1])
    if "분기" in period:
        start_month = max(1, month - 2)
        return date(year, start_month, 1), end
    if "연간" in period:
        return date(year, 1, 1), end
    return date(year, month, 1), end


def _build_manifest(
    rows: list[dict[str, str]],
    *,
    candidate_handoff_path: Path,
    financial_cache_dir: Path,
    sector_supplement_path: Path,
    output_csv: Path,
) -> dict[str, object]:
    reason_counts: dict[str, int] = {}
    for row in rows:
        for reason in row["diagnostic_reason_codes"].split(";"):
            if reason:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "row_count": len(rows),
        "candidate_handoff_path": str(candidate_handoff_path),
        "financial_cache_dir": str(financial_cache_dir),
        "sector_supplement_path": str(sector_supplement_path),
        "output_csv": str(output_csv),
        "diagnostic_only": True,
        "pit_revision_ready": False,
        "filled_current_data": _field_fill_counts(
            rows,
            [
                "candidate_id",
                "evidence_id",
                "revision_source_ref",
                "fiscal_period",
                "eps_estimate_current",
                "diagnostic_sector_id",
                "diagnostic_sector_name",
            ],
        ),
        "unfilled_required_data": _field_missing_counts(
            rows,
            [
                "available_at",
                "estimate_as_of_date",
                "eps_estimate_1m_ago",
                "eps_estimate_3m_ago",
                "analyst_revision_up_count_1m",
                "analyst_revision_down_count_1m",
                "sector_id",
                "sector_revision_percentile",
            ],
        ),
        "reason_counts": dict(sorted(reason_counts.items())),
        "boundary_notice": BOUNDARY_NOTICE,
        "next_required_data": [
            "available_at",
            "estimate_as_of_date",
            "eps_estimate_1m_ago",
            "eps_estimate_3m_ago",
            "analyst_revision_up_count_1m",
            "analyst_revision_down_count_1m",
            "sector_id",
            "sector_revision_percentile",
        ],
    }


def _read_sector_supplement(path: Path) -> dict[str, dict[str, str]]:
    rows = _read_csv_rows(path)
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        candidate_id = str(row.get("candidate_id") or "").strip()
        if candidate_id:
            result[candidate_id] = row
    return result


def _field_fill_counts(rows: list[dict[str, str]], fields: list[str]) -> dict[str, int]:
    return {
        field: sum(1 for row in rows if str(row.get(field) or "").strip())
        for field in fields
    }


def _field_missing_counts(rows: list[dict[str, str]], fields: list[str]) -> dict[str, int]:
    return {
        field: sum(1 for row in rows if not str(row.get(field) or "").strip())
        for field in fields
    }


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build diagnostic-only v1.4 revision handoff from chart financial caches."
    )
    project_root = Path(__file__).resolve().parents[3]
    parser.add_argument(
        "--candidate-handoff",
        type=Path,
        default=project_root
        / "data"
        / "v1_3_liquidity"
        / "v1_3_candidate_liquidity_handoff_records_latest.csv",
    )
    parser.add_argument(
        "--financial-cache-dir",
        type=Path,
        default=project_root / "data",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "data" / "v1_4_revision",
    )
    parser.add_argument(
        "--sector-supplement",
        type=Path,
        default=None,
        help="Optional diagnostic KRX sector supplement CSV to merge by candidate_id.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_revision_diagnostic_handoff(
        RevisionDiagnosticHandoffConfig(
            candidate_handoff_path=args.candidate_handoff,
            financial_cache_dir=args.financial_cache_dir,
            output_dir=args.output_dir,
            sector_supplement_path=args.sector_supplement,
        )
    )
    manifest = result["manifest"]
    print(
        "v1.4 diagnostic revision handoff rows={rows} pit_revision_ready={ready} output={output}".format(
            rows=manifest["row_count"],
            ready=manifest["pit_revision_ready"],
            output=result["output_csv"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
