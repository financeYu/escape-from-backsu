"""Unified local GUI for current chart viewing and backtest evaluation."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from gui_mvp.backtest_viewer import BacktestEvaluationFrame
from gui_mvp.chart_topn import Top5App


class UnifiedGuiApp:
    """Top-level tabbed GUI owned by ``gui_mvp``."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("GUI MVP")
        self.root.geometry("1280x780")
        self.root.minsize(1040, 680)

        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True)

        current_price_tab = ttk.Frame(notebook)
        backtest_tab = ttk.Frame(notebook)
        notebook.add(current_price_tab, text="현재 주가 기준")
        notebook.add(backtest_tab, text="백테스트 전용")

        self.chart_app = Top5App(
            current_price_tab,
            configure_window=False,
            startup_due_check=False,
        )
        self.backtest_app = BacktestEvaluationFrame(backtest_tab, configure_window=False)


def main() -> int:
    root = tk.Tk()
    app = UnifiedGuiApp(root)
    _ = app
    root.mainloop()
    return 0


__all__ = ("UnifiedGuiApp", "main")


if __name__ == "__main__":
    raise SystemExit(main())
