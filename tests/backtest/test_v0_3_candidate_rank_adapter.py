from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp import (  # noqa: E402
    CandidateRankingSnapshotConfig,
    build_candidate_ranking_snapshot,
    run_conservative_backtest,
)
from Quant_mvp.backtest_mvp.contracts import validate_backtest_ranking_input  # noqa: E402


def candidate(strategy_type: str = "momentum", **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "candidate_id": "sc:test",
        "linked_strategy_hypothesis_id": "sh:test",
        "candidate_version": "v0.3.0",
        "status": "ready_for_eval",
        "data_requirements": ["daily_ohlcv"],
        "experiment_scope": {
            "strategy_type": strategy_type,
            "entry_rule": "include securities with signal_percentile >= 0.80",
        },
    }
    payload.update(overrides)
    return payload


def prices() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    paths = {
        "005930": lambda day: 100.0 + day * 2.0,
        "000660": lambda day: 100.0 + day * 1.0,
        "035420": lambda day: 160.0 - day * 1.0,
        "051910": lambda day: 100.0 + ((-1) ** day) * 5.0 + day * 0.2,
        "068270": lambda day: 100.0 + ((-1) ** day) * 1.0 + day * 0.1,
    }
    dates = pd.bdate_range("2026-01-02", periods=45)
    for ticker, price_fn in paths.items():
        for day, date in enumerate(dates):
            close = price_fn(day)
            rows.append(
                {
                    "ticker": ticker,
                    "date": date.date().isoformat(),
                    "open": close - 0.5,
                    "high": close + 1.0,
                    "low": close - 1.0,
                    "close": close,
                    "volume": 1000 + day,
                }
            )
    return pd.DataFrame(rows)


def test_momentum_candidate_builds_backtest_compatible_ranking_snapshot() -> None:
    snapshot = build_candidate_ranking_snapshot(
        candidate("momentum"),
        prices(),
        config=CandidateRankingSnapshotConfig(rebalance_step_days=5),
    )

    validate_backtest_ranking_input(snapshot)
    assert {"ticker", "ranking_date", "rank", "ranking_validity_flag"}.issubset(snapshot.columns)
    assert "signal" not in snapshot.columns
    assert "signal_percentile" not in snapshot.columns
    valid = snapshot.loc[snapshot["ranking_validity_flag"].eq("valid")]
    assert not valid.empty
    assert valid.iloc[0]["ticker"] == "005930"
    assert valid["rank"].min() == 1
    assert snapshot["no_feedback_check"].str.contains("must_not_feed").all()


def test_candidate_ranking_snapshot_can_feed_conservative_backtest() -> None:
    snapshot = build_candidate_ranking_snapshot(
        candidate("momentum"),
        prices(),
        config=CandidateRankingSnapshotConfig(rebalance_step_days=5),
    )

    result = run_conservative_backtest(
        snapshot,
        prices(),
        config={"defaults": {"top_n": 1, "holding_period_days": 1, "execution_lag_days": 1}},
    )

    assert result.summary.period_count > 0
    assert result.to_security_frame()["selected"].any()


def test_nested_strategy_candidate_registry_record_is_supported() -> None:
    record = {"strategy_candidate": candidate("momentum")}

    snapshot = build_candidate_ranking_snapshot(
        record,
        prices(),
        config=CandidateRankingSnapshotConfig(rebalance_step_days=5),
    )

    assert snapshot["candidate_id"].eq("sc:test").all()
    validate_backtest_ranking_input(snapshot)


def test_reversal_candidate_ranks_short_horizon_losers_first() -> None:
    reversal_prices = prices().loc[lambda frame: frame["ticker"].isin(["005930", "000660", "035420"])]
    snapshot = build_candidate_ranking_snapshot(
        candidate("reversal"),
        reversal_prices,
        config=CandidateRankingSnapshotConfig(rebalance_step_days=5, entry_percentile_threshold=0.60),
    )

    valid = snapshot.loc[snapshot["ranking_validity_flag"].eq("valid")]
    assert not valid.empty
    first_rebalance = valid.loc[valid["ranking_date"].eq(valid["ranking_date"].min())]
    assert first_rebalance.sort_values("rank").iloc[0]["ticker"] == "035420"


def test_volatility_candidate_uses_rolling_volatility_state() -> None:
    snapshot = build_candidate_ranking_snapshot(
        candidate("volatility"),
        prices(),
        config=CandidateRankingSnapshotConfig(rebalance_step_days=5, entry_percentile_threshold=0.60),
    )

    valid = snapshot.loc[snapshot["ranking_validity_flag"].eq("valid")]
    assert not valid.empty
    assert set(valid["candidate_signal_family"]) == {"rolling_volatility_state"}
    assert "051910" in set(valid.sort_values("rank").head(3)["ticker"])


def test_non_ready_candidate_is_rejected_before_snapshot() -> None:
    with pytest.raises(ValueError, match="ready_for_eval"):
        build_candidate_ranking_snapshot(
            candidate("momentum", status="proposed"),
            prices(),
        )


def test_snapshot_rejects_unsupported_strategy_type() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        build_candidate_ranking_snapshot(
            candidate("value"),
            prices(),
        )
