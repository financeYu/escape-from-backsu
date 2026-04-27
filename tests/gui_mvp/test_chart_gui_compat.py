from __future__ import annotations

import os
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
import gui_mvp.chart_topn as chart_topn  # noqa: E402
from gui_mvp.chart_topn import (  # noqa: E402
    LEGACY_SCORE_NOTICE,
    Top5App,
    find_latest_official_ranking_csv,
    format_official_ranking_choice,
    format_official_ranking_value,
    list_official_ranking_csvs,
    load_official_ranking_csv,
    official_ranking_display_rows,
    resolve_official_ranking_basis,
    sort_official_ranking_for_display,
    summarize_official_ranking_source,
)
from gui_mvp.launcher import build_launch_specs, build_viewer_command  # noqa: E402
from stock_core.pipeline import daily_update  # noqa: E402


def _valid_ranking_row(ticker: str = "005930", rank: int = 1) -> dict[str, object]:
    return {
        "ticker": ticker,
        "date": "2026-04-24",
        "rank": rank,
        "technical_composite_score": 1.25 if rank == 1 else 0.5,
        "final_composite_score": 1.25 if rank == 1 else 0.5,
        "coverage_metric": 1.0 if rank == 1 else 0.6667,
        "data_quality_flag": "valid" if rank == 1 else "partial",
        "warmup_status": "ready",
        "coverage_status": "adequate" if rank == 1 else "partial",
        "ranking_validity_flag": "valid" if rank == 1 else "partial",
        "valid_score_count": 3 if rank == 1 else 2,
        "expected_score_count": 3,
        "neutral_shrinkage_count": 0 if rank == 1 else 1,
        "review_routed_score_count": 5,
        "final_score_policy": "technical_only_no_valuation",
        "technical_only_notice": "kospi200_technical_only_mvp_no_valuation_or_fundamental_activation",
    }


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
    rows = [_valid_ranking_row()]
    rows[0]["종목명"] = "삼성전자"
    pd.DataFrame(rows).to_csv(canonical_path, index=False)
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


def test_chart_viewer_falls_back_to_latest_json(tmp_path: Path, monkeypatch) -> None:
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    (outputs_dir / "latest_top.json").write_text(
        '[{"종목코드":"5930","종목명":"삼성전자","점수":1.0}]',
        encoding="utf-8",
    )
    monkeypatch.setattr(chart_topn, "CHART_MVP_ROOT", tmp_path)
    monkeypatch.setattr(chart_topn, "load_latest_top5_snapshot", lambda: pd.DataFrame())

    records, source = chart_topn.load_latest_topn_records()

    assert source == "latest_top.json"
    assert records[0]["종목코드"] == "005930"


def test_chart_completion_summary_includes_chart_artifacts() -> None:
    lines = chart_topn.summarize_chart_artifacts(
        {
            "render_charts": True,
            "chart_paths": ["outputs/charts/005930.png", "outputs/charts/000660.png"],
            "chart_failed_count": 1,
            "chart_failed_codes": ["035420"],
        }
    )

    assert "차트 파일: 2개 저장" in lines
    assert any("035420" in line for line in lines)


def test_chart_viewer_legacy_score_notice_names_placeholder_boundary() -> None:
    assert "legacy placeholder" in LEGACY_SCORE_NOTICE
    assert "final_composite_score" in LEGACY_SCORE_NOTICE


def test_official_ranking_csv_loader_validates_step20_score_file(tmp_path: Path) -> None:
    path = tmp_path / "latest_ranking.csv"
    pd.DataFrame([_valid_ranking_row("5930"), _valid_ranking_row("000660", rank=2)]).to_csv(
        path,
        index=False,
    )

    frame = load_official_ranking_csv(path)

    assert frame.iloc[0]["ticker"] == "005930"
    assert frame.iloc[0]["final_composite_score"] == 1.25


def test_official_ranking_auto_discovery_uses_valid_latest_csv(tmp_path: Path) -> None:
    valid_path = tmp_path / "latest_ranking.csv"
    invalid_path = tmp_path / "latest_top.csv"
    pd.DataFrame([{"종목코드": "005930", "점수": 0.0}]).to_csv(invalid_path, index=False)
    pd.DataFrame([_valid_ranking_row()]).to_csv(valid_path, index=False)

    found = find_latest_official_ranking_csv((tmp_path,))

    assert found == valid_path


def test_official_ranking_csv_list_supports_in_gui_selection(tmp_path: Path) -> None:
    first_path = tmp_path / "old_latest_ranking.csv"
    second_path = tmp_path / "new_latest_ranking.csv"
    rows = [_valid_ranking_row()]
    pd.DataFrame(rows).to_csv(first_path, index=False)
    pd.DataFrame(rows).to_csv(second_path, index=False)
    os.utime(first_path, (1_000_000, 1_000_000))
    os.utime(second_path, (2_000_000, 2_000_000))

    paths = list_official_ranking_csvs((tmp_path,))
    label = format_official_ranking_choice(paths[0], repo_root=tmp_path)

    assert paths[0] == second_path
    assert "new_latest_ranking.csv" in label


def test_official_ranking_csv_loader_rejects_chart_runtime_topn(tmp_path: Path) -> None:
    path = tmp_path / "latest_top.csv"
    pd.DataFrame([{"종목코드": "005930", "점수": 0.0}]).to_csv(path, index=False)

    try:
        load_official_ranking_csv(path)
    except ValueError as exc:
        assert "missing required columns" in str(exc)
    else:
        raise AssertionError("chart runtime Top-N output must not load as Step 20 ranking")


def test_official_ranking_display_formatter() -> None:
    assert format_official_ranking_value("final_composite_score", 1.23456) == "1.2346"
    assert format_official_ranking_value("coverage_metric", 0.5) == "50.00%"
    assert format_official_ranking_value("rank", 1.0) == "1"
    assert format_official_ranking_value("final_composite_score", pd.NA) == ""


def test_official_ranking_display_rows_and_source_summary() -> None:
    frame = pd.DataFrame(
        [
            {
                "rank": 1,
                "ticker": "005930",
                "date": "2026-04-24",
                "final_composite_score": 1.23456,
                "technical_composite_score": 1.23456,
                "coverage_metric": 1.0,
                "coverage_status": "adequate",
                "ranking_validity_flag": "valid",
                "valid_score_count": 3,
                "expected_score_count": 3,
                "neutral_shrinkage_count": 0,
                "final_score_policy": "technical_only_no_valuation",
            }
        ]
    )

    rows = official_ranking_display_rows(frame)
    summary = summarize_official_ranking_source(frame, "latest_ranking.csv")

    assert rows[0][0:4] == ["1", "005930", "2026-04-24", "1.2346"]
    assert "latest_ranking.csv" in summary
    assert "기준일: 2026-04-24" in summary
    assert "final_composite_score" in summary


def test_official_ranking_basis_selection_is_display_only_sorting() -> None:
    frame = pd.DataFrame(
        [
            {
                "rank": 1,
                "ticker": "005930",
                "date": "2026-04-24",
                "final_composite_score": 1.0,
                "technical_composite_score": 1.0,
                "coverage_metric": 0.5,
                "valid_score_count": 1,
            },
            {
                "rank": 2,
                "ticker": "000660",
                "date": "2026-04-24",
                "final_composite_score": 0.5,
                "technical_composite_score": 0.5,
                "coverage_metric": 1.0,
                "valid_score_count": 3,
            },
        ]
    )

    assert resolve_official_ranking_basis("커버리지") == "coverage_metric"
    display = sort_official_ranking_for_display(frame, "커버리지")

    assert display["ticker"].tolist() == ["000660", "005930"]
    assert display["rank"].tolist() == [2, 1]


def test_gui_mvp_launcher_builds_stable_viewer_commands() -> None:
    assert build_viewer_command("chart", python_executable="python") == (
        "python",
        "-m",
        "gui_mvp",
        "chart",
    )
    assert [spec.key for spec in build_launch_specs(python_executable="python")] == [
        "chart",
        "backtest",
    ]


def test_gui_mvp_help_does_not_start_event_loop() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "gui_mvp", "--help"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "launcher|chart|backtest" in completed.stdout
