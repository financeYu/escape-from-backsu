"""Compatibility wrapper for the canonical CLI under ``chart_mvp/src``."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_IMPL_PATH = SRC_DIR / "app" / "cli.py"
_SPEC = importlib.util.spec_from_file_location("_chart_mvp_src_app_cli", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load CLI implementation from {_IMPL_PATH}")

_impl = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_impl)

run_daily_top5_update = _impl.run_daily_top5_update
run_daily_top5_update_if_due = _impl.run_daily_top5_update_if_due
fetch_stock_name = _impl.fetch_stock_name
refresh_stock_data = _impl.refresh_stock_data
get_cache_path = _impl.get_cache_path
plot_stock_data = _impl.plot_stock_data


def _sync_impl_hooks() -> None:
    _impl.run_daily_top5_update = run_daily_top5_update
    _impl.run_daily_top5_update_if_due = run_daily_top5_update_if_due
    _impl.fetch_stock_name = fetch_stock_name
    _impl.refresh_stock_data = refresh_stock_data
    _impl.get_cache_path = get_cache_path
    _impl.plot_stock_data = plot_stock_data


def run_single_stock(code: str, pages: int, show_chart: bool = True) -> int:
    _sync_impl_hooks()
    return _impl.run_single_stock(code=code, pages=pages, show_chart=show_chart)


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
    _sync_impl_hooks()
    return _impl.run_daily_scan(
        pages=pages,
        workers=workers,
        use_cache=use_cache,
        refresh_universe=refresh_universe,
        render_charts=render_charts,
        top_n=top_n,
        use_market_cap_override=use_market_cap_override,
        due_only=due_only,
    )


def build_parser():
    return _impl.build_parser()


def main(argv: list[str] | None = None) -> int:
    _sync_impl_hooks()
    return _impl.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
