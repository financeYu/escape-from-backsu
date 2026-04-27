"""Desktop chart GUI extracted from ``chart_mvp``.

The GUI remains a local runtime viewer. It does not promote chart runtime
outputs to canonical ranking evidence.
"""

from __future__ import annotations

from datetime import datetime
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
from src.scanner.latest_ranking_validation import validate_step15_latest_ranking_output


LATEST_TOP_JSON_NAMES = ("latest_top.json", "latest_top5.json")
LEGACY_SCORE_NOTICE = (
    "현재 Top N 표의 '점수'는 chart_mvp legacy placeholder입니다. "
    "정식 MVP v0.1 점수는 Step 20 랭킹 CSV의 final_composite_score를 "
    "읽기 전용으로 열어 확인하세요."
)
OFFICIAL_RANKING_FILETYPES = (
    ("CSV files", "*.csv"),
    ("All files", "*.*"),
)
OFFICIAL_RANKING_AUTO_SEARCH_ROOTS = (
    REPO_ROOT / "reports",
    REPO_ROOT / "outputs",
    REPO_ROOT / "docs" / "releases",
    CHART_MVP_ROOT / "outputs",
)
OFFICIAL_RANKING_CSV_PATTERNS = (
    "*latest*ranking*.csv",
    "*ranking*.csv",
    "*latest*.csv",
)
OFFICIAL_RANKING_BASIS_OPTIONS: tuple[tuple[str, str], ...] = (
    ("final_composite_score", "정식 랭킹 점수"),
    ("technical_composite_score", "기술 점수"),
    ("coverage_metric", "커버리지"),
    ("valid_score_count", "유효 점수 수"),
)
DEFAULT_OFFICIAL_RANKING_BASIS = OFFICIAL_RANKING_BASIS_OPTIONS[0][1]
OFFICIAL_RANKING_DISPLAY_COLUMNS: tuple[tuple[str, str, int], ...] = (
    ("rank", "순위", 70),
    ("ticker", "종목코드", 90),
    ("date", "기준일", 120),
    ("final_composite_score", "final_composite_score", 170),
    ("technical_composite_score", "technical_composite_score", 190),
    ("coverage_metric", "coverage", 100),
    ("coverage_status", "coverage_status", 130),
    ("ranking_validity_flag", "validity", 110),
    ("valid_score_count", "valid_count", 100),
    ("expected_score_count", "expected_count", 120),
    ("neutral_shrinkage_count", "neutral_shrink", 120),
    ("final_score_policy", "policy", 190),
)


def load_latest_topn_records() -> tuple[list[dict], str]:
    """Load latest Top-N rows for GUI display, with JSON fallback."""

    try:
        latest_df = load_latest_top5_snapshot()
    except Exception as exc:
        csv_error = str(exc)
    else:
        if not latest_df.empty:
            return latest_df.to_dict(orient="records"), "CSV"
        csv_error = ""

    outputs_dir = CHART_MVP_ROOT / "outputs"
    for file_name in LATEST_TOP_JSON_NAMES:
        json_path = outputs_dir / file_name
        if not json_path.exists():
            continue
        try:
            records = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(records, list):
            normalized = []
            for record in records:
                if not isinstance(record, dict):
                    continue
                row = dict(record)
                if "종목코드" in row:
                    row["종목코드"] = str(row["종목코드"]).zfill(6)
                normalized.append(row)
            if normalized:
                return normalized, file_name

    if csv_error:
        raise ValueError(f"저장된 Top-N 결과를 읽지 못했습니다: {csv_error}")
    return [], ""


def summarize_chart_artifacts(meta: dict) -> list[str]:
    """Return user-facing chart artifact status lines for completion dialogs."""

    chart_paths = list(meta.get("chart_paths") or [])
    chart_failed_codes = list(meta.get("chart_failed_codes") or [])
    chart_failed_count = int(meta.get("chart_failed_count") or len(chart_failed_codes))
    if not meta.get("render_charts"):
        return ["차트 파일 저장: 선택 안 함"]

    lines = [f"차트 파일: {len(chart_paths)}개 저장"]
    if chart_paths:
        preview = chart_paths[:3]
        lines.append("차트 경로: " + "; ".join(str(path) for path in preview))
        if len(chart_paths) > len(preview):
            lines.append(f"추가 차트: {len(chart_paths) - len(preview)}개")
    if chart_failed_count:
        failed = ", ".join(str(code) for code in chart_failed_codes[:10])
        lines.append(f"차트 저장 실패: {chart_failed_count}개 ({failed})")
    return lines


def load_official_ranking_csv(path: str | Path) -> pd.DataFrame:
    """Load and validate a Step 20 latest-ranking CSV for read-only display."""

    frame = pd.read_csv(path, dtype={"ticker": "string"})
    if "ticker" in frame.columns:
        frame = frame.copy()
        frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    validate_step15_latest_ranking_output(frame)
    return frame


def find_latest_official_ranking_csv(
    search_roots: tuple[Path, ...] = OFFICIAL_RANKING_AUTO_SEARCH_ROOTS,
) -> Path | None:
    """Find the newest valid Step 20 ranking CSV under known output roots."""

    candidates = list_official_ranking_csvs(search_roots)
    return candidates[0] if candidates else None


def list_official_ranking_csvs(
    search_roots: tuple[Path, ...] = OFFICIAL_RANKING_AUTO_SEARCH_ROOTS,
) -> list[Path]:
    """Return valid Step 20 ranking CSVs sorted newest first."""

    candidates: dict[Path, float] = {}
    for root in search_roots:
        if not root.exists():
            continue
        for pattern in OFFICIAL_RANKING_CSV_PATTERNS:
            for path in root.rglob(pattern):
                if not path.is_file() or path in candidates:
                    continue
                try:
                    load_official_ranking_csv(path)
                except Exception:
                    continue
                candidates[path] = path.stat().st_mtime

    return sorted(candidates, key=lambda path: (candidates[path], str(path)), reverse=True)


def format_official_ranking_choice(path: Path, *, repo_root: Path = REPO_ROOT) -> str:
    """Return a compact label for a discovered Step 20 ranking CSV."""

    try:
        display_path = path.relative_to(repo_root)
    except ValueError:
        display_path = path
    timestamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    return f"{display_path} | {timestamp}"


def resolve_official_ranking_basis(label_or_key: str) -> str:
    """Resolve a GUI basis label to a Step 20 ranking column."""

    normalized = str(label_or_key).strip()
    allowed = {key for key, _label in OFFICIAL_RANKING_BASIS_OPTIONS}
    if normalized in allowed:
        return normalized
    for key, label in OFFICIAL_RANKING_BASIS_OPTIONS:
        if normalized == label:
            return key
    return "final_composite_score"


def sort_official_ranking_for_display(frame: pd.DataFrame, basis: str) -> pd.DataFrame:
    """Sort a read-only display copy without redefining canonical ranking."""

    basis_column = resolve_official_ranking_basis(basis)
    display = frame.copy()
    if basis_column in {"final_composite_score", "technical_composite_score", "coverage_metric"}:
        display["_display_basis_value"] = pd.to_numeric(display[basis_column], errors="coerce")
        return display.sort_values(
            by=["_display_basis_value", "rank", "ticker"],
            ascending=[False, True, True],
            na_position="last",
            kind="mergesort",
        ).drop(columns=["_display_basis_value"])
    if basis_column == "valid_score_count":
        display["_display_basis_value"] = pd.to_numeric(display[basis_column], errors="coerce")
        return display.sort_values(
            by=["_display_basis_value", "rank", "ticker"],
            ascending=[False, True, True],
            na_position="last",
            kind="mergesort",
        ).drop(columns=["_display_basis_value"])
    return display.sort_values(by=["rank", "ticker"], ascending=[True, True], kind="mergesort")


def format_official_ranking_value(column: str, value: object) -> str:
    """Format Step 20 ranking values for the GUI without changing semantics."""

    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass

    if column in {"final_composite_score", "technical_composite_score"}:
        return f"{float(value):.4f}"
    if column == "coverage_metric":
        return f"{float(value) * 100:.2f}%"
    if column in {
        "rank",
        "valid_score_count",
        "expected_score_count",
        "neutral_shrinkage_count",
        "review_routed_score_count",
    }:
        return f"{int(float(value))}"
    return str(value)


def official_ranking_display_rows(
    frame: pd.DataFrame,
    basis: str = "final_composite_score",
) -> list[list[str]]:
    """Return formatted Step 20 ranking rows for read-only GUI display."""

    rows: list[list[str]] = []
    for _, row in sort_official_ranking_for_display(frame, basis).iterrows():
        rows.append(
            [
                format_official_ranking_value(column, row.get(column))
                for column, _label, _width in OFFICIAL_RANKING_DISPLAY_COLUMNS
            ]
        )
    return rows


def summarize_official_ranking_source(
    frame: pd.DataFrame,
    source_path: str | Path,
    basis: str = "final_composite_score",
) -> str:
    """Return the read-only source summary shown above the Step 20 ranking table."""

    dates = frame["date"].astype("string").dropna().unique().tolist() if "date" in frame else []
    date_text = ", ".join(str(date) for date in dates[:3]) if dates else "알 수 없음"
    if len(dates) > 3:
        date_text += f" 외 {len(dates) - 3}개"
    basis_column = resolve_official_ranking_basis(basis)
    return (
        f"읽기 전용 파일: {source_path} | 행 수: {len(frame)} | 기준일: {date_text} | "
        f"표시 기준: {basis_column} | canonical rank 컬럼은 그대로 유지됩니다. "
        "재무/밸류에이션 점수와 매수/매도 추천은 포함하지 않습니다."
    )

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

    def __init__(
        self,
        root: tk.Misc,
        *,
        configure_window: bool = True,
        startup_due_check: bool = True,
    ) -> None:
        self.root = root
        if configure_window:
            self._configure_window()

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
        self.official_score_basis_var = tk.StringVar(value=DEFAULT_OFFICIAL_RANKING_BASIS)
        self.official_ranking_choice_var = tk.StringVar(value="")
        self.progress_var = tk.DoubleVar(value=0.0)

        self._current_top5: list[dict] = []
        self._official_ranking_source_path: Path | None = None
        self._official_ranking_choices: dict[str, Path] = {}
        self.official_ranking_choice_combo: ttk.Combobox | None = None
        self._is_running = False
        self._auto_refresh_job: str | None = None

        self._build_ui()
        self.refresh_official_ranking_choices(show_status=False)
        self._load_latest_results()
        self._load_latest_meta()
        if startup_due_check:
            self._run_startup_due_check()

    def _configure_window(self) -> None:
        if not isinstance(self.root, (tk.Tk, tk.Toplevel)):
            return
        self.root.title("Configured Universe Top-N Viewer")
        self.root.geometry("1240x720")
        self.root.minsize(1020, 640)
        self.root.resizable(True, True)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        self._build_control_section(container)
        self._build_action_section(container)
        self._build_notice_section(container)
        self._build_table_section(container)
        self._build_status_section(container)
        self._build_progress_section(container)

    def _build_control_section(self, container: ttk.Frame) -> None:
        control_frame = ttk.LabelFrame(container, text="실행 설정", padding=10)
        control_frame.pack(fill=tk.X)

        self._build_page_controls(control_frame)
        self._build_refresh_controls(control_frame)
        self._build_auto_refresh_controls(control_frame)

    def _build_page_controls(self, control_frame: ttk.LabelFrame) -> None:
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

    def _build_refresh_controls(self, control_frame: ttk.LabelFrame) -> None:
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

    def _build_auto_refresh_controls(self, control_frame: ttk.LabelFrame) -> None:
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

    def _build_action_section(self, container: ttk.Frame) -> None:
        action_frame = ttk.Frame(container, padding=(0, 10, 0, 10))
        action_frame.pack(fill=tk.X)
        self.run_button = ttk.Button(action_frame, text="Top N 갱신 실행", command=self.run_update)
        self.run_button.pack(side=tk.LEFT)
        ttk.Button(action_frame, text="선택 종목 차트 보기", command=self.open_selected_chart).pack(
            side=tk.LEFT,
            padx=(8, 0),
        )
        ttk.Label(action_frame, text="점수 기준").pack(side=tk.LEFT, padx=(14, 4))
        ttk.Combobox(
            action_frame,
            textvariable=self.official_score_basis_var,
            values=[label for _key, label in OFFICIAL_RANKING_BASIS_OPTIONS],
            state="readonly",
            width=14,
        ).pack(side=tk.LEFT)
        ttk.Label(action_frame, text="CSV 파일").pack(side=tk.LEFT, padx=(14, 4))
        self.official_ranking_choice_combo = ttk.Combobox(
            action_frame,
            textvariable=self.official_ranking_choice_var,
            state="readonly",
            width=36,
        )
        self.official_ranking_choice_combo.pack(side=tk.LEFT)
        self.official_ranking_choice_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._select_official_ranking_choice(),
        )
        ttk.Button(
            action_frame,
            text="목록 새로고침",
            command=lambda: self.refresh_official_ranking_choices(show_status=True),
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(
            action_frame,
            text="점수 새로고침",
            command=self.open_latest_official_ranking_viewer,
        ).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(
            container,
            text=LEGACY_SCORE_NOTICE,
            foreground="#7c2d12",
            wraplength=1120,
            justify=tk.LEFT,
        ).pack(fill=tk.X, pady=(0, 8))

    def _build_notice_section(self, container: ttk.Frame) -> None:
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

    def _build_table_section(self, container: ttk.Frame) -> None:
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

    def _build_status_section(self, container: ttk.Frame) -> None:
        status_frame = ttk.Frame(container)
        status_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        ttk.Label(status_frame, textvariable=self.last_updated_var).pack(side=tk.RIGHT)

    def _build_progress_section(self, container: ttk.Frame) -> None:
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
        try:
            latest_df = load_latest_top5_snapshot()
        except Exception:
            latest_df = pd.DataFrame()

        if not latest_df.empty:
            records = latest_df.to_dict(orient="records")
            self._fill_tree(records)
            if self._is_algorithm_snapshot(latest_df):
                self.set_status("저장된 알고리즘 랭킹 결과를 먼저 표시했습니다.")
            else:
                self.set_status("저장된 latest_top 결과를 먼저 표시했습니다.")
            return

        try:
            records, source = load_latest_topn_records()
        except Exception as exc:
            self.set_status(str(exc))
            return

        if not records:
            self.set_status("대기 중 - 저장된 Top N 결과 없음")
            return

        self._current_top5 = records
        self._fill_tree(records)
        self.set_status(f"저장된 latest_top 결과를 먼저 표시했습니다. ({source})")

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
        artifact_lines = summarize_chart_artifacts(meta)
        if artifact_lines:
            summary += "\n" + "\n".join(artifact_lines)
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

    def refresh_official_ranking_choices(self, *, show_status: bool) -> None:
        paths = list_official_ranking_csvs()
        choices = {format_official_ranking_choice(path): path for path in paths}
        self._official_ranking_choices = choices
        labels = list(choices)
        if self.official_ranking_choice_combo is not None:
            self.official_ranking_choice_combo.configure(values=labels)

        current = self.official_ranking_choice_var.get()
        if labels and current not in choices:
            self.official_ranking_choice_var.set(labels[0])
            self._official_ranking_source_path = choices[labels[0]]
        elif labels and current in choices:
            self._official_ranking_source_path = choices[current]
        elif not labels:
            self.official_ranking_choice_var.set("")
            self._official_ranking_source_path = None

        if show_status:
            if labels:
                self.set_status(f"정식 Step 20 CSV {len(labels)}개를 찾았습니다.")
            else:
                self.set_status("정식 Step 20 CSV를 찾지 못했습니다.")

    def _select_official_ranking_choice(self) -> None:
        selected = self.official_ranking_choice_var.get()
        self._official_ranking_source_path = self._official_ranking_choices.get(selected)

    def open_latest_official_ranking_viewer(self) -> None:
        self._select_official_ranking_choice()
        source_path = self._official_ranking_source_path
        if source_path is None:
            source_path = find_latest_official_ranking_csv()
        if source_path is None:
            messagebox.showerror(
                "정식 점수 CSV 없음",
                "GUI 목록에서 선택할 수 있는 Step 20 형식의 랭킹 CSV를 찾지 못했습니다. "
                "먼저 정식 랭킹 CSV를 생성한 뒤 목록 새로고침을 눌러 주세요.",
            )
            return

        self._official_ranking_source_path = source_path
        try:
            frame = load_official_ranking_csv(source_path)
        except Exception as exc:
            messagebox.showerror("정식 점수 새로고침 실패", str(exc))
            return
        self._open_official_ranking_window(frame, source_path)

    def _open_official_ranking_window(self, frame: pd.DataFrame, source_path: Path) -> None:
        window = tk.Toplevel(self.root)
        window.title("Step 20 정식 랭킹 점수")
        window.geometry("1320x720")

        container = ttk.Frame(window, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(container)
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text="MVP v0.1 KOSPI200 technical-only final_composite_score",
            font=("", 13, "bold"),
        ).pack(side=tk.LEFT, anchor="w")
        ttk.Button(
            header,
            text="점수 새로고침",
            command=lambda: refresh_official_ranking(),
        ).pack(side=tk.RIGHT)
        ttk.Label(header, text="표시 기준").pack(side=tk.RIGHT, padx=(12, 4))
        basis_var = tk.StringVar(value=self.official_score_basis_var.get())
        basis_combo = ttk.Combobox(
            header,
            textvariable=basis_var,
            values=[label for _key, label in OFFICIAL_RANKING_BASIS_OPTIONS],
            state="readonly",
            width=14,
        )
        basis_combo.pack(side=tk.RIGHT)

        source_var = tk.StringVar(value="")
        status_var = tk.StringVar(value="")
        ttk.Label(
            container,
            textvariable=source_var,
            foreground="#444444",
            wraplength=1240,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(4, 4))
        ttk.Label(container, textvariable=status_var, foreground="#166534").pack(
            anchor="w",
            pady=(0, 10),
        )

        table_frame = ttk.Frame(container)
        table_frame.pack(fill=tk.BOTH, expand=True)

        column_ids = tuple(column for column, _label, _width in OFFICIAL_RANKING_DISPLAY_COLUMNS)
        tree = ttk.Treeview(table_frame, columns=column_ids, show="headings", height=18)
        for column, label, width in OFFICIAL_RANKING_DISPLAY_COLUMNS:
            tree.heading(column, text=label)
            tree.column(column, width=width, minwidth=width, anchor="center", stretch=True)

        current_frame = {"frame": frame}

        def fill_official_ranking(display_frame: pd.DataFrame, *, status: str) -> None:
            current_frame["frame"] = display_frame
            for item in tree.get_children():
                tree.delete(item)
            basis = resolve_official_ranking_basis(basis_var.get())
            for values in official_ranking_display_rows(display_frame, basis=basis):
                tree.insert("", tk.END, values=values)
            source_var.set(
                summarize_official_ranking_source(display_frame, source_path, basis=basis)
            )
            status_var.set(status)

        def refresh_official_ranking() -> None:
            try:
                refreshed = load_official_ranking_csv(source_path)
            except Exception as exc:
                status_var.set("새로고침 실패")
                messagebox.showerror("점수 새로고침 실패", str(exc))
                return
            fill_official_ranking(refreshed, status="점수 새로고침 완료")

        basis_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: fill_official_ranking(
                current_frame["frame"],
                status="표시 기준을 변경했습니다.",
            ),
        )
        y_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        x_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        fill_official_ranking(frame, status="점수 파일을 불러왔습니다.")

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
        try:
            self._open_chart_window(code=code, name=name)
        except Exception as exc:
            self.set_status(f"{name} 차트 표시 실패")
            messagebox.showerror("차트 표시 실패", str(exc))
            return
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


__all__ = (
    "LEGACY_SCORE_NOTICE",
    "Top5App",
    "find_latest_official_ranking_csv",
    "format_official_ranking_choice",
    "format_official_ranking_value",
    "list_official_ranking_csvs",
    "load_latest_topn_records",
    "load_official_ranking_csv",
    "main",
    "official_ranking_display_rows",
    "resolve_official_ranking_basis",
    "sort_official_ranking_for_display",
    "summarize_chart_artifacts",
    "summarize_official_ranking_source",
)


if __name__ == "__main__":
    raise SystemExit(main())
