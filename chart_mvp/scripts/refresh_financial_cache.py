"""Refresh Naver financial statement caches for the local KOSPI200 snapshot.

This is a validation/reproducibility helper. It writes runtime cache files under
``chart_mvp/data`` and does not enable valuation, technical scoring, composite
scoring, ranking, or backtesting.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.cache.csv_cache import get_financial_statement_cache_path, save_financial_statements
from stock_core.providers.kospi200_universe_provider import get_kospi200_constituents
from stock_core.providers.naver_finance import crawl_financial_statements


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh local Naver financial statement caches for KOSPI200 validation."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of universe entries to refresh.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.15,
        help="Delay between Naver requests.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip codes with existing non-empty financial statement cache files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    constituents = get_kospi200_constituents(refresh=False)
    if args.limit is not None:
        constituents = constituents[: max(args.limit, 0)]

    success: list[str] = []
    skipped: list[str] = []
    empty: list[str] = []
    failures: list[tuple[str, str]] = []

    for index, item in enumerate(constituents, start=1):
        code = item["code"]
        cache_path = get_financial_statement_cache_path(code)
        if args.skip_existing and cache_path.exists() and cache_path.stat().st_size > 0:
            skipped.append(code)
            print(f"[{index:03d}/{len(constituents)}] skipped {code}: existing cache")
            continue

        try:
            frame = crawl_financial_statements(code=code)
            save_financial_statements(frame, code)
        except Exception as exc:  # pragma: no cover - live network and vendor HTML dependent
            failures.append((code, str(exc)))
            print(f"[{index:03d}/{len(constituents)}] failed {code}: {exc}")
        else:
            if frame.empty:
                empty.append(code)
            else:
                success.append(code)
            print(f"[{index:03d}/{len(constituents)}] saved {code}: rows={len(frame)}")

        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    print("SUMMARY")
    print(
        "success={success} skipped={skipped} empty={empty} failures={failures}".format(
            success=len(success),
            skipped=len(skipped),
            empty=len(empty),
            failures=len(failures),
        )
    )
    if empty:
        print("empty_codes=" + ",".join(empty))
    if failures:
        for code, error in failures:
            print(f"failure {code}: {error}")
    print("Boundary: refreshed caches remain inventory-only runtime artifacts.")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
