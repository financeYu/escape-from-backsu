"""Evaluation-only Backtest MVP contracts owned by Quant_mvp.

The contracts in this module are evaluation-only. They validate already-built
Step 15/16-compatible technical snapshot inputs and price inputs, then hold
Backtest MVP result objects. They do not define scores, create rankings, or use
valuation/fundamental data. The v0.3 runner remains a ranking snapshot top_n
conservative evaluator, not a strategy-specific entry/exit/risk engine. The
legacy ``src.backtest`` package re-exports this module for compatibility.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import math
import tomllib

import pandas as pd

from src.preprocess.schema_validator import KOSPI200_SYMBOL_POLICY, SymbolPolicy
from src.scores.schema import find_missing_columns, find_valuation_fundamental_columns
from src.validation.horizon_policy import HorizonPolicy, resolve_horizon_policy


STEP17_BACKTEST_NOTICE = "Step 17 conservative backtest evaluation only"

RANKING_DATE_COLUMNS: tuple[str, ...] = ("ranking_date", "decision_date", "date")
RANK_COLUMNS: tuple[str, ...] = ("rank", "latest_rank")
PRICE_INPUT_COLUMNS: tuple[str, ...] = (
    "ticker",
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
)

ALLOWED_REBALANCE_FREQUENCIES = frozenset(
    {
        "every_ranking_date",
        "daily",
        "weekly",
        "monthly",
    }
)
ALLOWED_PRICE_POLICIES = frozenset({"open", "close"})
ALLOWED_MISSING_PRICE_POLICIES = frozenset({"flag_and_skip", "raise"})

FORBIDDEN_BACKTEST_INPUT_EXACT_COLUMNS = frozenset(
    {
        "future_return",
        "forward_return",
        "expected_return",
        "alpha",
        "signal",
        "buy",
        "sell",
        "valuation_score",
        "cheap",
        "undervalued",
        "per",
        "pbr",
        "roe",
        "eps",
        "bps",
        "book_value",
        "earnings",
        "net_income",
        "revenue",
        "sales",
        "operating_income",
        "cash_flow",
        "free_cash_flow",
        "market_cap",
        "shares_outstanding",
        "financial_statement",
        "realized_holding_return",
        "backtest_period_return",
        "evaluation_return",
    }
)

FORBIDDEN_BACKTEST_INPUT_PREFIXES = (
    "future_return",
    "forward_return",
    "expected_return",
    "alpha_",
    "signal_",
    "buy_",
    "sell_",
    "valuation_",
    "fundamental_",
    "financial_",
    "market_cap_",
    "backtest_",
)

FORBIDDEN_BACKTEST_INPUT_SUFFIXES = (
    "_future_return",
    "_forward_return",
    "_expected_return",
    "_alpha",
    "_signal",
    "_buy",
    "_sell",
    "_valuation_score",
    "_fundamental_score",
)

BLOCKED_STATUS_VALUES = frozenset(
    {
        "blocked",
        "blocked_by_data",
        "insufficient_input",
        "insufficient_data",
        "rejected",
        "excluded",
        "not_eligible",
    }
)


class BacktestLimitationFlag:
    """Stable Step 17 limitation flag values."""

    INSUFFICIENT_PRICE_HISTORY = "insufficient_price_history"
    MISSING_EXECUTION_PRICE = "missing_execution_price"
    MISSING_EXIT_PRICE = "missing_exit_price"
    UPSTREAM_ROW_BLOCKED = "upstream_row_blocked"
    MISSING_UPSTREAM_RANK = "missing_upstream_rank"
    UNIVERSE_SURVIVORSHIP_BIAS_WARNING = "universe_survivorship_bias_warning"
    CORPORATE_ACTION_ADJUSTMENT_UNKNOWN = "corporate_action_adjustment_unknown"
    NON_POINT_IN_TIME_CONSTITUENT_WARNING = "non_point_in_time_constituent_warning"


DEFAULT_DATA_LIMITATION_FLAGS: tuple[str, ...] = (
    BacktestLimitationFlag.UNIVERSE_SURVIVORSHIP_BIAS_WARNING,
    BacktestLimitationFlag.CORPORATE_ACTION_ADJUSTMENT_UNKNOWN,
    BacktestLimitationFlag.NON_POINT_IN_TIME_CONSTITUENT_WARNING,
)


@dataclass(frozen=True)
class BacktestConfig:
    """Config-first conservative backtest assumptions."""

    rebalance_frequency: str = "every_ranking_date"
    holding_period_days: int = 20
    top_n: int = 20
    weight_method: str = "equal_weight"
    execution_lag_days: int = 1
    execution_price_policy: str = "open"
    exit_price_policy: str = "close"
    transaction_cost_bps: float = 10.0
    slippage_bps: float = 5.0
    missing_price_policy: str = "flag_and_skip"
    limitation_flags: tuple[str, ...] = DEFAULT_DATA_LIMITATION_FLAGS

    def __post_init__(self) -> None:
        rebalance_frequency = self.rebalance_frequency.strip().lower()
        weight_method = self.weight_method.strip().lower()
        execution_price_policy = self.execution_price_policy.strip().lower()
        exit_price_policy = self.exit_price_policy.strip().lower()
        missing_price_policy = self.missing_price_policy.strip().lower()

        if rebalance_frequency not in ALLOWED_REBALANCE_FREQUENCIES:
            raise ValueError(
                "Step 17 rebalance_frequency must be one of: "
                f"{', '.join(sorted(ALLOWED_REBALANCE_FREQUENCIES))}"
            )
        if self.holding_period_days < 1:
            raise ValueError("Step 17 holding_period_days must be at least 1.")
        if self.top_n < 1:
            raise ValueError("Step 17 top_n must be at least 1.")
        if weight_method != "equal_weight":
            raise ValueError("Step 17 weight_method currently supports equal_weight only.")
        if self.execution_lag_days < 1:
            raise ValueError("Step 17 execution_lag_days must be at least 1.")
        if execution_price_policy not in ALLOWED_PRICE_POLICIES:
            raise ValueError("Step 17 execution_price_policy must be open or close.")
        if exit_price_policy not in ALLOWED_PRICE_POLICIES:
            raise ValueError("Step 17 exit_price_policy must be open or close.")
        if self.transaction_cost_bps < 0:
            raise ValueError("Step 17 transaction_cost_bps must be non-negative.")
        if self.slippage_bps < 0:
            raise ValueError("Step 17 slippage_bps must be non-negative.")
        if missing_price_policy not in ALLOWED_MISSING_PRICE_POLICIES:
            raise ValueError("Step 17 missing_price_policy must be flag_and_skip or raise.")

        object.__setattr__(self, "rebalance_frequency", rebalance_frequency)
        object.__setattr__(self, "weight_method", weight_method)
        object.__setattr__(self, "execution_price_policy", execution_price_policy)
        object.__setattr__(self, "exit_price_policy", exit_price_policy)
        object.__setattr__(self, "missing_price_policy", missing_price_policy)
        object.__setattr__(self, "limitation_flags", _dedupe_flags(self.limitation_flags))

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "BacktestConfig":
        """Create config from a mapping, ignoring unknown TOML sections."""

        defaults = values.get("defaults", values)
        if not isinstance(defaults, Mapping):
            raise ValueError("Step 17 backtest config defaults must be a mapping.")
        known_fields = cls.__dataclass_fields__.keys()
        kwargs = {key: value for key, value in defaults.items() if key in known_fields}
        return cls(**kwargs)

    @classmethod
    def from_toml_file(cls, path: str | Path) -> "BacktestConfig":
        """Load Step 17 config from a TOML file."""

        with Path(path).open("rb") as handle:
            payload = tomllib.load(handle)
        return cls.from_mapping(payload)

    @classmethod
    def from_horizon_policy(
        cls,
        horizon_policy: HorizonPolicy | Mapping[str, Any] | str | None = None,
        **overrides: Any,
    ) -> "BacktestConfig":
        """Create config from explicit HorizonPolicy values.

        This preserves existing constructor defaults unless the caller chooses
        the v1.0-rc policy path.
        """

        if isinstance(horizon_policy, HorizonPolicy):
            policy = horizon_policy
        elif isinstance(horizon_policy, Mapping):
            policy = HorizonPolicy.from_mapping(horizon_policy)
        else:
            policy = resolve_horizon_policy(horizon_policy)
        values = {
            "rebalance_frequency": policy.rebalance_frequency,
            "holding_period_days": policy.holding_period_trading_days,
            "execution_lag_days": policy.entry_lag_trading_days,
        }
        values.update(overrides)
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON/DataFrame-friendly config dictionary."""

        return {
            "rebalance_frequency": self.rebalance_frequency,
            "holding_period_days": self.holding_period_days,
            "top_n": self.top_n,
            "weight_method": self.weight_method,
            "execution_lag_days": self.execution_lag_days,
            "execution_price_policy": self.execution_price_policy,
            "exit_price_policy": self.exit_price_policy,
            "transaction_cost_bps": self.transaction_cost_bps,
            "slippage_bps": self.slippage_bps,
            "missing_price_policy": self.missing_price_policy,
            "limitation_flags": self.limitation_flags,
        }


@dataclass(frozen=True)
class BacktestSecurityResult:
    """One selected or skipped security row for a Step 17 evaluation period."""

    ticker: str
    decision_date: str
    upstream_rank: int | None
    selected: bool
    skipped: bool
    skip_reasons: tuple[str, ...] = ()
    limitation_flags: tuple[str, ...] = ()
    execution_date: str | None = None
    exit_date: str | None = None
    execution_price: float | None = None
    exit_price: float | None = None
    backtest_weight: float | None = None
    realized_holding_return: float | None = None
    evaluation_return: float | None = None
    evaluation_start_date: str | None = None
    evaluation_end_date: str | None = None
    transaction_cost_bps: float = 0.0
    slippage_bps: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "decision_date": self.decision_date,
            "upstream_rank": self.upstream_rank,
            "selected": self.selected,
            "skipped": self.skipped,
            "skip_reasons": self.skip_reasons,
            "limitation_flags": self.limitation_flags,
            "execution_date": self.execution_date,
            "exit_date": self.exit_date,
            "execution_price": self.execution_price,
            "exit_price": self.exit_price,
            "backtest_weight": self.backtest_weight,
            "realized_holding_return": self.realized_holding_return,
            "evaluation_return": self.evaluation_return,
            "evaluation_start_date": self.evaluation_start_date,
            "evaluation_end_date": self.evaluation_end_date,
            "transaction_cost_bps": self.transaction_cost_bps,
            "slippage_bps": self.slippage_bps,
        }


@dataclass(frozen=True)
class BacktestPeriodResult:
    """Portfolio-level result for one deterministic rebalance decision date."""

    decision_date: str
    selected_security_count: int
    valid_security_count: int
    skipped_security_count: int
    backtest_period_return: float | None
    limitation_flags: tuple[str, ...]
    security_results: tuple[BacktestSecurityResult, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_date": self.decision_date,
            "selected_security_count": self.selected_security_count,
            "valid_security_count": self.valid_security_count,
            "skipped_security_count": self.skipped_security_count,
            "backtest_period_return": self.backtest_period_return,
            "limitation_flags": self.limitation_flags,
        }


@dataclass(frozen=True)
class BacktestSummary:
    """Deterministic Step 17 portfolio aggregation."""

    period_count: int
    selected_security_count: int
    valid_security_count: int
    skipped_security_count: int
    mean_period_return: float | None
    cumulative_return: float | None
    average_turnover_proxy: float | None
    max_drawdown: float | None
    annualized_return: float | None
    period_volatility: float | None
    annualized_volatility: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    hit_rate: float | None
    coverage_ratio: float | None
    exposure_stability: float | None
    benchmark_relative_return: float | None
    benchmark_comparison_status: str
    warmup_period_count: int
    oos_stability_status: str
    limitation_flags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "period_count": self.period_count,
            "selected_security_count": self.selected_security_count,
            "valid_security_count": self.valid_security_count,
            "skipped_security_count": self.skipped_security_count,
            "mean_period_return": self.mean_period_return,
            "cumulative_return": self.cumulative_return,
            "average_turnover_proxy": self.average_turnover_proxy,
            "max_drawdown": self.max_drawdown,
            "annualized_return": self.annualized_return,
            "period_volatility": self.period_volatility,
            "annualized_volatility": self.annualized_volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "hit_rate": self.hit_rate,
            "coverage_ratio": self.coverage_ratio,
            "exposure_stability": self.exposure_stability,
            "benchmark_relative_return": self.benchmark_relative_return,
            "benchmark_comparison_status": self.benchmark_comparison_status,
            "warmup_period_count": self.warmup_period_count,
            "oos_stability_status": self.oos_stability_status,
            "limitation_flags": self.limitation_flags,
        }


@dataclass(frozen=True)
class ConservativeBacktestResult:
    """Complete in-memory Step 17 conservative backtest result."""

    config: BacktestConfig
    period_results: tuple[BacktestPeriodResult, ...]
    summary: BacktestSummary
    metadata: Mapping[str, Any]
    limitation_flags: tuple[str, ...]

    def to_security_frame(self) -> pd.DataFrame:
        rows = [
            security.to_dict()
            for period in self.period_results
            for security in period.security_results
        ]
        return pd.DataFrame(rows)

    def to_period_frame(self) -> pd.DataFrame:
        return pd.DataFrame([period.to_dict() for period in self.period_results])

    def to_summary_dict(self) -> dict[str, Any]:
        payload = self.summary.to_dict()
        payload["metadata"] = dict(self.metadata)
        payload["config"] = self.config.to_dict()
        payload["limitation_flags"] = self.limitation_flags
        return payload


def coerce_frame(
    rows: pd.DataFrame | Iterable[Mapping[str, Any]],
    *,
    context: str,
) -> pd.DataFrame:
    """Return a defensive DataFrame copy from rows."""

    if isinstance(rows, pd.DataFrame):
        frame = rows.copy(deep=True)
    else:
        frame = pd.DataFrame(list(rows))
    if frame.empty:
        raise ValueError(f"{context} must not be empty.")
    return frame


def validate_backtest_ranking_input(
    frame: pd.DataFrame,
    *,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> tuple[str, str]:
    """Validate Step 17 ranking snapshot input and return date/rank columns."""

    date_column = find_ranking_date_column(frame.columns)
    rank_column = find_rank_column(frame.columns)
    required = ("ticker", date_column, rank_column)
    missing = find_missing_columns(frame.columns, required)
    if missing:
        raise ValueError(
            "Step 17 ranking input missing required columns: " f"{', '.join(missing)}"
        )
    forbidden = find_forbidden_backtest_input_columns(frame.columns)
    if forbidden:
        raise ValueError(
            "Step 17 ranking input contains forbidden columns: "
            f"{', '.join(forbidden)}"
        )
    assert_ticker_strings(
        frame["ticker"],
        context="Step 17 ranking input",
        symbol_policy=symbol_policy,
    )
    pd.to_datetime(frame[date_column], errors="raise")
    return date_column, rank_column


def validate_backtest_price_input(
    frame: pd.DataFrame,
    *,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> None:
    """Validate Step 17 OHLCV price input."""

    missing = find_missing_columns(frame.columns, PRICE_INPUT_COLUMNS)
    if missing:
        raise ValueError(
            "Step 17 price input missing required columns: " f"{', '.join(missing)}"
        )
    forbidden = find_forbidden_backtest_input_columns(frame.columns)
    if forbidden:
        raise ValueError(
            "Step 17 price input contains forbidden columns: " f"{', '.join(forbidden)}"
        )
    assert_ticker_strings(
        frame["ticker"],
        context="Step 17 price input",
        symbol_policy=symbol_policy,
    )
    pd.to_datetime(frame["date"], errors="raise")
    for column in ("open", "high", "low", "close", "volume"):
        values = pd.to_numeric(frame[column], errors="coerce")
        present = frame[column].notna()
        invalid = present & (values.isna() | ~values.map(math.isfinite))
        if invalid.any():
            raise ValueError(f"Step 17 price input {column} must be finite when present.")
        if column == "volume":
            missing_volume = values.isna()
            if missing_volume.any():
                raise ValueError("Step 17 price input volume must be non-missing.")
            non_positive = values <= 0
            if non_positive.any():
                raise ValueError("Step 17 price input volume must be positive.")
            continue
        non_positive = present & (values <= 0)
        if non_positive.any():
            raise ValueError(f"Step 17 price input {column} must be positive.")


def find_ranking_date_column(columns: Iterable[str]) -> str:
    present = {str(column) for column in columns}
    for column in RANKING_DATE_COLUMNS:
        if column in present:
            return column
    raise ValueError(
        "Step 17 ranking input requires ranking_date, decision_date, or Step 15 date."
    )


def find_rank_column(columns: Iterable[str]) -> str:
    present = {str(column) for column in columns}
    for column in RANK_COLUMNS:
        if column in present:
            return column
    raise ValueError("Step 17 ranking input requires rank or latest_rank.")


def find_forbidden_backtest_input_columns(columns: Iterable[str]) -> list[str]:
    """Return columns that are not allowed as Step 17 inputs."""

    column_names = tuple(str(column) for column in columns)
    forbidden: set[str] = set(find_valuation_fundamental_columns(column_names))
    for column in column_names:
        normalized = column.lower()
        if (
            normalized in FORBIDDEN_BACKTEST_INPUT_EXACT_COLUMNS
            or normalized.startswith(FORBIDDEN_BACKTEST_INPUT_PREFIXES)
            or normalized.endswith(FORBIDDEN_BACKTEST_INPUT_SUFFIXES)
        ):
            forbidden.add(column)
    return sorted(forbidden)


def assert_ticker_strings(
    series: pd.Series,
    *,
    context: str,
    symbol_policy: SymbolPolicy = KOSPI200_SYMBOL_POLICY,
) -> None:
    """Reject non-string tickers and enforce the configured symbol policy."""

    invalid = series.map(lambda value: not isinstance(value, str) or value.strip() == "")
    if invalid.any():
        raise ValueError(f"{context} ticker values must be non-empty strings.")
    unsafe = series.map(lambda value: not symbol_policy.is_valid(value))
    if unsafe.any():
        raise ValueError(f"{context} ticker values must preserve {symbol_policy.display_rule}.")


def is_upstream_blocked(row: pd.Series) -> bool:
    """Return whether an upstream row explicitly marks itself blocked."""

    if "blocked" in row.index and _truthy(row["blocked"]):
        return True
    for column in (
        "ranking_validity_flag",
        "validity_flag",
        "coverage_status",
        "data_quality_flag",
        "score_coverage_status",
        "score_data_quality_flag",
        "eligibility",
        "adoption_state",
    ):
        if column not in row.index:
            continue
        value = _status_value(row[column])
        if value in BLOCKED_STATUS_VALUES:
            return True
    return False


def safe_float(value: object) -> float | None:
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    numeric = pd.to_numeric(value, errors="coerce")
    try:
        parsed = float(numeric)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def safe_int(value: object) -> int | None:
    numeric = safe_float(value)
    if numeric is None:
        return None
    if numeric % 1 != 0:
        return None
    return int(numeric)


def date_string(value: object) -> str:
    timestamp = pd.Timestamp(pd.to_datetime(value, errors="raise"))
    return timestamp.date().isoformat()


def _status_value(value: object) -> str:
    if value is None or value is pd.NA:
        return ""
    return str(value).strip().lower()


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value is pd.NA:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _dedupe_flags(flags: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(flag) for flag in flags if str(flag)))


__all__ = (
    "BacktestConfig",
    "BacktestLimitationFlag",
    "BacktestPeriodResult",
    "BacktestSecurityResult",
    "BacktestSummary",
    "ConservativeBacktestResult",
    "DEFAULT_DATA_LIMITATION_FLAGS",
    "PRICE_INPUT_COLUMNS",
    "RANKING_DATE_COLUMNS",
    "RANK_COLUMNS",
    "STEP17_BACKTEST_NOTICE",
    "assert_ticker_strings",
    "coerce_frame",
    "date_string",
    "find_forbidden_backtest_input_columns",
    "find_rank_column",
    "find_ranking_date_column",
    "is_upstream_blocked",
    "safe_float",
    "safe_int",
    "validate_backtest_price_input",
    "validate_backtest_ranking_input",
)
