"""Step 9 Part A raw score implementation.

This module owns only the Part A Research Tester raw scores. It does not create
normalized score columns, rankings, composites, signals, valuation scores, or
backtest outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import re
import tomllib
from typing import Mapping

import pandas as pd

from .schema import (
    IDENTITY_COLUMNS,
    SCORE_METADATA_COLUMNS,
    assert_no_forbidden_output_columns,
    assert_no_valuation_fundamental_columns,
    require_columns,
    validate_raw_score_output_frame,
)
from .score_contracts import (
    IMPLEMENTED_FOR_RESEARCH,
    NOT_IMPLEMENTED_MISSING_CONTRACT,
    PART_A_MISSING_REASON_COLUMNS,
    PART_A_RAW_COLUMNS,
    PART_A_SCORE_CONTRACTS,
    ScoreImplementationContract,
)


TICKER_PATTERN = re.compile(r"^[0-9A-Z]{6}$")
STEP7_REQUIRED_COLUMNS = (
    "ticker",
    "date",
    "history_count",
    "minimum_history_required",
    "warmup_state",
)


@dataclass(frozen=True)
class PartAScoreConfig:
    return_window: int
    atr_window: int
    rsi_window: int
    realized_vol_window: int
    realized_vol_percentile_window: int
    minimum_history_by_score: Mapping[str, int]
    bollinger_window: int = 20

    @property
    def part_a_minimum_history_required(self) -> int:
        return max(self.minimum_history_by_score.values())

    @property
    def realized_vol_column(self) -> str:
        return f"realized_vol_{self.realized_vol_window}"


def load_part_a_score_config(
    *,
    windows_config_path: str | Path = "Quant_mvp/config/windows.toml",
    scores_config_path: str | Path = "Quant_mvp/config/scores.toml",
) -> PartAScoreConfig:
    """Load Part A score config from the Quant score registry and windows config."""

    windows_config = _load_toml(Path(windows_config_path))
    scores_config = _load_toml(Path(scores_config_path))
    minimum_history = _minimum_history_by_score(scores_config)
    return PartAScoreConfig(
        return_window=_positive_int(windows_config.get("returns", {}).get("short"), "returns.short"),
        atr_window=_positive_int(windows_config.get("volatility", {}).get("atr"), "volatility.atr"),
        rsi_window=_positive_int(windows_config.get("indicators", {}).get("rsi"), "indicators.rsi"),
        bollinger_window=_positive_int(
            windows_config.get("indicators", {}).get("bollinger"),
            "indicators.bollinger",
        ),
        realized_vol_window=_positive_int(
            windows_config.get("volatility", {}).get("realized_vol"),
            "volatility.realized_vol",
        ),
        realized_vol_percentile_window=_positive_int(
            windows_config.get("normalization", {}).get("time_series_window"),
            "normalization.time_series_window",
        ),
        minimum_history_by_score=minimum_history,
    )


def calculate_step9_part_a_raw_scores(
    frame: pd.DataFrame,
    *,
    config: PartAScoreConfig | None = None,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """Calculate Step 9 Part A raw score output from Step 7 indicator rows."""

    score_config = config or load_part_a_score_config()
    data = _prepare_step7_indicator_input(frame, as_of_date=as_of_date)
    output = data.loc[:, list(IDENTITY_COLUMNS)].copy()

    for contract in PART_A_SCORE_CONTRACTS:
        output[contract.raw_column] = pd.Series(pd.NA, index=output.index, dtype="Float64")
        output[contract.missing_reason_column] = pd.NA

    _apply_blocked_contracts(output)
    _apply_short_term_overreaction(output, data, score_config)
    _apply_atr_adjusted_oversold_distance(output, data, score_config)
    _apply_rsi_price_divergence(output, data, score_config)
    _apply_realized_vol_percentile(output, data, score_config)
    _add_shared_metadata(output, data, score_config)
    output = output[
        [
            *IDENTITY_COLUMNS,
            *PART_A_RAW_COLUMNS,
            *SCORE_METADATA_COLUMNS,
            *PART_A_MISSING_REASON_COLUMNS,
        ]
    ]
    validate_raw_score_output_frame(output, context="Step 9 Part A raw score output")
    return output


def _apply_blocked_contracts(output: pd.DataFrame) -> None:
    for contract in PART_A_SCORE_CONTRACTS:
        if contract.implementation_status != NOT_IMPLEMENTED_MISSING_CONTRACT:
            continue
        output[contract.missing_reason_column] = "not_implemented_due_to_missing_contract"


def _apply_short_term_overreaction(
    output: pd.DataFrame,
    data: pd.DataFrame,
    config: PartAScoreConfig,
) -> None:
    contract = _implemented_contract("short_term_overreaction")
    return_values, invalid_denominator = _trailing_return(data, config.return_window)
    if return_values is None:
        _mark_missing_dependency(output, data, contract, config)
        return

    ready = _score_ready(data, contract, config)
    raw = (-return_values).where(ready)
    output[contract.raw_column] = raw.astype("Float64")
    output[contract.missing_reason_column] = _missing_reason(
        data,
        contract,
        config,
        ready=ready,
        values=raw,
        denominator_invalid=invalid_denominator,
    )


def _apply_atr_adjusted_oversold_distance(
    output: pd.DataFrame,
    data: pd.DataFrame,
    config: PartAScoreConfig,
) -> None:
    contract = _implemented_contract("atr_adjusted_oversold_distance")
    atr_column = f"atr_{config.atr_window}"
    anchor_column = f"bollinger_mid_{config.bollinger_window}"
    if any(column not in data.columns for column in ("close", atr_column, anchor_column)):
        _mark_missing_dependency(output, data, contract, config)
        return

    close = pd.to_numeric(data["close"], errors="coerce")
    atr = pd.to_numeric(data[atr_column], errors="coerce")
    anchor = pd.to_numeric(data[anchor_column], errors="coerce")
    valid_denominator = atr.gt(0)
    ready = _score_ready(data, contract, config)
    raw = ((anchor - close) / atr.where(valid_denominator)).where(ready)
    output[contract.raw_column] = raw.astype("Float64")
    output[contract.missing_reason_column] = _missing_reason(
        data,
        contract,
        config,
        ready=ready,
        values=raw,
        denominator_invalid=atr.notna() & ~valid_denominator,
    )


def _apply_rsi_price_divergence(
    output: pd.DataFrame,
    data: pd.DataFrame,
    config: PartAScoreConfig,
) -> None:
    contract = _implemented_contract("rsi_price_divergence")
    rsi_column = f"rsi_{config.rsi_window}"
    return_values, invalid_denominator = _trailing_return(data, config.return_window)
    if return_values is None or rsi_column not in data.columns:
        _mark_missing_dependency(output, data, contract, config)
        return

    rsi = pd.to_numeric(data[rsi_column], errors="coerce")
    rsi_delta = rsi - rsi.groupby(data["ticker"], sort=False).shift(config.return_window)
    ready = _score_ready(data, contract, config)
    raw = ((-return_values).clip(lower=0.0) * rsi_delta.clip(lower=0.0)).where(ready)
    output[contract.raw_column] = raw.astype("Float64")
    output[contract.missing_reason_column] = _missing_reason(
        data,
        contract,
        config,
        ready=ready,
        values=raw,
        denominator_invalid=invalid_denominator,
    )


def _apply_realized_vol_percentile(
    output: pd.DataFrame,
    data: pd.DataFrame,
    config: PartAScoreConfig,
) -> None:
    contract = _implemented_contract("realized_vol_percentile")
    raw_column = contract.raw_column
    reason_column = contract.missing_reason_column
    source_column = config.realized_vol_column

    if source_column not in data.columns:
        _mark_missing_dependency(output, data, contract, config)
        return

    data[source_column] = pd.to_numeric(data[source_column], errors="coerce")
    minimum_history = config.minimum_history_by_score[contract.score_name]
    percentile = data.groupby("ticker", group_keys=False, sort=False)[source_column].transform(
        lambda values: values.rolling(
            config.realized_vol_percentile_window,
            min_periods=minimum_history,
        ).apply(_current_average_percentile, raw=False)
    )
    ready = _score_ready(data, contract, config)
    output[raw_column] = percentile.where(ready).astype("Float64")
    reason = _base_missing_reason(data, contract, config, ready=ready)
    reason = reason.mask(
        ready & reason.isna() & data[source_column].isna(),
        "missing_required_input",
    )
    reason = reason.mask(
        ready & reason.isna() & output[raw_column].isna(),
        "insufficient_observations",
    )
    output[reason_column] = reason


def _add_shared_metadata(
    output: pd.DataFrame,
    data: pd.DataFrame,
    config: PartAScoreConfig,
) -> None:
    output["score_warmup_state"] = data["warmup_state"].astype("string")
    raw_presence_count = output.loc[:, list(PART_A_RAW_COLUMNS)].notna().sum(axis=1)
    output["score_coverage_status"] = "blocked"
    output.loc[raw_presence_count.gt(0), "score_coverage_status"] = "partial"
    output.loc[raw_presence_count.eq(len(PART_A_RAW_COLUMNS)), "score_coverage_status"] = "adequate"
    output["score_data_quality_flag"] = _aggregate_data_quality_flags(output)

    output["minimum_history_required"] = data["minimum_history_required"].clip(
        lower=config.part_a_minimum_history_required
    )


def _trailing_return(
    data: pd.DataFrame,
    window: int,
) -> tuple[pd.Series | None, pd.Series | None]:
    return_column = f"return_{window}d"
    if return_column in data.columns:
        return pd.to_numeric(data[return_column], errors="coerce"), None
    if "close" not in data.columns:
        return None, None

    close = pd.to_numeric(data["close"], errors="coerce")
    prior_close = close.groupby(data["ticker"], sort=False).shift(window)
    valid_denominator = prior_close.gt(0)
    returns = (close / prior_close.where(valid_denominator)) - 1.0
    denominator_invalid = prior_close.notna() & ~valid_denominator
    return returns, denominator_invalid


def _score_ready(
    data: pd.DataFrame,
    contract: ScoreImplementationContract,
    config: PartAScoreConfig,
) -> pd.Series:
    minimum_history = config.minimum_history_by_score[contract.score_name]
    return data["warmup_state"].eq("ready") & data["history_count"].ge(minimum_history)


def _mark_missing_dependency(
    output: pd.DataFrame,
    data: pd.DataFrame,
    contract: ScoreImplementationContract,
    config: PartAScoreConfig,
) -> None:
    ready = _score_ready(data, contract, config)
    reason = _base_missing_reason(data, contract, config, ready=ready)
    output[contract.missing_reason_column] = reason.mask(
        ready & reason.isna(),
        "missing_dependency",
    )


def _missing_reason(
    data: pd.DataFrame,
    contract: ScoreImplementationContract,
    config: PartAScoreConfig,
    *,
    ready: pd.Series,
    values: pd.Series,
    denominator_invalid: pd.Series | None = None,
) -> pd.Series:
    reason = _base_missing_reason(data, contract, config, ready=ready)
    if denominator_invalid is not None:
        reason = reason.mask(
            ready & reason.isna() & denominator_invalid,
            "zero_denominator",
        )
    reason = reason.mask(
        ready & reason.isna() & values.isna(),
        "missing_required_input",
    )
    return reason


def _base_missing_reason(
    data: pd.DataFrame,
    contract: ScoreImplementationContract,
    config: PartAScoreConfig,
    *,
    ready: pd.Series,
) -> pd.Series:
    reason = pd.Series(pd.NA, index=data.index, dtype="string")
    reason = reason.mask(data["warmup_state"].eq("warmup"), "warmup")
    reason = reason.mask(
        data["warmup_state"].eq("insufficient_history"),
        "insufficient_history",
    )
    minimum_history = config.minimum_history_by_score[contract.score_name]
    reason = reason.mask(
        ~ready & reason.isna() & data["history_count"].lt(minimum_history),
        "insufficient_observations",
    )
    return reason


def _aggregate_data_quality_flags(output: pd.DataFrame) -> pd.Series:
    reason_frame = output.loc[:, list(PART_A_MISSING_REASON_COLUMNS)].astype("string")
    flags: list[str] = []
    for _, row in reason_frame.iterrows():
        row_flags: set[str] = set()
        values = set(row.dropna().astype(str))
        if "warmup" in values:
            row_flags.add("warmup")
        if "insufficient_history" in values:
            row_flags.add("insufficient_history")
        if "insufficient_observations" in values:
            row_flags.add("insufficient_observations")
        if {"missing_required_input", "missing_dependency"} & values:
            row_flags.add("missing_required_input")
        if "zero_denominator" in values:
            row_flags.add("invalid_numeric")
        if "not_implemented_due_to_missing_contract" in values:
            row_flags.add("blocked")
        flags.append(";".join(sorted(row_flags)) if row_flags else "valid")
    return pd.Series(flags, index=output.index, dtype="string")


def _prepare_step7_indicator_input(
    frame: pd.DataFrame,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None,
) -> pd.DataFrame:
    require_columns(frame, STEP7_REQUIRED_COLUMNS, context="Step 9 Part A input")
    assert_no_forbidden_output_columns(frame, context="Step 9 Part A input")
    assert_no_valuation_fundamental_columns(frame, context="Step 9 Part A input")

    data = frame.copy()
    data["ticker"] = data["ticker"].astype("string").str.strip()
    valid_ticker = data["ticker"].map(
        lambda value: isinstance(value, str) and bool(TICKER_PATTERN.fullmatch(value)),
        na_action="ignore",
    ).fillna(False)
    invalid_ticker = ~valid_ticker
    if invalid_ticker.any():
        raise ValueError("Step 9 Part A input ticker must be six-character string values.")

    data["date"] = pd.to_datetime(data["date"], errors="raise")
    _assert_no_future_dates(data["date"], as_of_date=as_of_date)
    duplicate_rows = data.duplicated(["ticker", "date"], keep=False)
    if duplicate_rows.any():
        raise ValueError("Step 9 Part A input contains duplicate ticker/date rows.")

    data["history_count"] = pd.to_numeric(data["history_count"], errors="raise").astype("int64")
    data["minimum_history_required"] = pd.to_numeric(
        data["minimum_history_required"], errors="raise"
    ).astype("int64")
    data["warmup_state"] = data["warmup_state"].astype("string")
    allowed_warmup = {"ready", "warmup", "insufficient_history"}
    unknown_warmup = sorted(set(data["warmup_state"].dropna()) - allowed_warmup)
    if unknown_warmup:
        raise ValueError(f"Step 9 Part A input has unknown warmup_state values: {unknown_warmup}")

    return data.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def _current_average_percentile(values: pd.Series) -> float:
    if values.empty or pd.isna(values.iloc[-1]):
        return float("nan")
    current = values.iloc[-1]
    observed = values.dropna()
    if observed.empty:
        return float("nan")
    less_count = int((observed < current).sum())
    equal_count = int((observed == current).sum())
    average_rank = less_count + ((equal_count + 1) / 2.0)
    return float(average_rank / len(observed))


def _implemented_contract(score_name: str) -> ScoreImplementationContract:
    for contract in PART_A_SCORE_CONTRACTS:
        if (
            contract.score_name == score_name
            and contract.implementation_status == IMPLEMENTED_FOR_RESEARCH
        ):
            return contract
    raise KeyError(f"No implemented Part A contract for {score_name}.")


def _load_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _positive_int(value: object, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Quant_mvp/config/windows.toml {name} must be a positive integer.") from exc
    if isinstance(value, bool) or parsed <= 0:
        raise ValueError(f"Quant_mvp/config/windows.toml {name} must be a positive integer.")
    return parsed


def _minimum_history_by_score(scores_config: Mapping[str, object]) -> dict[str, int]:
    score_entries = scores_config.get("scores", [])
    values: dict[str, int] = {}
    if isinstance(score_entries, list):
        for entry in score_entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("score_id") or entry.get("name")
            if isinstance(name, str):
                values[name] = _positive_int(entry.get("minimum_history"), f"{name}.minimum_history")

    minimum_history: dict[str, int] = {}
    for contract in PART_A_SCORE_CONTRACTS:
        minimum_history[contract.score_name] = values.get(
            contract.score_name,
            contract.minimum_history,
        )
    return minimum_history


def _assert_no_future_dates(
    dates: pd.Series,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None,
) -> None:
    if as_of_date is None:
        return
    cutoff = _as_timestamp(as_of_date)
    future_mask = dates.dt.normalize() > cutoff
    if future_mask.any():
        first_future = dates.loc[future_mask].min().date()
        raise ValueError(f"Step 9 Part A input contains future dates after {cutoff.date()}: first={first_future}")


def _as_timestamp(value: date | datetime | pd.Timestamp | str) -> pd.Timestamp:
    if isinstance(value, pd.Timestamp):
        return pd.Timestamp(value.date())
    if isinstance(value, datetime):
        return pd.Timestamp(value.date())
    return pd.Timestamp(value)
