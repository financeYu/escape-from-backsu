"""Collect KIS revision raw snapshots as append-only JSONL."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.ml.kis_revision_snapshot_collector import (  # noqa: E402
    DEFAULT_SNAPSHOT_DIR,
    collect_kis_revision_raw_snapshots,
    ensure_kis_access_token,
)
from stock_core.ml.kis_revision_snapshot_schema import KIS_REVISION_ENDPOINTS  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    endpoints = args.endpoint or list(KIS_REVISION_ENDPOINTS)

    if args.dry_run:
        token_state = ensure_kis_access_token(
            force_refresh=args.force_refresh_token,
            refresh_allowed=False,
            timeout_seconds=args.timeout_seconds,
        )
        summary = {
            "dry_run": True,
            "codes": args.code,
            "endpoints": endpoints,
            "start_date": args.start_date,
            "end_date": args.end_date,
            "output_dir": str(args.output_dir),
            "token": token_state.redacted_summary(),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if token_state.status == "ready" else 2

    result = collect_kis_revision_raw_snapshots(
        codes=args.code,
        endpoints=endpoints,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
        force_refresh_token=args.force_refresh_token,
        timeout_seconds=args.timeout_seconds,
        max_pages=args.max_pages,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    today = datetime.now().strftime("%Y%m%d")
    one_month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--code",
        action="append",
        required=True,
        help="Korean short stock code. Repeat for multiple codes.",
    )
    parser.add_argument(
        "--endpoint",
        action="append",
        choices=sorted(KIS_REVISION_ENDPOINTS),
        help="KIS revision endpoint key. Defaults to all supported endpoints.",
    )
    parser.add_argument("--start-date", default=one_month_ago, help="YYYYMMDD start date for opinion endpoints.")
    parser.add_argument("--end-date", default=today, help="YYYYMMDD end date for opinion endpoints.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_SNAPSHOT_DIR)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument("--force-refresh-token", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
