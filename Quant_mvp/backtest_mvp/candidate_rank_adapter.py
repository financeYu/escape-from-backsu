"""Build v0.3 candidate-only ranking snapshots from OHLCV prices.

The adapter converts predeclared StrategyCandidate rules into the ranking
snapshot shape consumed by the conservative backtest runner. It does not run a
backtest, optimize rules, write production rankings, or create adoption
decisions.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

from Quant_mvp.backtest_mvp.contracts import (
    validate_backtest_price_input,
    validate_backtest_ranking_input,
)
from src.preprocess.schema_validator import KOSPI200_SYMBOL_POLICY, SymbolPolicy


V0_3_RANKING_SNAPSHOT_NOTICE = (
    "v0.3 candidate ranking snapshot; evidence-only backtest input; "
    "not production ranking, not a score input, not a model feature source, "
    "not an adoption decision"
)

SUPPORTED_STRATEGY_TYPES = frozenset({"momentum", "reversal", "volatility", "other"})
EVALUABLE_CANDIDATE_STATUSES = frozenset({"evaluable"})


@dataclass(frozen=True)
class CandidateRankingSnapshotConfig:
    """Candidate-only signal-to-rank adapter assumptions."""

    momentum_window: int = 20
    reversal_window: int = 5
    volatility_window: int = 20
    rebalance_step_days: int = 20
    entry_percentile_threshold: float = 0.80
    include_blocked_rows: bool = True

    def __post_init__(self) -> None:
        if self.momentum_window < 1:
            raise ValueError("momentum_window must be at least 1")
        if self.reversal_window < 1:
            raise ValueError("reversal_window must be at least 1")
        if self.volatility_window < 2:
            raise ValueError("volatility_window must be at least 2")
        if self.rebalance_step_days < 1:
            raise ValueError("rebalance_step_days must be at least 1")
        if not 0.0 < self.entry_percentile_threshold <= 1.0:
            raise ValueError("entry_percentile_threshold must be in (0, 1]")


def build_candidate_ranking_snapshot(
    candidate_record: Mapping[str, Any],
    prices: pd.DataFrame | Iterable[Mapping[str, Any]],
    *,
    config: CandidateRankingSnapshotConfig | Mapping[str, Any] | None = None,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> pd.DataFrame:
    """Return a ranking snapshot for one ready v0.3 StrategyCandidate."""

    resolved_config = _resolve_config(config)
    candidate = _strategy_candidate_payload(candidate_record)
    _validate_candidate(candidate)
    price_frame = _prepare_price_frame(prices, symbol_policy=symbol_policy)

    strategy_type = _strategy_type(candidate)
    feature_frame = _candidate_feature_frame(
        price_frame,
        strategy_type=strategy_type,
        config=resolved_config,
    )
    ranking = _ranking_snapshot_frame(
        feature_frame,
        candidate=candidate,
        strategy_type=strategy_type,
        config=resolved_config,
    )
    validate_backtest_ranking_input(ranking, symbol_policy=symbol_policy)
    return ranking


def _resolve_config(
    config: CandidateRankingSnapshotConfig | Mapping[str, Any] | None,
) -> CandidateRankingSnapshotConfig:
    if config is None:
        return CandidateRankingSnapshotConfig()
    if isinstance(config, CandidateRankingSnapshotConfig):
        return config
    return CandidateRankingSnapshotConfig(**dict(config))


def _strategy_candidate_payload(candidate_record: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = candidate_record.get("strategy_candidate")
    if isinstance(nested, Mapping):
        return nested
    return candidate_record


def _validate_candidate(candidate: Mapping[str, Any]) -> None:
    if candidate.get("status") not in EVALUABLE_CANDIDATE_STATUSES:
        raise ValueError("v0.3 ranking snapshot requires an evaluable StrategyCandidate")
    data_requirements = {str(item) for item in _as_list(candidate.get("data_requirements"))}
    if "daily_ohlcv" not in data_requirements and "daily_ohlcv_candidate_review_only" not in data_requirements:
        raise ValueError("v0.3 ranking snapshot requires daily_ohlcv data")
    strategy_type = _strategy_type(candidate)
    if strategy_type not in SUPPORTED_STRATEGY_TYPES:
        raise ValueError(f"unsupported v0.3 strategy_type for OHLCV adapter: {strategy_type}")


def _strategy_type(candidate: Mapping[str, Any]) -> str:
    scope = candidate.get("experiment_scope")
    if isinstance(scope, Mapping) and scope.get("strategy_type"):
        return str(scope["strategy_type"])
    return str(candidate.get("strategy_type") or "other")


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _prepare_price_frame(
    prices: pd.DataFrame | Iterable[Mapping[str, Any]],
    *,
    symbol_policy: SymbolPolicy,
) -> pd.DataFrame:
    frame = prices.copy(deep=True) if isinstance(prices, pd.DataFrame) else pd.DataFrame(list(prices))
    validate_backtest_price_input(frame, symbol_policy=symbol_policy)
    prepared = frame.copy(deep=True)
    prepared["ticker"] = prepared["ticker"].map(symbol_policy.normalize).astype("string")
    prepared["date"] = pd.to_datetime(prepared["date"], errors="raise").dt.normalize()
    for column in ("open", "high", "low", "close", "volume"):
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
    return prepared.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def _candidate_feature_frame(
    prices: pd.DataFrame,
    *,
    strategy_type: str,
    config: CandidateRankingSnapshotConfig,
) -> pd.DataFrame:
    frame = prices[["ticker", "date", "close"]].copy(deep=True)
    grouped = frame.groupby("ticker", group_keys=False, sort=False)
    daily_return = grouped["close"].pct_change()
    frame["_return_20d"] = grouped["close"].pct_change(config.momentum_window)
    frame["_return_5d"] = grouped["close"].pct_change(config.reversal_window)
    frame["_volatility_20d"] = daily_return.groupby(frame["ticker"], group_keys=False).rolling(
        config.volatility_window
    ).std().reset_index(level=0, drop=True)

    if strategy_type == "reversal":
        frame["candidate_signal_value"] = -frame["_return_5d"]
        frame["candidate_signal_family"] = "short_horizon_reversal"
    elif strategy_type == "volatility":
        frame["candidate_signal_value"] = frame["_volatility_20d"]
        frame["candidate_signal_family"] = "rolling_volatility_state"
    else:
        frame["candidate_signal_value"] = frame["_return_20d"]
        frame["candidate_signal_family"] = (
            "medium_horizon_momentum" if strategy_type == "momentum" else "generic_ohlcv_return_proxy"
        )

    return frame.drop(columns=["_return_20d", "_return_5d", "_volatility_20d"])


def _ranking_snapshot_frame(
    feature_frame: pd.DataFrame,
    *,
    candidate: Mapping[str, Any],
    strategy_type: str,
    config: CandidateRankingSnapshotConfig,
) -> pd.DataFrame:
    rebalance_dates = _rebalance_dates(feature_frame["date"], config.rebalance_step_days)
    frame = feature_frame.loc[feature_frame["date"].isin(rebalance_dates)].copy(deep=True)
    if frame.empty:
        raise ValueError("no rebalance dates available for candidate ranking snapshot")

    frame["candidate_signal_percentile"] = frame.groupby("date")["candidate_signal_value"].rank(
        pct=True,
        method="first",
        ascending=True,
    )
    frame["ranking_validity_flag"] = "valid"
    missing_signal = frame["candidate_signal_value"].isna()
    below_threshold = frame["candidate_signal_percentile"].lt(config.entry_percentile_threshold)
    frame.loc[missing_signal, "ranking_validity_flag"] = "insufficient_data"
    frame.loc[~missing_signal & below_threshold, "ranking_validity_flag"] = "blocked"

    frame["rank"] = (
        frame.loc[frame["ranking_validity_flag"].eq("valid")]
        .groupby("date")["candidate_signal_value"]
        .rank(method="first", ascending=False)
    )
    frame["rank"] = frame["rank"].astype("Int64")

    if not config.include_blocked_rows:
        frame = frame.loc[frame["ranking_validity_flag"].eq("valid")].copy(deep=True)
    if frame.empty:
        raise ValueError("candidate ranking snapshot has no valid rows after filtering")

    frame["ranking_date"] = frame["date"].dt.date.astype(str)
    frame["candidate_id"] = candidate.get("candidate_id")
    frame["candidate_version"] = candidate.get("candidate_version") or candidate.get("version")
    frame["linked_strategy_hypothesis_id"] = (
        candidate.get("linked_strategy_hypothesis_id") or candidate.get("hypothesis_id")
    )
    frame["strategy_type"] = strategy_type
    frame["no_lookahead_check"] = "signal_uses_prices_available_through_ranking_date_close"
    frame["no_feedback_check"] = "ranking_snapshot_must_not_feed_scores_rankings_reports_models_or_auto_adoption"
    frame["snapshot_boundary"] = V0_3_RANKING_SNAPSHOT_NOTICE

    columns = [
        "ticker",
        "ranking_date",
        "rank",
        "ranking_validity_flag",
        "candidate_id",
        "candidate_version",
        "linked_strategy_hypothesis_id",
        "strategy_type",
        "candidate_signal_value",
        "candidate_signal_percentile",
        "candidate_signal_family",
        "no_lookahead_check",
        "no_feedback_check",
        "snapshot_boundary",
    ]
    return frame[columns].sort_values(["ranking_date", "rank", "ticker"], na_position="last").reset_index(drop=True)


def _rebalance_dates(dates: pd.Series, step_days: int) -> pd.DatetimeIndex:
    unique_dates = pd.DatetimeIndex(sorted(pd.to_datetime(dates.dropna().unique())))
    if len(unique_dates) == 0:
        return unique_dates
    return unique_dates[::step_days]


__all__ = (
    "CandidateRankingSnapshotConfig",
    "EVALUABLE_CANDIDATE_STATUSES",
    "SUPPORTED_STRATEGY_TYPES",
    "V0_3_RANKING_SNAPSHOT_NOTICE",
    "build_candidate_ranking_snapshot",
)
