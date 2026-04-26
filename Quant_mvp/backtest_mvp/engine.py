"""Conservative Backtest MVP runner owned by Quant_mvp.

This module evaluates frozen upstream ranking snapshots against OHLCV prices.
It does not call score formula modules, mutate upstream ranking/report outputs,
or use valuation/fundamental data.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from Quant_mvp.backtest_mvp.contracts import (
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


_PriceLocation = dict[str, Any]


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
    prepared_rankings, price_by_ticker = _prepare_backtest_inputs(
        ranking_snapshots,
        prices,
        symbol_policy=symbol_policy,
    )
    period_results = _evaluate_periods(
        prepared_rankings,
        price_by_ticker=price_by_ticker,
        config=resolved_config,
    )
    summary = _build_summary(period_results, resolved_config)
    limitation_flags = _dedupe_flags(
        (*resolved_config.limitation_flags, *summary.limitation_flags)
    )
    return ConservativeBacktestResult(
        config=resolved_config,
        period_results=period_results,
        summary=summary,
        metadata=_build_result_metadata(resolved_config),
        limitation_flags=limitation_flags,
    )


def _prepare_backtest_inputs(
    ranking_snapshots: pd.DataFrame | Iterable[Mapping[str, Any]],
    prices: pd.DataFrame | Iterable[Mapping[str, Any]],
    *,
    symbol_policy: SymbolPolicy,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
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
        symbol_policy=symbol_policy,
    )
    prepared_prices = _prepare_price_frame(price_frame, symbol_policy=symbol_policy)
    return prepared_rankings, _price_history_by_ticker(prepared_prices)


def _price_history_by_ticker(prepared_prices: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        ticker: group.reset_index(drop=True)
        for ticker, group in prepared_prices.groupby("ticker", sort=True)
    }


def _evaluate_periods(
    prepared_rankings: pd.DataFrame,
    *,
    price_by_ticker: Mapping[str, pd.DataFrame],
    config: BacktestConfig,
) -> tuple[BacktestPeriodResult, ...]:
    return tuple(
        _evaluate_period(
            date,
            prepared_rankings.loc[prepared_rankings["_decision_ts"].eq(date)],
            price_by_ticker=price_by_ticker,
            config=config,
        )
        for date in _rebalance_dates(prepared_rankings, config)
    )


def _build_result_metadata(config: BacktestConfig) -> dict[str, str]:
    return {
        "step": "Step 17",
        "engine": "conservative_backtest_core",
        "boundary_notice": STEP17_BACKTEST_NOTICE,
        "upstream_inputs": "Step 15/16-compatible technical snapshots are read-only",
        "valuation_fundamental_status": "deferred_to_step18",
        "selection_policy": "top_n_by_upstream_rank_only",
        "weight_method": config.weight_method,
    }


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
    symbol_policy: SymbolPolicy,
) -> pd.DataFrame:
    prepared = frame.copy(deep=True)
    prepared["ticker"] = _normalize_tickers(prepared["ticker"], symbol_policy=symbol_policy)
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


def _prepare_price_frame(frame: pd.DataFrame, *, symbol_policy: SymbolPolicy) -> pd.DataFrame:
    prepared = frame.copy(deep=True)
    prepared["ticker"] = _normalize_tickers(prepared["ticker"], symbol_policy=symbol_policy)
    prepared["date"] = pd.to_datetime(prepared["date"], errors="raise").dt.normalize()
    for column in ("open", "high", "low", "close", "volume"):
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    if prepared.duplicated(["ticker", "date"]).any():
        raise ValueError("Step 17 price input contains duplicate ticker/date rows.")
    return prepared.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def _normalize_tickers(series: pd.Series, *, symbol_policy: SymbolPolicy) -> pd.Series:
    return series.map(symbol_policy.normalize).astype("string")


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
    skipped_rows, candidate_rows = _partition_period_rows(
        rows,
        decision_date=decision_date,
        config=config,
    )
    selected_rows = _select_top_ranked_rows(candidate_rows, config)
    weight = (1.0 / len(selected_rows)) if selected_rows else None
    selected_results = _evaluate_selected_rows(
        selected_rows,
        decision_ts=decision_ts,
        decision_date=decision_date,
        price_by_ticker=price_by_ticker,
        weight=weight,
        config=config,
    )
    all_results = (*skipped_rows, *selected_results)
    valid_results = _valid_security_results(selected_results)
    return BacktestPeriodResult(
        decision_date=decision_date,
        selected_security_count=len(selected_rows),
        valid_security_count=len(valid_results),
        skipped_security_count=sum(1 for result in all_results if result.skipped),
        backtest_period_return=_period_return(selected_rows, selected_results),
        limitation_flags=_period_limitation_flags(config, all_results),
        security_results=all_results,
    )


def _partition_period_rows(
    rows: pd.DataFrame,
    *,
    decision_date: str,
    config: BacktestConfig,
) -> tuple[tuple[BacktestSecurityResult, ...], tuple[pd.Series, ...]]:
    skipped_rows: list[BacktestSecurityResult] = []
    candidate_rows: list[pd.Series] = []
    for _, row in rows.iterrows():
        upstream_rank = safe_int(row["_upstream_rank"])
        skip_reason = _ranking_skip_reason(row, upstream_rank)
        if skip_reason:
            skipped_rows.append(
                _skipped_result(
                    row,
                    decision_date=decision_date,
                    upstream_rank=upstream_rank,
                    reason=skip_reason,
                    config=config,
                )
            )
            continue
        candidate_rows.append(row)
    return tuple(skipped_rows), tuple(candidate_rows)


def _ranking_skip_reason(row: pd.Series, upstream_rank: int | None) -> str | None:
    if is_upstream_blocked(row):
        return BacktestLimitationFlag.UPSTREAM_ROW_BLOCKED
    if upstream_rank is None:
        return BacktestLimitationFlag.MISSING_UPSTREAM_RANK
    return None


def _select_top_ranked_rows(
    candidate_rows: Sequence[pd.Series],
    config: BacktestConfig,
) -> tuple[pd.Series, ...]:
    return tuple(
        sorted(
            candidate_rows,
            key=lambda row: (float(row["_upstream_rank"]), str(row["ticker"])),
        )[: config.top_n]
    )


def _evaluate_selected_rows(
    selected_rows: Sequence[pd.Series],
    *,
    decision_ts: pd.Timestamp,
    decision_date: str,
    price_by_ticker: Mapping[str, pd.DataFrame],
    weight: float | None,
    config: BacktestConfig,
) -> tuple[BacktestSecurityResult, ...]:
    return tuple(
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


def _valid_security_results(
    selected_results: Sequence[BacktestSecurityResult],
) -> tuple[BacktestSecurityResult, ...]:
    return tuple(
        result
        for result in selected_results
        if not result.skipped and result.realized_holding_return is not None
    )


def _period_return(
    selected_rows: Sequence[pd.Series],
    selected_results: Sequence[BacktestSecurityResult],
) -> float | None:
    if not selected_rows:
        return None
    return sum(
        (result.backtest_weight or 0.0) * (result.realized_holding_return or 0.0)
        for result in selected_results
    )


def _period_limitation_flags(
    config: BacktestConfig,
    all_results: Sequence[BacktestSecurityResult],
) -> tuple[str, ...]:
    return _dedupe_flags(
        (
            *config.limitation_flags,
            *(flag for result in all_results for flag in result.limitation_flags),
        )
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
    flags = tuple(location["flags"])

    if flags:
        if config.missing_price_policy == "raise":
            raise ValueError(
                "Step 17 price lookup failed for "
                f"{ticker} on {decision_date}: {', '.join(flags)}"
            )
        return _price_skipped_security_result(
            ticker,
            decision_date=decision_date,
            upstream_rank=upstream_rank,
            location=location,
            flags=flags,
            weight=weight,
            config=config,
        )

    realized_holding_return = _realized_holding_return(
        execution_price=location["execution_price"],
        exit_price=location["exit_price"],
        config=config,
    )
    return _evaluated_security_result(
        ticker,
        decision_date=decision_date,
        upstream_rank=upstream_rank,
        location=location,
        weight=weight,
        realized_holding_return=realized_holding_return,
        config=config,
    )


def _price_skipped_security_result(
    ticker: str,
    *,
    decision_date: str,
    upstream_rank: int | None,
    location: _PriceLocation,
    flags: Sequence[str],
    weight: float | None,
    config: BacktestConfig,
) -> BacktestSecurityResult:
    return BacktestSecurityResult(
        ticker=ticker,
        decision_date=decision_date,
        upstream_rank=upstream_rank,
        selected=True,
        skipped=True,
        skip_reasons=tuple(flags),
        limitation_flags=_dedupe_flags((*config.limitation_flags, *flags)),
        execution_date=location["execution_date"],
        exit_date=location["exit_date"],
        execution_price=location["execution_price"],
        exit_price=location["exit_price"],
        backtest_weight=weight,
        transaction_cost_bps=config.transaction_cost_bps,
        slippage_bps=config.slippage_bps,
    )


def _evaluated_security_result(
    ticker: str,
    *,
    decision_date: str,
    upstream_rank: int | None,
    location: _PriceLocation,
    weight: float | None,
    realized_holding_return: float,
    config: BacktestConfig,
) -> BacktestSecurityResult:
    return BacktestSecurityResult(
        ticker=ticker,
        decision_date=decision_date,
        upstream_rank=upstream_rank,
        selected=True,
        skipped=False,
        limitation_flags=config.limitation_flags,
        execution_date=location["execution_date"],
        exit_date=location["exit_date"],
        execution_price=location["execution_price"],
        exit_price=location["exit_price"],
        backtest_weight=weight,
        realized_holding_return=realized_holding_return,
        evaluation_return=realized_holding_return,
        evaluation_start_date=location["execution_date"],
        evaluation_end_date=location["exit_date"],
        transaction_cost_bps=config.transaction_cost_bps,
        slippage_bps=config.slippage_bps,
    )


def _realized_holding_return(
    *,
    execution_price: float,
    exit_price: float,
    config: BacktestConfig,
) -> float:
    gross_return = (exit_price / execution_price) - 1.0
    round_trip_drag = 2.0 * (config.transaction_cost_bps + config.slippage_bps) / 10_000.0
    return gross_return - round_trip_drag


def _price_location(
    price_history: pd.DataFrame | None,
    *,
    decision_ts: pd.Timestamp,
    config: BacktestConfig,
) -> _PriceLocation:
    flags: list[str] = []
    execution_index = _execution_index(price_history, decision_ts, config)
    if execution_index is None or price_history is None:
        return _missing_price_location()

    execution_date, execution_price = _price_point(
        price_history,
        execution_index,
        config.execution_price_policy,
    )
    if execution_price is None or execution_price <= 0:
        flags.append(BacktestLimitationFlag.MISSING_EXECUTION_PRICE)

    exit_index = execution_index + config.holding_period_days
    if exit_index >= len(price_history):
        return _missing_exit_price_location(
            execution_date=execution_date,
            execution_price=execution_price,
            flags=flags,
        )

    exit_date, exit_price = _price_point(
        price_history,
        exit_index,
        config.exit_price_policy,
    )
    if exit_price is None or exit_price <= 0:
        flags.append(BacktestLimitationFlag.MISSING_EXIT_PRICE)

    return _price_location_payload(
        execution_date=execution_date,
        exit_date=exit_date,
        execution_price=execution_price,
        exit_price=exit_price,
        flags=tuple(_dedupe_flags(flags)),
    )


def _execution_index(
    price_history: pd.DataFrame | None,
    decision_ts: pd.Timestamp,
    config: BacktestConfig,
) -> int | None:
    if price_history is None or price_history.empty:
        return None
    dates = price_history["date"].to_numpy()
    start_index = int(np.searchsorted(dates, decision_ts.to_datetime64(), side="left"))
    execution_index = start_index + config.execution_lag_days
    if start_index >= len(price_history) or execution_index >= len(price_history):
        return None
    return execution_index


def _price_point(
    price_history: pd.DataFrame,
    row_index: int,
    price_policy: str,
) -> tuple[str, float | None]:
    row = price_history.iloc[row_index]
    return date_string(row["date"]), safe_float(row[price_policy])


def _missing_price_location() -> _PriceLocation:
    return _price_location_payload(
        execution_date=None,
        exit_date=None,
        execution_price=None,
        exit_price=None,
        flags=(
            BacktestLimitationFlag.INSUFFICIENT_PRICE_HISTORY,
            BacktestLimitationFlag.MISSING_EXECUTION_PRICE,
            BacktestLimitationFlag.MISSING_EXIT_PRICE,
        ),
    )


def _missing_exit_price_location(
    *,
    execution_date: str,
    execution_price: float | None,
    flags: list[str],
) -> _PriceLocation:
    flags.extend(
        (
            BacktestLimitationFlag.INSUFFICIENT_PRICE_HISTORY,
            BacktestLimitationFlag.MISSING_EXIT_PRICE,
        )
    )
    return _price_location_payload(
        execution_date=execution_date,
        exit_date=None,
        execution_price=execution_price,
        exit_price=None,
        flags=tuple(flags),
    )


def _price_location_payload(
    *,
    execution_date: str | None,
    exit_date: str | None,
    execution_price: float | None,
    exit_price: float | None,
    flags: Sequence[str],
) -> _PriceLocation:
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
