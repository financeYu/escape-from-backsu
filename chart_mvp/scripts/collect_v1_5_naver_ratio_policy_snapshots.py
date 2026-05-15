"""Collect reference-only Naver PER/PBR policy snapshots for v1.5 review."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.providers.naver_finance import (  # noqa: E402
    NAVER_RATIO_POLICY_SNAPSHOT_COLUMNS,
    build_session,
    extract_ratio_policy_snapshot_from_html,
    fetch_main_page_html,
)


def main() -> int:
    args = _parse_args()
    selection_rows = _naver_ratio_policy_ticker_selection_rows(
        args.pending_handoff,
        max_codes=args.max_naver_ratio_policy_tickers,
    )
    codes = [row["ticker"] for row in selection_rows if row.get("collection_target_status") == "selected"]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = args.raw_html_dir or (args.output_dir / "naver_ratio_policy_raw_html")
    raw_dir.mkdir(parents=True, exist_ok=True)
    selection_csv = args.output_dir / "v1_5_naver_ratio_policy_ticker_selection_latest.csv"
    selection_manifest = args.output_dir / "v1_5_naver_ratio_policy_ticker_selection_manifest_latest.json"
    _write_naver_ratio_policy_ticker_selection(
        selection_csv,
        selection_manifest,
        selection_rows,
        args.pending_handoff,
    )

    rows = []
    failures = []
    with build_session() as session:
        for code in codes:
            fetched_at = datetime.now(UTC).replace(microsecond=0).isoformat()
            try:
                html = fetch_main_page_html(code=code, session=session, timeout=args.timeout_seconds)
                raw_path = _raw_html_path(raw_dir, code, fetched_at)
                raw_path.write_bytes(html.encode("utf-8"))
                rows.append(
                    extract_ratio_policy_snapshot_from_html(
                        html,
                        code,
                        fetched_at=fetched_at,
                        raw_html_path=str(raw_path),
                    )
                )
            except Exception as exc:  # pragma: no cover - exercised by live crawl failures.
                failures.append({"ticker": code, "error": type(exc).__name__, "message": str(exc)})
            time.sleep(args.sleep_seconds)

    csv_path = args.output_dir / "v1_5_naver_ratio_policy_snapshot_latest.csv"
    json_path = args.output_dir / "v1_5_naver_ratio_policy_snapshot_latest.json"
    manifest_path = args.output_dir / "v1_5_naver_ratio_policy_snapshot_manifest_latest.json"
    _write_csv(csv_path, rows)
    payload = {
        "schema_version": "v1_5_naver_ratio_policy_snapshot_payload_v1_0",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "row_count": len(rows),
        "failure_count": len(failures),
        "scoring_activation_allowed": False,
        "rows": rows,
        "failures": failures,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v1_5_naver_ratio_policy_snapshot_manifest_v1_0",
        "created_at": payload["created_at"],
        "candidate_codes": codes,
        "candidate_selection_csv": str(selection_csv),
        "candidate_selection_manifest": str(selection_manifest),
        "collection_target_policy": "v1_5_naver_ratio_collection_target_policy_v1",
        "selection_policy": "v1_5_naver_ratio_collection_target_policy_v1",
        "hardcoded_tickers_used": False,
        "row_count": len(rows),
        "failure_count": len(failures),
        "output_csv": str(csv_path),
        "output_json": str(json_path),
        "raw_html_dir": str(raw_dir),
        "source_lineage_status_counts": _status_counts(rows, "source_lineage_status"),
        "missing_policy_field_counts": _missing_field_counts(rows),
        "usable_as_available_v1_5_fundamentals": False,
        "promotion_status": "not_promoted",
        "promotion_blocked_reason": (
            "Naver crawl snapshots document fetch-time page policy only; historical "
            "PIT availability still requires snapshot time <= evaluation_date."
        ),
        "failures": failures,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "v1.5 Naver ratio policy snapshots rows={rows} failures={failures} manifest={manifest}".format(
            rows=len(rows),
            failures=len(failures),
            manifest=manifest_path,
        )
    )
    return 1 if failures and not rows else 0


def _candidate_codes(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return sorted({str(row.get("ticker", "")).strip() for row in rows if row.get("ticker")})


def _naver_ratio_policy_ticker_selection_rows(path: Path, max_codes: int = 0) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        pending_rows = list(csv.DictReader(handle))
    grouped: dict[str, dict[str, object]] = {}
    for row in pending_rows:
        ticker = str(row.get("ticker", "")).strip()
        if not ticker:
            continue
        entry = grouped.setdefault(
            ticker,
            {
                "ticker": ticker,
                "candidate_count": set(),
                "per_pbr_field_count": 0,
                "quality_profitability_field_count": 0,
                "source_file_count": set(),
                "latest_evaluation_date": "",
            },
        )
        _as_string_set(entry["candidate_count"]).add(row.get("candidate_id", ""))
        field_name = row.get("field_name", "")
        if field_name in {"price_to_earnings", "price_to_book"}:
            entry["per_pbr_field_count"] = int(entry["per_pbr_field_count"]) + 1
        if field_name in {"debt_ratio", "net_margin", "operating_margin", "roe"}:
            entry["quality_profitability_field_count"] = int(entry["quality_profitability_field_count"]) + 1
        if row.get("source_financial_cache_path"):
            _as_string_set(entry["source_file_count"]).add(row.get("source_financial_cache_path", ""))
        evaluation_date = row.get("evaluation_date", "")
        if evaluation_date > str(entry["latest_evaluation_date"]):
            entry["latest_evaluation_date"] = evaluation_date
    ranked = []
    for entry in grouped.values():
        per_pbr_count = int(entry["per_pbr_field_count"])
        quality_count = int(entry["quality_profitability_field_count"])
        source_count = len(_as_string_set(entry["source_file_count"]))
        collection_priority_score = per_pbr_count * 10 + quality_count * 2 + source_count
        collection_target_status = (
            "eligible" if collection_priority_score > 0 and per_pbr_count > 0 else "not_selected_no_per_pbr_need"
        )
        collection_target_reason = "daily_candidate_handoff_ratio_collection_need_not_hardcoded"
        ranked.append(
            {
                "ticker": str(entry["ticker"]),
                "selection_source": str(path),
                "candidate_count": str(len(_as_string_set(entry["candidate_count"]))),
                "per_pbr_field_count": str(per_pbr_count),
                "quality_profitability_field_count": str(quality_count),
                "source_file_count": str(source_count),
                "latest_evaluation_date": str(entry["latest_evaluation_date"]),
                "collection_priority_score": str(collection_priority_score),
                "collection_target_status": collection_target_status,
                "collection_target_reason": collection_target_reason,
                "selection_score": str(collection_priority_score),
                "selection_status": collection_target_status,
                "selection_reason": collection_target_reason,
            }
        )
    ranked.sort(key=lambda row: (-int(row["collection_priority_score"]), row["ticker"]))
    limit = max_codes if max_codes > 0 else len(ranked)
    selected = 0
    for row in ranked:
        if row["collection_target_status"] == "eligible" and selected < limit:
            row["collection_target_status"] = "selected"
            row["selection_status"] = "selected"
            selected += 1
        elif row["collection_target_status"] == "eligible":
            row["collection_target_status"] = "not_selected_limit"
            row["selection_status"] = "not_selected_limit"
    return ranked


def _as_string_set(value: object) -> set[str]:
    return value if isinstance(value, set) else set()


def _write_naver_ratio_policy_ticker_selection(
    csv_path: Path,
    manifest_path: Path,
    rows: list[dict[str, str]],
    pending_handoff_path: Path,
) -> None:
    columns = [
        "ticker",
        "selection_source",
        "candidate_count",
        "per_pbr_field_count",
        "quality_profitability_field_count",
        "source_file_count",
        "latest_evaluation_date",
        "collection_priority_score",
        "collection_target_status",
        "collection_target_reason",
        "selection_score",
        "selection_status",
        "selection_reason",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    selected_codes = [row["ticker"] for row in rows if row.get("collection_target_status") == "selected"]
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "v1_5_naver_ratio_policy_ticker_selection_v1_0",
                "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
                "collection_target_policy": "v1_5_naver_ratio_collection_target_policy_v1",
                "selection_policy": "v1_5_naver_ratio_collection_target_policy_v1",
                "selection_source": str(pending_handoff_path),
                "hardcoded_tickers_used": False,
                "selected_codes": selected_codes,
                "row_count": len(rows),
                "selected_count": len(selected_codes),
                "scoring_activation_allowed": False,
                "compatibility_alias_columns": [
                    "selection_score",
                    "selection_status",
                    "selection_reason",
                ],
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _raw_html_path(raw_dir: Path, code: str, fetched_at: str) -> Path:
    safe_timestamp = fetched_at.replace(":", "").replace("-", "").replace("+", "Z")
    return raw_dir / f"{code}_main_naver_{safe_timestamp}.html"


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=NAVER_RATIO_POLICY_SNAPSHOT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _status_counts(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(field, "")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _missing_field_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for field in row.get("missing_policy_fields", "").split("|"):
            if field:
                counts[field] = counts.get(field, 0) + 1
    return dict(sorted(counts.items()))


def _parse_args() -> argparse.Namespace:
    default_output_dir = PROJECT_ROOT / "data" / "v1_5_valuation"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pending-handoff",
        type=Path,
        default=default_output_dir / "v1_5_chart_local_valuation_quality_pending_handoff_latest.csv",
    )
    parser.add_argument("--output-dir", type=Path, default=default_output_dir)
    parser.add_argument("--raw-html-dir", type=Path, default=None)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument("--sleep-seconds", type=float, default=0.3)
    parser.add_argument(
        "--max-naver-ratio-policy-tickers",
        type=int,
        default=0,
        help="Maximum daily Naver ratio-policy tickers selected from the current pending handoff; 0 means all eligible.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
