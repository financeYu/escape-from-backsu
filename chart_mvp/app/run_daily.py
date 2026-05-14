"""Top-level module entry point for one-click daily execution."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.pipeline.daily_update import run_daily_top5_update, run_daily_top5_update_if_due
from stock_core.utils.logging_utils import configure_logging


def _configure_stdio_for_utf8() -> None:
    """Prefer UTF-8 for local CLI output on Windows terminals."""

    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local configured-universe Top-N daily batch")
    parser.add_argument("--pages", type=int, default=20, help="Number of provider daily pages to fetch per stock")
    parser.add_argument("--top-n", type=int, default=5, help="Number of ranked stocks to keep and render")
    parser.add_argument(
        "--market-cap-override",
        action="store_true",
        help="Prioritize the configured market-cap leader codes before filling the rest by score",
    )
    parser.add_argument("--workers", type=int, default=None, help="Optional parallel worker count for batch processing")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass cache and fetch directly from the current provider",
    )
    parser.add_argument(
        "--refresh-universe",
        action="store_true",
        help="Attempt a live universe refresh before falling back to the snapshot",
    )
    parser.add_argument(
        "--no-render-charts",
        action="store_true",
        help="Skip chart image generation during the batch",
    )
    parser.add_argument(
        "--due-only",
        action="store_true",
        help="Run only when the latest business-day 21:00 update is due or missed",
    )
    parser.add_argument(
        "--no-kis-revision-snapshots",
        action="store_true",
        help="Skip append-only KIS v1.4 revision raw snapshot collection during the daily batch",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdio_for_utf8()
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    runner = run_daily_top5_update_if_due if args.due_only else run_daily_top5_update
    top5_df, meta = runner(
        pages=args.pages,
        use_cache=not args.no_cache,
        refresh_universe=args.refresh_universe,
        render_charts=not args.no_render_charts,
        max_workers=args.workers,
        top_n=args.top_n,
        use_market_cap_override=args.market_cap_override,
        collect_kis_revision_snapshots=not args.no_kis_revision_snapshots,
    )

    if top5_df is None:
        print()
        print("Daily update skipped")
        print(f"Reason: {meta['reason']}")
        print(f"Due at: {meta.get('due_at')}")
        print(f"Last successful update date: {meta.get('due_last_successful_update_date')}")
        return 0

    print()
    print(f"Top {args.top_n} Summary")
    print(top5_df.to_string(index=False))
    print()
    print(f"Processed: {meta['processed_count']} / {meta['universe_size']}")
    print(f"Failed: {meta['failed_count']}")
    print(f"Workers: {meta['max_workers']}")
    print(f"CSV: {meta['output_csv']}")
    print(f"JSON: {meta['output_json']}")
    print(f"META: {meta['output_meta']}")
    if meta.get("market_cap_override"):
        print(f"NOTICE: {meta['market_cap_override_message']}")
        print(f"NOTICE_CODES: {', '.join(meta['market_cap_override_codes'])}")
    if meta["chart_paths"]:
        print(f"Charts: {len(meta['chart_paths'])} files in {PROJECT_ROOT / 'outputs' / 'charts'}")
    kis_meta = meta.get("kis_revision_raw_snapshot") or {}
    if kis_meta:
        print(f"KIS revision raw snapshots: {kis_meta.get('status')}")
        if kis_meta.get("output_path"):
            print(f"KIS revision raw snapshot file: {kis_meta['output_path']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
