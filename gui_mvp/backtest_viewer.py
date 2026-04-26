"""Evaluation-only backtest GUI helpers.

This module displays results from ``Quant_mvp.backtest_mvp``. It must not send
realized returns back into scoring, ranking, or report generation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import traceback
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Quant_mvp.backtest_mvp import (  # noqa: E402
    STEP17_BACKTEST_NOTICE,
    BacktestConfig,
    ConservativeBacktestResult,
    run_conservative_backtest,
)


@dataclass(frozen=True)
class BacktestCsvSelection:
    """CSV paths selected by the GUI."""

    ranking_csv: Path
    price_csv: Path


def read_backtest_csv(path: str | Path) -> pd.DataFrame:
    """Read a backtest CSV while preserving six-digit ticker strings."""

    return pd.read_csv(path, dtype={"ticker": "string"})


def run_backtest_from_csv(
    selection: BacktestCsvSelection,
    *,
    config: BacktestConfig | Mapping[str, Any] | None = None,
) -> ConservativeBacktestResult:
    """Run the conservative backtest from GUI-selected CSV files."""

    ranking_frame = read_backtest_csv(selection.ranking_csv)
    price_frame = read_backtest_csv(selection.price_csv)
    return run_backtest_from_frames(ranking_frame, price_frame, config=config)


def run_backtest_from_frames(
    ranking_frame: pd.DataFrame,
    price_frame: pd.DataFrame,
    *,
    config: BacktestConfig | Mapping[str, Any] | None = None,
) -> ConservativeBacktestResult:
    """Run an evaluation-only backtest from in-memory frames."""

    return run_conservative_backtest(ranking_frame, price_frame, config=config)


def summarize_backtest_result(result: ConservativeBacktestResult) -> list[tuple[str, str]]:
    """Return stable display rows for a conservative backtest result."""

    summary = result.summary
    return [
        ("boundary_notice", str(result.metadata.get("boundary_notice", STEP17_BACKTEST_NOTICE))),
        ("period_count", str(summary.period_count)),
        ("selected_security_count", str(summary.selected_security_count)),
        ("valid_security_count", str(summary.valid_security_count)),
        ("skipped_security_count", str(summary.skipped_security_count)),
        ("mean_period_return", format_percent(summary.mean_period_return)),
        ("cumulative_return", format_percent(summary.cumulative_return)),
        ("average_turnover_proxy", format_percent(summary.average_turnover_proxy)),
        ("max_drawdown", format_percent(summary.max_drawdown)),
        ("limitation_flags", ", ".join(result.limitation_flags)),
    ]


def format_percent(value: object) -> str:
    """Format optional decimal returns for display."""

    if value is None or value is pd.NA:
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return ""
    if pd.isna(numeric):
        return ""
    return f"{numeric * 100:.2f}%"


class BacktestEvaluationFrame:
    """Tkinter viewer for Step 17 conservative backtest evaluation results."""

    def __init__(self, root: tk.Misc, *, configure_window: bool = True) -> None:
        self.root = root
        if configure_window:
            self._configure_window()

        self.ranking_path_var = tk.StringVar(value="")
        self.price_path_var = tk.StringVar(value="")
        self.top_n_var = tk.IntVar(value=20)
        self.holding_days_var = tk.IntVar(value=20)
        self.execution_lag_var = tk.IntVar(value=1)
        self.transaction_cost_var = tk.DoubleVar(value=10.0)
        self.slippage_var = tk.DoubleVar(value=5.0)
        self.status_var = tk.StringVar(value="대기 중")

        self._is_running = False
        self._build_ui()

    def _configure_window(self) -> None:
        if not isinstance(self.root, (tk.Tk, tk.Toplevel)):
            return
        self.root.title("Conservative Backtest Viewer")
        self.root.geometry("1240x760")
        self.root.minsize(1040, 680)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        input_frame = ttk.LabelFrame(container, text="입력 CSV", padding=10)
        input_frame.pack(fill=tk.X)
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="랭킹 CSV").grid(row=0, column=0, sticky="w")
        ttk.Entry(input_frame, textvariable=self.ranking_path_var).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(8, 8),
        )
        ttk.Button(input_frame, text="찾기", command=self._browse_ranking_csv).grid(row=0, column=2)

        ttk.Label(input_frame, text="가격 CSV").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(input_frame, textvariable=self.price_path_var).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(8, 8),
            pady=(8, 0),
        )
        ttk.Button(input_frame, text="찾기", command=self._browse_price_csv).grid(row=1, column=2, pady=(8, 0))

        config_frame = ttk.LabelFrame(container, text="평가 설정", padding=10)
        config_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(config_frame, text="Top N").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(config_frame, from_=1, to=200, textvariable=self.top_n_var, width=8).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(8, 18),
        )
        ttk.Label(config_frame, text="보유일").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(config_frame, from_=1, to=252, textvariable=self.holding_days_var, width=8).grid(
            row=0,
            column=3,
            sticky="w",
            padx=(8, 18),
        )
        ttk.Label(config_frame, text="실행 지연일").grid(row=0, column=4, sticky="w")
        ttk.Spinbox(config_frame, from_=0, to=20, textvariable=self.execution_lag_var, width=8).grid(
            row=0,
            column=5,
            sticky="w",
            padx=(8, 18),
        )
        ttk.Label(config_frame, text="거래비용 bps").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(
            config_frame,
            from_=0,
            to=500,
            increment=1,
            textvariable=self.transaction_cost_var,
            width=8,
        ).grid(row=1, column=1, sticky="w", padx=(8, 18), pady=(8, 0))
        ttk.Label(config_frame, text="슬리피지 bps").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Spinbox(
            config_frame,
            from_=0,
            to=500,
            increment=1,
            textvariable=self.slippage_var,
            width=8,
        ).grid(row=1, column=3, sticky="w", padx=(8, 18), pady=(8, 0))

        action_frame = ttk.Frame(container, padding=(0, 10, 0, 10))
        action_frame.pack(fill=tk.X)
        self.run_button = ttk.Button(action_frame, text="백테스트 평가 실행", command=self.run_evaluation)
        self.run_button.pack(side=tk.LEFT)
        ttk.Label(action_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=(12, 0))

        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True)

        summary_tab = ttk.Frame(notebook, padding=8)
        period_tab = ttk.Frame(notebook, padding=8)
        security_tab = ttk.Frame(notebook, padding=8)
        notebook.add(summary_tab, text="요약")
        notebook.add(period_tab, text="기간별")
        notebook.add(security_tab, text="종목별")

        self.summary_tree = self._build_tree(summary_tab, ("항목", "값"), {"항목": 260, "값": 760})
        self.period_tree = self._build_tree(
            period_tab,
            (
                "decision_date",
                "selected_security_count",
                "valid_security_count",
                "skipped_security_count",
                "backtest_period_return",
                "limitation_flags",
            ),
            {
                "decision_date": 130,
                "selected_security_count": 160,
                "valid_security_count": 150,
                "skipped_security_count": 160,
                "backtest_period_return": 170,
                "limitation_flags": 360,
            },
        )
        self.security_tree = self._build_tree(
            security_tab,
            (
                "decision_date",
                "ticker",
                "upstream_rank",
                "selected",
                "skipped",
                "execution_date",
                "exit_date",
                "realized_holding_return",
                "evaluation_return",
                "limitation_flags",
            ),
            {
                "decision_date": 120,
                "ticker": 100,
                "upstream_rank": 110,
                "selected": 90,
                "skipped": 90,
                "execution_date": 120,
                "exit_date": 120,
                "realized_holding_return": 170,
                "evaluation_return": 150,
                "limitation_flags": 300,
            },
        )

    def _build_tree(
        self,
        parent: ttk.Frame,
        columns: tuple[str, ...],
        widths: Mapping[str, int],
    ) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=columns, show="headings")
        for column in columns:
            tree.heading(column, text=column)
            tree.column(column, width=widths[column], minwidth=min(widths[column], 120), anchor="center")
        y_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        x_scrollbar = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return tree

    def _browse_ranking_csv(self) -> None:
        path = filedialog.askopenfilename(title="랭킹 CSV 선택", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            self.ranking_path_var.set(path)

    def _browse_price_csv(self) -> None:
        path = filedialog.askopenfilename(title="가격 CSV 선택", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            self.price_path_var.set(path)

    def _resolve_config(self) -> BacktestConfig:
        return BacktestConfig(
            top_n=self.top_n_var.get(),
            holding_period_days=self.holding_days_var.get(),
            execution_lag_days=self.execution_lag_var.get(),
            transaction_cost_bps=self.transaction_cost_var.get(),
            slippage_bps=self.slippage_var.get(),
        )

    def run_evaluation(self) -> None:
        if self._is_running:
            return
        ranking_path = self.ranking_path_var.get().strip()
        price_path = self.price_path_var.get().strip()
        if not ranking_path or not price_path:
            messagebox.showinfo("입력 필요", "랭킹 CSV와 가격 CSV를 모두 선택해 주세요.")
            return

        self._is_running = True
        self.run_button.state(["disabled"])
        self.status_var.set("평가 실행 중...")

        selection = BacktestCsvSelection(Path(ranking_path), Path(price_path))
        config = self._resolve_config()
        worker = threading.Thread(
            target=self._run_evaluation_worker,
            args=(selection, config),
            daemon=True,
        )
        worker.start()

    def _run_evaluation_worker(
        self,
        selection: BacktestCsvSelection,
        config: BacktestConfig,
    ) -> None:
        try:
            result = run_backtest_from_csv(selection, config=config)
            self.root.after(0, lambda: self._finish_evaluation(result))
        except Exception as exc:
            error_text = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            self.root.after(0, lambda: self._fail_evaluation(error_text))

    def _finish_evaluation(self, result: ConservativeBacktestResult) -> None:
        self._fill_summary_tree(result)
        self._fill_frame_tree(self.period_tree, result.to_period_frame())
        self._fill_frame_tree(self.security_tree, result.to_security_frame())

        self._is_running = False
        self.run_button.state(["!disabled"])
        self.status_var.set("평가 완료")

    def _fail_evaluation(self, error_text: str) -> None:
        self._is_running = False
        self.run_button.state(["!disabled"])
        self.status_var.set("평가 실패")
        messagebox.showerror("평가 실패", error_text)

    def _fill_summary_tree(self, result: ConservativeBacktestResult) -> None:
        self._clear_tree(self.summary_tree)
        for label, value in summarize_backtest_result(result):
            self.summary_tree.insert("", tk.END, values=(label, value))

    def _fill_frame_tree(self, tree: ttk.Treeview, frame: pd.DataFrame) -> None:
        self._clear_tree(tree)
        if frame.empty:
            return
        columns = tuple(tree["columns"])
        for _, row in frame.iterrows():
            tree.insert("", tk.END, values=[self._format_cell(column, row.get(column)) for column in columns])

    @staticmethod
    def _clear_tree(tree: ttk.Treeview) -> None:
        for item in tree.get_children():
            tree.delete(item)

    @staticmethod
    def _format_cell(column: str, value: object) -> str:
        if isinstance(value, tuple):
            return ", ".join(str(item) for item in value)
        if "return" in column:
            return format_percent(value)
        if value is None or value is pd.NA:
            return ""
        return str(value)


def main() -> int:
    root = tk.Tk()
    app = BacktestEvaluationFrame(root)
    _ = app
    root.mainloop()
    return 0


BacktestEvaluationApp = BacktestEvaluationFrame

__all__ = (
    "BacktestCsvSelection",
    "BacktestEvaluationApp",
    "BacktestEvaluationFrame",
    "format_percent",
    "main",
    "read_backtest_csv",
    "run_backtest_from_csv",
    "run_backtest_from_frames",
    "summarize_backtest_result",
)


if __name__ == "__main__":
    raise SystemExit(main())
