from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_gui.service import (  # noqa: E402
    BacktestInputPaths,
    BacktestRunRequest,
    build_equity_curve,
    export_result_bundle,
    run_backtest_from_csv,
)
from src.backtest import BacktestConfig  # noqa: E402


def test_gui_module_imports_without_starting_event_loop() -> None:
    import Quant_mvp.backtest_gui.app as app

    assert app.EVALUATION_ONLY_NOTICE.startswith("evaluation-only")


def _ranking_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "005930",
                "ranking_date": "2026-01-02",
                "rank": 1,
                "technical_composite_score": 0.10,
                "final_composite_score": 0.10,
                "ranking_validity_flag": "valid",
            },
            {
                "ticker": "000660",
                "ranking_date": "2026-01-02",
                "rank": 2,
                "technical_composite_score": 0.05,
                "final_composite_score": 0.05,
                "ranking_validity_flag": "valid",
            },
        ]
    )


def _price_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for ticker, execution_open, exit_close in (
        ("005930", 100.0, 110.0),
        ("000660", 200.0, 240.0),
    ):
        rows.extend(
            [
                {
                    "ticker": ticker,
                    "date": "2026-01-02",
                    "open": 1.0,
                    "high": 1.0,
                    "low": 1.0,
                    "close": 1.0,
                    "volume": 100,
                },
                {
                    "ticker": ticker,
                    "date": "2026-01-05",
                    "open": execution_open,
                    "high": execution_open,
                    "low": execution_open,
                    "close": execution_open,
                    "volume": 100,
                },
                {
                    "ticker": ticker,
                    "date": "2026-01-06",
                    "open": exit_close,
                    "high": exit_close,
                    "low": exit_close,
                    "close": exit_close,
                    "volume": 100,
                },
            ]
        )
    return pd.DataFrame(rows)


def _write_inputs(tmp_path: Path) -> BacktestInputPaths:
    ranking_csv = tmp_path / "ranking.csv"
    price_csv = tmp_path / "prices.csv"
    _ranking_frame().to_csv(ranking_csv, index=False)
    _price_frame().to_csv(price_csv, index=False)
    return BacktestInputPaths(ranking_csv=ranking_csv, price_csv=price_csv)


def test_run_backtest_from_csv_preserves_engine_selection_boundary(tmp_path: Path) -> None:
    request = BacktestRunRequest(
        inputs=_write_inputs(tmp_path),
        config=BacktestConfig(
            top_n=1,
            holding_period_days=1,
            execution_lag_days=1,
            transaction_cost_bps=0,
            slippage_bps=0,
        ),
    )

    artifacts = run_backtest_from_csv(request)

    selected = artifacts.security_frame.loc[artifacts.security_frame["selected"].eq(True)]
    assert selected["ticker"].tolist() == ["005930"]
    assert artifacts.summary["boundary_notice"].startswith("evaluation-only")
    assert artifacts.equity_frame["equity"].tolist() == pytest.approx([1.10])


def test_export_result_bundle_writes_generated_evaluation_files(tmp_path: Path) -> None:
    request = BacktestRunRequest(
        inputs=_write_inputs(tmp_path),
        config=BacktestConfig(
            top_n=2,
            holding_period_days=1,
            execution_lag_days=1,
            transaction_cost_bps=0,
            slippage_bps=0,
        ),
    )
    artifacts = run_backtest_from_csv(request)

    paths = export_result_bundle(artifacts, tmp_path / "generated")

    assert set(paths) == {"summary", "periods", "securities", "equity"}
    summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
    assert summary["metadata"]["selection_policy"] == "top_n_by_upstream_rank_only"
    assert paths["periods"].exists()
    assert paths["securities"].exists()
    assert paths["equity"].exists()


def test_forbidden_input_columns_are_still_rejected_by_engine(tmp_path: Path) -> None:
    ranking = _ranking_frame()
    ranking["expected_return"] = 0.10
    ranking_csv = tmp_path / "ranking.csv"
    price_csv = tmp_path / "prices.csv"
    ranking.to_csv(ranking_csv, index=False)
    _price_frame().to_csv(price_csv, index=False)

    request = BacktestRunRequest(
        inputs=BacktestInputPaths(ranking_csv=ranking_csv, price_csv=price_csv),
        config=BacktestConfig(top_n=1),
    )

    with pytest.raises(ValueError, match="forbidden columns"):
        run_backtest_from_csv(request)


def test_build_equity_curve_treats_missing_period_return_as_flat() -> None:
    frame = pd.DataFrame(
        [
            {"decision_date": "2026-01-02", "backtest_period_return": 0.10},
            {"decision_date": "2026-01-03", "backtest_period_return": None},
            {"decision_date": "2026-01-04", "backtest_period_return": -0.05},
        ]
    )

    equity = build_equity_curve(frame)

    assert equity["equity"].tolist() == pytest.approx([1.10, 1.10, 1.045])
