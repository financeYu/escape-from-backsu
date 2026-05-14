"""Diagnostic KRX sector supplement for v1.4 revision data gaps.

This helper collects KRX sector classification metadata for candidate tickers.
It does not collect point-in-time analyst revision history and must not be used
as v1.4 revision feature input by itself.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Iterable, Mapping


SCHEMA_VERSION = "v1_4_krx_sector_supplement_v1_0"
BOUNDARY_NOTICE = "diagnostic_only_krx_sector_classification_not_pit_revision_history"
OUTPUT_COLUMNS = [
    "schema_version",
    "candidate_id",
    "evidence_id",
    "source_ticker",
    "company_name",
    "diagnostic_sector_id",
    "diagnostic_sector_name",
    "sector_source_ref",
    "sector_source_date",
    "pit_revision_usable",
    "sector_revision_percentile_usable",
    "diagnostic_status",
    "diagnostic_reason_codes",
    "boundary_notice",
]

SectorFetcher = Callable[[str, str], Iterable[Mapping[str, object]]]


@dataclass(frozen=True)
class RevisionSectorSupplementConfig:
    """Paths and source options for a diagnostic KRX sector supplement."""

    candidate_handoff_path: Path
    output_dir: Path
    sector_source_date: str | None = None
    market: str = "KOSPI"
    output_csv_name: str = "v1_4_krx_sector_supplement_latest.csv"
    output_manifest_name: str = "v1_4_krx_sector_supplement_manifest_latest.json"


def build_revision_sector_supplement(
    config: RevisionSectorSupplementConfig,
    *,
    sector_fetcher: SectorFetcher | None = None,
) -> dict[str, object]:
    """Build and write a diagnostic KRX sector supplement."""

    config.output_dir.mkdir(parents=True, exist_ok=True)
    candidate_rows = _read_csv_rows(config.candidate_handoff_path)
    source_date = config.sector_source_date or _default_sector_source_date(candidate_rows)
    sector_rows = list((sector_fetcher or fetch_krx_sector_rows)(source_date, config.market))
    sector_by_ticker = _normalize_sector_rows(sector_rows)
    rows = [
        _build_candidate_sector_row(
            candidate_row,
            sector_by_ticker=sector_by_ticker,
            source_date=source_date,
            market=config.market,
        )
        for candidate_row in candidate_rows
    ]
    output_csv = config.output_dir / config.output_csv_name
    output_manifest = config.output_dir / config.output_manifest_name
    _write_csv(output_csv, rows)
    manifest = _build_manifest(
        rows,
        candidate_handoff_path=config.candidate_handoff_path,
        output_csv=output_csv,
        source_date=source_date,
        market=config.market,
        source_sector_row_count=len(sector_rows),
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


def fetch_krx_sector_rows(source_date: str, market: str) -> list[dict[str, object]]:
    """Fetch KRX sector classifications through pykrx using local KRX env setup."""

    from stock_core.pipeline.kospi200_membership_history import _load_pykrx_login_env

    _load_pykrx_login_env()
    from pykrx import stock

    frame = stock.get_market_sector_classifications(_compact_date(source_date), market)
    if frame.index.name:
        frame = frame.reset_index()
    return [dict(row) for row in frame.to_dict(orient="records")]


def _build_candidate_sector_row(
    candidate_row: dict[str, str],
    *,
    sector_by_ticker: dict[str, dict[str, str]],
    source_date: str,
    market: str,
) -> dict[str, str]:
    ticker = str(candidate_row.get("candidate_ticker") or "").strip()
    sector = sector_by_ticker.get(ticker)
    reasons = [
        "krx_sector_classification_not_revision_history",
        "sector_revision_percentile_still_requires_pit_revision_distribution",
    ]
    status = "diagnostic_sector_available"
    if sector is None:
        reasons.append("krx_sector_missing_for_ticker")
        status = "diagnostic_sector_missing"
    sector_name = str((sector or {}).get("sector_name") or "").strip()
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": str(candidate_row.get("candidate_id") or "").strip(),
        "evidence_id": str(candidate_row.get("evidence_id") or "").strip(),
        "source_ticker": ticker,
        "company_name": str(candidate_row.get("company_name") or "").strip(),
        "diagnostic_sector_id": _sector_id(sector_name),
        "diagnostic_sector_name": sector_name,
        "sector_source_ref": f"pykrx.get_market_sector_classifications({source_date},{market})"
        if sector is not None
        else "",
        "sector_source_date": source_date,
        "pit_revision_usable": "false",
        "sector_revision_percentile_usable": "false",
        "diagnostic_status": status,
        "diagnostic_reason_codes": ";".join(reasons),
        "boundary_notice": BOUNDARY_NOTICE,
    }


def _normalize_sector_rows(rows: Iterable[Mapping[str, object]]) -> dict[str, dict[str, str]]:
    normalized: dict[str, dict[str, str]] = {}
    for row in rows:
        ticker = str(
            row.get("ticker")
            or row.get("code")
            or row.get("종목코드")
            or row.get("ISU_SRT_CD")
            or ""
        ).strip()
        sector_name = str(
            row.get("sector_name")
            or row.get("industry")
            or row.get("업종명")
            or row.get("IDX_IND_NM")
            or ""
        ).strip()
        if ticker and sector_name:
            normalized[ticker.zfill(6)] = {"sector_name": sector_name}
    return normalized


def _sector_id(sector_name: str) -> str:
    if not sector_name:
        return ""
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "_", sector_name).strip("_")
    return f"krx_sector:{slug or sector_name}"


def _default_sector_source_date(candidate_rows: list[dict[str, str]]) -> str:
    dates = sorted(
        {
            value
            for row in candidate_rows
            for key in ("as_of_date", "market_cap_as_of_date")
            for value in [str(row.get(key) or "").strip()]
            if value
        }
    )
    return dates[-1] if dates else date.today().isoformat()


def _compact_date(value: str) -> str:
    return value.replace("-", "")


def _build_manifest(
    rows: list[dict[str, str]],
    *,
    candidate_handoff_path: Path,
    output_csv: Path,
    source_date: str,
    market: str,
    source_sector_row_count: int,
) -> dict[str, object]:
    reason_counts: dict[str, int] = {}
    for row in rows:
        for reason in row["diagnostic_reason_codes"].split(";"):
            if reason:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
    matched_count = sum(1 for row in rows if row["diagnostic_status"] == "diagnostic_sector_available")
    return {
        "schema_version": SCHEMA_VERSION,
        "row_count": len(rows),
        "matched_sector_count": matched_count,
        "candidate_handoff_path": str(candidate_handoff_path),
        "output_csv": str(output_csv),
        "sector_source_date": source_date,
        "market": market,
        "source_sector_row_count": source_sector_row_count,
        "diagnostic_only": True,
        "pit_revision_ready": False,
        "usable_for_v1_4_feature_manifest": False,
        "partially_supplemented_data": ["diagnostic_sector_id", "diagnostic_sector_name"],
        "still_required_for_completion": [
            "available_at",
            "estimate_as_of_date",
            "eps_estimate_1m_ago",
            "eps_estimate_3m_ago",
            "analyst_revision_up_count_1m",
            "analyst_revision_down_count_1m",
            "sector_id_with_pit_taxonomy_version",
            "sector_revision_percentile",
        ],
        "reason_counts": dict(sorted(reason_counts.items())),
        "boundary_notice": BOUNDARY_NOTICE,
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
        description="Build diagnostic-only KRX sector supplement for v1.4 revision gaps."
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
    parser.add_argument("--sector-source-date")
    parser.add_argument("--market", default="KOSPI")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "data" / "v1_4_revision",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_revision_sector_supplement(
        RevisionSectorSupplementConfig(
            candidate_handoff_path=args.candidate_handoff,
            output_dir=args.output_dir,
            sector_source_date=args.sector_source_date,
            market=args.market,
        )
    )
    manifest = result["manifest"]
    print(
        "v1.4 KRX sector supplement rows={rows} matched={matched} pit_revision_ready={ready} output={output}".format(
            rows=manifest["row_count"],
            matched=manifest["matched_sector_count"],
            ready=manifest["pit_revision_ready"],
            output=result["output_csv"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
