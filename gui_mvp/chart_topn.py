"""Desktop chart GUI extracted from ``chart_mvp``.

The GUI remains a local runtime viewer. It does not promote chart runtime
outputs to canonical ranking evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import traceback

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
CHART_MVP_ROOT = REPO_ROOT / "chart_mvp"
CHART_SRC_DIR = CHART_MVP_ROOT / "src"

for path in (REPO_ROOT, CHART_SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from stock_core.utils import paths as _paths  # Ensure MPLCONFIGDIR before matplotlib import.

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from stock_core.cache.csv_cache import load_financial_statements
from stock_core.charts.matplotlib_renderer import plot_stock_data
from stock_core.pipeline.daily_update import (
    MARKET_CAP_OVERRIDE_MESSAGE,
    get_daily_top5_due_status,
    load_latest_algorithm_ranking_snapshot,
    load_latest_top5_snapshot,
    prepare_chart_dataframe,
    run_daily_top5_update,
)
from stock_core.providers.naver_price_provider import get_price_df
from stock_core.utils.constants import CLOSE_COLUMN, DATE_COLUMN, PREV_DIFF_COLUMN, VOLUME_COLUMN
from stock_core.utils.logging_utils import configure_logging

from src.composite.contracts import DEFAULT_COMPOSITE_INPUT_REGISTRY
from src.scanner.latest_ranking import build_latest_ranking_output
from src.scores import calculate_all_raw_scores, normalize_cross_sectional_scores
from src.selection.adoption_synthesis_contracts import Step14AdoptionState


TECHNICAL_INDICATORS_PATH = REPO_ROOT / "data" / "processed" / "technical_indicators.csv"
LATEST_SCORE_TOP_CSV_PATH = CHART_MVP_ROOT / "outputs" / "latest_score_top.csv"
LATEST_SCORE_TOP_JSON_PATH = CHART_MVP_ROOT / "outputs" / "latest_score_top.json"
LATEST_SCORE_TOP_META_PATH = CHART_MVP_ROOT / "outputs" / "latest_score_top_meta.json"
TOPN_TECHNICAL_ONLY_NOTICE = (
    "KOSPI200 기술지표 전용 Top N 표시입니다. 점수·랭킹은 재무/밸류에이션 "
    "데이터를 반영하지 않습니다."
)
FINANCIAL_DISPLAY_NOTICE = (
    "재무/밸류에이션 캐시 표시 전용입니다. candidate-only이며 Top N 점수·랭킹에 "
    "반영되지 않습니다."
)


class Top5App:
    """Tkinter app for the local Top-N chart workflow."""

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
        ttk.Spinbox(control_frame, from_=1, to=50, textvariable=self.pages_var, width=6).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(8, 18),
        )
        ttk.Label(control_frame, text="Top N").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(control_frame, from_=1, to=50, textvariable=self.top_n_var, width=6).grid(
            row=0,
            column=3,
            sticky="w",
            padx=(8, 18),
        )

        ttk.Checkbutton(control_frame, text="캐시 사용", variable=self.use_cache_var).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(10, 0),
        )
        ttk.Checkbutton(control_frame, text="빠른 갱신 모드", variable=self.fast_mode_var).grid(
            row=1,
            column=1,
            sticky="w",
            padx=(14, 0),
            pady=(10, 0),
        )
        ttk.Checkbutton(
            control_frame,
            text="Top N 차트 파일 저장",
            variable=self.render_charts_var,
        ).grid(row=1, column=2, sticky="w", padx=(14, 0), pady=(10, 0))
        ttk.Checkbutton(
            control_frame,
            text="유니버스 새로고침 시도",
            variable=self.refresh_universe_var,
        ).grid(row=1, column=3, sticky="w", padx=(14, 0), pady=(10, 0))
        ttk.Checkbutton(
            control_frame,
            text="시총 고정 우선",
            variable=self.market_cap_override_var,
        ).grid(row=1, column=4, sticky="w", padx=(14, 0), pady=(10, 0))
        ttk.Checkbutton(
            control_frame,
            text="자동 새로고침",
            variable=self.auto_refresh_var,
            command=self._toggle_auto_refresh,
        ).grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Label(control_frame, text="간격(분)").grid(row=2, column=1, sticky="w", pady=(10, 0))
        ttk.Spinbox(
            control_frame,
            from_=1,
            to=180,
            textvariable=self.auto_refresh_minutes_var,
            width=6,
        ).grid(row=2, column=2, sticky="w", padx=(8, 18), pady=(10, 0))

        action_frame = ttk.Frame(container, padding=(0, 10, 0, 10))
        action_frame.pack(fill=tk.X)
        self.run_button = ttk.Button(action_frame, text="Top N 갱신 실행", command=self.run_update)
        self.run_button.pack(side=tk.LEFT)
        ttk.Button(action_frame, text="선택 종목 차트 보기", command=self.open_selected_chart).pack(
            side=tk.LEFT,
            padx=(8, 0),
        )

        notice = ttk.Label(
            container,
            text=f"옵션 안내: {MARKET_CAP_OVERRIDE_MESSAGE}",
            foreground="#b45309",
        )
        if self.market_cap_override_var.get():
            notice.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(container, text=TOPN_TECHNICAL_ONLY_NOTICE, foreground="#92400e").pack(
            fill=tk.X,
            pady=(0, 8),
        )

        table_frame = ttk.LabelFrame(container, text="Top N 기술지표 표시", padding=8)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("순위", "종목코드", "종목명", "점수", "최신일", "유효성", "종가", "전일대비", "거래량")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        column_widths = {
            "순위": 60,
            "종목코드": 95,
            "종목명": 240,
            "점수": 110,
            "최신일": 110,
            "유효성": 90,
            "종가": 120,
            "전일대비": 120,
            "거래량": 150,
        }
        for column in columns:
            heading = "기술점수" if column == "점수" else column
            self.tree.heading(column, text=heading)
            self.tree.column(
                column,
                width=column_widths[column],
                minwidth=column_widths[column],
                anchor="center",
                stretch=True,
            )

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
        self.progress = ttk.Progressbar(
            progress_frame,
            orient=tk.HORIZONTAL,
            mode="determinate",
            variable=self.progress_var,
        )
        self.progress.pack(fill=tk.X)

    def _load_latest_results(self) -> None:
        latest_df = load_latest_top5_snapshot()
        if latest_df.empty:
            self.set_status("대기 중 - 저장된 Top N 기술지표 표시 없음")
            return

        records = latest_df.to_dict(orient="records")
        self._fill_tree(records)
        if self._is_algorithm_snapshot(latest_df):
            self.set_status("저장된 알고리즘 랭킹 결과를 먼저 표시했습니다.")
        else:
            self.set_status("저장된 latest_top 결과를 먼저 표시했습니다.")

    def _load_latest_meta(self) -> None:
        meta_path = CHART_MVP_ROOT / "outputs" / "last_run_meta.json"
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

        if self._refresh_from_algorithm_snapshot():
            return

        self.set_status("알고리즘 랭킹 스냅샷 없음")
        messagebox.showwarning(
            "갱신 불가",
            "점수 기반 latest_score_top.csv 또는 reports/selection/latest_ranking.csv가 없어 Top N을 갱신할 수 없습니다.\n"
            "0점 placeholder 경로는 실행하지 않았습니다.",
        )

    def _refresh_from_algorithm_snapshot(self) -> bool:
        top_n = self.top_n_var.get()
        latest_df = load_latest_algorithm_ranking_snapshot()
        if self._should_rebuild_algorithm_snapshot(latest_df, top_n=top_n):
            latest_df = self._rebuild_algorithm_snapshot(top_n=top_n)
        if latest_df.empty:
            return False

        records = latest_df.head(top_n).to_dict(orient="records")
        records = self._enrich_records_with_latest_prices(records)
        self._fill_tree(records)
        latest_date = self._latest_display_date(records)
        if latest_date:
            self.last_updated_var.set(f"마지막 갱신: {latest_date}")
        self.progress.configure(maximum=max(len(records), 1))
        self.progress_var.set(len(records))
        score_date = self._latest_score_date(records)
        if score_date and latest_date and score_date != latest_date:
            self.set_status(f"점수 기반 Top {top_n} 갱신 완료 (점수 {score_date}, 가격 {latest_date})")
        else:
            self.set_status(f"점수 기반 Top {top_n} 갱신 완료")
        return True

    @staticmethod
    def _should_rebuild_algorithm_snapshot(latest_df: pd.DataFrame, *, top_n: int) -> bool:
        if latest_df.empty or len(latest_df) < top_n:
            return True
        if not TECHNICAL_INDICATORS_PATH.exists() or not LATEST_SCORE_TOP_CSV_PATH.exists():
            return False
        try:
            if TECHNICAL_INDICATORS_PATH.stat().st_mtime > LATEST_SCORE_TOP_CSV_PATH.stat().st_mtime:
                return True
            meta = json.loads(LATEST_SCORE_TOP_META_PATH.read_text(encoding="utf-8"))
        except Exception:
            return False
        return int(meta.get("top_n", 0) or 0) < top_n

    def _rebuild_algorithm_snapshot(self, *, top_n: int) -> pd.DataFrame:
        if not TECHNICAL_INDICATORS_PATH.exists():
            return pd.DataFrame()

        source = pd.read_csv(TECHNICAL_INDICATORS_PATH, dtype={"ticker": str})
        raw_scores = calculate_all_raw_scores(source)
        normalized_scores = normalize_cross_sectional_scores(raw_scores)
        ranking = build_latest_ranking_output(
            normalized_scores,
            self._mvp_v0_1_adoption_synthesis_table(),
            top_n=top_n,
        )
        self._export_algorithm_snapshot(ranking, source_rows=len(source), top_n=top_n)
        return self._normalize_algorithm_display_frame(ranking)

    @staticmethod
    def _mvp_v0_1_adoption_synthesis_table() -> pd.DataFrame:
        states = {
            "short_term_overreaction": (Step14AdoptionState.CORE_ADOPTED.value, False),
            "atr_adjusted_oversold_distance": (Step14AdoptionState.CONDITIONAL_ADOPTED.value, True),
            "donchian_breakout_distance": (Step14AdoptionState.CORE_ADOPTED.value, False),
            "bollinger_width_squeeze": (Step14AdoptionState.REGIME_ONLY.value, False),
            "cmf_confirmation": (Step14AdoptionState.CONDITIONAL_ADOPTED.value, True),
            "rsi_price_divergence": (Step14AdoptionState.CONDITIONAL_ADOPTED.value, True),
            "realized_vol_percentile": (Step14AdoptionState.DIAGNOSTIC_ONLY.value, False),
            "efficiency_ratio_trend": (Step14AdoptionState.TECHNICAL_ONLY.value, False),
        }
        rows: list[dict[str, object]] = []
        for spec in DEFAULT_COMPOSITE_INPUT_REGISTRY:
            adoption_state, manual_review_required = states[spec.score_name]
            rows.append(
                {
                    "score_name": spec.score_name,
                    "family": spec.family,
                    "branch": spec.branch,
                    "role": spec.role.value,
                    "eligibility": spec.eligibility.value,
                    "source_review_status": "adopt_candidate",
                    "adoption_state": adoption_state,
                    "adoption_reason": "Frozen MVP v0.1 technical-only GUI refresh.",
                    "evidence_sources": "docs/releases/step20_score_lineage_manifest.md",
                    "limitations": "GUI refresh preserves Step 20 direct-ranking boundaries.",
                    "manual_review_required": manual_review_required,
                    "normalized_score_column": spec.normalized_column,
                    "score_input_column": spec.raw_column,
                    "coverage_status": "ok",
                    "redundancy_status": "ok",
                    "complexity_status": "simple",
                    "regime_fit_status": "broad",
                    "downstream_usage_note": "Display-only Top N refresh; no valuation or backtest feedback.",
                }
            )
        return pd.DataFrame(rows)

    @staticmethod
    def _export_algorithm_snapshot(ranking: pd.DataFrame, *, source_rows: int, top_n: int) -> None:
        LATEST_SCORE_TOP_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        ranking.to_csv(LATEST_SCORE_TOP_CSV_PATH, index=False, encoding="utf-8")
        ranking.to_json(LATEST_SCORE_TOP_JSON_PATH, orient="records", force_ascii=False, indent=2)
        meta = {
            "top_n": top_n,
            "ranking_date": str(ranking["date"].iloc[0]) if not ranking.empty else None,
            "input": str(TECHNICAL_INDICATORS_PATH),
            "output_csv": str(LATEST_SCORE_TOP_CSV_PATH),
            "output_json": str(LATEST_SCORE_TOP_JSON_PATH),
            "rows_in_input": source_rows,
            "rows_in_output": len(ranking),
            "technical_only_notice": "KOSPI200 technical-only scanner v0.1; no valuation/fundamental data.",
        }
        LATEST_SCORE_TOP_META_PATH.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _normalize_algorithm_display_frame(frame: pd.DataFrame) -> pd.DataFrame:
        normalized = frame.copy()
        if "ticker" in normalized.columns:
            normalized["ticker"] = normalized["ticker"].astype(str).str.zfill(6)
            normalized["종목코드"] = normalized["ticker"]
        if "rank" in normalized.columns:
            normalized["순위"] = normalized["rank"]
        if "final_composite_score" in normalized.columns:
            normalized["점수"] = normalized["final_composite_score"]
        normalized["ranking_snapshot_source"] = "latest_score_top"
        normalized["canonical_ranking_source"] = "root src.scanner.latest_ranking"
        return normalized

    def _enrich_records_with_latest_prices(self, records: list[dict]) -> list[dict]:
        enriched: list[dict] = []
        pages = max(self.pages_var.get(), 1)
        for row in records:
            updated = dict(row)
            code = self._as_text(self._first_present(updated, ("종목코드", "ticker", "code"))).zfill(6)
            if code:
                updated["종목코드"] = code
            try:
                price = self._latest_price_snapshot(code=code, pages=pages, use_cache=self.use_cache_var.get())
            except Exception:
                price = {}
            updated.update({key: value for key, value in price.items() if not self._is_blank(value)})
            enriched.append(updated)
        return enriched

    @staticmethod
    def _latest_price_snapshot(*, code: str, pages: int, use_cache: bool) -> dict[str, object]:
        if not code:
            return {}
        frame = get_price_df(code=code, pages=max(pages, 1), use_cache=use_cache)
        if frame.empty:
            return {}
        ordered = frame.sort_values(DATE_COLUMN).reset_index(drop=True)
        latest = ordered.iloc[-1]
        if float(latest.get(VOLUME_COLUMN, 0.0)) <= 0:
            completed = ordered[pd.to_numeric(ordered[VOLUME_COLUMN], errors="coerce").fillna(0.0) > 0]
            if not completed.empty:
                latest = completed.iloc[-1]
        position = int(latest.name)
        latest_close = float(latest[CLOSE_COLUMN])
        if PREV_DIFF_COLUMN in ordered.columns and not Top5App._is_blank(latest.get(PREV_DIFF_COLUMN)):
            latest_change = float(latest[PREV_DIFF_COLUMN])
        else:
            previous_close = float(ordered.iloc[position - 1][CLOSE_COLUMN]) if position > 0 else latest_close
            latest_change = latest_close - previous_close
        return {
            "최신일": pd.Timestamp(latest[DATE_COLUMN]).strftime("%Y-%m-%d"),
            "종가": latest_close,
            "전일대비": latest_change,
            "거래량": float(latest[VOLUME_COLUMN]),
        }

    @classmethod
    def _latest_display_date(cls, records: list[dict]) -> str:
        for row in records:
            value = cls._first_present(row, ("최신일", "date"))
            if not cls._is_blank(value):
                return str(value)
        return ""

    @classmethod
    def _latest_score_date(cls, records: list[dict]) -> str:
        for row in records:
            value = cls._first_present(row, ("date",))
            if not cls._is_blank(value):
                return str(value)[:10]
        return ""

    def run_legacy_update(self) -> None:
        """Run the legacy chart placeholder scorer for compatibility only."""

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
        self.set_status(
            f"완료: {meta['processed_count']}건 처리, 실패 {meta['failed_count']}건, "
            f"작업자 {meta['max_workers']}개"
        )
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
        self._current_top5 = records
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in records:
            code = self._as_text(self._first_present(row, ("종목코드", "ticker", "code")))
            name = self._as_text(self._first_present(row, ("종목명", "name", "stock_name"))) or code
            iid = code or None
            self.tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(
                    self._as_text(self._first_present(row, ("순위", "rank"))),
                    code,
                    name,
                    self._format_score(row),
                    self._as_text(self._first_present(row, ("최신일", "date"))),
                    self._as_text(self._first_present(row, ("ranking_validity_flag", "coverage_status", "data_quality_flag"))),
                    self._format_plain_number(self._first_present(row, ("종가", "close"))),
                    self._format_signed_number(self._first_present(row, ("전일대비", "change"))),
                    self._format_plain_number(self._first_present(row, ("거래량", "volume"))),
                ),
            )

    @staticmethod
    def _is_algorithm_snapshot(frame: pd.DataFrame) -> bool:
        return (
            "final_composite_score" in frame.columns
            or "technical_composite_score" in frame.columns
            or frame.get("ranking_snapshot_source", pd.Series(dtype=object)).eq("latest_score_top").any()
        )

    @staticmethod
    def _is_blank(value: object) -> bool:
        if value is None:
            return True
        try:
            if pd.isna(value):
                return True
        except (TypeError, ValueError):
            pass
        return isinstance(value, str) and value.strip() == ""

    @classmethod
    def _first_present(cls, row: dict, keys: tuple[str, ...]) -> object:
        for key in keys:
            value = row.get(key)
            if not cls._is_blank(value):
                return value
        return ""

    @classmethod
    def _as_text(cls, value: object) -> str:
        if cls._is_blank(value):
            return ""
        return str(value)

    @classmethod
    def _format_score(cls, row: dict) -> str:
        value = cls._first_present(row, ("점수", "final_composite_score", "technical_composite_score"))
        if cls._is_blank(value):
            return ""
        try:
            return f"{float(value):.4f}"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _format_plain_number(value: object) -> str:
        if Top5App._is_blank(value):
            return ""
        try:
            return f"{float(value):,.0f}"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _format_signed_number(value: object) -> str:
        if Top5App._is_blank(value):
            return ""

        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)
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

        code = str(selection[0])
        record = next(
            (
                row
                for row in self._current_top5
                if self._as_text(self._first_present(row, ("종목코드", "ticker", "code"))) == code
            ),
            {},
        )
        name = self._as_text(self._first_present(record, ("종목명", "name", "stock_name"))) or code
        if not code or not name:
            messagebox.showerror("오류", "선택한 종목 정보를 읽을 수 없습니다.")
            return

        self.set_status(f"{name} 차트 준비 중...")
        self._open_chart_window(code=code, name=name)
        self.set_status(f"{name} 차트 표시 완료")

    def _open_chart_window(self, code: str, name: str) -> None:
        df = prepare_chart_dataframe(
            code=code,
            requested_pages=self.pages_var.get(),
            use_cache=self.use_cache_var.get(),
        )
        fig = plot_stock_data(df, stock_label=f"{name} ({code})", source_label="GUI 차트", show=False)

        window = tk.Toplevel(self.root)
        window.title(f"{name} ({code}) 차트")
        window.geometry("1320x900")

        notebook = ttk.Notebook(window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        chart_tab = ttk.Frame(notebook, padding=12)
        financial_tab = ttk.Frame(notebook, padding=12)
        notebook.add(chart_tab, text="차트")
        notebook.add(financial_tab, text="재무제표(표시 전용)")

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
        ttk.Label(header, text="저장된 네이버 파이낸셜 재무제표 캐시입니다.").pack(
            anchor="w",
            pady=(4, 0),
        )
        ttk.Label(header, text=FINANCIAL_DISPLAY_NOTICE, foreground="#92400e").pack(
            anchor="w",
            pady=(4, 0),
        )

        try:
            raw_frame = load_financial_statements(code)
        except FileNotFoundError:
            ttk.Label(parent, text="저장된 재무제표가 없습니다. 먼저 데이터를 새로고침해 주세요.").pack(
                anchor="w"
            )
            return
        except Exception as exc:
            ttk.Label(parent, text=f"재무제표를 불러오지 못했습니다: {exc}").pack(anchor="w")
            return

        if raw_frame.empty:
            ttk.Label(parent, text="표시할 재무제표 데이터가 없습니다.").pack(anchor="w")
            return

        summary_frame = ttk.LabelFrame(parent, text="표시 전용 주요 지표", padding=12)
        summary_frame.pack(fill=tk.X, pady=(0, 12))
        self._render_financial_summary_cards(summary_frame, raw_frame)

        table_frame = ttk.LabelFrame(parent, text="재무제표 표 (점수 미반영)", padding=8)
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
            ttk.Label(parent, text="요약 카드로 보여줄 지표를 찾지 못했습니다. 아래 표를 확인해 주세요.").pack(
                anchor="w"
            )

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
        pivot = ordered.pivot_table(
            index="metric",
            columns="period",
            values="value",
            aggfunc="first",
            fill_value="",
        )
        return pivot.reindex(columns=period_order, fill_value="").reset_index()

    @staticmethod
    def _resolve_latest_financial_period(raw_frame: pd.DataFrame) -> str:
        periods = [period for period in raw_frame["period"].astype(str).tolist() if period]
        if not periods:
            return ""
        return periods[-1]

    @staticmethod
    def _find_financial_metric_value(
        raw_frame: pd.DataFrame,
        aliases: tuple[str, ...],
        period: str,
    ) -> str | None:
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


__all__ = ("Top5App", "main")


if __name__ == "__main__":
    raise SystemExit(main())
