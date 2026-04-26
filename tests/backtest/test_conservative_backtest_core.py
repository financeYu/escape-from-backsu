from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp import (  # noqa: E402
    BacktestConfig,
    BacktestLimitationFlag,
    run_conservative_backtest,
)
from Quant_mvp.backtest_mvp.contracts import assert_ticker_strings  # noqa: E402
from src.preprocess.schema_validator import GENERIC_EXCHANGE_SYMBOL_POLICY  # noqa: E402


def ranking_rows(**overrides: object) -> pd.DataFrame:
    rows: list[dict[str, object]] = [
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
        {
            "ticker": "035420",
            "ranking_date": "2026-01-02",
            "rank": 3,
            "technical_composite_score": 0.90,
            "final_composite_score": 0.90,
            "ranking_validity_flag": "valid",
        },
    ]
    for row in rows:
        row.update(overrides)
    return pd.DataFrame(rows)


def price_rows(**overrides: object) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    prices = {
        "005930": (100.0, 110.0),
        "000660": (200.0, 240.0),
        "035420": (50.0, 150.0),
    }
    for ticker, (execution_open, exit_close) in prices.items():
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
    for row in rows:
        row.update(overrides)
    return pd.DataFrame(rows)


def one_period_config(**overrides: object) -> BacktestConfig:
    values: dict[str, object] = {
        "top_n": 2,
        "holding_period_days": 1,
        "execution_lag_days": 1,
        "transaction_cost_bps": 0.0,
        "slippage_bps": 0.0,
    }
    values.update(overrides)
    return BacktestConfig(**values)


def test_default_backtest_config_file_loads() -> None:
    config = BacktestConfig.from_toml_file(
        PROJECT_ROOT / "Quant_mvp" / "backtest_mvp" / "config" / "backtest.toml"
    )

    assert config.weight_method == "equal_weight"
    assert config.missing_price_policy == "flag_and_skip"


def selected_tickers(result) -> list[str]:
    security_frame = result.to_security_frame()
    selected = security_frame.loc[security_frame["selected"].eq(True)]
    return selected["ticker"].tolist()


def test_no_reranking_by_realized_returns() -> None:
    result = run_conservative_backtest(
        ranking_rows(),
        price_rows(),
        config=one_period_config(),
    )

    assert selected_tickers(result) == ["005930", "000660"]
    assert "035420" not in selected_tickers(result)


def test_equal_weight_top_n_selection() -> None:
    result = run_conservative_backtest(
        ranking_rows(),
        price_rows(),
        config=one_period_config(),
    )

    security_frame = result.to_security_frame()
    selected = security_frame.loc[security_frame["selected"].eq(True)]

    assert selected["backtest_weight"].tolist() == [0.5, 0.5]
    assert result.period_results[0].backtest_period_return == pytest.approx(0.15)


def test_execution_lag_days_respected() -> None:
    result = run_conservative_backtest(
        ranking_rows(),
        price_rows(),
        config=one_period_config(execution_lag_days=1),
    )

    security_frame = result.to_security_frame()
    selected = security_frame.loc[security_frame["ticker"].eq("005930")].iloc[0]

    assert selected["execution_date"] == "2026-01-05"
    assert selected["exit_date"] == "2026-01-06"


def test_missing_execution_price_creates_flag() -> None:
    prices = price_rows()
    mask = prices["ticker"].eq("005930") & prices["date"].eq("2026-01-05")
    prices.loc[mask, "open"] = None

    result = run_conservative_backtest(
        ranking_rows(),
        prices,
        config=one_period_config(),
    )

    row = result.to_security_frame().loc[lambda frame: frame["ticker"].eq("005930")].iloc[0]
    assert bool(row["skipped"]) is True
    assert BacktestLimitationFlag.MISSING_EXECUTION_PRICE in row["limitation_flags"]


def test_missing_exit_price_creates_flag() -> None:
    prices = price_rows()
    mask = prices["ticker"].eq("005930") & prices["date"].eq("2026-01-06")
    prices.loc[mask, "close"] = None

    result = run_conservative_backtest(
        ranking_rows(),
        prices,
        config=one_period_config(),
    )

    row = result.to_security_frame().loc[lambda frame: frame["ticker"].eq("005930")].iloc[0]
    assert bool(row["skipped"]) is True
    assert BacktestLimitationFlag.MISSING_EXIT_PRICE in row["limitation_flags"]


def test_costs_and_slippage_reduce_return_deterministically() -> None:
    no_cost = run_conservative_backtest(
        ranking_rows().head(1),
        price_rows(),
        config=one_period_config(top_n=1),
    )
    with_cost = run_conservative_backtest(
        ranking_rows().head(1),
        price_rows(),
        config=one_period_config(
            top_n=1,
            transaction_cost_bps=10.0,
            slippage_bps=5.0,
        ),
    )

    no_cost_return = no_cost.to_security_frame().iloc[0]["realized_holding_return"]
    with_cost_return = with_cost.to_security_frame().iloc[0]["realized_holding_return"]

    assert no_cost_return == pytest.approx(0.10)
    assert with_cost_return == pytest.approx(0.097)


def test_ticker_leading_zero_is_preserved() -> None:
    result = run_conservative_backtest(
        ranking_rows().head(1),
        price_rows(),
        config=one_period_config(top_n=1),
    )

    assert result.to_security_frame().iloc[0]["ticker"] == "005930"

    bad_ranking = pd.DataFrame(
        [
            {
                "ticker": 5930,
                "ranking_date": "2026-01-02",
                "rank": 1,
            }
        ]
    )
    with pytest.raises(ValueError, match="ticker values must be non-empty strings"):
        run_conservative_backtest(bad_ranking, price_rows(), config=one_period_config(top_n=1))


def test_backtest_contract_can_use_generic_symbol_policy_for_extension_contracts() -> None:
    tickers = pd.Series(["AAPL", "MSFT"], dtype="string")

    assert_ticker_strings(
        tickers,
        context="extension contract",
        symbol_policy=GENERIC_EXCHANGE_SYMBOL_POLICY,
    )
    with pytest.raises(ValueError, match="six-digit string format"):
        assert_ticker_strings(tickers, context="default contract")


def test_backtest_runner_can_use_generic_symbol_policy_for_extension_contracts() -> None:
    ranking = ranking_rows()
    ranking["ticker"] = ["AAPL", "MSFT", "NVDA"]
    prices = price_rows()
    prices["ticker"] = prices["ticker"].replace(
        {"005930": "AAPL", "000660": "MSFT", "035420": "NVDA"}
    )

    result = run_conservative_backtest(
        ranking,
        prices,
        config=one_period_config(),
        symbol_policy=GENERIC_EXCHANGE_SYMBOL_POLICY,
    )

    assert selected_tickers(result) == ["AAPL", "MSFT"]
    with pytest.raises(ValueError, match="six-digit string format"):
        run_conservative_backtest(ranking, prices, config=one_period_config())


def test_upstream_blocked_row_is_excluded_and_reported() -> None:
    ranking = ranking_rows().head(2)
    ranking.loc[0, "blocked"] = True

    result = run_conservative_backtest(
        ranking,
        price_rows(),
        config=one_period_config(top_n=1),
    )
    security_frame = result.to_security_frame()

    blocked = security_frame.loc[security_frame["ticker"].eq("005930")].iloc[0]
    selected = security_frame.loc[security_frame["selected"].eq(True)]

    assert bool(blocked["selected"]) is False
    assert BacktestLimitationFlag.UPSTREAM_ROW_BLOCKED in blocked["limitation_flags"]
    assert selected["ticker"].tolist() == ["000660"]


def test_realized_holding_return_stays_inside_step17_result_objects() -> None:
    ranking = ranking_rows()

    result = run_conservative_backtest(
        ranking,
        price_rows(),
        config=one_period_config(),
    )

    assert "realized_holding_return" in result.to_security_frame().columns
    assert "realized_holding_return" not in ranking.columns


@pytest.mark.parametrize(
    "column",
    (
        "future_return",
        "forward_return",
        "expected_return",
        "valuation_score",
        "PER",
        "PBR",
        "ROE",
        "market_cap",
    ),
)
def test_valuation_fundamental_and_forbidden_columns_are_not_accepted(column: str) -> None:
    ranking = ranking_rows()
    ranking[column] = 1

    with pytest.raises(ValueError, match="forbidden columns"):
        run_conservative_backtest(ranking, price_rows(), config=one_period_config())
