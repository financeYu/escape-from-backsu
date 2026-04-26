"""Conservative Step 17 backtest runner.

This module evaluates frozen upstream ranking snapshots against OHLCV prices.
It does not call score formula modules, mutate upstream ranking/report outputs,
or use valuation/fundamental data.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from src.backtest.contracts import (
    DEFAULT_DATA_LIMITATION_FLAGS,
    STEP17_BACKTEST_NOTICE,
    BacktestConfig,
    BacktestLimitationFlag,
    BacktestPeriodResult,
    BacktestSecurityResult,
    BacktestSummary,
    ConservativeBacktestResult,
    coerce_frame,
    date_string,
    is_upstream_blocked,
    safe_float,
    safe_int,
    validate_backtest_price_input,
    validate_backtest_ranking_input,
)
from src.preprocess.schema_validator import KOSPI200_SYMBOL_POLICY, SymbolPolicy


def run_conservative_backtest(
    ranking_snapshots: pd.DataFrame | Iterable[Mapping[str, Any]],
    prices: pd.DataFrame | Iterable[Mapping[str, Any]],
    *,
    config: BacktestConfig | Mapping[str, Any] | None = None,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> ConservativeBacktestResult:
    """Run a deterministic, evaluation-only Step 17 backtest.

    Selection is based only on upstream rank. Realized holding-period returns
    are computed only inside the returned Step 17 result objects.
    """

    resolved_config = _resolve_config(config)
    ranking_frame = coerce_frame(
        ranking_snapshots,
        context="Step 17 ranking snapshots",
    )
    price_frame = coerce_frame(prices, context="Step 17 OHLCV prices")
    date_column, rank_column = validate_backtest_ranking_input(
        ranking_frame,
        symbol_policy=symbol_policy,
    )
    validate_backtest_price_input(price_frame, symbol_policy=symbol_policy)

    prepared_rankings = _prepare_ranking_frame(
        ranking_frame,
        date_column=date_column,
        rank_column=rank_column,
    )
    prepared_prices = _prepare_price_frame(price_frame)
    price_by_ticker = {
        ticker: group.reset_index(drop=True)
        for ticker, group in prepared_prices.groupby("ticker", sort=True)
    }

    period_results = tuple(
        _evaluate_period(
            date,
            prepared_rankings.loc[prepared_rankings["_decision_ts"].eq(date)],
            price_by_ticker=price_by_ticker,
            config=resolved_config,
        )
        for date in _rebalance_dates(prepared_rankings, resolved_config)
    )
    summary = _build_summary(period_results, resolved_config)
    limitation_flags = _dedupe_flags(
        (*resolved_config.limitation_flags, *summary.limitation_flags)
    )
    metadata = {
        "step": "Step 17",
        "engine": "conservative_backtest_core",
        "boundary_notice": STEP17_BACKTEST_NOTICE,
        "upstream_inputs": "Step 15/16-compatible technical snapshots are read-only",
        "valuation_fundamental_status": "deferred_to_step18",
        "selection_policy": "top_n_by_upstream_rank_only",
        "weight_method": resolved_config.weight_method,
    }
    return ConservativeBacktestResult(
        config=resolved_config,
        period_results=period_results,
        summary=summary,
        metadata=metadata,
        limitation_flags=limitation_flags,
    )


def _resolve_config(config: BacktestConfig | Mapping[str, Any] | None) -> BacktestConfig:
    if config is None:
        return BacktestConfig()
    if isinstance(config, BacktestConfig):
        return config
    return BacktestConfig.from_mapping(config)


def _prepare_ranking_frame(
    frame: pd.DataFrame,
    *,
    date_column: str,
    rank_column: str,
) -> pd.DataFrame:
    prepared = frame.copy(deep=True)
    prepared["_decision_ts"] = pd.to_datetime(prepared[date_column], errors="raise").dt.normalize()
    prepared["_upstream_rank"] = pd.to_numeric(prepared[rank_column], errors="coerce")
    if prepared.duplicated(["ticker", "_decision_ts"]).any():
        raise ValueError("Step 17 ranking input contains duplicate ticker/date rows.")
    return prepared.sort_values(
        by=["_decision_ts", "_upstream_rank", "ticker"],
        ascending=[True, True, True],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)


def _prepare_price_frame(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.copy(deep=True)
    prepared["date"] = pd.to_datetime(prepared["date"], errors="raise").dt.normalize()
    for column in ("open", "high", "low", "close", "volume"):
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    if prepared.duplicated(["ticker", "date"]).any():
        raise ValueError("Step 17 price input contains duplicate ticker/date rows.")
    return prepared.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def _rebalance_dates(frame: pd.DataFrame, config: BacktestConfig) -> tuple[pd.Timestamp, ...]:
    dates = tuple(pd.Timestamp(date) for date in sorted(frame["_decision_ts"].unique()))
    if config.rebalance_frequency in {"every_ranking_date", "daily"}:
        return dates
    selected: list[pd.Timestamp] = []
    seen: set[tuple[int, int]] = set()
    for date in dates:
        if config.rebalance_frequency == "weekly":
            iso = date.isocalendar()
            key = (int(iso.year), int(iso.week))
        else:
            key = (int(date.year), int(date.month))
        if key in seen:
            continue
        seen.add(key)
        selected.append(date)
    return tuple(selected)


def _evaluate_period(
    decision_ts: pd.Timestamp,
    rows: pd.DataFrame,
    *,
    price_by_ticker: Mapping[str, pd.DataFrame],
    config: BacktestConfig,
) -> BacktestPeriodResult:
    decision_date = date_string(decision_ts)
    skipped_rows: list[BacktestSecurityResult] = []
    candidate_rows: list[pd.Series] = []

    for _, row in rows.iterrows():
        upstream_rank = safe_int(row["_upstream_rank"])
        if is_upstream_blocked(row):
            skipped_rows.append(
                _skipped_result(
                    row,
                    decision_date=decision_date,
                    upstream_rank=upstream_rank,
                    reason=BacktestLimitationFlag.UPSTREAM_ROW_BLOCKED,
                    config=config,
                )
            )
            continue
        if upstream_rank is None:
            skipped_rows.append(
                _skipped_result(
                    row,
                    decision_date=decision_date,
                    upstream_rank=None,
                    reason=BacktestLimitationFlag.MISSING_UPSTREAM_RANK,
                    config=config,
                )
            )
            continue
        candidate_rows.append(row)

    selected_rows = tuple(
        sorted(
            candidate_rows,
            key=lambda row: (float(row["_upstream_rank"]), str(row["ticker"])),
        )[: config.top_n]
    )
    weight = (1.0 / len(selected_rows)) if selected_rows else None
    selected_results = tuple(
        _evaluate_security(
            row,
            decision_ts=decision_ts,
            decision_date=decision_date,
            price_history=price_by_ticker.get(str(row["ticker"])),
            weight=weight,
            config=config,
        )
        for row in selected_rows
    )
    all_results = (*skipped_rows, *selected_results)
    valid_results = tuple(
        result
        for result in selected_results
        if not result.skipped and result.realized_holding_return is not None
    )
    period_return = None
    if selected_rows:
        period_return = sum(
            (result.backtest_weight or 0.0) * (result.realized_holding_return or 0.0)
            for result in selected_results
        )
    limitation_flags = _dedupe_flags(
        (
            *config.limitation_flags,
            *(
                flag
                for result in all_results
                for flag in result.limitation_flags
            ),
        )
    )
    return BacktestPeriodResult(
        decision_date=decision_date,
        selected_security_count=len(selected_rows),
        valid_security_count=len(valid_results),
        skipped_security_count=sum(1 for result in all_results if result.skipped),
        backtest_period_return=period_return,
        limitation_flags=limitation_flags,
        security_results=all_results,
    )


def _evaluate_security(
    row: pd.Series,
    *,
    decision_ts: pd.Timestamp,
    decision_date: str,
    price_history: pd.DataFrame | None,
    weight: float | None,
    config: BacktestConfig,
) -> BacktestSecurityResult:
    ticker = str(row["ticker"])
    upstream_rank = safe_int(row["_upstream_rank"])
    location = _price_location(
        price_history,
        decision_ts=decision_ts,
        config=config,
    )
    flags = list(location["flags"])
    execution_date = location["execution_date"]
    exit_date = location["exit_date"]
    execution_price = location["execution_price"]
    exit_price = location["exit_price"]

    if flags:
        if config.missing_price_policy == "raise":
            raise ValueError(
                "Step 17 price lookup failed for "
                f"{ticker} on {decision_date}: {', '.join(flags)}"
            )
        return BacktestSecurityResult(
            ticker=ticker,
            decision_date=decision_date,
            upstream_rank=upstream_rank,
            selected=True,
            skipped=True,
            skip_reasons=tuple(flags),
            limitation_flags=_dedupe_flags((*config.limitation_flags, *flags)),
            execution_date=execution_date,
            exit_date=exit_date,
            execution_price=execution_price,
            exit_price=exit_price,
            backtest_weight=weight,
            transaction_cost_bps=config.transaction_cost_bps,
            slippage_bps=config.slippage_bps,
        )

    gross_return = (exit_price / execution_price) - 1.0
    round_trip_drag = 2.0 * (config.transaction_cost_bps + config.slippage_bps) / 10_000.0
    realized_holding_return = gross_return - round_trip_drag
    return BacktestSecurityResult(
        ticker=ticker,
        decision_date=decision_date,
        upstream_rank=upstream_rank,
        selected=True,
        skipped=False,
        limitation_flags=config.limitation_flags,
        execution_date=execution_date,
        exit_date=exit_date,
        execution_price=execution_price,
        exit_price=exit_price,
        backtest_weight=weight,
        realized_holding_return=realized_holding_return,
        evaluation_return=realized_holding_return,
        evaluation_start_date=execution_date,
        evaluation_end_date=exit_date,
        transaction_cost_bps=config.transaction_cost_bps,
        slippage_bps=config.slippage_bps,
    )


def _price_location(
    price_history: pd.DataFrame | None,
    *,
    decision_ts: pd.Timestamp,
    config: BacktestConfig,
) -> dict[str, Any]:
    flags: list[str] = []
    if price_history is None or price_history.empty:
        return {
            "execution_date": None,
            "exit_date": None,
            "execution_price": None,
            "exit_price": None,
            "flags": (
                BacktestLimitationFlag.INSUFFICIENT_PRICE_HISTORY,
                BacktestLimitationFlag.MISSING_EXECUTION_PRICE,
                BacktestLimitationFlag.MISSING_EXIT_PRICE,
            ),
        }

    dates = price_history["date"].to_numpy()
    start_index = int(np.searchsorted(dates, decision_ts.to_datetime64(), side="left"))
    if start_index >= len(price_history):
        return {
            "execution_date": None,
            "exit_date": None,
            "execution_price": None,
            "exit_price": None,
            "flags": (
                BacktestLimitationFlag.INSUFFICIENT_PRICE_HISTORY,
                BacktestLimitationFlag.MISSING_EXECUTION_PRICE,
                BacktestLimitationFlag.MISSING_EXIT_PRICE,
            ),
        }
    execution_index = start_index + config.execution_lag_days
    if execution_index >= len(price_history):
        return {
            "execution_date": None,
            "exit_date": None,
            "execution_price": None,
            "exit_price": None,
            "flags": (
                BacktestLimitationFlag.INSUFFICIENT_PRICE_HISTORY,
                BacktestLimitationFlag.MISSING_EXECUTION_PRICE,
                BacktestLimitationFlag.MISSING_EXIT_PRICE,
            ),
        }
    exit_index = execution_index + config.holding_period_days
    execution_row = price_history.iloc[execution_index]
    execution_date = date_string(execution_row["date"])
    execution_price = safe_float(execution_row[config.execution_price_policy])
    if execution_price is None or execution_price <= 0:
        flags.append(BacktestLimitationFlag.MISSING_EXECUTION_PRICE)

    if exit_index >= len(price_history):
        flags.extend(
            (
                BacktestLimitationFlag.INSUFFICIENT_PRICE_HISTORY,
                BacktestLimitationFlag.MISSING_EXIT_PRICE,
            )
        )
        return {
            "execution_date": execution_date,
            "exit_date": None,
            "execution_price": execution_price,
            "exit_price": None,
            "flags": tuple(flags),
        }

    exit_row = price_history.iloc[exit_index]
    exit_date = date_string(exit_row["date"])
    exit_price = safe_float(exit_row[config.exit_price_policy])
    if exit_price is None or exit_price <= 0:
        flags.append(BacktestLimitationFlag.MISSING_EXIT_PRICE)
    return {
        "execution_date": execution_date,
        "exit_date": exit_date,
        "execution_price": execution_price,
        "exit_price": exit_price,
        "flags": tuple(_dedupe_flags(flags)),
    }


def _skipped_result(
    row: pd.Series,
    *,
    decision_date: str,
    upstream_rank: int | None,
    reason: str,
    config: BacktestConfig,
) -> BacktestSecurityResult:
    return BacktestSecurityResult(
        ticker=str(row["ticker"]),
        decision_date=decision_date,
        upstream_rank=upstream_rank,
        selected=False,
        skipped=True,
        skip_reasons=(reason,),
        limitation_flags=_dedupe_flags((*config.limitation_flags, reason)),
        transaction_cost_bps=config.transaction_cost_bps,
        slippage_bps=config.slippage_bps,
    )


def _build_summary(
    period_results: Sequence[BacktestPeriodResult],
    config: BacktestConfig,
) -> BacktestSummary:
    period_returns = [
        result.backtest_period_return
        for result in period_results
        if result.backtest_period_return is not None
    ]
    mean_period_return = (
        sum(period_returns) / len(period_returns) if period_returns else None
    )
    cumulative_return = _cumulative_return(period_returns)
    limitation_flags = _dedupe_flags(
        (
            *DEFAULT_DATA_LIMITATION_FLAGS,
            *config.limitation_flags,
            *(
                flag
                for period in period_results
                for flag in period.limitation_flags
            ),
        )
    )
    return BacktestSummary(
        period_count=len(period_results),
        selected_security_count=sum(period.selected_security_count for period in period_results),
        valid_security_count=sum(period.valid_security_count for period in period_results),
        skipped_security_count=sum(period.skipped_security_count for period in period_results),
        mean_period_return=mean_period_return,
        cumulative_return=cumulative_return,
        average_turnover_proxy=_average_turnover_proxy(period_results),
        max_drawdown=_max_drawdown(period_returns),
        limitation_flags=limitation_flags,
    )


def _cumulative_return(period_returns: Sequence[float]) -> float | None:
    if not period_returns:
        return None
    equity = 1.0
    for value in period_returns:
        equity *= 1.0 + value
    return equity - 1.0


def _max_drawdown(period_returns: Sequence[float]) -> float | None:
    if not period_returns:
        return None
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in period_returns:
        equity *= 1.0 + value
        peak = max(peak, equity)
        drawdown = (equity / peak) - 1.0
        max_drawdown = min(max_drawdown, drawdown)
    return max_drawdown


def _average_turnover_proxy(
    period_results: Sequence[BacktestPeriodResult],
) -> float | None:
    previous: dict[str, float] | None = None
    turnovers: list[float] = []
    for period in period_results:
        weights = {
            result.ticker: float(result.backtest_weight)
            for result in period.security_results
            if result.selected and result.backtest_weight is not None
        }
        if previous is not None:
            tickers = set(previous).union(weights)
            turnover = 0.5 * sum(
                abs(weights.get(ticker, 0.0) - previous.get(ticker, 0.0))
                for ticker in tickers
            )
            turnovers.append(turnover)
        previous = weights
    if not turnovers:
        return None
    return sum(turnovers) / len(turnovers)


def _dedupe_flags(flags: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(flag) for flag in flags if str(flag)))


__all__ = ("run_conservative_backtest",)
