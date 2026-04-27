"""Command entrypoint for local GUI viewers."""

from __future__ import annotations

import sys


USAGE = "Usage: python -m gui_mvp [launcher|chart|backtest]"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    target = "launcher"
    if args:
        target = args[0].strip().lower()

    if target in {"-h", "--help", "help"}:
        print(USAGE)
        return 0

    if target in {"launcher", "home", "gui", "menu"}:
        from gui_mvp.launcher import main as launcher_main

        return launcher_main()
    if target in {"chart", "topn", "top-n"}:
        from gui_mvp.chart_topn import main as chart_main

        return chart_main()
    if target in {"backtest", "bt"}:
        from gui_mvp.backtest_viewer import main as backtest_main

        return backtest_main()

    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
