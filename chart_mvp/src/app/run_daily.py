"""Standalone runner for the stock_core daily update pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
SRC_DIR = CURRENT_FILE.parents[1]

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.pipeline.daily_update import run_daily_update
from stock_core.utils.logging_utils import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the modular daily stock update")
    parser.add_argument("--pages", type=int, default=20, help="Number of Naver daily pages to fetch per stock")
    parser.add_argument("--top-n", type=int, default=5, help="Number of ranked stocks to keep and render")
    parser.add_argument("--limit", type=int, default=None, help="Optional universe limit for lightweight runs")
    parser.add_argument(
        "--no-render-charts",
        action="store_true",
        help="Skip chart image generation during the daily update",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    result = run_daily_update(
        pages=args.pages,
        render_charts=not args.no_render_charts,
        limit=args.limit,
        top_n=args.top_n,
    )
    print(result.rankings.to_string(index=False))
    print(f"[Info] Saved top-{args.top_n} table to: {result.output_path}")
    if result.chart_paths:
        print(f"[Info] Saved {len(result.chart_paths)} chart files.")
    if result.failed_codes:
        print(f"[Info] Failed scans: {len(result.failed_codes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
