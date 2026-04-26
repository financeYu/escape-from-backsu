"""Command entrypoint for local GUI viewers."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    target = "unified"
    if args:
        target = args[0].strip().lower()

    if target in {"unified", "gui", "tabs"}:
        from gui_mvp.unified_app import main as unified_main

        return unified_main()
    if target in {"chart", "topn", "top-n"}:
        from gui_mvp.chart_topn import main as chart_main

        return chart_main()

    print("Usage: python -m gui_mvp [unified|chart]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
