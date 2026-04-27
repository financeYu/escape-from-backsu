"""Evaluation-only backtest GUI helpers.

This module displays results from ``src.backtest``. It must not send realized
returns back into scoring, ranking, or report generation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
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

DEFAULT_BACKTEST_EXPORT_DIR = REPO_ROOT / "reports" / "backtest" / "generated" / "gui_mvp"
ALLOWED_REPO_EXPORT_ROOTS = (REPO_ROOT / "reports" / "backtest" / "generated",)

from src.backtest import (  # noqa: E402
    STEP17_BACKTEST_NOTICE,
    BacktestConfig,
    ConservativeBacktestResult,
    run_conservative_backtest,
)
from src.backtest.contracts import (  # noqa: E402
    ALLOWED_MISSING_PRICE_POLICIES,
    ALLOWED_PRICE_POLICIES,
    ALLOWED_REBALANCE_FREQUENCIES,
)


@dataclass(frozen=True)
class BacktestCsvSelection:
    """CSV paths selected by the GUI."""

    ranking_csv: Path
    price_csv: Path


def read_backtest_csv(path: str | Path) -> pd.DataFrame:
    """Read a backtest CSV while preserving six-digit ticker strings."""

    frame = pd.read_csv(path, dtype={"ticker": "string"})
    if "ticker" in frame.columns:
        frame = frame.copy()
        frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    return frame


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


def build_equity_curve(period_frame: pd.DataFrame) -> pd.DataFrame:
    """Build a display-only equity curve from period returns."""

    if period_frame.empty:
        return pd.DataFrame(columns=["decision_date", "period_return", "equity"])

    equity = 1.0
    rows: list[dict[str, object]] = []
    for _, row in period_frame.iterrows():
        period_return = row.get("backtest_period_return")
        if pd.isna(period_return):
            period_return = 0.0
        period_return = float(period_return)
        equity *= 1.0 + period_return
        rows.append(
            {
                "decision_date": row.get("decision_date"),
                "period_return": period_return,
                "equity": equity,
            }
        )
    return pd.DataFrame(rows)


def export_backtest_result_bundle(
    result: ConservativeBacktestResult,
    output_dir: str | Path,
    *,
    stem: str = "gui_mvp_backtest",
) -> dict[str, Path]:
    """Write generated evaluation-only result files to a local folder."""

    resolved = validate_backtest_export_dir(output_dir)
    resolved.mkdir(parents=True, exist_ok=True)
    period_frame = result.to_period_frame()
    security_frame = result.to_security_frame()
    equity_frame = build_equity_curve(period_frame)
    summary = result.to_summary_dict()
    summary["boundary_notice"] = str(result.metadata.get("boundary_notice", STEP17_BACKTEST_NOTICE))

    summary_path = resolved / f"{stem}_summary.json"
    period_path = resolved / f"{stem}_periods.csv"
    security_path = resolved / f"{stem}_securities.csv"
    equity_path = resolved / f"{stem}_equity.csv"

    summary_path.write_text(
        json.dumps(_json_ready(summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    period_frame.to_csv(period_path, index=False, encoding="utf-8-sig")
    security_frame.to_csv(security_path, index=False, encoding="utf-8-sig")
    equity_frame.to_csv(equity_path, index=False, encoding="utf-8-sig")
    return {
        "summary": summary_path,
        "periods": period_path,
        "securities": security_path,
        "equity": equity_path,
    }


def validate_backtest_export_dir(output_dir: str | Path) -> Path:
    """Return a safe export directory for generated backtest artifacts."""

    resolved = Path(output_dir).expanduser().resolve()
    repo_root = REPO_ROOT.resolve()
    if _is_relative_to(resolved, repo_root):
        allowed = tuple(path.resolve() for path in ALLOWED_REPO_EXPORT_ROOTS)
        if not any(_is_relative_to(resolved, root) for root in allowed):
            raise ValueError(
                "저장 위치가 저장소 내부라면 reports/backtest/generated/ 아래만 사용할 수 있습니다."
            )
    return resolved


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


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


def _json_ready(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value


class BacktestEvaluationApp:
    """Tkinter viewer for Step 17 conservative backtest evaluation results."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Conservative Backtest Viewer")
        self.root.geometry("1240x760")
        self.root.minsize(1040, 680)

        self.ranking_path_var = tk.StringVar(value="")
        self.price_path_var = tk.StringVar(value="")
        self.rebalance_frequency_var = tk.StringVar(value="every_ranking_date")
        self.top_n_var = tk.IntVar(value=20)
        self.holding_days_var = tk.IntVar(value=20)
        self.execution_lag_var = tk.IntVar(value=1)
        self.execution_price_policy_var = tk.StringVar(value="open")
        self.exit_price_policy_var = tk.StringVar(value="close")
        self.transaction_cost_var = tk.DoubleVar(value=10.0)
        self.slippage_var = tk.DoubleVar(value=5.0)
        self.missing_price_policy_var = tk.StringVar(value="flag_and_skip")
        self.status_var = tk.StringVar(value="대기 중")

        self._is_running = False
        self._last_result: ConservativeBacktestResult | None = None
        self._build_ui()

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

        ttk.Label(config_frame, text="리밸런싱").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            config_frame,
            textvariable=self.rebalance_frequency_var,
            values=sorted(ALLOWED_REBALANCE_FREQUENCIES),
            state="readonly",
            width=20,
        ).grid(row=0, column=1, sticky="w", padx=(8, 18))
        ttk.Label(config_frame, text="Top N").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(config_frame, from_=1, to=200, textvariable=self.top_n_var, width=8).grid(
            row=0,
            column=3,
            sticky="w",
            padx=(8, 18),
        )
        ttk.Label(config_frame, text="보유일").grid(row=0, column=4, sticky="w")
        ttk.Spinbox(config_frame, from_=1, to=252, textvariable=self.holding_days_var, width=8).grid(
            row=0,
            column=5,
            sticky="w",
            padx=(8, 18),
        )
        ttk.Label(config_frame, text="실행 지연일").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(config_frame, from_=0, to=20, textvariable=self.execution_lag_var, width=8).grid(
            row=1,
            column=1,
            sticky="w",
            padx=(8, 18),
            pady=(8, 0),
        )
        ttk.Label(config_frame, text="진입가격").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Combobox(
            config_frame,
            textvariable=self.execution_price_policy_var,
            values=sorted(ALLOWED_PRICE_POLICIES),
            state="readonly",
            width=8,
        ).grid(row=1, column=3, sticky="w", padx=(8, 18), pady=(8, 0))
        ttk.Label(config_frame, text="청산가격").grid(row=1, column=4, sticky="w", pady=(8, 0))
        ttk.Combobox(
            config_frame,
            textvariable=self.exit_price_policy_var,
            values=sorted(ALLOWED_PRICE_POLICIES),
            state="readonly",
            width=8,
        ).grid(row=1, column=5, sticky="w", padx=(8, 18), pady=(8, 0))
        ttk.Label(config_frame, text="거래비용 bps").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(
            config_frame,
            from_=0,
            to=500,
            increment=1,
            textvariable=self.transaction_cost_var,
            width=8,
        ).grid(row=2, column=1, sticky="w", padx=(8, 18), pady=(8, 0))
        ttk.Label(config_frame, text="슬리피지 bps").grid(row=2, column=2, sticky="w", pady=(8, 0))
        ttk.Spinbox(
            config_frame,
            from_=0,
            to=500,
            increment=1,
            textvariable=self.slippage_var,
            width=8,
        ).grid(row=2, column=3, sticky="w", padx=(8, 18), pady=(8, 0))
        ttk.Label(config_frame, text="가격 누락").grid(row=2, column=4, sticky="w", pady=(8, 0))
        ttk.Combobox(
            config_frame,
            textvariable=self.missing_price_policy_var,
            values=sorted(ALLOWED_MISSING_PRICE_POLICIES),
            state="readonly",
            width=16,
        ).grid(row=2, column=5, sticky="w", padx=(8, 18), pady=(8, 0))

        action_frame = ttk.Frame(container, padding=(0, 10, 0, 10))
        action_frame.pack(fill=tk.X)
        self.run_button = ttk.Button(action_frame, text="백테스트 평가 실행", command=self.run_evaluation)
        self.run_button.pack(side=tk.LEFT)
        self.export_button = ttk.Button(action_frame, text="결과 내보내기", command=self.export_results)
        self.export_button.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(action_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=(12, 0))

        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True)

        summary_tab = ttk.Frame(notebook, padding=8)
        period_tab = ttk.Frame(notebook, padding=8)
        security_tab = ttk.Frame(notebook, padding=8)
        equity_tab = ttk.Frame(notebook, padding=8)
        notebook.add(summary_tab, text="요약")
        notebook.add(period_tab, text="기간별")
        notebook.add(security_tab, text="종목별")
        notebook.add(equity_tab, text="Equity Curve")

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
        self.equity_canvas = tk.Canvas(equity_tab, background="white", highlightthickness=1)
        self.equity_canvas.pack(fill=tk.BOTH, expand=True)

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
            rebalance_frequency=self.rebalance_frequency_var.get(),
            top_n=self.top_n_var.get(),
            holding_period_days=self.holding_days_var.get(),
            execution_lag_days=self.execution_lag_var.get(),
            execution_price_policy=self.execution_price_policy_var.get(),
            exit_price_policy=self.exit_price_policy_var.get(),
            transaction_cost_bps=self.transaction_cost_var.get(),
            slippage_bps=self.slippage_var.get(),
            missing_price_policy=self.missing_price_policy_var.get(),
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
        self._last_result = result
        self._fill_summary_tree(result)
        period_frame = result.to_period_frame()
        self._fill_frame_tree(self.period_tree, period_frame)
        self._fill_frame_tree(self.security_tree, result.to_security_frame())
        self._draw_equity_curve(build_equity_curve(period_frame))

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

    def export_results(self) -> None:
        if self._last_result is None:
            messagebox.showinfo("결과 없음", "먼저 백테스트 평가를 실행해 주세요.")
            return
        DEFAULT_BACKTEST_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        selected = filedialog.askdirectory(
            title="결과 저장 폴더 선택",
            initialdir=str(DEFAULT_BACKTEST_EXPORT_DIR),
        )
        if not selected:
            return
        try:
            paths = export_backtest_result_bundle(self._last_result, selected)
        except Exception as exc:
            messagebox.showerror("내보내기 실패", str(exc))
            return
        joined = "\n".join(f"{key}: {path}" for key, path in paths.items())
        messagebox.showinfo("내보내기 완료", joined)

    def _draw_equity_curve(self, frame: pd.DataFrame) -> None:
        canvas = self.equity_canvas
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
        if frame.empty:
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
        denominator = max(len(values) - 1, 1)
        point_pairs = []
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
    app = BacktestEvaluationApp(root)
    _ = app
    root.mainloop()
    return 0


__all__ = (
    "BacktestCsvSelection",
    "BacktestEvaluationApp",
    "build_equity_curve",
    "export_backtest_result_bundle",
    "format_percent",
    "main",
    "read_backtest_csv",
    "run_backtest_from_csv",
    "run_backtest_from_frames",
    "summarize_backtest_result",
    "validate_backtest_export_dir",
)


if __name__ == "__main__":
    raise SystemExit(main())
