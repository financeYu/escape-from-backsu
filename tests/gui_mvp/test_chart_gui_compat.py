from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHART_MVP_ROOT = PROJECT_ROOT / "chart_mvp"

for path in (PROJECT_ROOT, CHART_MVP_ROOT, CHART_MVP_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.run_gui import Top5App as CompatTop5App  # noqa: E402
from gui_mvp.chart_topn import Top5App  # noqa: E402
from stock_core.pipeline import daily_update  # noqa: E402


def test_chart_mvp_run_gui_remains_compatibility_wrapper() -> None:
    assert CompatTop5App is Top5App


def test_chart_mvp_run_gui_imports_from_chart_cwd() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.run_gui import Top5App; print(Top5App.__module__)",
        ],
        cwd=CHART_MVP_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "gui_mvp.chart_topn"


def test_financial_statement_pivot_lives_in_gui_mvp() -> None:
    raw = pd.DataFrame(
        [
            {"metric": "매출액", "period": "2023/12", "value": "100"},
            {"metric": "매출액", "period": "2024/12(E)", "value": "120"},
            {"metric": "영업이익", "period": "2023/12", "value": "10"},
        ]
    )

    pivot = Top5App._build_financial_statement_pivot(raw)

    assert pivot.columns.tolist() == ["metric", "2023/12", "2024/12(E)"]
    assert pivot.iloc[0]["metric"] == "매출액"


def test_algorithm_score_display_prefers_final_composite_score() -> None:
    row = {
        "technical_composite_score": 0.9,
        "final_composite_score": 1.1292949962298064,
    }

    assert Top5App._format_score(row) == "1.1293"


class _DummyVar:
    def __init__(self, value=0):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _DummyProgress:
    def __init__(self):
        self.options = {}

    def configure(self, **kwargs):
        self.options.update(kwargs)


def test_topn_refresh_uses_algorithm_snapshot_scores(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = pd.DataFrame(
        [
            {
                "ticker": "005930",
                "rank": 1,
                "date": "2026-04-24",
                "technical_composite_score": 0.9,
                "final_composite_score": 1.25,
            },
            {
                "ticker": "000660",
                "rank": 2,
                "date": "2026-04-24",
                "technical_composite_score": 0.8,
                "final_composite_score": 1.10,
            },
        ]
    )
    monkeypatch.setattr("gui_mvp.chart_topn.load_latest_algorithm_ranking_snapshot", lambda: frame)

    app = Top5App.__new__(Top5App)
    app.top_n_var = _DummyVar(1)
    app.pages_var = _DummyVar(1)
    app.use_cache_var = _DummyVar(True)
    app.progress_var = _DummyVar()
    app.last_updated_var = _DummyVar()
    app.progress = _DummyProgress()
    app._is_running = False
    captured = {}
    app._fill_tree = lambda records: captured.setdefault("records", records)
    app.set_status = lambda text: captured.setdefault("status", text)
    app._latest_price_snapshot = lambda **_kwargs: {
        "최신일": "2026-04-24",
        "종가": 100.0,
        "전일대비": 1.0,
        "거래량": 1000.0,
    }

    app.run_update()

    assert captured["records"][0]["final_composite_score"] == 1.25
    assert len(captured["records"]) == 1
    assert captured["records"][0]["최신일"] == "2026-04-24"
    assert captured["records"][0]["종가"] == 100.0
    assert captured["status"] == "점수 기반 Top 1 갱신 완료"
    assert app.last_updated_var.value == "마지막 갱신: 2026-04-24"


def test_topn_refresh_rebuilds_when_saved_snapshot_is_short(monkeypatch: pytest.MonkeyPatch) -> None:
    saved = pd.DataFrame(
        [
            {
                "ticker": "005930",
                "rank": 1,
                "date": "2026-04-20",
                "final_composite_score": 1.25,
            }
        ]
    )
    rebuilt = pd.DataFrame(
        [
            {
                "ticker": f"{index:06d}",
                "rank": index,
                "date": "2026-04-20",
                "final_composite_score": 1.0 / index,
            }
            for index in range(1, 11)
        ]
    )
    monkeypatch.setattr("gui_mvp.chart_topn.load_latest_algorithm_ranking_snapshot", lambda: saved)

    app = Top5App.__new__(Top5App)
    app.top_n_var = _DummyVar(10)
    app.pages_var = _DummyVar(1)
    app.use_cache_var = _DummyVar(True)
    app.progress_var = _DummyVar()
    app.last_updated_var = _DummyVar()
    app.progress = _DummyProgress()
    captured = {}
    app._fill_tree = lambda records: captured.setdefault("records", records)
    app.set_status = lambda text: captured.setdefault("status", text)
    app._rebuild_algorithm_snapshot = lambda *, top_n: rebuilt.head(top_n)
    app._latest_price_snapshot = lambda **_kwargs: {"최신일": "2026-04-24"}

    assert app._refresh_from_algorithm_snapshot() is True

    assert len(captured["records"]) == 10
    assert captured["records"][9]["final_composite_score"] == pytest.approx(0.1)
    assert captured["records"][0]["최신일"] == "2026-04-24"


def test_topn_refresh_blocks_legacy_placeholder_when_algorithm_snapshot_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("gui_mvp.chart_topn.load_latest_algorithm_ranking_snapshot", pd.DataFrame)

    app = Top5App.__new__(Top5App)
    app.top_n_var = _DummyVar(10)
    app._is_running = False
    captured = {}
    app.set_status = lambda text: captured.setdefault("status", text)
    app._rebuild_algorithm_snapshot = lambda *, top_n: pd.DataFrame()
    monkeypatch.setattr("gui_mvp.chart_topn.messagebox.showwarning", lambda *args, **kwargs: None)

    app.run_update()

    assert captured["status"] == "알고리즘 랭킹 스냅샷 없음"
    assert app._is_running is False


def test_algorithm_snapshot_loader_reads_canonical_latest_ranking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outputs_dir = tmp_path / "chart_outputs"
    outputs_dir.mkdir()
    canonical_path = tmp_path / "reports" / "selection" / "latest_ranking.csv"
    canonical_path.parent.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "ticker": "005930",
                "rank": 1,
                "date": "2026-04-24",
                "종목명": "삼성전자",
                "technical_composite_score": 1.25,
                "final_composite_score": 1.25,
            },
        ]
    ).to_csv(canonical_path, index=False)
    monkeypatch.setattr(daily_update, "OUTPUTS_DIR", outputs_dir)
    monkeypatch.setattr(daily_update, "CANONICAL_LATEST_RANKING_CSV_PATH", canonical_path)

    frame = daily_update.load_latest_algorithm_ranking_snapshot()

    assert frame.iloc[0]["종목코드"] == "005930"
    assert frame.iloc[0]["점수"] == pytest.approx(1.25)
    assert frame.iloc[0]["ranking_snapshot_source"] == "reports/selection/latest_ranking.csv"


def test_chart_topn_number_formatters_tolerate_blank_values() -> None:
    assert Top5App._format_plain_number("") == ""
    assert Top5App._format_plain_number(pd.NA) == ""
    assert Top5App._format_signed_number("") == ""
    assert Top5App._format_signed_number(pd.NA) == ""
