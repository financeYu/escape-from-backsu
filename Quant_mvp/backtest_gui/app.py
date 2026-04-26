"""Tkinter GUI for local evaluation-only backtest runs."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

import pandas as pd

from Quant_mvp.backtest_mvp import BacktestConfig
from Quant_mvp.backtest_mvp.contracts import (
    ALLOWED_MISSING_PRICE_POLICIES,
    ALLOWED_PRICE_POLICIES,
    ALLOWED_REBALANCE_FREQUENCIES,
)
from Quant_mvp.backtest_gui.service import (
    BacktestInputPaths,
    BacktestRunArtifacts,
    BacktestRunRequest,
    EVALUATION_ONLY_NOTICE,
    export_result_bundle,
    run_backtest_from_csv,
)


class BacktestGuiApp(tk.Tk):
    """Local GUI shell that delegates calculations to `Quant_mvp.backtest_mvp`."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Quant Backtest GUI")
        self.geometry("1180x760")
        self.minsize(980, 620)
        self.artifacts: BacktestRunArtifacts | None = None

        self.ranking_path = tk.StringVar()
        self.price_path = tk.StringVar()
        self.status_text = tk.StringVar(value="CSV를 선택한 뒤 백테스트를 실행하세요.")
        self.notice_text = tk.StringVar(value=EVALUATION_ONLY_NOTICE)

        self.rebalance_frequency = tk.StringVar(value="every_ranking_date")
        self.holding_period_days = tk.IntVar(value=20)
        self.top_n = tk.IntVar(value=20)
        self.execution_lag_days = tk.IntVar(value=1)
        self.execution_price_policy = tk.StringVar(value="open")
        self.exit_price_policy = tk.StringVar(value="close")
        self.transaction_cost_bps = tk.DoubleVar(value=10.0)
        self.slippage_bps = tk.DoubleVar(value=5.0)
        self.missing_price_policy = tk.StringVar(value="flag_and_skip")

        self._build_layout()

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        input_frame = ttk.LabelFrame(self, text="입력 CSV")
        input_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="Ranking").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(input_frame, textvariable=self.ranking_path).grid(
            row=0, column=1, sticky="ew", padx=4, pady=6
        )
        ttk.Button(input_frame, text="선택", command=self._pick_ranking).grid(
            row=0, column=2, padx=8, pady=6
        )
        ttk.Label(input_frame, text="OHLCV").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(input_frame, textvariable=self.price_path).grid(
            row=1, column=1, sticky="ew", padx=4, pady=6
        )
        ttk.Button(input_frame, text="선택", command=self._pick_prices).grid(
            row=1, column=2, padx=8, pady=6
        )

        controls = ttk.LabelFrame(self, text="백테스트 파라미터")
        controls.grid(row=1, column=0, sticky="ew", padx=10, pady=6)
        for index in range(8):
            controls.columnconfigure(index, weight=1)

        self._combo(
            controls,
            "Rebalance",
            self.rebalance_frequency,
            sorted(ALLOWED_REBALANCE_FREQUENCIES),
            0,
            0,
        )
        self._spin(controls, "Holding days", self.holding_period_days, 1, 252, 0, 2)
        self._spin(controls, "Top N", self.top_n, 1, 200, 0, 4)
        self._spin(controls, "Lag days", self.execution_lag_days, 0, 20, 0, 6)
        self._combo(
            controls,
            "Entry price",
            self.execution_price_policy,
            sorted(ALLOWED_PRICE_POLICIES),
            1,
            0,
        )
        self._combo(
            controls,
            "Exit price",
            self.exit_price_policy,
            sorted(ALLOWED_PRICE_POLICIES),
            1,
            2,
        )
        self._float_spin(controls, "Cost bps", self.transaction_cost_bps, 0, 500, 1, 4)
        self._float_spin(controls, "Slip bps", self.slippage_bps, 0, 500, 1, 6)
        self._combo(
            controls,
            "Missing price",
            self.missing_price_policy,
            sorted(ALLOWED_MISSING_PRICE_POLICIES),
            2,
            0,
        )

        actions = ttk.Frame(self)
        actions.grid(row=2, column=0, sticky="ew", padx=10, pady=6)
        actions.columnconfigure(2, weight=1)
        ttk.Button(actions, text="백테스트 실행", command=self._run_backtest).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(actions, text="결과 내보내기", command=self._export_results).grid(
            row=0, column=1, padx=(0, 8)
        )
        ttk.Label(actions, textvariable=self.status_text).grid(row=0, column=2, sticky="w")

        notebook = ttk.Notebook(self)
        notebook.grid(row=3, column=0, sticky="nsew", padx=10, pady=6)
        self.summary_tree = self._tree_tab(notebook, "Summary", ("field", "value"))
        self.period_tree = self._tree_tab(
            notebook,
            "Periods",
            (
                "decision_date",
                "selected_security_count",
                "valid_security_count",
                "skipped_security_count",
                "backtest_period_return",
            ),
        )
        self.security_tree = self._tree_tab(
            notebook,
            "Securities",
            (
                "ticker",
                "decision_date",
                "upstream_rank",
                "selected",
                "skipped",
                "realized_holding_return",
                "execution_date",
                "exit_date",
            ),
        )
        curve_frame = ttk.Frame(notebook)
        curve_frame.rowconfigure(0, weight=1)
        curve_frame.columnconfigure(0, weight=1)
        self.curve_canvas = tk.Canvas(curve_frame, background="white", highlightthickness=1)
        self.curve_canvas.grid(row=0, column=0, sticky="nsew")
        notebook.add(curve_frame, text="Equity Curve")

        notice = ttk.Label(self, textvariable=self.notice_text, anchor="w")
        notice.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))

    def _combo(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        values: list[str],
        row: int,
        column: int,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=8, pady=6)
        ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=20).grid(
            row=row, column=column + 1, sticky="ew", padx=4, pady=6
        )

    def _spin(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.IntVar,
        from_: int,
        to: int,
        row: int,
        column: int,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=8, pady=6)
        ttk.Spinbox(parent, textvariable=variable, from_=from_, to=to, width=8).grid(
            row=row, column=column + 1, sticky="ew", padx=4, pady=6
        )

    def _float_spin(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.DoubleVar,
        from_: float,
        to: float,
        row: int,
        column: int,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=8, pady=6)
        ttk.Spinbox(
            parent,
            textvariable=variable,
            from_=from_,
            to=to,
            increment=1.0,
            width=8,
        ).grid(row=row, column=column + 1, sticky="ew", padx=4, pady=6)

    def _tree_tab(self, notebook: ttk.Notebook, title: str, columns: tuple[str, ...]) -> ttk.Treeview:
        frame = ttk.Frame(notebook)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for column in columns:
            tree.heading(column, text=column)
            tree.column(column, width=160, anchor="w")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        notebook.add(frame, text=title)
        return tree

    def _pick_ranking(self) -> None:
        self._pick_csv(self.ranking_path)

    def _pick_prices(self) -> None:
        self._pick_csv(self.price_path)

    def _pick_csv(self, variable: tk.StringVar) -> None:
        selected = filedialog.askopenfilename(
            title="CSV 선택",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if selected:
            variable.set(selected)

    def _config_from_controls(self) -> BacktestConfig:
        return BacktestConfig(
            rebalance_frequency=self.rebalance_frequency.get(),
            holding_period_days=int(self.holding_period_days.get()),
            top_n=int(self.top_n.get()),
            execution_lag_days=int(self.execution_lag_days.get()),
            execution_price_policy=self.execution_price_policy.get(),
            exit_price_policy=self.exit_price_policy.get(),
            transaction_cost_bps=float(self.transaction_cost_bps.get()),
            slippage_bps=float(self.slippage_bps.get()),
            missing_price_policy=self.missing_price_policy.get(),
        )

    def _run_backtest(self) -> None:
        try:
            if not self.ranking_path.get() or not self.price_path.get():
                raise ValueError("Ranking CSV와 OHLCV CSV를 모두 선택해야 합니다.")
            request = BacktestRunRequest(
                inputs=BacktestInputPaths(
                    ranking_csv=Path(self.ranking_path.get()),
                    price_csv=Path(self.price_path.get()),
                ),
                config=self._config_from_controls(),
            )
            self.status_text.set("실행 중...")
            self.update_idletasks()
            self.artifacts = run_backtest_from_csv(request)
            self._render_artifacts(self.artifacts)
            period_count = self.artifacts.summary.get("period_count", 0)
            self.status_text.set(f"완료: {period_count}개 기간 평가 결과를 표시했습니다.")
        except Exception as exc:  # pragma: no cover - Tkinter event boundary
            self.status_text.set("실패")
            messagebox.showerror("백테스트 실행 실패", str(exc))

    def _export_results(self) -> None:
        if self.artifacts is None:
            messagebox.showinfo("결과 없음", "먼저 백테스트를 실행하세요.")
            return
        selected = filedialog.askdirectory(title="결과 저장 폴더 선택")
        if not selected:
            return
        try:
            paths = export_result_bundle(self.artifacts, selected)
            joined = "\n".join(f"{key}: {path}" for key, path in paths.items())
            messagebox.showinfo("내보내기 완료", joined)
        except Exception as exc:  # pragma: no cover - Tkinter event boundary
            messagebox.showerror("내보내기 실패", str(exc))

    def _render_artifacts(self, artifacts: BacktestRunArtifacts) -> None:
        self._clear_tree(self.summary_tree)
        for key, value in artifacts.summary.items():
            self.summary_tree.insert("", "end", values=(key, self._display_value(value)))
        self._frame_to_tree(self.period_tree, artifacts.period_frame)
        self._frame_to_tree(self.security_tree, artifacts.security_frame)
        self._draw_equity_curve(artifacts.equity_frame)

    def _frame_to_tree(self, tree: ttk.Treeview, frame: pd.DataFrame) -> None:
        self._clear_tree(tree)
        columns = tree["columns"]
        for _, row in frame.iterrows():
            tree.insert("", "end", values=tuple(self._display_value(row.get(column)) for column in columns))

    def _clear_tree(self, tree: ttk.Treeview) -> None:
        for item in tree.get_children():
            tree.delete(item)

    def _draw_equity_curve(self, frame: pd.DataFrame) -> None:
        canvas = self.curve_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 600)
        height = max(canvas.winfo_height(), 300)
        padding = 42
        canvas.create_text(
            padding,
            18,
            anchor="w",
            text="Equity curve is display-only backtest output.",
            fill="#333333",
        )
        if frame.empty or len(frame) < 1:
            canvas.create_text(width / 2, height / 2, text="표시할 결과가 없습니다.", fill="#666666")
            return
        values = frame["equity"].astype(float).tolist()
        minimum = min(values)
        maximum = max(values)
        if minimum == maximum:
            minimum -= 0.01
            maximum += 0.01
        usable_width = width - (padding * 2)
        usable_height = height - (padding * 2)
        point_pairs: list[tuple[float, float]] = []
        denominator = max(len(values) - 1, 1)
        for index, value in enumerate(values):
            x = padding + usable_width * (index / denominator)
            y = height - padding - usable_height * ((value - minimum) / (maximum - minimum))
            point_pairs.append((x, y))
        canvas.create_line(padding, height - padding, width - padding, height - padding, fill="#cccccc")
        canvas.create_line(padding, padding, padding, height - padding, fill="#cccccc")
        if len(point_pairs) >= 2:
            points = [coordinate for point in point_pairs for coordinate in point]
            canvas.create_line(*points, fill="#1f77b4", width=2)
        else:
            for x, y in point_pairs[:1]:
                canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#1f77b4")
        canvas.create_text(padding, padding - 10, anchor="w", text=f"max {maximum:.4f}", fill="#555555")
        canvas.create_text(padding, height - padding + 16, anchor="w", text=f"min {minimum:.4f}", fill="#555555")

    def _display_value(self, value: Any) -> str:
        if isinstance(value, float):
            return f"{value:.6f}"
        if isinstance(value, (tuple, list)):
            return ", ".join(str(item) for item in value)
        if pd.isna(value) if value is not None and not isinstance(value, (tuple, list, dict)) else False:
            return ""
        return str(value)


def main() -> None:
    app = BacktestGuiApp()
    app.mainloop()


if __name__ == "__main__":
    main()
