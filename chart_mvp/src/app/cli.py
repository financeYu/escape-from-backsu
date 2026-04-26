"""CLI entry points for single-stock charts and configured-universe scans."""

from __future__ import annotations

import argparse
import sys

from stock_core.charts.matplotlib_renderer import plot_stock_data
from stock_core.cache.csv_cache import get_cache_path, refresh_stock_data
from stock_core.pipeline.daily_update import run_daily_top5_update, run_daily_top5_update_if_due
from stock_core.providers.kospi200_universe_provider import normalize_stock_code
from stock_core.providers.naver_finance import fetch_stock_name


def run_single_stock(code: str, pages: int, show_chart: bool = True) -> int:
    """Run the legacy single-stock flow with the modular backend."""

    normalized_code = normalize_stock_code(code)
    stock_name = normalized_code
    try:
        stock_name = fetch_stock_name(normalized_code)
    except Exception as exc:
        print(f"[Warning] Failed to fetch stock name for {normalized_code}: {exc}")

    print(f"[Info] Preparing chart for {stock_name} ({normalized_code}), pages={pages}")

    try:
        final_df, source = refresh_stock_data(code=normalized_code, pages=pages)
    except Exception as exc:
        print(f"[Error] {exc}")
        return 1

    source_label = "평일 갱신" if source == "fetched" else "주말 캐시"
    print(final_df.tail())
    print(f"[Info] Stock: {stock_name} ({normalized_code})")
    print(f"[Info] Data source: {source_label}")
    print(f"[Info] Cache file: {get_cache_path(normalized_code)}")
    plot_stock_data(final_df, stock_label=stock_name, source_label=source_label, show=show_chart)
    return 0


def run_daily_scan(
    pages: int,
    workers: int | None = None,
    use_cache: bool = True,
    refresh_universe: bool = False,
    render_charts: bool = True,
    top_n: int = 5,
    use_market_cap_override: bool = False,
    due_only: bool = False,
) -> int:
    """Run the current daily Top-N batch flow used by the GUI and scripts."""

    runner = run_daily_top5_update_if_due if due_only else run_daily_top5_update
    top5_df, meta = runner(
        pages=pages,
        use_cache=use_cache,
        refresh_universe=refresh_universe,
        render_charts=render_charts,
        max_workers=workers,
        top_n=top_n,
        use_market_cap_override=use_market_cap_override,
    )
    if top5_df is None:
        print(f"[Info] Daily update skipped: {meta['reason']}")
        print(f"[Info] Due at: {meta.get('due_at')}")
        print(f"[Info] Last successful update date: {meta.get('due_last_successful_update_date')}")
        return 0

    print(top5_df.to_string(index=False))
    print(f"[Info] Saved top-{top_n} table to: {meta['output_csv']}")
    print(f"[Info] Saved JSON to: {meta['output_json']}")
    if meta["chart_paths"]:
        print(f"[Info] Saved {len(meta['chart_paths'])} chart files.")
    if meta["failed_count"]:
        print(f"[Info] Failed scans: {meta['failed_count']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build a small CLI with a batch default and a single-stock mode."""

    parser = argparse.ArgumentParser(description="Local stock analysis and configured-universe scan tool")
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Run the daily configured-universe batch scan")
    scan_parser.add_argument("--pages", type=int, default=20, help="Number of provider daily pages to fetch per stock")
    scan_parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Optional parallel worker count for batch processing",
    )
    scan_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass cache and fetch directly from the current provider",
    )
    scan_parser.add_argument(
        "--refresh-universe",
        action="store_true",
        help="Attempt a live universe refresh before falling back to the snapshot",
    )
    scan_parser.add_argument(
        "--no-render-charts",
        action="store_true",
        help="Skip chart image generation during the batch",
    )
    scan_parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Number of ranked stocks to keep and render",
    )
    scan_parser.add_argument(
        "--market-cap-override",
        action="store_true",
        help="Prioritize the configured market-cap leader codes before filling the rest by score",
    )
    scan_parser.add_argument(
        "--due-only",
        action="store_true",
        help="Run only when the latest business-day 21:00 update is due or missed",
    )

    single_parser = subparsers.add_parser("single", help="Render a single-stock chart")
    single_parser.add_argument("--code", default="005930", help="Stock code")
    single_parser.add_argument("--pages", type=int, default=20, help="Number of provider daily pages to fetch")
    single_parser.add_argument(
        "--no-show-charts",
        action="store_true",
        help="Prepare the single-stock flow without opening the chart window",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Dispatch CLI commands. No arguments defaults to one-click daily scan."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "scan"):
        pages = getattr(args, "pages", 20)
        return run_daily_scan(
            pages=pages,
            workers=getattr(args, "workers", None),
            use_cache=not getattr(args, "no_cache", False),
            refresh_universe=getattr(args, "refresh_universe", False),
            render_charts=not getattr(args, "no_render_charts", False),
            top_n=getattr(args, "top_n", 5),
            use_market_cap_override=getattr(args, "market_cap_override", False),
            due_only=getattr(args, "due_only", False),
        )

    if args.command == "single":
        return run_single_stock(code=args.code, pages=args.pages, show_chart=not args.no_show_charts)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
