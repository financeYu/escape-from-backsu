from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gui_mvp.backtest_viewer import (  # noqa: E402
    BacktestCsvSelection,
    BacktestEvaluationApp,
    BacktestEvaluationFrame,
    format_percent,
    run_backtest_from_csv,
    run_backtest_from_frames,
    summarize_backtest_result,
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


def test_format_percent_handles_optional_values() -> None:
    assert format_percent(None) == ""
    assert format_percent(0.1234) == "12.34%"


def test_backtest_app_alias_keeps_compatibility() -> None:
    assert BacktestEvaluationApp is BacktestEvaluationFrame
