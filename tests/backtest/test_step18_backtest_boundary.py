from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest import BacktestConfig, run_conservative_backtest  # noqa: E402
from src.validation.step17_backtest_guardrails import validate_step17_backtest_input  # noqa: E402
from src.validation.step18_valuation_fundamental_guardrails import (  # noqa: E402
    validate_step18_backtest_candidate_availability,
)


def ranking_rows(**overrides: object) -> pd.DataFrame:
    rows = [
        {
            "ticker": "005930",
            "ranking_date": "2026-04-01",
            "rank": 1,
            "technical_composite_score": 1.2,
            "final_composite_score": 1.2,
            "ranking_validity_flag": "valid",
        },
        {
            "ticker": "000660",
            "ranking_date": "2026-04-01",
            "rank": 2,
            "technical_composite_score": 0.8,
            "final_composite_score": 0.8,
            "ranking_validity_flag": "valid",
        },
    ]
    for row in rows:
        row.update(overrides)
    return pd.DataFrame(rows)


def price_rows() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for ticker, execution_open, exit_close in (
        ("005930", 100.0, 110.0),
        ("000660", 200.0, 210.0),
    ):
        rows.extend(
            [
                {
                    "ticker": ticker,
                    "date": "2026-04-01",
                    "open": 1.0,
                    "high": 1.0,
                    "low": 1.0,
                    "close": 1.0,
                    "volume": 100,
                },
                {
                    "ticker": ticker,
                    "date": "2026-04-02",
                    "open": execution_open,
                    "high": execution_open,
                    "low": execution_open,
                    "close": execution_open,
                    "volume": 100,
                },
                {
                    "ticker": ticker,
                    "date": "2026-04-03",
                    "open": exit_close,
                    "high": exit_close,
                    "low": exit_close,
                    "close": exit_close,
                    "volume": 100,
                },
            ]
        )
    return pd.DataFrame(rows)


def candidate_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "symbol": "005930",
        "company_name": "Samsung Electronics",
        "metric_name": "pbr",
        "metric_value": 1.2,
        "metric_unit": "ratio",
        "metric_category": "valuation",
        "fiscal_period": "2025Q4",
        "report_date": "2026-03-15",
        "available_date": "2026-04-10",
        "source": "synthetic_fixture",
        "quality_flags": ("synthetic", "candidate_only"),
    }
    record.update(overrides)
    return record


def one_period_config() -> BacktestConfig:
    return BacktestConfig(
        top_n=1,
        holding_period_days=1,
        execution_lag_days=1,
        transaction_cost_bps=0.0,
        slippage_bps=0.0,
    )


def test_step17_backtest_remains_technical_rank_only_with_candidate_sidecar() -> None:
    result = run_conservative_backtest(
        ranking_rows(),
        price_rows(),
        config=one_period_config(),
    )

    validate_step18_backtest_candidate_availability(
        [candidate_record(available_date="2026-03-31")],
        decision_date="2026-04-01",
    )
    security_frame = result.to_security_frame()

    assert security_frame.loc[security_frame["selected"].eq(True), "ticker"].tolist() == ["005930"]
    assert "per" not in security_frame.columns
    assert "pbr" not in security_frame.columns


def test_candidate_records_are_rejected_before_backtest_decision_availability() -> None:
    with pytest.raises(ValueError, match="not available for evaluation_date"):
        validate_step18_backtest_candidate_availability(
            [candidate_record(available_date="2026-04-10")],
            decision_date="2026-04-01",
        )


@pytest.mark.parametrize("column", ("per", "pbr", "roe", "fundamental_margin"))
def test_candidate_columns_are_rejected_as_step17_backtest_inputs(column: str) -> None:
    frame = ranking_rows()
    frame[column] = 1.0

    with pytest.raises(ValueError, match="forbidden Step 17 fields"):
        validate_step17_backtest_input(frame)
    with pytest.raises(ValueError, match="forbidden columns"):
        run_conservative_backtest(frame, price_rows(), config=one_period_config())
