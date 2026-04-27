from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pandas as pd


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
    pd.DataFrame(
        [
            {
                "ticker": "5930",
                "date": "2026-04-24",
                "rank": 1,
                "technical_composite_score": 1.25,
                "final_composite_score": 1.25,
                "coverage_metric": 1.0,
                "data_quality_flag": "valid",
                "warmup_status": "ready",
                "coverage_status": "adequate",
                "ranking_validity_flag": "valid",
                "valid_score_count": 3,
                "expected_score_count": 3,
                "neutral_shrinkage_count": 0,
                "review_routed_score_count": 5,
                "final_score_policy": "technical_only_no_valuation",
                "technical_only_notice": "kospi200_technical_only_mvp_no_valuation_or_fundamental_activation",
            },
            {
                "ticker": "000660",
                "date": "2026-04-24",
                "rank": 2,
                "technical_composite_score": 0.5,
                "final_composite_score": 0.5,
                "coverage_metric": 0.6667,
                "data_quality_flag": "partial",
                "warmup_status": "ready",
                "coverage_status": "partial",
                "ranking_validity_flag": "partial",
                "valid_score_count": 2,
                "expected_score_count": 3,
                "neutral_shrinkage_count": 1,
                "review_routed_score_count": 5,
                "final_score_policy": "technical_only_no_valuation",
                "technical_only_notice": "kospi200_technical_only_mvp_no_valuation_or_fundamental_activation",
            },
        ]
    ).to_csv(path, index=False)

    frame = load_official_ranking_csv(path)

    assert frame.iloc[0]["ticker"] == "005930"
    assert frame.iloc[0]["final_composite_score"] == 1.25


def test_official_ranking_auto_discovery_uses_valid_latest_csv(tmp_path: Path) -> None:
    valid_path = tmp_path / "latest_ranking.csv"
    invalid_path = tmp_path / "latest_top.csv"
    pd.DataFrame([{"종목코드": "005930", "점수": 0.0}]).to_csv(invalid_path, index=False)
    pd.DataFrame(
        [
            {
                "ticker": "005930",
                "date": "2026-04-24",
                "rank": 1,
                "technical_composite_score": 1.25,
                "final_composite_score": 1.25,
                "coverage_metric": 1.0,
                "data_quality_flag": "valid",
                "warmup_status": "ready",
                "coverage_status": "adequate",
                "ranking_validity_flag": "valid",
                "valid_score_count": 3,
                "expected_score_count": 3,
                "neutral_shrinkage_count": 0,
                "review_routed_score_count": 5,
                "final_score_policy": "technical_only_no_valuation",
                "technical_only_notice": "kospi200_technical_only_mvp_no_valuation_or_fundamental_activation",
            },
        ]
    ).to_csv(valid_path, index=False)

    found = find_latest_official_ranking_csv((tmp_path,))

    assert found == valid_path


def test_official_ranking_csv_list_supports_in_gui_selection(tmp_path: Path) -> None:
    first_path = tmp_path / "old_latest_ranking.csv"
    second_path = tmp_path / "new_latest_ranking.csv"
    rows = [
        {
            "ticker": "005930",
            "date": "2026-04-24",
            "rank": 1,
            "technical_composite_score": 1.25,
            "final_composite_score": 1.25,
            "coverage_metric": 1.0,
            "data_quality_flag": "valid",
            "warmup_status": "ready",
            "coverage_status": "adequate",
            "ranking_validity_flag": "valid",
            "valid_score_count": 3,
            "expected_score_count": 3,
            "neutral_shrinkage_count": 0,
            "review_routed_score_count": 5,
            "final_score_policy": "technical_only_no_valuation",
            "technical_only_notice": "kospi200_technical_only_mvp_no_valuation_or_fundamental_activation",
        },
    ]
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
