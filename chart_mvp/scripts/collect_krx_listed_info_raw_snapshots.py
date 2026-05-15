"""Collect KRX listed-info raw snapshots for v1.4 mapping supplements."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.ml.krx_listed_info_snapshot import (  # noqa: E402
    DEFAULT_KRX_LISTED_INFO_PAGE_COUNT,
    DEFAULT_KRX_LISTED_INFO_SNAPSHOT_DIR,
    check_krx_listed_info_api_key_readiness,
    collect_krx_listed_info_raw_snapshots,
    load_krx_listed_info_api_key_config,
)
from stock_core.providers.kospi200_universe_provider import get_kospi200_constituents  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    codes = _resolve_codes(args)
    if args.dry_run:
        readiness = check_krx_listed_info_api_key_readiness(load_krx_listed_info_api_key_config())
        summary = {
            "dry_run": True,
            "output_dir": str(args.output_dir),
            "page_count": 1 if not args.all_history else args.page_count,
            "max_pages": args.max_pages,
            "query_mode": "all_history_page" if args.all_history else "code_supplement_latest",
            "codes_requested": len(codes) if codes is not None else 0,
            "krx_listed_info_api_key": readiness.to_dict(),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if readiness.status == "ready" else 2

    try:
        result = collect_krx_listed_info_raw_snapshots(
            codes=codes,
            output_dir=args.output_dir,
            page_count=args.page_count,
            max_pages=args.max_pages,
            timeout_seconds=args.timeout_seconds,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "secret_values_redacted": True,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    else:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_KRX_LISTED_INFO_SNAPSHOT_DIR)
    parser.add_argument("--page-count", type=int, default=DEFAULT_KRX_LISTED_INFO_PAGE_COUNT)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument(
        "--code",
        action="append",
        default=[],
        help="Collect only the latest listed-info supplement for this stock code. Can be repeated.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit when using the local KOSPI200 universe supplement mode.",
    )
    parser.add_argument(
        "--all-history",
        action="store_true",
        help="Collect raw paged listed-info history instead of local-universe code supplements.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def _resolve_codes(args: argparse.Namespace) -> list[str] | None:
    if args.all_history:
        return None
    codes = list(args.code)
    if not codes:
        codes = [str(item["code"]) for item in get_kospi200_constituents(refresh=False)]
    if args.limit is not None:
        codes = codes[: args.limit]
    return codes


if __name__ == "__main__":
    raise SystemExit(main())
