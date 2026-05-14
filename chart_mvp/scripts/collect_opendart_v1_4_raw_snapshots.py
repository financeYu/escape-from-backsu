"""Collect OpenDART raw snapshots for v1.4 PIT data supplements."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.ml.opendart_v1_4_snapshot import (  # noqa: E402
    DEFAULT_OPENDART_SNAPSHOT_DIR,
    OPENDART_V1_4_ENDPOINTS,
    check_opendart_api_key_readiness,
    collect_opendart_v1_4_raw_snapshots,
    load_opendart_api_key_config,
)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    endpoints = args.endpoint or list(OPENDART_V1_4_ENDPOINTS)

    if args.dry_run:
        readiness = check_opendart_api_key_readiness(load_opendart_api_key_config())
        summary = {
            "dry_run": True,
            "codes": args.code,
            "endpoints": endpoints,
            "bgn_de": args.bgn_de,
            "end_de": args.end_de,
            "bsns_year": args.bsns_year,
            "reprt_code": args.reprt_code,
            "output_dir": str(args.output_dir),
            "opendart_api_key": readiness.to_dict(),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if readiness.status == "ready" else 2

    result = collect_opendart_v1_4_raw_snapshots(
        codes=args.code,
        endpoints=endpoints,
        bgn_de=args.bgn_de,
        end_de=args.end_de,
        bsns_year=args.bsns_year,
        reprt_code=args.reprt_code,
        output_dir=args.output_dir,
        timeout_seconds=args.timeout_seconds,
        max_pages=args.max_pages,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    today = datetime.now()
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
        choices=sorted(OPENDART_V1_4_ENDPOINTS),
        help="OpenDART endpoint key. Defaults to all supported endpoints.",
    )
    parser.add_argument("--bgn-de", default=f"{today.year - 1}0101", help="Disclosure search start date YYYYMMDD.")
    parser.add_argument("--end-de", default=today.strftime("%Y%m%d"), help="Disclosure search end date YYYYMMDD.")
    parser.add_argument("--bsns-year", default=str(today.year - 1), help="Business year for single_account.")
    parser.add_argument("--reprt-code", default="11011", help="Report code: 11011 annual, 11012 half, 11013 Q1, 11014 Q3.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OPENDART_SNAPSHOT_DIR)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
