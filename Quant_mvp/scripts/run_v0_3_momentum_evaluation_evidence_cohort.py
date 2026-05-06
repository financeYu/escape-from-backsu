"""Run approved v0.3 EvaluationEvidence for the momentum cohort.

This script consumes the existing momentum-evaluable StrategyCandidate cohort
and local daily price CSV files, then writes evidence-only EvaluationEvidence
records. It does not train a model, write runtime rankings, or approve
strategies.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Quant_mvp.backtest_mvp.candidate_rank_adapter import CandidateRankingSnapshotConfig
from Quant_mvp.backtest_mvp.candidate_rank_adapter import SUPPORTED_STRATEGY_TYPES
from Quant_mvp.backtest_mvp.evaluation_evidence import (
    run_v0_3_evaluation_evidence,
    strategy_candidate_payload,
    validate_evaluation_evidence_output_path,
    write_evaluation_evidence_markdown,
)
from Quant_mvp.scripts.build_v0_3_momentum_evaluation_evidence_packets import (
    DEFAULT_COHORT_ID,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REGISTRY,
    load_registry,
)
from Quant_mvp.scripts.v0_3_ml_label_policy import (
    GENERIC_PROXY_LABEL_ROLE,
    GENERIC_PROXY_LABEL_STATUS,
    GENERIC_PROXY_LIMITATION,
    GENERIC_PROXY_REVIEW_NOTE,
)


DEFAULT_PRICES_DIR = Path("Quant_mvp/data/v0_3/local_price_inputs")
DEFAULT_PRICE_GLOB = "*_daily_prices.csv"
DEFAULT_STRATEGY_TYPES = ("momentum",)
DEFAULT_MOMENTUM_WINDOW = 20
DEFAULT_REBALANCE_STEP_DAYS = 20
DEFAULT_ENTRY_PERCENTILE_THRESHOLD = 0.80
DEFAULT_HOLDING_PERIOD_DAYS = 20
DEFAULT_EXECUTION_LAG_DAYS = 1
DEFAULT_TRANSACTION_COST_BPS = 10.0
DEFAULT_SLIPPAGE_BPS = 5.0
RECORDED_EVIDENCE_STATUS = "evidence_recorded"
DRY_RUN_ACTUAL_METRIC_SOURCE = "candidate_level_evaluation_evidence_dry_run"
DRY_RUN_ACTUAL_METRIC_ROLE = "candidate_level_metric_not_label"
EVALUATION_EVIDENCE_CONTRACT_REF = "docs/extension/v0_3_evaluation_evidence_contract.md"
STRATEGY_CANDIDATE_REGISTRY_CONTRACT_REF = (
    "docs/extension/v0_3_strategy_candidate_registry_contract.md"
)
EVALUATION_EVIDENCE_METHOD_REF = "Quant_mvp/backtest_mvp/evaluation_evidence.py"
DRY_RUN_ADJUSTMENT_BOUNDARY = (
    "dry_run_reports_existing_local_price_coverage_only_and_does_not_auto_adjust_"
    "StrategyCandidate_test_period_or_effective_max_date_without_explicit_approval"
)
DRY_RUN_ADVISORY = (
    "Keep blocked candidates contract_only until approved local price coverage satisfies "
    "the existing StrategyCandidate test_period/effective_max_date boundary; do not shorten "
    "or rewrite the candidate contract from this dry-run."
)
QUANT_LOCAL_PRICE_INPUT_BOUNDARY = (
    "price inputs for this runner must stay under Quant_mvp/; do not read "
    "chart_mvp, runtime outputs, caches, or external market-data paths from "
    "this v0.3 EvaluationEvidence lane"
)
ZERO_OHLCV_EXCEPTION_POLICY = (
    "rows with non-positive open/high/low/volume are treated as "
    "suspended_or_delisted_like_price_rows and excluded from candidate-only "
    "EvaluationEvidence inputs; source CSV files are not modified"
)
ZERO_OHLCV_EXCEPTION_COLUMNS = ("open", "high", "low", "volume")
IDENTICAL_DUPLICATE_EXCEPTION_POLICY = (
    "identical duplicate ticker/date price rows are collapsed before "
    "candidate-only EvaluationEvidence inputs; conflicting duplicate rows "
    "remain blockers and source CSV files are not modified"
)
DUPLICATE_PRICE_COLUMNS = ("open", "high", "low", "close", "volume")
BENCHMARK_REFERENCE_COMPARISON_STATUS = "available_equal_weight_local_price_input_reference"
BENCHMARK_REFERENCE_ROLE = "benchmark_reference_feature_not_label"
BENCHMARK_REFERENCE_METHOD = (
    "equal_weight_return_over_candidate_evaluation_periods_from_existing_"
    "Quant_mvp_local_price_inputs"
)
WALK_FORWARD_STABILITY_METHOD = (
    "chronological_fold_stability_over_existing_candidate_evaluation_periods_"
    "using_no_lookahead_backtest_period_returns"
)
WALK_FORWARD_FOLD_COUNT = 3
WALK_FORWARD_MIN_VALID_PERIODS = 6
WALK_FORWARD_MIN_PASS_RATIO = 2 / 3
WALK_FORWARD_PASS_STATUS = "recorded_walk_forward_pass"
WALK_FORWARD_FAIL_STATUS = "recorded_walk_forward_fail"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--prices-dir", type=Path, default=DEFAULT_PRICES_DIR)
    parser.add_argument("--price-glob", default=DEFAULT_PRICE_GLOB)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--cohort-id", default=DEFAULT_COHORT_ID)
    parser.add_argument(
        "--strategy-types",
        default=",".join(DEFAULT_STRATEGY_TYPES),
        help=(
            "Comma-separated strategy_type filter for evaluable StrategyCandidates. "
            "Default preserves the historical momentum cohort."
        ),
    )
    parser.add_argument("--expected-count", type=int, help="Optional selected-candidate count guard.")
    parser.add_argument("--created-at", default=date.today().isoformat(), help="YYYY-MM-DD evidence date.")
    parser.add_argument("--max-date", help="Optional YYYY-MM-DD upper bound for price rows.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run candidate evaluations and print a compact status summary without writing evidence files.",
    )
    return parser.parse_args(argv)


def parse_strategy_types(value: str | list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if value is None:
        return DEFAULT_STRATEGY_TYPES
    if isinstance(value, str):
        raw_items = value.split(",")
    else:
        raw_items = list(value)
    strategy_types = tuple(
        dict.fromkeys(item.strip() for item in raw_items if item and item.strip())
    )
    if not strategy_types:
        raise ValueError("at least one strategy type is required")
    unsupported = sorted(set(strategy_types) - set(SUPPORTED_STRATEGY_TYPES))
    if unsupported:
        raise ValueError(f"unsupported v0.3 strategy_types for OHLCV adapter: {unsupported}")
    return strategy_types


def select_evaluable_candidates_by_strategy_type(
    rows: list[dict[str, Any]],
    *,
    strategy_types: tuple[str, ...] = DEFAULT_STRATEGY_TYPES,
) -> list[dict[str, Any]]:
    allowed = set(strategy_types)
    selected: list[dict[str, Any]] = []
    for row in rows:
        candidate = strategy_candidate_payload(row)
        scope = candidate.get("experiment_scope")
        strategy_type = scope.get("strategy_type") if isinstance(scope, dict) else None
        if candidate.get("status") == "evaluable" and strategy_type in allowed:
            selected.append(row)
    return sorted(
        selected,
        key=lambda row: str(strategy_candidate_payload(row).get("candidate_id") or ""),
    )


def strategy_type_from_candidate(candidate: dict[str, Any]) -> str:
    scope = candidate.get("experiment_scope")
    return str(scope.get("strategy_type") or "unknown") if isinstance(scope, dict) else "unknown"


def load_chart_daily_prices(
    prices_dir: Path,
    *,
    price_glob: str = DEFAULT_PRICE_GLOB,
    max_date: str | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(prices_dir.glob(price_glob)):
        ticker = path.name.removesuffix("_daily_prices.csv")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            if len(fieldnames) < 7:
                raise ValueError(f"{path} does not look like a daily price CSV")
            date_column, close_column = fieldnames[0], fieldnames[1]
            open_column, high_column, low_column, volume_column = (
                fieldnames[3],
                fieldnames[4],
                fieldnames[5],
                fieldnames[6],
            )
            for row in reader:
                row_date = str(row.get(date_column) or "")
                if max_date and row_date > max_date:
                    continue
                rows.append(
                    {
                        "ticker": ticker,
                        "date": row_date,
                        "open": row.get(open_column),
                        "high": row.get(high_column),
                        "low": row.get(low_column),
                        "close": row.get(close_column),
                        "volume": row.get(volume_column),
                    }
                )
    if not rows:
        raise ValueError(f"no daily price rows found under {prices_dir}")
    return pd.DataFrame(rows)


def validate_quant_local_prices_dir(prices_dir: Path, *, project_root: Path) -> Path:
    root = project_root.resolve()
    candidate = prices_dir
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    quant_root = (root / "Quant_mvp").resolve()
    if not (resolved == quant_root or quant_root in resolved.parents):
        raise ValueError(
            "v0.3 EvaluationEvidence price inputs must stay under Quant_mvp "
            f"for this task; got {prices_dir}. {QUANT_LOCAL_PRICE_INPUT_BOUNDARY}"
        )
    return resolved


def candidate_test_period_window(candidate: dict[str, Any]) -> tuple[str | None, str | None]:
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", str(candidate.get("test_period") or ""))
    if len(dates) < 2:
        return (None, None)
    return (dates[0], dates[1])


def effective_candidate_max_date(
    candidate: dict[str, Any],
    *,
    created_at: str,
    max_date: str | None,
) -> str:
    _, test_period_end = candidate_test_period_window(candidate)
    bounds = [created_at]
    if max_date:
        bounds.append(max_date)
    if test_period_end:
        bounds.append(test_period_end)
    return min(bounds)


def effective_candidate_max_date_inputs(
    candidate: dict[str, Any],
    *,
    created_at: str,
    max_date: str | None,
) -> dict[str, Any]:
    test_period_start, test_period_end = candidate_test_period_window(candidate)
    effective_max_date = effective_candidate_max_date(
        candidate,
        created_at=created_at,
        max_date=max_date,
    )
    return {
        "created_at": created_at,
        "requested_max_date": max_date,
        "test_period_start": test_period_start,
        "test_period_end": test_period_end,
        "effective_max_date": effective_max_date,
        "effective_max_date_rule": "min(created_at, requested_max_date_if_any, StrategyCandidate_test_period_end_if_any)",
        "auto_adjustment": "not_performed_requires_explicit_approval",
    }


def filter_prices_for_candidate(
    price_frame: pd.DataFrame,
    candidate_max_date: str,
    *,
    candidate_min_date: str | None = None,
) -> pd.DataFrame:
    price_dates = price_frame["date"].astype(str)
    filter_mask = price_dates.le(candidate_max_date)
    if candidate_min_date:
        filter_mask = filter_mask & price_dates.ge(candidate_min_date)
    filtered = price_frame.loc[filter_mask].copy()
    if filtered.empty:
        window = (
            f"{candidate_min_date} through {candidate_max_date}"
            if candidate_min_date
            else f"on or before candidate max date {candidate_max_date}"
        )
        raise ValueError(f"no daily price rows available for candidate window {window}")
    return filtered


def _parse_first_int(value: Any, *, default: int) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else default


def _parse_first_float(value: Any, *, default: float) -> float:
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group(0)) if match else default


def ranking_config_from_candidate(candidate: dict[str, Any]) -> CandidateRankingSnapshotConfig:
    signal_inputs = candidate.get("signal_inputs")
    scope = candidate.get("experiment_scope")
    signal_inputs = signal_inputs if isinstance(signal_inputs, dict) else {}
    scope = scope if isinstance(scope, dict) else {}
    entry_percentile = _parse_first_float(
        scope.get("entry_rule") or signal_inputs.get("entry_rule"),
        default=DEFAULT_ENTRY_PERCENTILE_THRESHOLD,
    )
    if entry_percentile > 1.0:
        entry_percentile = entry_percentile / 100.0
    rebalance_rule = scope.get("rebalance_rule") or signal_inputs.get("rebalance_rule")
    return CandidateRankingSnapshotConfig(
        momentum_window=_parse_first_int(
            signal_inputs.get("signal_calculation_window"),
            default=DEFAULT_MOMENTUM_WINDOW,
        ),
        rebalance_step_days=_parse_first_int(
            rebalance_rule,
            default=DEFAULT_REBALANCE_STEP_DAYS,
        ),
        entry_percentile_threshold=entry_percentile,
    )


def backtest_config_from_candidate(candidate: dict[str, Any]) -> dict[str, dict[str, float | int]]:
    scope = candidate.get("experiment_scope")
    signal_inputs = candidate.get("signal_inputs")
    scope = scope if isinstance(scope, dict) else {}
    signal_inputs = signal_inputs if isinstance(signal_inputs, dict) else {}
    return {
        "defaults": {
            "holding_period_days": _parse_first_int(
                scope.get("holding_period") or signal_inputs.get("exit_rule"),
                default=DEFAULT_HOLDING_PERIOD_DAYS,
            ),
            "execution_lag_days": DEFAULT_EXECUTION_LAG_DAYS,
            "transaction_cost_bps": DEFAULT_TRANSACTION_COST_BPS,
            "slippage_bps": DEFAULT_SLIPPAGE_BPS,
        }
    }


def price_coverage_summary(price_frame: pd.DataFrame) -> dict[str, Any]:
    if price_frame.empty:
        return {
            "row_count": 0,
            "ticker_count": 0,
            "date_start": None,
            "date_end": None,
        }
    return {
        "row_count": len(price_frame),
        "ticker_count": int(price_frame["ticker"].nunique()),
        "date_start": str(price_frame["date"].min()),
        "date_end": str(price_frame["date"].max()),
    }


def zero_ohlcv_exception_summary(price_frame: pd.DataFrame) -> dict[str, Any]:
    field_counts = {column: 0 for column in ZERO_OHLCV_EXCEPTION_COLUMNS}
    if price_frame.empty:
        return {
            "policy": ZERO_OHLCV_EXCEPTION_POLICY,
            "input_row_count": 0,
            "excluded_row_count": 0,
            "retained_row_count": 0,
            "affected_ticker_count": 0,
            "field_counts": field_counts,
            "sample": [],
        }

    working = price_frame.copy(deep=True)
    excluded = pd.Series(False, index=working.index)
    for column in ZERO_OHLCV_EXCEPTION_COLUMNS:
        values = pd.to_numeric(working[column], errors="coerce")
        mask = values.isna() | values.le(0)
        field_counts[column] = int(mask.sum())
        excluded = excluded | mask

    affected = working.loc[excluded].copy()
    sample_columns = ["ticker", "date", *ZERO_OHLCV_EXCEPTION_COLUMNS]
    sample = affected[sample_columns].head(10).to_dict("records") if not affected.empty else []
    return {
        "policy": ZERO_OHLCV_EXCEPTION_POLICY,
        "input_row_count": int(len(working)),
        "excluded_row_count": int(excluded.sum()),
        "retained_row_count": int((~excluded).sum()),
        "affected_ticker_count": int(affected["ticker"].nunique()) if not affected.empty else 0,
        "field_counts": field_counts,
        "sample": sample,
    }


def apply_zero_ohlcv_exception_policy(price_frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    summary = zero_ohlcv_exception_summary(price_frame)
    if summary["excluded_row_count"] == 0:
        return price_frame.copy(deep=True), summary

    working = price_frame.copy(deep=True)
    keep = pd.Series(True, index=working.index)
    for column in ZERO_OHLCV_EXCEPTION_COLUMNS:
        values = pd.to_numeric(working[column], errors="coerce")
        keep = keep & values.notna() & values.gt(0)
    return working.loc[keep].copy().reset_index(drop=True), summary


def duplicate_ticker_date_exception_summary(price_frame: pd.DataFrame) -> dict[str, Any]:
    empty_summary = {
        "policy": IDENTICAL_DUPLICATE_EXCEPTION_POLICY,
        "input_row_count": int(len(price_frame)),
        "duplicate_row_count": 0,
        "duplicate_pair_count": 0,
        "redundant_row_count": 0,
        "retained_row_count": int(len(price_frame)),
        "affected_ticker_count": 0,
        "conflicting_duplicate_pair_count": 0,
        "sample": [],
    }
    if price_frame.empty:
        return empty_summary

    duplicate_mask = price_frame.duplicated(["ticker", "date"], keep=False)
    duplicate_rows = price_frame.loc[duplicate_mask].copy()
    if duplicate_rows.empty:
        return empty_summary

    duplicate_pairs = duplicate_rows.groupby(["ticker", "date"], sort=True)
    distinct_counts = duplicate_pairs[list(DUPLICATE_PRICE_COLUMNS)].nunique(dropna=False)
    conflicting_pairs = distinct_counts.loc[distinct_counts.gt(1).any(axis=1)]
    retained = price_frame.drop_duplicates(["ticker", "date"], keep="first")
    sample_columns = ["ticker", "date", *DUPLICATE_PRICE_COLUMNS]
    return {
        "policy": IDENTICAL_DUPLICATE_EXCEPTION_POLICY,
        "input_row_count": int(len(price_frame)),
        "duplicate_row_count": int(len(duplicate_rows)),
        "duplicate_pair_count": int(duplicate_pairs.ngroups),
        "redundant_row_count": int(len(price_frame) - len(retained)),
        "retained_row_count": int(len(retained)),
        "affected_ticker_count": int(duplicate_rows["ticker"].nunique()),
        "conflicting_duplicate_pair_count": int(len(conflicting_pairs)),
        "sample": duplicate_rows[sample_columns].head(10).to_dict("records"),
    }


def apply_duplicate_ticker_date_exception_policy(
    price_frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    summary = duplicate_ticker_date_exception_summary(price_frame)
    if summary["conflicting_duplicate_pair_count"]:
        return price_frame.copy(deep=True), summary
    if summary["redundant_row_count"] == 0:
        return price_frame.copy(deep=True), summary
    collapsed = price_frame.drop_duplicates(["ticker", "date"], keep="first")
    return collapsed.copy().reset_index(drop=True), summary


def required_rows_per_ticker_for_candidate(candidate: dict[str, Any]) -> int:
    ranking_config = ranking_config_from_candidate(candidate)
    backtest_config = backtest_config_from_candidate(candidate)["defaults"]
    scope = candidate.get("experiment_scope")
    scope = scope if isinstance(scope, dict) else {}
    strategy_type = str(scope.get("strategy_type") or "")
    if strategy_type == "reversal":
        signal_window = ranking_config.reversal_window
    elif strategy_type == "volatility":
        signal_window = ranking_config.volatility_window
    else:
        signal_window = ranking_config.momentum_window
    return (
        int(signal_window)
        + int(backtest_config["execution_lag_days"])
        + int(backtest_config["holding_period_days"])
        + 1
    )


def candidate_price_preflight(
    candidate: dict[str, Any],
    price_frame: pd.DataFrame,
    *,
    created_at: str,
    max_date: str | None,
) -> dict[str, Any]:
    required_rows = required_rows_per_ticker_for_candidate(candidate)
    max_date_inputs = effective_candidate_max_date_inputs(
        candidate,
        created_at=created_at,
        max_date=max_date,
    )
    candidate_max_date = str(max_date_inputs["effective_max_date"])
    candidate_min_date = max_date_inputs["test_period_start"]
    try:
        candidate_price_frame = filter_prices_for_candidate(
            price_frame,
            candidate_max_date,
            candidate_min_date=candidate_min_date,
        )
    except ValueError as exc:
        return {
            "candidate_id": candidate.get("candidate_id"),
            "effective_max_date": candidate_max_date,
            "effective_max_date_inputs": max_date_inputs,
            "required_rows_per_ticker": required_rows,
            "candidate_price": {
                "row_count": 0,
                "ticker_count": 0,
                "date_start": None,
                "date_end": None,
            },
            "max_rows_per_ticker": 0,
            "min_rows_per_ticker": 0,
            "tickers_meeting_required_rows": 0,
            "coverage_status": "blocked_no_candidate_price_rows",
            "coverage_blocker": str(exc),
            "next_evaluation_condition": "existing local prices must include rows inside StrategyCandidate test_period",
            "advisory": DRY_RUN_ADVISORY,
        }

    rows_by_ticker = candidate_price_frame.groupby("ticker", sort=True).size()
    max_rows = int(rows_by_ticker.max()) if not rows_by_ticker.empty else 0
    min_rows = int(rows_by_ticker.min()) if not rows_by_ticker.empty else 0
    tickers_ready = int(rows_by_ticker.ge(required_rows).sum()) if not rows_by_ticker.empty else 0
    if tickers_ready == 0:
        coverage_status = "blocked_insufficient_rows_per_ticker_for_signal_and_holding_period"
    else:
        coverage_status = "candidate_price_coverage_ready_for_actual_run"
    return {
        "candidate_id": candidate.get("candidate_id"),
        "effective_max_date": candidate_max_date,
        "effective_max_date_inputs": max_date_inputs,
        "required_rows_per_ticker": required_rows,
        "candidate_price": price_coverage_summary(candidate_price_frame),
        "max_rows_per_ticker": max_rows,
        "min_rows_per_ticker": min_rows,
        "tickers_meeting_required_rows": tickers_ready,
        "coverage_status": coverage_status,
        "coverage_blocker": None if tickers_ready else (
            f"requires at least {required_rows} rows per ticker, "
            f"but max available is {max_rows}"
        ),
        "next_evaluation_condition": (
            "ready_for_approved_actual_run_with_existing_candidate_period"
            if tickers_ready
            else "existing local prices must provide required rows per ticker before effective_max_date"
        ),
        "advisory": DRY_RUN_ADVISORY if not tickers_ready else "dry_run_only_no_evidence_file_written",
    }


def source_refs_for_run(registry: Path, prices_dir: Path) -> list[str]:
    return [
        EVALUATION_EVIDENCE_CONTRACT_REF,
        STRATEGY_CANDIDATE_REGISTRY_CONTRACT_REF,
        str(registry),
        str(prices_dir),
        EVALUATION_EVIDENCE_METHOD_REF,
    ]


def candidate_rule_fingerprint(candidate: dict[str, Any]) -> str:
    scope = candidate.get("experiment_scope")
    signal_inputs = candidate.get("signal_inputs")
    scope = scope if isinstance(scope, dict) else {}
    signal_inputs = signal_inputs if isinstance(signal_inputs, dict) else {}
    payload = {
        "strategy_type": scope.get("strategy_type"),
        "entry_rule": scope.get("entry_rule") or signal_inputs.get("entry_rule"),
        "exit_rule": scope.get("exit_rule") or signal_inputs.get("exit_rule"),
        "holding_period": scope.get("holding_period"),
        "rebalance_rule": scope.get("rebalance_rule") or signal_inputs.get("rebalance_rule"),
        "signal_calculation_window": signal_inputs.get("signal_calculation_window"),
        "signal_definition": signal_inputs.get("signal_definition"),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _cumulative_return(values: list[float]) -> float | None:
    if not values:
        return None
    equity = 1.0
    for value in values:
        equity *= 1.0 + value
    return equity - 1.0


def _period_reference_window(period_result: Any) -> tuple[str, str] | None:
    valid = [
        security
        for security in getattr(period_result, "security_results", ())
        if getattr(security, "execution_date", None)
        and getattr(security, "exit_date", None)
        and getattr(security, "skipped", True) is False
    ]
    if not valid:
        return None
    execution_dates = sorted({str(security.execution_date) for security in valid})
    exit_dates = sorted({str(security.exit_date) for security in valid})
    if len(execution_dates) != 1 or len(exit_dates) != 1:
        return None
    return execution_dates[0], exit_dates[0]


def _equal_weight_reference_period_return(
    price_by_date: dict[str, pd.DataFrame],
    *,
    execution_date: str,
    exit_date: str,
    execution_price_policy: str,
    exit_price_policy: str,
    round_trip_drag: float,
) -> tuple[float | None, int]:
    entry = price_by_date.get(execution_date)
    exit_ = price_by_date.get(exit_date)
    if entry is None or exit_ is None:
        return None, 0
    entry = entry[["ticker", execution_price_policy]].copy()
    exit_ = exit_[["ticker", exit_price_policy]].copy()
    if entry.empty or exit_.empty:
        return None, 0
    entry[execution_price_policy] = pd.to_numeric(entry[execution_price_policy], errors="coerce")
    exit_[exit_price_policy] = pd.to_numeric(exit_[exit_price_policy], errors="coerce")
    merged = entry.merge(exit_, on="ticker", how="inner", suffixes=("_entry", "_exit"))
    if merged.empty:
        return None, 0
    entry_column = f"{execution_price_policy}_entry"
    exit_column = f"{exit_price_policy}_exit"
    if entry_column not in merged:
        entry_column = execution_price_policy
    if exit_column not in merged:
        exit_column = exit_price_policy
    valid = merged.loc[
        merged[entry_column].notna()
        & merged[exit_column].notna()
        & merged[entry_column].gt(0)
        & merged[exit_column].gt(0)
    ].copy()
    if valid.empty:
        return None, 0
    returns = (valid[exit_column] / valid[entry_column]) - 1.0 - round_trip_drag
    return float(returns.mean()), int(len(valid))


def equal_weight_reference_summary(price_frame: pd.DataFrame, backtest_result: Any) -> dict[str, Any]:
    config = backtest_result.config
    round_trip_drag = 2.0 * (config.transaction_cost_bps + config.slippage_bps) / 10_000.0
    price_lookup = price_frame.copy()
    price_lookup["date"] = price_lookup["date"].astype(str)
    price_by_date = {
        str(date_value): group
        for date_value, group in price_lookup.groupby("date", sort=False)
    }
    period_returns: list[float] = []
    period_counts: list[int] = []
    missing_period_count = 0
    for period_result in backtest_result.period_results:
        window = _period_reference_window(period_result)
        if window is None:
            missing_period_count += 1
            continue
        period_return, security_count = _equal_weight_reference_period_return(
            price_by_date,
            execution_date=window[0],
            exit_date=window[1],
            execution_price_policy=config.execution_price_policy,
            exit_price_policy=config.exit_price_policy,
            round_trip_drag=round_trip_drag,
        )
        if period_return is None:
            missing_period_count += 1
            continue
        period_returns.append(period_return)
        period_counts.append(security_count)
    benchmark_return = _cumulative_return(period_returns)
    return {
        "status": (
            BENCHMARK_REFERENCE_COMPARISON_STATUS
            if benchmark_return is not None
            else "not_available_without_reference_price_overlap"
        ),
        "method": BENCHMARK_REFERENCE_METHOD,
        "benchmark_return": benchmark_return,
        "proxy_return": benchmark_return,
        "period_count": len(period_returns),
        "missing_period_count": missing_period_count,
        "average_reference_security_count": (
            sum(period_counts) / len(period_counts) if period_counts else None
        ),
        "reference_role": BENCHMARK_REFERENCE_ROLE,
    }


def _period_reference_rows(price_frame: pd.DataFrame, backtest_result: Any) -> list[dict[str, Any]]:
    config = backtest_result.config
    round_trip_drag = 2.0 * (config.transaction_cost_bps + config.slippage_bps) / 10_000.0
    price_lookup = price_frame.copy()
    price_lookup["date"] = price_lookup["date"].astype(str)
    price_by_date = {
        str(date_value): group
        for date_value, group in price_lookup.groupby("date", sort=False)
    }
    rows: list[dict[str, Any]] = []
    for period_result in sorted(backtest_result.period_results, key=lambda period: str(period.decision_date)):
        strategy_return = getattr(period_result, "backtest_period_return", None)
        window = _period_reference_window(period_result)
        reference_return = None
        reference_security_count = 0
        if window is not None:
            reference_return, reference_security_count = _equal_weight_reference_period_return(
                price_by_date,
                execution_date=window[0],
                exit_date=window[1],
                execution_price_policy=config.execution_price_policy,
                exit_price_policy=config.exit_price_policy,
                round_trip_drag=round_trip_drag,
            )
        relative_return = (
            float(strategy_return) - float(reference_return)
            if strategy_return is not None and reference_return is not None
            else None
        )
        rows.append(
            {
                "decision_date": str(period_result.decision_date),
                "strategy_return": strategy_return,
                "reference_return": reference_return,
                "relative_return": relative_return,
                "valid_security_count": int(getattr(period_result, "valid_security_count", 0) or 0),
                "reference_security_count": reference_security_count,
            }
        )
    return rows


def _walk_forward_folds(rows: list[dict[str, Any]], *, fold_count: int = WALK_FORWARD_FOLD_COUNT) -> list[list[dict[str, Any]]]:
    if not rows:
        return []
    resolved_fold_count = max(1, min(fold_count, len(rows)))
    base_size, remainder = divmod(len(rows), resolved_fold_count)
    folds: list[list[dict[str, Any]]] = []
    start = 0
    for index in range(resolved_fold_count):
        size = base_size + (1 if index < remainder else 0)
        folds.append(rows[start : start + size])
        start += size
    return folds


def _fold_summary(index: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    strategy_returns = [float(row["strategy_return"]) for row in rows if row.get("strategy_return") is not None]
    reference_returns = [float(row["reference_return"]) for row in rows if row.get("reference_return") is not None]
    strategy_return = _cumulative_return(strategy_returns)
    reference_return = _cumulative_return(reference_returns)
    relative_return = (
        strategy_return - reference_return
        if strategy_return is not None and reference_return is not None
        else None
    )
    dates = [str(row["decision_date"]) for row in rows]
    return {
        "fold_index": index,
        "start": min(dates) if dates else None,
        "end": max(dates) if dates else None,
        "period_count": len(rows),
        "strategy_return": strategy_return,
        "reference_return": reference_return,
        "relative_return": relative_return,
        "relative_return_positive": relative_return is not None and relative_return > 0,
        "valid_security_count": sum(int(row.get("valid_security_count") or 0) for row in rows),
        "reference_security_count": sum(int(row.get("reference_security_count") or 0) for row in rows),
    }


def walk_forward_stability_summary(price_frame: pd.DataFrame, backtest_result: Any) -> dict[str, Any]:
    period_rows = [
        row
        for row in _period_reference_rows(price_frame, backtest_result)
        if row.get("strategy_return") is not None and row.get("reference_return") is not None
    ]
    fold_summaries = [
        _fold_summary(index, rows)
        for index, rows in enumerate(_walk_forward_folds(period_rows), start=1)
        if rows
    ]
    passing_fold_count = sum(1 for fold in fold_summaries if fold["relative_return_positive"] is True)
    valid_fold_count = len(fold_summaries)
    pass_ratio = passing_fold_count / valid_fold_count if valid_fold_count else 0.0
    aggregate_strategy_return = _cumulative_return(
        [float(row["strategy_return"]) for row in period_rows if row.get("strategy_return") is not None]
    )
    aggregate_reference_return = _cumulative_return(
        [float(row["reference_return"]) for row in period_rows if row.get("reference_return") is not None]
    )
    aggregate_relative_return = (
        aggregate_strategy_return - aggregate_reference_return
        if aggregate_strategy_return is not None and aggregate_reference_return is not None
        else None
    )
    passed = (
        len(period_rows) >= WALK_FORWARD_MIN_VALID_PERIODS
        and valid_fold_count >= 2
        and pass_ratio >= WALK_FORWARD_MIN_PASS_RATIO
        and aggregate_relative_return is not None
        and aggregate_relative_return > 0
    )
    status = WALK_FORWARD_PASS_STATUS if passed else WALK_FORWARD_FAIL_STATUS
    return {
        "status": status,
        "method": WALK_FORWARD_STABILITY_METHOD,
        "period_count": len(period_rows),
        "fold_count": valid_fold_count,
        "passing_fold_count": passing_fold_count,
        "passing_fold_ratio": pass_ratio,
        "minimum_valid_periods": WALK_FORWARD_MIN_VALID_PERIODS,
        "minimum_pass_ratio": WALK_FORWARD_MIN_PASS_RATIO,
        "aggregate_strategy_return": aggregate_strategy_return,
        "aggregate_reference_return": aggregate_reference_return,
        "aggregate_relative_return": aggregate_relative_return,
        "folds": fold_summaries,
        "label_role": "candidate_level_oos_walk_forward_stability_check",
    }


def attach_walk_forward_stability_check(
    evidence: dict[str, Any],
    *,
    price_frame: pd.DataFrame,
    backtest_result: Any,
) -> None:
    summary = walk_forward_stability_summary(price_frame, backtest_result)
    status = str(summary["status"])
    evidence["walk_forward_stability_summary"] = summary
    for payload_name in ("metric_summary", "performance_metric_summary"):
        payload = evidence.setdefault(payload_name, {})
        payload["oos_stability_status"] = status
        payload["walk_forward_passing_fold_ratio"] = summary["passing_fold_ratio"]
        payload["walk_forward_passing_fold_count"] = summary["passing_fold_count"]
        payload["walk_forward_fold_count"] = summary["fold_count"]
        payload["walk_forward_aggregate_relative_return"] = summary["aggregate_relative_return"]
    evidence.setdefault("required_evaluation_checks", {})["oos_walk_forward_stability"] = {
        "status": status,
        "check": "walk_forward_or_out_of_sample_stability_recorded_for_candidate_level_labeling",
        "method": WALK_FORWARD_STABILITY_METHOD,
        "metric_refs": [
            "metric_summary.oos_stability_status",
            "walk_forward_stability_summary",
        ],
    }
    notes = [
        note
        for note in evidence.get("review_notes", [])
        if note != "walk_forward_or_out_of_sample_stability remains a downstream evidence requirement"
    ]
    notes.append(
        "walk-forward stability is recorded from existing candidate-only evaluation periods; "
        "it is label evidence only and not production activation"
    )
    evidence["review_notes"] = notes


def attach_benchmark_reference_comparison(
    evidence: dict[str, Any],
    *,
    price_frame: pd.DataFrame,
    backtest_result: Any,
) -> None:
    reference = equal_weight_reference_summary(price_frame, backtest_result)
    if reference["benchmark_return"] is None:
        evidence.setdefault("known_limitations", []).append("benchmark_reference_comparison_missing")
        evidence.setdefault("review_notes", []).append(
            "benchmark/reference comparison could not be computed from existing local price inputs"
        )
        return

    metric_summary = evidence.setdefault("metric_summary", {})
    performance_summary = evidence.setdefault("performance_metric_summary", {})
    total_return = _metric_value(evidence, "performance_metric_summary.total_return", "metric_summary.total_return")
    benchmark_return = float(reference["benchmark_return"])
    benchmark_relative_return = (
        float(total_return) - benchmark_return
        if total_return is not None
        else None
    )
    for payload in (metric_summary, performance_summary):
        payload["benchmark_return"] = benchmark_return
        payload["proxy_return"] = benchmark_return
        payload["benchmark_relative_return"] = benchmark_relative_return
        payload["excess_return_vs_proxy"] = benchmark_relative_return
        payload["benchmark_comparison"] = BENCHMARK_REFERENCE_COMPARISON_STATUS
        payload["benchmark_reference_role"] = BENCHMARK_REFERENCE_ROLE
    evidence["benchmark_reference_summary"] = reference | {
        "benchmark_relative_return": benchmark_relative_return,
        "generic_momentum_proxy_role": "benchmark_reference_context_only_not_label",
    }
    evidence.setdefault("required_evaluation_checks", {})["benchmark_reference_comparison"] = {
        "status": "recorded",
        "method": BENCHMARK_REFERENCE_METHOD,
        "metric_role": BENCHMARK_REFERENCE_ROLE,
    }
    notes = [
        note
        for note in evidence.get("review_notes", [])
        if note != "benchmark series comparison is not computed unless an approved benchmark input is supplied later"
    ]
    notes.append(
        "benchmark/reference comparison uses existing Quant_mvp local price inputs only and remains a reference feature"
    )
    evidence["review_notes"] = notes


def mark_generic_proxy_label(evidence: dict[str, Any]) -> None:
    evidence["label_use_status"] = GENERIC_PROXY_LABEL_STATUS
    evidence["supervised_label_eligible"] = False
    evidence.setdefault("known_limitations", [])
    if GENERIC_PROXY_LIMITATION not in evidence["known_limitations"]:
        evidence["known_limitations"].append(GENERIC_PROXY_LIMITATION)
    evidence.setdefault("review_notes", [])
    evidence["review_notes"].append(GENERIC_PROXY_REVIEW_NOTE)
    if isinstance(evidence.get("metric_summary"), dict):
        evidence["metric_summary"]["label_role"] = GENERIC_PROXY_LABEL_ROLE


def require_recorded_candidate_evidence(evidence: dict[str, Any]) -> None:
    valid_count = None
    metric_summary = evidence.get("metric_summary")
    if isinstance(metric_summary, dict):
        valid_count = metric_summary.get("valid_security_count")
    if evidence.get("status") != RECORDED_EVIDENCE_STATUS or not valid_count:
        raise ValueError(
            "momentum cohort actual run did not produce candidate-level metric_summary labels "
            f"for {evidence.get('candidate_id')}: status={evidence.get('status')}, "
            f"valid_security_count={valid_count}. Keep this candidate contract_only until "
            "approved price coverage and candidate-specific rules produce a valid run."
        )


def resolve_output_dir(output_dir: Path, *, project_root: Path) -> Path:
    boundary_probe = output_dir / "__boundary_probe__.md"
    return validate_evaluation_evidence_output_path(
        boundary_probe,
        project_root=project_root,
    ).parent


def write_manifest(
    evidence_records: list[dict[str, Any]],
    paths: list[Path],
    *,
    output_dir: Path,
    project_root: Path,
    cohort_id: str,
    prices_dir: Path,
    price_row_count: int,
    strategy_types: tuple[str, ...] = DEFAULT_STRATEGY_TYPES,
    zero_ohlcv_exception: dict[str, Any] | None = None,
    duplicate_ticker_date_exception: dict[str, Any] | None = None,
) -> Path:
    root = project_root.resolve()
    resolved_output_dir = resolve_output_dir(output_dir, project_root=project_root)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = resolved_output_dir / "manifest.json"
    limitation_counts = Counter(
        str(flag)
        for record in evidence_records
        for flag in record.get("known_limitations", [])
    )
    label_use_status_counts = Counter(str(record.get("label_use_status") or "candidate_specific") for record in evidence_records)
    status_counts = Counter(str(record["status"]) for record in evidence_records)
    strategy_type_counts = Counter(str(record.get("strategy_type") or "unknown") for record in evidence_records)
    manifest_status = next(iter(status_counts)) if len(status_counts) == 1 else "mixed"
    manifest = {
        "schema_version": "v0_3_evaluation_evidence_cohort_manifest_0_2",
        "cohort_id": cohort_id,
        "strategy_types": list(strategy_types),
        "strategy_type_counts": dict(sorted(strategy_type_counts.items())),
        "status": manifest_status,
        "candidate_count": len(evidence_records),
        "evaluation_ids": [str(record["evaluation_id"]) for record in evidence_records],
        "candidate_ids": [str(record["candidate_id"]) for record in evidence_records],
        "evidence_status_counts": dict(sorted(status_counts.items())),
        "failure_flag_counts": dict(
            sorted(Counter(str(flag) for record in evidence_records for flag in record.get("failure_flags", [])).items())
        ),
        "known_limitation_counts": dict(sorted(limitation_counts.items())),
        "label_use_status_counts": dict(sorted(label_use_status_counts.items())),
        "required_evaluation_check_ids": sorted(
            str(check_id)
            for record in evidence_records[:1]
            for check_id in record.get("required_evaluation_checks", {})
        ),
        "price_input_ref": str(prices_dir),
        "price_row_count": price_row_count,
        "zero_ohlcv_exception_summary": zero_ohlcv_exception or zero_ohlcv_exception_summary(
            pd.DataFrame(columns=["ticker", "date", "open", "high", "low", "close", "volume"])
        ),
        "duplicate_ticker_date_exception_summary": duplicate_ticker_date_exception
        or duplicate_ticker_date_exception_summary(
            pd.DataFrame(columns=["ticker", "date", "open", "high", "low", "close", "volume"])
        ),
        "packet_paths": [
            str(path.resolve().relative_to(root)).replace("\\", "/")
            for path in paths
        ],
        "generated_output_boundary": "Quant_mvp/backtest_mvp/docs/v0_3_evaluation_evidence/",
        "no_feedback_check": "evaluation_metrics_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "production_boundary_check": "no_automatic_production_activation_claim",
        "model_training_status": "not_run_metric_summary_generation_only",
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest_path


def run_momentum_evaluation_evidence_cohort(
    *,
    registry: Path,
    prices_dir: Path,
    output_dir: Path,
    project_root: Path,
    cohort_id: str,
    created_at: str,
    price_glob: str = DEFAULT_PRICE_GLOB,
    max_date: str | None = None,
    expected_count: int | None = None,
    strategy_types: tuple[str, ...] = DEFAULT_STRATEGY_TYPES,
) -> dict[str, Any]:
    registry_rows = load_registry(registry)
    selected = select_evaluable_candidates_by_strategy_type(registry_rows, strategy_types=strategy_types)
    if expected_count is not None and len(selected) != expected_count:
        raise ValueError(
            f"expected {expected_count} evaluable candidates for strategy_types={list(strategy_types)}, "
            f"found {len(selected)}"
        )

    prices_dir = validate_quant_local_prices_dir(prices_dir, project_root=project_root)
    raw_price_frame = load_chart_daily_prices(prices_dir, price_glob=price_glob, max_date=max_date or created_at)
    price_frame, zero_ohlcv_exception = apply_zero_ohlcv_exception_policy(raw_price_frame)
    price_frame, duplicate_ticker_date_exception = apply_duplicate_ticker_date_exception_policy(price_frame)
    candidate_rule_counts = Counter(
        candidate_rule_fingerprint(dict(strategy_candidate_payload(registry_record)))
        for registry_record in selected
    )
    resolved_output_dir = resolve_output_dir(output_dir, project_root=project_root)
    evidence_records: list[dict[str, Any]] = []
    paths: list[Path] = []
    for registry_record in selected:
        candidate = dict(strategy_candidate_payload(registry_record))
        candidate_max_date = effective_candidate_max_date(
            candidate,
            created_at=created_at,
            max_date=max_date,
        )
        candidate_min_date, _ = candidate_test_period_window(candidate)
        candidate_price_frame = filter_prices_for_candidate(
            price_frame,
            candidate_max_date,
            candidate_min_date=candidate_min_date,
        )
        evidence_result = run_v0_3_evaluation_evidence(
            registry_record,
            candidate_price_frame,
            ranking_config=ranking_config_from_candidate(candidate),
            backtest_config=backtest_config_from_candidate(candidate),
            created_at=created_at,
            source_refs=source_refs_for_run(registry, prices_dir),
        )
        evidence = evidence_result.to_dict()
        evidence["strategy_type"] = strategy_type_from_candidate(candidate)
        attach_benchmark_reference_comparison(
            evidence,
            price_frame=candidate_price_frame,
            backtest_result=evidence_result.backtest_result,
        )
        attach_walk_forward_stability_check(
            evidence,
            price_frame=candidate_price_frame,
            backtest_result=evidence_result.backtest_result,
        )
        evidence["zero_ohlcv_exception_summary"] = zero_ohlcv_exception
        evidence["duplicate_ticker_date_exception_summary"] = duplicate_ticker_date_exception
        if zero_ohlcv_exception["excluded_row_count"]:
            evidence.setdefault("known_limitations", []).append("suspended_or_delisted_like_price_rows_excluded")
            evidence.setdefault("review_notes", []).append(
                "non-positive open/high/low/volume rows were excluded from EvaluationEvidence inputs and summarized"
            )
        if duplicate_ticker_date_exception["redundant_row_count"]:
            evidence.setdefault("known_limitations", []).append("identical_duplicate_ticker_date_rows_collapsed")
            evidence.setdefault("review_notes", []).append(
                "identical duplicate ticker/date price rows were collapsed before EvaluationEvidence inputs"
            )
        require_recorded_candidate_evidence(evidence)
        if candidate_rule_counts[candidate_rule_fingerprint(candidate)] > 1:
            evidence.setdefault("review_notes", []).append(
                "shared generic momentum proxy is retained only as a benchmark/reference feature; "
                "this recorded row remains candidate-level EvaluationEvidence"
            )
        packet_path = resolved_output_dir / f"{evidence['evaluation_id']}.md"
        paths.append(
            write_evaluation_evidence_markdown(
                evidence,
                packet_path,
                project_root=project_root,
            )
        )
        evidence_records.append(evidence)

    manifest_path = write_manifest(
        evidence_records,
        paths,
        output_dir=output_dir,
        project_root=project_root,
        cohort_id=cohort_id,
        strategy_types=strategy_types,
        prices_dir=prices_dir,
        price_row_count=len(price_frame),
        zero_ohlcv_exception=zero_ohlcv_exception,
        duplicate_ticker_date_exception=duplicate_ticker_date_exception,
    )
    return {
        "cohort_id": cohort_id,
        "strategy_types": list(strategy_types),
        "candidate_count": len(evidence_records),
        "strategy_type_counts": dict(
            sorted(
                Counter(
                    str(record.get("strategy_type") or "unknown")
                    for record in evidence_records
                ).items()
            )
        ),
        "status_counts": dict(sorted(Counter(str(record["status"]) for record in evidence_records).items())),
        "manifest": str(manifest_path),
        "packet_paths": [str(path) for path in paths],
        "raw_price_row_count": int(zero_ohlcv_exception["input_row_count"]),
        "zero_ohlcv_retained_row_count": int(zero_ohlcv_exception["retained_row_count"]),
        "price_row_count": len(price_frame),
        "zero_ohlcv_exception_summary": zero_ohlcv_exception,
        "duplicate_ticker_date_exception_summary": duplicate_ticker_date_exception,
    }


def _candidate_dry_run_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    metric_summary = evidence.get("metric_summary")
    metric_summary = metric_summary if isinstance(metric_summary, dict) else {}
    return {
        "candidate_id": evidence.get("candidate_id"),
        "evaluation_id": evidence.get("evaluation_id"),
        "status": evidence.get("status"),
        "valid_security_count": metric_summary.get("valid_security_count"),
        "label_use_status": evidence.get("label_use_status") or "candidate_specific",
        "failure_flags": list(evidence.get("failure_flags", [])),
    }


def _metric_value(evidence: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        current: Any = evidence
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]
        if current is not None:
            return current
    return None


def _candidate_level_evidence_row(evidence: dict[str, Any]) -> dict[str, Any]:
    candidate_id = str(evidence.get("candidate_id") or "")
    metric_subject_id = candidate_id
    total_return = _metric_value(
        evidence,
        "performance_metric_summary.total_return",
        "metric_summary.total_return",
    )
    proxy_return = _metric_value(
        evidence,
        "performance_metric_summary.proxy_return",
        "metric_summary.proxy_return",
        "performance_metric_summary.benchmark_return",
        "metric_summary.benchmark_return",
    )
    excess_return_vs_proxy = _metric_value(
        evidence,
        "performance_metric_summary.excess_return_vs_proxy",
        "metric_summary.excess_return_vs_proxy",
        "performance_metric_summary.benchmark_relative_return",
        "metric_summary.benchmark_relative_return",
    )
    if excess_return_vs_proxy is None and total_return is not None and proxy_return is not None:
        excess_return_vs_proxy = float(total_return) - float(proxy_return)
    return {
        "candidate_id": candidate_id,
        "evidence_id": evidence.get("evaluation_id"),
        "evidence_status": evidence.get("status"),
        "metric_subject_type": "strategy_candidate",
        "metric_subject_id": metric_subject_id,
        "candidate_metric_match": metric_subject_id == candidate_id,
        "candidate_metric_match_reason": (
            "candidate_id_matches_candidate_level_evaluation_evidence"
            if metric_subject_id == candidate_id
            else "evidence_candidate_id_mismatch"
        ),
        "total_return": total_return,
        "benchmark_return": _metric_value(
            evidence,
            "performance_metric_summary.benchmark_return",
            "metric_summary.benchmark_return",
        ),
        "proxy_return": proxy_return,
        "excess_return_vs_proxy": excess_return_vs_proxy,
        "max_drawdown": _metric_value(
            evidence,
            "risk_metric_summary.max_drawdown",
            "metric_summary.max_drawdown",
        ),
        "sharpe": _metric_value(
            evidence,
            "risk_metric_summary.sharpe_ratio",
            "metric_summary.sharpe_ratio",
        ),
        "turnover": _metric_value(
            evidence,
            "risk_metric_summary.turnover_proxy",
            "metric_summary.turnover_proxy",
        ),
        "failure_flags": list(evidence.get("failure_flags", [])),
        "actual_metric_source": DRY_RUN_ACTUAL_METRIC_SOURCE,
        "actual_metric_role": DRY_RUN_ACTUAL_METRIC_ROLE,
        "excluded_untradable": False,
        "excluded_untradable_row_count": int(
            _metric_value(evidence, "zero_ohlcv_exception_summary.excluded_row_count") or 0
        ),
        "label_source": "not_generated_dry_run_metric_only",
        "supervised_label_eligible": False,
    }


def generic_proxy_reference_feature() -> dict[str, Any]:
    return {
        "metric_subject_type": "generic_proxy",
        "metric_subject_id": GENERIC_PROXY_LABEL_ROLE,
        "metric_use_status": "benchmark_reference_feature_candidate",
        "candidate_metric_match": False,
        "candidate_metric_match_reason": GENERIC_PROXY_LIMITATION,
        "label_source": "unlabeled",
        "supervised_label_eligible": False,
    }


def _blocked_candidate_summary(
    *,
    candidate_id: str,
    error: ValueError,
    preflight: dict[str, Any],
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "status": "blocked_for_actual_label",
        "blocked_reason": str(error),
        "preflight": preflight,
    }


def dry_run_momentum_evaluation_evidence_cohort(
    *,
    registry: Path,
    prices_dir: Path,
    cohort_id: str,
    created_at: str,
    price_glob: str = DEFAULT_PRICE_GLOB,
    max_date: str | None = None,
    expected_count: int | None = None,
    project_root: Path = PROJECT_ROOT,
    strategy_types: tuple[str, ...] = DEFAULT_STRATEGY_TYPES,
) -> dict[str, Any]:
    registry_rows = load_registry(registry)
    selected = select_evaluable_candidates_by_strategy_type(registry_rows, strategy_types=strategy_types)
    if expected_count is not None and len(selected) != expected_count:
        raise ValueError(
            f"expected {expected_count} evaluable candidates for strategy_types={list(strategy_types)}, "
            f"found {len(selected)}"
        )

    prices_dir = validate_quant_local_prices_dir(prices_dir, project_root=project_root)
    price_load_error: str | None = None
    try:
        raw_price_frame = load_chart_daily_prices(prices_dir, price_glob=price_glob, max_date=max_date or created_at)
    except ValueError as exc:
        price_load_error = str(exc)
        raw_price_frame = pd.DataFrame(columns=["ticker", "date", "open", "high", "low", "close", "volume"])
    price_frame, zero_ohlcv_exception = apply_zero_ohlcv_exception_policy(raw_price_frame)
    price_frame, duplicate_ticker_date_exception = apply_duplicate_ticker_date_exception_policy(price_frame)
    candidate_rule_counts = Counter(
        candidate_rule_fingerprint(dict(strategy_candidate_payload(registry_record)))
        for registry_record in selected
    )
    summaries: list[dict[str, Any]] = []
    candidate_level_evidence_rows: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for registry_record in selected:
        candidate = dict(strategy_candidate_payload(registry_record))
        candidate_id = str(candidate.get("candidate_id") or "")
        preflight = candidate_price_preflight(
            candidate,
            price_frame,
            created_at=created_at,
            max_date=max_date,
        )
        preflight["zero_ohlcv_exception_summary"] = zero_ohlcv_exception
        preflight["duplicate_ticker_date_exception_summary"] = duplicate_ticker_date_exception
        if price_load_error:
            blocked.append(
                {
                    "candidate_id": candidate_id,
                    "status": "blocked_for_actual_label",
                    "blocked_reason": price_load_error,
                    "preflight": preflight,
                }
            )
            continue
        try:
            candidate_max_date = effective_candidate_max_date(
                candidate,
                created_at=created_at,
                max_date=max_date,
            )
            candidate_min_date, _ = candidate_test_period_window(candidate)
            candidate_price_frame = filter_prices_for_candidate(
                price_frame,
                candidate_max_date,
                candidate_min_date=candidate_min_date,
            )
            evidence_result = run_v0_3_evaluation_evidence(
                registry_record,
                candidate_price_frame,
                ranking_config=ranking_config_from_candidate(candidate),
                backtest_config=backtest_config_from_candidate(candidate),
                created_at=created_at,
                source_refs=source_refs_for_run(registry, prices_dir),
            )
            evidence = evidence_result.to_dict()
            evidence["strategy_type"] = strategy_type_from_candidate(candidate)
            attach_benchmark_reference_comparison(
                evidence,
                price_frame=candidate_price_frame,
                backtest_result=evidence_result.backtest_result,
            )
            attach_walk_forward_stability_check(
                evidence,
                price_frame=candidate_price_frame,
                backtest_result=evidence_result.backtest_result,
            )
            evidence["zero_ohlcv_exception_summary"] = zero_ohlcv_exception
            evidence["duplicate_ticker_date_exception_summary"] = duplicate_ticker_date_exception
            if zero_ohlcv_exception["excluded_row_count"]:
                evidence.setdefault("known_limitations", []).append("suspended_or_delisted_like_price_rows_excluded")
                evidence.setdefault("review_notes", []).append(
                    "non-positive open/high/low/volume rows were excluded from EvaluationEvidence inputs and summarized"
                )
            if duplicate_ticker_date_exception["redundant_row_count"]:
                evidence.setdefault("known_limitations", []).append("identical_duplicate_ticker_date_rows_collapsed")
                evidence.setdefault("review_notes", []).append(
                    "identical duplicate ticker/date price rows were collapsed before EvaluationEvidence inputs"
                )
            require_recorded_candidate_evidence(evidence)
            if candidate_rule_counts[candidate_rule_fingerprint(candidate)] > 1:
                evidence.setdefault("review_notes", []).append(
                    "shared generic momentum proxy is retained only as a benchmark/reference feature; "
                    "this dry-run row remains candidate-level and is not a supervised label"
                )
            summary = _candidate_dry_run_summary(evidence)
            summary["preflight"] = preflight
            summaries.append(summary)
            candidate_level_evidence_rows.append(_candidate_level_evidence_row(evidence))
        except ValueError as exc:
            blocked.append(_blocked_candidate_summary(candidate_id=candidate_id, error=exc, preflight=preflight))

    status_counts = Counter(str(summary["status"]) for summary in summaries)
    label_use_status_counts = Counter(str(summary["label_use_status"]) for summary in summaries)
    candidate_metric_match_true_count = sum(
        row.get("candidate_metric_match") is True
        for row in candidate_level_evidence_rows
    )
    candidate_level_excluded_untradable_row_count = sum(
        int(row.get("excluded_untradable_row_count") or 0)
        for row in candidate_level_evidence_rows
    )
    excluded_untradable_count = int(zero_ohlcv_exception.get("excluded_row_count") or 0)
    next_condition = (
        "all candidates passed dry-run coverage; actual EvaluationEvidence run still requires approved owner-lane execution"
        if not blocked
        else "resolve blocked candidate local price coverage against existing StrategyCandidate test_period/effective_max_date before actual EvaluationEvidence"
    )
    return {
        "mode": "dry_run",
        "output_written": False,
        "adjustment_boundary": DRY_RUN_ADJUSTMENT_BOUNDARY,
        "next_evaluation_condition": next_condition,
        "advisory": DRY_RUN_ADVISORY if blocked else "dry_run_only_no_evidence_file_written",
        "cohort_id": cohort_id,
        "strategy_types": list(strategy_types),
        "candidate_count": len(selected),
        "strategy_type_counts": dict(
            sorted(
                Counter(
                    strategy_type_from_candidate(dict(strategy_candidate_payload(registry_record)))
                    for registry_record in selected
                ).items()
            )
        ),
        "recorded_count": len(summaries),
        "blocked_count": len(blocked),
        "candidate_level_evidence_count": len(candidate_level_evidence_rows),
        "candidate_metric_match_true_count": candidate_metric_match_true_count,
        "excluded_untradable_count": excluded_untradable_count,
        "candidate_level_excluded_untradable_row_count": candidate_level_excluded_untradable_row_count,
        "evidence_status_counts": dict(sorted(status_counts.items())),
        "label_use_status_counts": dict(sorted(label_use_status_counts.items())),
        "price_input_ref": str(prices_dir),
        "price_input_status": "blocked_no_local_price_rows" if price_load_error else "loaded",
        "price_input_blocker": price_load_error,
        "price_coverage": price_coverage_summary(price_frame),
        "raw_price_row_count": int(zero_ohlcv_exception["input_row_count"]),
        "zero_ohlcv_retained_row_count": int(zero_ohlcv_exception["retained_row_count"]),
        "price_row_count": len(price_frame),
        "zero_ohlcv_exception_summary": zero_ohlcv_exception,
        "duplicate_ticker_date_exception_summary": duplicate_ticker_date_exception,
        "candidate_summaries": summaries,
        "candidate_level_evidence_rows": candidate_level_evidence_rows,
        "benchmark_reference_features": [generic_proxy_reference_feature()],
        "blocked_candidates": blocked,
        "model_training_status": "not_run_metric_summary_generation_only",
        "label_generation_status": "not_run_candidate_level_metric_dry_run_only",
        "no_feedback_check": "evaluation_metrics_must_not_feed_scores_rankings_reports_models_or_auto_adoption",
        "production_boundary_check": "no_automatic_production_activation_claim",
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    strategy_types = parse_strategy_types(args.strategy_types)
    if args.dry_run:
        result = dry_run_momentum_evaluation_evidence_cohort(
            registry=args.registry,
            prices_dir=args.prices_dir,
            cohort_id=args.cohort_id,
            created_at=args.created_at,
            price_glob=args.price_glob,
            max_date=args.max_date,
            expected_count=args.expected_count,
            project_root=args.project_root,
            strategy_types=strategy_types,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    result = run_momentum_evaluation_evidence_cohort(
        registry=args.registry,
        prices_dir=args.prices_dir,
        output_dir=args.output_dir,
        project_root=args.project_root,
        cohort_id=args.cohort_id,
        created_at=args.created_at,
        price_glob=args.price_glob,
        max_date=args.max_date,
        expected_count=args.expected_count,
        strategy_types=strategy_types,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
