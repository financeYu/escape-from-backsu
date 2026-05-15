"""Pending-data v1.5 valuation handoff from local chart financial caches.

This helper repackages existing chart_mvp financial cache rows into v1.5
handoff-shaped rows. The local chart cache does not prove filing or
availability dates, so every emitted row remains pending_data and must not be
used as available valuation evidence.
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


SCHEMA_VERSION = "v1_5_chart_local_valuation_quality_pending_handoff_v1_0"
BOUNDARY_NOTICE = "pending_data_only_existing_chart_financial_cache_not_pit_fundamental_source"
OUTPUT_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "ticker",
    "company_name",
    "evaluation_date",
    "fiscal_period",
    "report_period_end_date",
    "filing_date",
    "disclosure_date",
    "availability_date",
    "source_ref",
    "field_name",
    "value",
    "unit",
    "currency",
    "sector_id",
    "industry_id",
    "industry_name",
    "reporting_lag_policy",
    "stale_data_policy",
    "restatement_policy",
    "pit_validation_status",
    "coverage_status",
    "data_quality_flags",
    "pending_reason",
    "source_metric",
    "source_period",
    "source_financial_cache_path",
    "selection_reason",
    "boundary_notice",
]

METRIC_MAP = {
    "PER(배)": ("price_to_earnings", "multiple"),
    "PBR(배)": ("price_to_book", "multiple"),
    "ROE(지배주주)": ("roe", "percent"),
    "영업이익률": ("operating_margin", "percent"),
    "순이익률": ("net_margin", "percent"),
    "부채비율": ("debt_ratio", "percent"),
    "시가배당률(%)": ("dividend_yield", "percent"),
}


@dataclass(frozen=True)
class V15ValuationQualityHandoffConfig:
    """Paths for building v1.5 pending-data handoff rows."""

    candidate_handoff_path: Path
    financial_cache_dir: Path
    output_dir: Path
    sector_supplement_path: Path | None = None
    output_csv_name: str = "v1_5_chart_local_valuation_quality_pending_handoff_latest.csv"
    output_manifest_name: str = "v1_5_chart_local_valuation_quality_pending_manifest_latest.json"


def build_v1_5_valuation_quality_handoff(
    config: V15ValuationQualityHandoffConfig,
) -> dict[str, object]:
    """Build and write pending-data v1.5 valuation-quality handoff rows."""

    config.output_dir.mkdir(parents=True, exist_ok=True)
    candidate_rows = _read_csv_rows(config.candidate_handoff_path)
    sector_supplement_path = config.sector_supplement_path or (
        config.financial_cache_dir / "v1_4_revision" / "v1_4_krx_sector_supplement_latest.csv"
    )
    sector_by_candidate = (
        _read_sector_supplement(sector_supplement_path)
        if sector_supplement_path.exists()
        else {}
    )
    rows: list[dict[str, str]] = []
    for candidate_row in candidate_rows:
        rows.extend(
            _build_candidate_rows(
                candidate_row,
                financial_cache_dir=config.financial_cache_dir,
                sector_row=sector_by_candidate.get(str(candidate_row.get("candidate_id") or "").strip()),
            )
        )
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


def _build_candidate_rows(
    candidate_row: dict[str, str],
    *,
    financial_cache_dir: Path,
    sector_row: dict[str, str] | None,
) -> list[dict[str, str]]:
    ticker = str(candidate_row.get("candidate_ticker") or candidate_row.get("ticker") or "").strip()
    cache_path = financial_cache_dir / f"{ticker}_financial_statements.csv"
    financial_rows = _read_csv_rows(cache_path) if ticker and cache_path.exists() else []
    evaluation_date = _candidate_reference_date(candidate_row)
    rows = []
    for source_metric, (field_name, unit) in METRIC_MAP.items():
        source_row = _select_metric_row(financial_rows, source_metric, reference_date=evaluation_date)
        if source_row is None:
            continue
        rows.append(
            _build_handoff_row(
                candidate_row,
                source_row,
                field_name=field_name,
                unit=unit,
                financial_cache_path=cache_path,
                sector_row=sector_row,
                evaluation_date=evaluation_date,
            )
        )
    return rows


def _build_handoff_row(
    candidate_row: dict[str, str],
    source_row: dict[str, str],
    *,
    field_name: str,
    unit: str,
    financial_cache_path: Path,
    sector_row: dict[str, str] | None,
    evaluation_date: date | None,
) -> dict[str, str]:
    ticker = str(candidate_row.get("candidate_ticker") or candidate_row.get("ticker") or "").strip()
    source_metric = str(source_row.get("metric") or "").strip()
    source_period = str(source_row.get("period") or "").strip()
    report_period_end = _period_end_date(source_period)
    pending_reasons = [
        "availability_date_missing",
        "filing_or_disclosure_date_missing",
        "chart_financial_cache_not_pit_verified",
    ]
    source_ref = "chart_mvp_financial_cache_pending_pit:{ticker}:{file}:{metric}:{period}".format(
        ticker=ticker,
        file=financial_cache_path.name,
        metric=source_metric,
        period=source_period,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": str(candidate_row.get("candidate_id") or "").strip(),
        "evidence_id": str(candidate_row.get("evidence_id") or "").strip(),
        "ticker": ticker,
        "company_name": str(candidate_row.get("company_name") or "").strip(),
        "evaluation_date": evaluation_date.isoformat() if evaluation_date else "",
        "fiscal_period": source_period,
        "report_period_end_date": report_period_end.isoformat() if report_period_end else "",
        "filing_date": "",
        "disclosure_date": "",
        "availability_date": "",
        "source_ref": source_ref,
        "field_name": field_name,
        "value": _normalize_number_text(str(source_row.get("value") or "").strip()),
        "unit": unit,
        "currency": "KRW" if unit == "per_share_krw" else "",
        "sector_id": str((sector_row or {}).get("diagnostic_sector_id") or "").strip(),
        "industry_id": "",
        "industry_name": str((sector_row or {}).get("diagnostic_sector_name") or "").strip(),
        "reporting_lag_policy": "pending_data_requires_external_pit_metadata",
        "stale_data_policy": "pending_data_requires_external_pit_metadata",
        "restatement_policy": "pending_data_requires_external_pit_metadata",
        "pit_validation_status": "pending_data",
        "coverage_status": "pending_data",
        "data_quality_flags": "|".join(
            [
                "chart_mvp_financial_cache",
                "missing_availability_date",
                "not_pit_verified",
                "candidate_only_pending_data",
            ]
        ),
        "pending_reason": ";".join(pending_reasons),
        "source_metric": source_metric,
        "source_period": source_period,
        "source_financial_cache_path": str(financial_cache_path),
        "selection_reason": "latest_non_estimate_financial_cache_row_on_or_before_evaluation_date",
        "boundary_notice": BOUNDARY_NOTICE,
    }


def _select_metric_row(
    rows: Iterable[dict[str, str]],
    metric: str,
    *,
    reference_date: date | None,
) -> dict[str, str] | None:
    candidates = [
        row
        for row in rows
        if str(row.get("metric") or "").strip() == metric
        and str(row.get("value") or "").strip()
        and "(E)" not in str(row.get("period") or "")
    ]
    candidates = [row for row in candidates if _period_end_date(str(row.get("period") or "")) is not None]
    if reference_date is not None:
        candidates = [
            row
            for row in candidates
            if _period_end_date(str(row.get("period") or "")) <= reference_date
        ]
    if not candidates:
        return None
    return sorted(candidates, key=_metric_sort_key)[0]


def _metric_sort_key(row: dict[str, str]) -> tuple[int, int, str]:
    period = str(row.get("period") or "")
    period_end = _period_end_date(period) or date.min
    annual_rank = 0 if "연간" in period else 1
    return (-period_end.toordinal(), annual_rank, period)


def _period_end_date(period: str) -> date | None:
    match = re.search(r"(\d{4})[./-](\d{2})", period)
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        return None
    return date(year, month, calendar.monthrange(year, month)[1])


def _candidate_reference_date(candidate_row: dict[str, str]) -> date | None:
    for key in ("as_of_date", "market_cap_as_of_date", "evaluation_date"):
        raw_value = str(candidate_row.get(key) or "").strip()
        if not raw_value:
            continue
        try:
            return date.fromisoformat(raw_value)
        except ValueError:
            continue
    return None


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
        for reason in row["pending_reason"].split(";"):
            if reason:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
    field_counts: dict[str, int] = {}
    for row in rows:
        field_name = row["field_name"]
        field_counts[field_name] = field_counts.get(field_name, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "row_count": len(rows),
        "candidate_count": len({row["candidate_id"] for row in rows}),
        "candidate_handoff_path": str(candidate_handoff_path),
        "financial_cache_dir": str(financial_cache_dir),
        "sector_supplement_path": str(sector_supplement_path),
        "output_csv": str(output_csv),
        "v1_5_status": "pending_data_only",
        "usable_as_available_v1_5_fundamentals": False,
        "can_fill_from_chart_mvp": [
            "candidate_id",
            "evidence_id",
            "ticker",
            "evaluation_date",
            "source_ref",
            "field_name",
            "value",
            "unit",
            "sector_id_when_v1_4_sector_supplement_exists",
            "industry_name_when_v1_4_sector_supplement_exists",
        ],
        "still_required_external_data": [
            "filing_date_or_disclosure_date",
            "availability_date",
            "source lineage proving the value was available by evaluation_date",
            "restatement policy metadata",
            "stale data policy metadata",
            "reporting lag policy metadata",
            "paired technical_ml and technical_ml_plus_valuation comparison artifacts",
        ],
        "field_counts": dict(sorted(field_counts.items())),
        "pending_reason_counts": dict(sorted(reason_counts.items())),
        "boundary_notice": BOUNDARY_NOTICE,
    }


def _read_sector_supplement(path: Path) -> dict[str, dict[str, str]]:
    rows = _read_csv_rows(path)
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        candidate_id = str(row.get("candidate_id") or "").strip()
        if candidate_id:
            result[candidate_id] = row
    return result


def _normalize_number_text(value: str) -> str:
    return value.replace(",", "").strip()


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
        description="Build pending-data v1.5 valuation handoff from chart financial caches."
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
        default=project_root / "data" / "v1_5_valuation",
    )
    parser.add_argument(
        "--sector-supplement",
        type=Path,
        default=None,
        help="Optional v1.4 sector supplement CSV to merge by candidate_id.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_v1_5_valuation_quality_handoff(
        V15ValuationQualityHandoffConfig(
            candidate_handoff_path=args.candidate_handoff,
            financial_cache_dir=args.financial_cache_dir,
            output_dir=args.output_dir,
            sector_supplement_path=args.sector_supplement,
        )
    )
    manifest = result["manifest"]
    print(
        "v1.5 chart-local valuation handoff rows={rows} status={status} output={output}".format(
            rows=manifest["row_count"],
            status=manifest["v1_5_status"],
            output=result["output_csv"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
