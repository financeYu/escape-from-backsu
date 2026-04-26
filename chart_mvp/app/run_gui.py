"""Local desktop GUI for browsing the Top-N stock list and charts."""

from __future__ import annotations

import sys
import threading
import traceback
import json
import math
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.utils import paths as _paths  # Ensure MPLCONFIGDIR is configured before matplotlib import.

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from stock_core.charts.matplotlib_renderer import plot_stock_data
from stock_core.cache.csv_cache import load_financial_statements
from stock_core.pipeline.daily_update import (
    MARKET_CAP_OVERRIDE_MESSAGE,
    get_daily_top5_due_status,
    load_latest_top5_snapshot,
    prepare_chart_dataframe,
    run_daily_top5_update,
)
from stock_core.utils.logging_utils import configure_logging


class Top5App:
    """Simple tkinter desktop app for the local Top-N workflow."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Configured Universe Top-N Viewer")
        self.root.geometry("1240x720")
        self.root.minsize(1020, 640)
        self.root.resizable(True, True)

        self.pages_var = tk.IntVar(value=1)
        self.top_n_var = tk.IntVar(value=5)
        self.use_cache_var = tk.BooleanVar(value=True)
        self.render_charts_var = tk.BooleanVar(value=False)
        self.refresh_universe_var = tk.BooleanVar(value=False)
        self.market_cap_override_var = tk.BooleanVar(value=False)
        self.fast_mode_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="대기 중")
        self.last_updated_var = tk.StringVar(value="마지막 갱신: 없음")
        self.auto_refresh_var = tk.BooleanVar(value=False)
        self.auto_refresh_minutes_var = tk.IntVar(value=30)
        self.progress_var = tk.DoubleVar(value=0.0)

        self._current_top5: list[dict] = []
        self._is_running = False
        self._auto_refresh_job: str | None = None

        self._build_ui()
        self._load_latest_results()
        self._load_latest_meta()
        self._run_startup_due_check()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        control_frame = ttk.LabelFrame(container, text="실행 설정", padding=10)
        control_frame.pack(fill=tk.X)

        ttk.Label(control_frame, text="페이지 수").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(control_frame, from_=1, to=50, textvariable=self.pages_var, width=6).grid(row=0, column=1, sticky="w", padx=(8, 18))
        ttk.Label(control_frame, text="Top N").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(control_frame, from_=1, to=50, textvariable=self.top_n_var, width=6).grid(row=0, column=3, sticky="w", padx=(8, 18))

        ttk.Checkbutton(control_frame, text="캐시 사용", variable=self.use_cache_var).grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Checkbutton(control_frame, text="빠른 갱신 모드", variable=self.fast_mode_var).grid(row=1, column=1, sticky="w", padx=(14, 0), pady=(10, 0))
        ttk.Checkbutton(control_frame, text="Top N 차트 파일 저장", variable=self.render_charts_var).grid(row=1, column=2, sticky="w", padx=(14, 0), pady=(10, 0))
        ttk.Checkbutton(control_frame, text="유니버스 새로고침 시도", variable=self.refresh_universe_var).grid(row=1, column=3, sticky="w", padx=(14, 0), pady=(10, 0))
        ttk.Checkbutton(control_frame, text="시총 고정 우선", variable=self.market_cap_override_var).grid(row=1, column=4, sticky="w", padx=(14, 0), pady=(10, 0))
        ttk.Checkbutton(
            control_frame,
            text="자동 새로고침",
            variable=self.auto_refresh_var,
            command=self._toggle_auto_refresh,
        ).grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Label(control_frame, text="간격(분)").grid(row=2, column=1, sticky="w", pady=(10, 0))
        ttk.Spinbox(control_frame, from_=1, to=180, textvariable=self.auto_refresh_minutes_var, width=6).grid(row=2, column=2, sticky="w", padx=(8, 18), pady=(10, 0))

        action_frame = ttk.Frame(container, padding=(0, 10, 0, 10))
        action_frame.pack(fill=tk.X)
        self.run_button = ttk.Button(action_frame, text="Top N 갱신 실행", command=self.run_update)
        self.run_button.pack(side=tk.LEFT)
        ttk.Button(action_frame, text="선택 종목 차트 보기", command=self.open_selected_chart).pack(side=tk.LEFT, padx=(8, 0))

        notice = ttk.Label(
            container,
            text=f"옵션 안내: {MARKET_CAP_OVERRIDE_MESSAGE}",
            foreground="#b45309",
        )
        if self.market_cap_override_var.get():
            notice.pack(fill=tk.X, pady=(0, 8))

        table_frame = ttk.LabelFrame(container, text="Top N 결과", padding=8)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("순위", "종목명", "점수", "최신일", "종가", "전일대비", "거래량")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        column_widths = {
            "순위": 60,
            "종목명": 300,
            "점수": 90,
            "최신일": 110,
            "종가": 140,
            "전일대비": 140,
            "거래량": 170,
        }
        for column in columns:
            self.tree.heading(column, text=column)
            self.tree.column(column, width=column_widths[column], minwidth=column_widths[column], anchor="center", stretch=True)

        y_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        x_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Double-1>", lambda _event: self.open_selected_chart())

        status_frame = ttk.Frame(container)
        status_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        ttk.Label(status_frame, textvariable=self.last_updated_var).pack(side=tk.RIGHT)

        progress_frame = ttk.Frame(container)
        progress_frame.pack(fill=tk.X, pady=(8, 0))
        self.progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, mode="determinate", variable=self.progress_var)
        self.progress.pack(fill=tk.X)

    def _load_latest_results(self) -> None:
        latest_df = load_latest_top5_snapshot()
        if latest_df.empty:
            self.set_status("대기 중 - 저장된 Top N 결과 없음")
            return

        self._fill_tree(latest_df.to_dict(orient="records"))
        self.set_status("저장된 latest_top 결과를 먼저 표시했습니다.")

    def _load_latest_meta(self) -> None:
        meta_path = PROJECT_ROOT / "outputs" / "last_run_meta.json"
        if not meta_path.exists():
            return

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return

        as_of = meta.get("as_of")
        if as_of:
            self.last_updated_var.set(f"마지막 갱신: {as_of}")

    def _run_startup_due_check(self) -> None:
        due_status = get_daily_top5_due_status()
        if not due_status.is_due:
            return
        self.set_status(f"{due_status.reason} 자동 갱신을 시작합니다.")
        self.root.after(500, self.run_update)

    def set_status(self, text: str) -> None:
        self.status_var.set(text)
        self.root.update_idletasks()

    def run_update(self) -> None:
        if self._is_running:
            return

        self._is_running = True
        self.run_button.state(["disabled"])
        self.set_status("배치 실행 중...")
        self.progress.configure(maximum=100)
        self.progress_var.set(0.0)

        worker = threading.Thread(target=self._run_update_worker, daemon=True)
        worker.start()

    def _run_update_worker(self) -> None:
        try:
            pages = 1 if self.fast_mode_var.get() else self.pages_var.get()
            worker_count = 8 if self.fast_mode_var.get() else 4
            top5_df, meta = run_daily_top5_update(
                pages=pages,
                use_cache=self.use_cache_var.get(),
                refresh_universe=self.refresh_universe_var.get(),
                render_charts=self.render_charts_var.get(),
                max_workers=worker_count,
                progress_callback=self._threadsafe_progress_update,
                top_n=self.top_n_var.get(),
                use_market_cap_override=self.market_cap_override_var.get(),
            )
            records = top5_df.to_dict(orient="records")
            self.root.after(0, lambda: self._finish_update(records, meta))
        except Exception as exc:
            error_text = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            self.root.after(0, lambda: self._fail_update(error_text))

    def _threadsafe_progress_update(self, completed: int, total: int, failed: int) -> None:
        self.root.after(0, lambda: self._update_progress(completed, total, failed))

    def _update_progress(self, completed: int, total: int, failed: int) -> None:
        self.progress.configure(maximum=max(total, 1))
        self.progress_var.set(completed)
        self.set_status(f"배치 실행 중... {completed}/{total} 완료, 실패 {failed}")

    def _finish_update(self, records: list[dict], meta: dict) -> None:
        self._current_top5 = records
        self._fill_tree(records)

        self._is_running = False
        self.run_button.state(["!disabled"])
        self.progress.configure(maximum=max(meta["processed_count"] + meta["failed_count"], 1))
        self.progress_var.set(meta["processed_count"] + meta["failed_count"])
        self.set_status(f"완료: {meta['processed_count']}건 처리, 실패 {meta['failed_count']}건, 작업자 {meta['max_workers']}개")
        self.last_updated_var.set(f"마지막 갱신: {meta.get('as_of', '알 수 없음')}")

        summary = (
            f"Top {meta.get('top_n', self.top_n_var.get())} 갱신 완료\n\n"
            f"처리: {meta['processed_count']} / {meta['universe_size']}\n"
            f"실패: {meta['failed_count']}\n"
            f"작업자 수: {meta['max_workers']}\n"
            f"CSV: {meta['output_csv']}\n"
            f"JSON: {meta['output_json']}"
        )
        if meta.get("market_cap_override"):
            summary += f"\n\n{meta.get('market_cap_override_message', '')}"
        messagebox.showinfo("배치 완료", summary)

    def _fail_update(self, error_text: str) -> None:
        self._is_running = False
        self.run_button.state(["!disabled"])
        self.set_status("실행 실패")
        messagebox.showerror("실행 실패", error_text)

    def _fill_tree(self, records: list[dict]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in records:
            code = str(row.get("종목코드", ""))
            iid = code or None
            self.tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(
                    row.get("순위", ""),
                    row.get("종목명", ""),
                    row.get("점수", ""),
                    row.get("최신일", ""),
                    self._format_plain_number(row.get("종가")),
                    self._format_signed_number(row.get("전일대비")),
                    self._format_plain_number(row.get("거래량")),
                ),
            )

    @staticmethod
    def _format_plain_number(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and math.isnan(value):
            return ""
        return f"{float(value):,.0f}"

    @staticmethod
    def _format_signed_number(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, float) and math.isnan(value):
            return ""

        numeric = float(value)
        if numeric > 0:
            return f"+{numeric:,.0f}"
        if numeric < 0:
            return f"{numeric:,.0f}"
        return "0"

    def open_selected_chart(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("선택 필요", "먼저 Top N 목록에서 종목을 선택해 주세요.")
            return

        item = self.tree.item(selection[0])
        values = item.get("values", [])
        if len(values) < 2:
            messagebox.showerror("오류", "선택한 종목 정보를 읽을 수 없습니다.")
            return

        code = str(selection[0])
        name = str(values[1])
        self.set_status(f"{name} 차트 준비 중...")
        self._open_chart_window(code=code, name=name)
        self.set_status(f"{name} 차트 표시 완료")

    def _open_chart_window(self, code: str, name: str) -> None:
        df = prepare_chart_dataframe(code=code, requested_pages=self.pages_var.get(), use_cache=self.use_cache_var.get())
        fig = plot_stock_data(df, stock_label=f"{name} ({code})", source_label="GUI 차트", show=False)

        window = tk.Toplevel(self.root)
        window.title(f"{name} ({code}) 차트")
        window.geometry("1320x900")

        notebook = ttk.Notebook(window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        chart_tab = ttk.Frame(notebook, padding=12)
        financial_tab = ttk.Frame(notebook, padding=12)
        notebook.add(chart_tab, text="차트")
        notebook.add(financial_tab, text="재무제표")

        canvas = FigureCanvasTkAgg(fig, master=chart_tab)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        canvas.draw()
        self._populate_financial_statement_tab(financial_tab, code=code, name=name)

        def _cleanup() -> None:
            try:
                plt.close(fig)
            finally:
                window.destroy()

        window.protocol("WM_DELETE_WINDOW", _cleanup)

    def _populate_financial_statement_tab(self, parent: ttk.Frame, code: str, name: str) -> None:
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(header, text=f"{name} ({code})", font=("", 14, "bold")).pack(anchor="w")
        ttk.Label(header, text="저장된 네이버 파이낸셜 재무제표 캐시입니다.").pack(anchor="w", pady=(4, 0))

        try:
            raw_frame = load_financial_statements(code)
        except FileNotFoundError:
            ttk.Label(parent, text="저장된 재무제표가 없습니다. 먼저 데이터를 새로고침해 주세요.").pack(anchor="w")
            return
        except Exception as exc:
            ttk.Label(parent, text=f"재무제표를 불러오지 못했습니다: {exc}").pack(anchor="w")
            return

        if raw_frame.empty:
            ttk.Label(parent, text="표시할 재무제표 데이터가 없습니다.").pack(anchor="w")
            return

        summary_frame = ttk.LabelFrame(parent, text="주요 지표", padding=12)
        summary_frame.pack(fill=tk.X, pady=(0, 12))
        self._render_financial_summary_cards(summary_frame, raw_frame)

        table_frame = ttk.LabelFrame(parent, text="재무제표 표", padding=8)
        table_frame.pack(fill=tk.BOTH, expand=True)
        self._render_financial_statement_table(table_frame, raw_frame)

    def _render_financial_summary_cards(self, parent: ttk.LabelFrame, raw_frame: pd.DataFrame) -> None:
        metric_aliases = [
            ("매출액", ("매출액",)),
            ("영업이익", ("영업이익",)),
            ("당기순이익", ("당기순이익", "순이익")),
            ("EPS", ("EPS",)),
            ("BPS", ("BPS",)),
            ("PER", ("PER",)),
            ("PBR", ("PBR",)),
            ("ROE", ("ROE",)),
        ]
        latest_period = self._resolve_latest_financial_period(raw_frame)
        shown_count = 0

        for label, aliases in metric_aliases:
            value = self._find_financial_metric_value(raw_frame, aliases, latest_period)
            if value is None:
                continue

            card = ttk.Frame(parent, padding=12)
            card.grid(row=shown_count // 4, column=shown_count % 4, sticky="nsew", padx=6, pady=6)
            ttk.Label(card, text=label).pack(anchor="w")
            ttk.Label(card, text=value, font=("", 16, "bold")).pack(anchor="w", pady=(6, 0))
            if latest_period:
                ttk.Label(card, text=latest_period).pack(anchor="w", pady=(6, 0))
            shown_count += 1

        for column in range(4):
            parent.columnconfigure(column, weight=1)

        if shown_count == 0:
            ttk.Label(parent, text="요약 카드로 보여줄 지표를 찾지 못했습니다. 아래 표를 확인해 주세요.").pack(anchor="w")

    def _render_financial_statement_table(self, parent: ttk.LabelFrame, raw_frame: pd.DataFrame) -> None:
        pivot = self._build_financial_statement_pivot(raw_frame)
        columns = list(pivot.columns)
        tree = ttk.Treeview(parent, columns=columns, show="headings")

        for column in columns:
            width = 180 if column == "metric" else 120
            heading = "항목" if column == "metric" else column
            tree.heading(column, text=heading)
            tree.column(column, width=width, minwidth=width, anchor="center")

        for _, row in pivot.iterrows():
            tree.insert("", tk.END, values=[row[column] for column in columns])

        y_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        x_scrollbar = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    @staticmethod
    def _build_financial_statement_pivot(raw_frame: pd.DataFrame) -> pd.DataFrame:
        ordered = raw_frame.loc[:, ["metric", "period", "value"]].copy()
        ordered = ordered[ordered["metric"].astype(str).str.strip() != ""]
        period_order = list(dict.fromkeys(ordered["period"].astype(str).tolist()))
        pivot = ordered.pivot_table(index="metric", columns="period", values="value", aggfunc="first", fill_value="")
        pivot = pivot.reindex(columns=period_order, fill_value="").reset_index()
        return pivot

    @staticmethod
    def _resolve_latest_financial_period(raw_frame: pd.DataFrame) -> str:
        periods = [period for period in raw_frame["period"].astype(str).tolist() if period]
        if not periods:
            return ""
        return periods[-1]

    @staticmethod
    def _find_financial_metric_value(raw_frame: pd.DataFrame, aliases: tuple[str, ...], period: str) -> str | None:
        metric_series = raw_frame["metric"].astype(str)
        matched = raw_frame[metric_series.apply(lambda metric: any(alias in metric for alias in aliases))]
        if matched.empty:
            return None
        if period:
            period_matched = matched[matched["period"].astype(str) == period]
            if not period_matched.empty:
                return str(period_matched.iloc[-1]["value"])
        return str(matched.iloc[-1]["value"])

    def _toggle_auto_refresh(self) -> None:
        if self.auto_refresh_var.get():
            self._schedule_auto_refresh()
            self.set_status("자동 새로고침이 활성화되었습니다.")
            return

        if self._auto_refresh_job is not None:
            self.root.after_cancel(self._auto_refresh_job)
            self._auto_refresh_job = None
        self.set_status("자동 새로고침이 비활성화되었습니다.")

    def _schedule_auto_refresh(self) -> None:
        if self._auto_refresh_job is not None:
            self.root.after_cancel(self._auto_refresh_job)
            self._auto_refresh_job = None

        interval_ms = max(self.auto_refresh_minutes_var.get(), 1) * 60 * 1000
        self._auto_refresh_job = self.root.after(interval_ms, self._auto_refresh_tick)

    def _auto_refresh_tick(self) -> None:
        self._auto_refresh_job = None

        if not self.auto_refresh_var.get():
            return

        if not self._is_running:
            self.run_update()

        self._schedule_auto_refresh()


def main() -> int:
    configure_logging()
    root = tk.Tk()
    app = Top5App(root)
    _ = app
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
