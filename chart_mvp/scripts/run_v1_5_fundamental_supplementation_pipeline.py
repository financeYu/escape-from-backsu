"""Run the local v1.5 fundamental supplementation pipeline.

The pipeline is candidate-only and evidence-only. It can optionally collect
OpenDART raw snapshots for the candidates already present in the v1.5 pending
handoff, then rebuild the supplementation artifacts from local files.
"""

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

from stock_core.ml.opendart_v1_4_snapshot import (  # noqa: E402
    DEFAULT_OPENDART_SNAPSHOT_DIR,
    collect_opendart_v1_4_raw_snapshots,
)
from stock_core.ml.v1_5_supplementation import (  # noqa: E402
    V15SupplementationConfig,
    build_v1_5_supplementation,
)
from stock_core.ml.v1_5_valuation_quality_handoff import (  # noqa: E402
    V15ValuationQualityHandoffConfig,
    build_v1_5_valuation_quality_handoff,
)
from stock_core.providers.naver_finance import (  # noqa: E402
    NAVER_RATIO_POLICY_SNAPSHOT_COLUMNS,
    build_session,
    extract_ratio_policy_snapshot_from_html,
    fetch_main_page_html,
)


def main() -> int:
    args = _parse_args()
    handoff_result = build_v1_5_valuation_quality_handoff(
        V15ValuationQualityHandoffConfig(
            candidate_handoff_path=args.candidate_handoff,
            financial_cache_dir=args.financial_cache_dir,
            output_dir=args.output_dir,
            sector_supplement_path=args.sector_supplement,
        )
    )
    pending_handoff_path = Path(str(handoff_result["output_csv"]))
    codes = _candidate_codes(pending_handoff_path)
    naver_selection_rows = _naver_ratio_policy_ticker_selection_rows(
        pending_handoff_path,
        max_codes=args.max_naver_ratio_policy_tickers,
    )
    naver_codes = [
        row["ticker"]
        for row in naver_selection_rows
        if row.get("collection_target_status") == "selected"
    ]
    naver_selection_csv = args.output_dir / "v1_5_naver_ratio_policy_ticker_selection_latest.csv"
    naver_selection_manifest = args.output_dir / "v1_5_naver_ratio_policy_ticker_selection_manifest_latest.json"
    _write_naver_ratio_policy_ticker_selection(
        naver_selection_csv,
        naver_selection_manifest,
        naver_selection_rows,
        pending_handoff_path,
    )
    collected_snapshot_path = None
    collection_status = "not_requested"

    if args.collect_opendart:
        result = collect_opendart_v1_4_raw_snapshots(
            codes=codes,
            endpoints=("disclosure_list", "single_account", "alot_matter"),
            bgn_de=args.bgn_de,
            end_de=args.end_de,
            bsns_year=args.bsns_year,
            reprt_code=args.reprt_code,
            output_dir=args.opendart_output_dir,
            timeout_seconds=args.timeout_seconds,
            max_pages=args.max_pages,
        )
        collected_snapshot_path = result.output_path
        collection_status = "collected"

    naver_snapshot_path = None
    naver_collection_status = "not_requested"
    if args.collect_naver_ratio_policy:
        naver_snapshot_path = args.output_dir / "v1_5_naver_ratio_policy_snapshot_latest.csv"
        naver_collection_status = _collect_naver_ratio_policy_snapshots(
            naver_codes,
            naver_snapshot_path,
            args.output_dir / "naver_ratio_policy_raw_html",
            args.timeout_seconds,
            args.sleep_seconds,
        )

    supplementation_result = build_v1_5_supplementation(
        V15SupplementationConfig(
            pending_handoff_path=pending_handoff_path,
            dart_raw_snapshot_path=collected_snapshot_path,
            naver_ratio_policy_snapshot_path=naver_snapshot_path,
            technical_ml_scores_path=args.technical_ml_scores,
            output_dir=args.output_dir,
        )
    )
    manifest = {
        "schema_version": "v1_5_fundamental_supplementation_pipeline_v1_0",
        "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "candidate_codes": codes,
        "naver_ratio_policy_candidate_selection_csv": str(naver_selection_csv),
        "naver_ratio_policy_candidate_selection_manifest": str(naver_selection_manifest),
        "naver_ratio_policy_selected_codes": naver_codes,
        "naver_ratio_policy_collection_target_policy": "v1_5_naver_ratio_collection_target_policy_v1",
        "naver_ratio_policy_selection_policy": "v1_5_naver_ratio_collection_target_policy_v1",
        "collection_status": collection_status,
        "collected_snapshot_path": str(collected_snapshot_path) if collected_snapshot_path else "",
        "naver_ratio_policy_collection_status": naver_collection_status,
        "naver_ratio_policy_snapshot_path": str(naver_snapshot_path) if naver_snapshot_path else "",
        "handoff_output": handoff_result["output_csv"],
        "supplementation_outputs": supplementation_result["outputs"],
        "limited_completion_update": supplementation_result["limited_completion_update"],
        "usable_as_available_v1_5_fundamentals": False,
        "promotion_status": "not_promoted",
    }
    manifest_path = args.output_dir / "v1_5_fundamental_supplementation_automation_manifest_latest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "v1.5 fundamental pipeline status={status} collection={collection} naver_collection={naver_collection} codes={codes} manifest={manifest}".format(
            status=manifest["limited_completion_update"]["current_status"],
            collection=collection_status,
            naver_collection=naver_collection_status,
            codes=",".join(naver_codes),
            manifest=manifest_path,
        )
    )
    if args.collect_naver_ratio_policy and naver_collection_status == "failed":
        return 1
    return 0


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
        cast_set(entry["candidate_count"]).add(row.get("candidate_id", ""))
        field_name = row.get("field_name", "")
        if field_name in {"price_to_earnings", "price_to_book"}:
            entry["per_pbr_field_count"] = int(entry["per_pbr_field_count"]) + 1
        if field_name in {"debt_ratio", "net_margin", "operating_margin", "roe"}:
            entry["quality_profitability_field_count"] = int(entry["quality_profitability_field_count"]) + 1
        if row.get("source_financial_cache_path"):
            cast_set(entry["source_file_count"]).add(row.get("source_financial_cache_path", ""))
        evaluation_date = row.get("evaluation_date", "")
        if evaluation_date > str(entry["latest_evaluation_date"]):
            entry["latest_evaluation_date"] = evaluation_date
    ranked = []
    for entry in grouped.values():
        per_pbr_count = int(entry["per_pbr_field_count"])
        quality_count = int(entry["quality_profitability_field_count"])
        source_count = len(cast_set(entry["source_file_count"]))
        collection_priority_score = per_pbr_count * 10 + quality_count * 2 + source_count
        collection_target_status = (
            "eligible" if collection_priority_score > 0 and per_pbr_count > 0 else "not_selected_no_per_pbr_need"
        )
        collection_target_reason = "daily_candidate_handoff_ratio_collection_need_not_hardcoded"
        ranked.append(
            {
                "ticker": str(entry["ticker"]),
                "selection_source": str(path),
                "candidate_count": str(len(cast_set(entry["candidate_count"]))),
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


def cast_set(value: object) -> set[str]:
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


def _collect_naver_ratio_policy_snapshots(
    codes: list[str],
    output_path: Path,
    raw_html_dir: Path,
    timeout_seconds: int,
    sleep_seconds: float,
) -> str:
    raw_html_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    failures = []
    with build_session() as session:
        for code in codes:
            fetched_at = datetime.now(UTC).replace(microsecond=0).isoformat()
            try:
                html = fetch_main_page_html(code=code, session=session, timeout=timeout_seconds)
                raw_path = raw_html_dir / f"{code}_main_naver_{fetched_at.replace(':', '').replace('-', '').replace('+', 'Z')}.html"
                raw_path.write_bytes(html.encode("utf-8"))
                rows.append(
                    extract_ratio_policy_snapshot_from_html(
                        html,
                        code,
                        fetched_at=fetched_at,
                        raw_html_path=str(raw_path),
                    )
                )
            except Exception as exc:  # pragma: no cover - live network failure path.
                failures.append({"ticker": code, "error": type(exc).__name__, "message": str(exc)})
            time.sleep(sleep_seconds)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=NAVER_RATIO_POLICY_SNAPSHOT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path = output_path.with_suffix(".json")
    json_path.write_text(
        json.dumps(
            {
                "schema_version": "v1_5_naver_ratio_policy_snapshot_payload_v1_0",
                "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
                "row_count": len(rows),
                "failure_count": len(failures),
                "scoring_activation_allowed": False,
                "rows": rows,
                "failures": failures,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return "collected" if rows and not failures else ("partial" if rows else "failed")


def _parse_args() -> argparse.Namespace:
    today = datetime.now()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-handoff",
        type=Path,
        default=PROJECT_ROOT / "data" / "v1_3_liquidity" / "v1_3_candidate_liquidity_handoff_records_latest.csv",
    )
    parser.add_argument("--financial-cache-dir", type=Path, default=PROJECT_ROOT / "data")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data" / "v1_5_valuation")
    parser.add_argument("--sector-supplement", type=Path, default=None)
    parser.add_argument("--technical-ml-scores", type=Path, default=PROJECT_ROOT.parent / "Quant_mvp" / "data" / "v0_4" / "selector_scores" / "v0_4_selector_scores.jsonl")
    parser.add_argument("--collect-opendart", action="store_true")
    parser.add_argument("--bgn-de", default=f"{today.year - 1}0101")
    parser.add_argument("--end-de", default=today.strftime("%Y%m%d"))
    parser.add_argument("--bsns-year", default=str(today.year - 1))
    parser.add_argument("--reprt-code", default="11011")
    parser.add_argument("--opendart-output-dir", type=Path, default=DEFAULT_OPENDART_SNAPSHOT_DIR)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument("--sleep-seconds", type=float, default=0.3)
    parser.add_argument("--collect-naver-ratio-policy", action="store_true")
    parser.add_argument(
        "--max-naver-ratio-policy-tickers",
        type=int,
        default=0,
        help="Maximum daily Naver ratio-policy tickers selected from the current pending handoff; 0 means all eligible.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
