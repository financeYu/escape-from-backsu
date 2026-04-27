from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui_mvp.backtest_viewer import (  # noqa: E402
    BacktestCsvSelection,
    build_equity_curve,
    export_backtest_result_bundle,
    format_percent,
    read_backtest_csv,
    run_backtest_from_csv,
    run_backtest_from_frames,
    summarize_backtest_result,
    validate_backtest_export_dir,
)


def ranking_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "005930",
                "ranking_date": "2026-01-02",
                "rank": 1,
                "technical_composite_score": 0.1,
                "final_composite_score": 0.1,
                "ranking_validity_flag": "valid",
            }
        ]
    )


def price_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "005930",
                "date": "2026-01-02",
                "open": 100.0,
                "high": 100.0,
                "low": 100.0,
                "close": 100.0,
                "volume": 100,
            },
            {
                "ticker": "005930",
                "date": "2026-01-05",
                "open": 100.0,
                "high": 100.0,
                "low": 100.0,
                "close": 100.0,
                "volume": 100,
            },
            {
                "ticker": "005930",
                "date": "2026-01-06",
                "open": 110.0,
                "high": 110.0,
                "low": 110.0,
                "close": 110.0,
                "volume": 100,
            },
        ]
    )


def test_backtest_viewer_runs_evaluation_only_from_frames() -> None:
    result = run_backtest_from_frames(
        ranking_rows(),
        price_rows(),
        config={
            "top_n": 1,
            "holding_period_days": 1,
            "execution_lag_days": 1,
            "transaction_cost_bps": 0.0,
            "slippage_bps": 0.0,
        },
    )

    summary_rows = dict(summarize_backtest_result(result))

    assert summary_rows["boundary_notice"] == "Step 17 conservative backtest evaluation only"
    assert summary_rows["selected_security_count"] == "1"
    assert "realized_holding_return" not in ranking_rows().columns


def test_backtest_csv_loader_preserves_ticker_leading_zero(tmp_path: Path) -> None:
    ranking_path = tmp_path / "ranking.csv"
    price_path = tmp_path / "prices.csv"
    ranking_rows().to_csv(ranking_path, index=False)
    price_rows().to_csv(price_path, index=False)

    result = run_backtest_from_csv(
        BacktestCsvSelection(ranking_path, price_path),
        config={
            "top_n": 1,
            "holding_period_days": 1,
            "execution_lag_days": 1,
            "transaction_cost_bps": 0.0,
            "slippage_bps": 0.0,
        },
    )

    assert result.to_security_frame().iloc[0]["ticker"] == "005930"


def test_backtest_csv_loader_restores_six_digit_ticker_width(tmp_path: Path) -> None:
    path = tmp_path / "ranking.csv"
    pd.DataFrame([{"ticker": "5930"}]).to_csv(path, index=False)

    frame = read_backtest_csv(path)

    assert frame.iloc[0]["ticker"] == "005930"


def test_format_percent_handles_optional_values() -> None:
    assert format_percent(None) == ""
    assert format_percent(0.1234) == "12.34%"


def test_backtest_viewer_builds_display_only_equity_curve() -> None:
    frame = pd.DataFrame(
        [
            {"decision_date": "2026-01-02", "backtest_period_return": 0.10},
            {"decision_date": "2026-01-03", "backtest_period_return": None},
            {"decision_date": "2026-01-04", "backtest_period_return": -0.05},
        ]
    )

    equity = build_equity_curve(frame)

    assert equity["equity"].tolist() == pytest.approx([1.1, 1.1, 1.045])


def test_backtest_viewer_exports_result_bundle(tmp_path: Path) -> None:
    result = run_backtest_from_frames(
        ranking_rows(),
        price_rows(),
        config={
            "top_n": 1,
            "holding_period_days": 1,
            "execution_lag_days": 1,
            "transaction_cost_bps": 0.0,
            "slippage_bps": 0.0,
        },
    )

    output_dir = PROJECT_ROOT / "reports" / "backtest" / "generated" / "gui_mvp" / tmp_path.name
    paths = export_backtest_result_bundle(result, output_dir)

    assert set(paths) == {"summary", "periods", "securities", "equity"}
    assert paths["summary"].read_text(encoding="utf-8")
    assert paths["equity"].exists()


def test_backtest_export_rejects_repo_source_paths() -> None:
    with pytest.raises(ValueError, match="reports/backtest/generated"):
        validate_backtest_export_dir(PROJECT_ROOT / "tests" / "gui_mvp")


def test_backtest_export_allows_ignored_generated_path() -> None:
    resolved = validate_backtest_export_dir(
        PROJECT_ROOT / "reports" / "backtest" / "generated" / "gui_mvp"
    )

    assert resolved.name == "gui_mvp"
