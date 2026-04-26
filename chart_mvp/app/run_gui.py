"""Compatibility wrapper for the extracted ``gui_mvp`` chart GUI."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui_mvp.chart_topn import Top5App, main  # noqa: E402


__all__ = ("Top5App", "main")


if __name__ == "__main__":
    raise SystemExit(main())
