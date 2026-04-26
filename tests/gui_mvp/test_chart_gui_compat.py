from __future__ import annotations

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
from gui_mvp.chart_topn import Top5App  # noqa: E402


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


def test_chart_topn_number_formatters_tolerate_blank_values() -> None:
    assert Top5App._format_plain_number("") == ""
    assert Top5App._format_plain_number(pd.NA) == ""
    assert Top5App._format_signed_number("") == ""
    assert Top5App._format_signed_number(pd.NA) == ""
