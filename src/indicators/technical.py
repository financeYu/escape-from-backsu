"""Step 7 technical indicator calculation layer.

This module computes deterministic OHLCV-derived indicator dependencies for
later score testing. It does not create scores, rankings, composites, adoption
decisions, or backtests.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
import tomllib
from typing import Iterable

import pandas as pd


REQUIRED_OHLCV_COLUMNS = ("ticker", "date", "open", "high", "low", "close", "volume")
OUTPUT_METADATA_COLUMNS = ("history_count", "minimum_history_required", "warmup_state")
DEFAULT_INPUT_PATH = "data/processed/daily_ohlcv.csv"
DEFAULT_OUTPUT_PATH = "data/processed/technical_indicators.csv"
DEFAULT_SUMMARY_REPORT_PATH = "reports/indicators/indicator_summary.md"
DEFAULT_VALIDATION_REPORT_PATH = "reports/indicators/indicator_validation_summary.csv"
FORBIDDEN_OUTPUT_TOKENS = ("score", "rank", "ranking", "composite", "alpha", "signal")


@dataclass(frozen=True)
class IndicatorPaths:
    """Config-derived Step 7 input and output paths."""

    input_path: str = DEFAULT_INPUT_PATH
    output_path: str = DEFAULT_OUTPUT_PATH
    summary_report_path: str = DEFAULT_SUMMARY_REPORT_PATH
    validation_report_path: str = DEFAULT_VALIDATION_REPORT_PATH


@dataclass(frozen=True)
class IndicatorWindows:
    """Config-derived lookback windows for raw technical indicators."""

    returns: dict[str, int]
    volatility: dict[str, int]
    indicators: dict[str, int]
    statistics: dict[str, int]
    warmup: dict[str, int]


@dataclass(frozen=True)
class IndicatorConfig:
    """Full Step 7 config resolved from data and window TOML files."""

    paths: IndicatorPaths
    windows: IndicatorWindows


@dataclass(frozen=True)
class IndicatorResult:
    """Written Step 7 artifacts and summary metrics."""

    indicators: pd.DataFrame
    validation_summary: pd.DataFrame
    summary: dict[str, object]
    output_path: Path
    summary_report_path: Path
    validation_report_path: Path


def load_indicator_config(
    *,
    data_config_path: str | Path = "config/data.toml",
    windows_config_path: str | Path = "config/windows.toml",
) -> IndicatorConfig:
    """Load Step 7 paths and windows from config files."""

    data_config = _load_toml(Path(data_config_path))
    windows_config = _load_toml(Path(windows_config_path))

    indicator_paths = data_config.get("indicators", {})
    paths = IndicatorPaths(
        input_path=str(indicator_paths.get("input_price_path", DEFAULT_INPUT_PATH)),
        output_path=str(indicator_paths.get("output_path", DEFAULT_OUTPUT_PATH)),
        summary_report_path=str(
            indicator_paths.get("summary_report_path", DEFAULT_SUMMARY_REPORT_PATH)
        ),
        validation_report_path=str(
            indicator_paths.get("validation_report_path", DEFAULT_VALIDATION_REPORT_PATH)
        ),
    )
    windows = IndicatorWindows(
        returns=_positive_ints(windows_config.get("returns", {}), "returns"),
        volatility=_positive_ints(windows_config.get("volatility", {}), "volatility"),
        indicators=_positive_ints(windows_config.get("indicators", {}), "indicators"),
        statistics=_positive_ints(windows_config.get("statistics", {}), "statistics"),
        warmup=_positive_ints(windows_config.get("warmup", {}), "warmup"),
    )
    return IndicatorConfig(paths=paths, windows=windows)


def calculate_technical_indicators(
    frame: pd.DataFrame,
    *,
    windows: IndicatorWindows,
    as_of_date: date | datetime | pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """Return OHLCV rows, status metadata, and raw indicator columns.

    All rolling values use current and prior rows only. Donchian high/low uses a
    prior-bar convention through ``shift(1)`` to avoid same-date breakout
    ambiguity.
    """

    _require_ohlcv_columns(frame)
    data = _prepare_ohlcv(frame, as_of_date=as_of_date)
    _add_history_status(data, windows)
    groups = data.groupby("ticker", group_keys=False, sort=False)

    close = groups["close"]
    high = groups["high"]
    low = groups["low"]

    data["return_1d"] = close.pct_change()
    for window in windows.returns.values():
        data[f"return_{window}d"] = close.pct_change(periods=window)

    previous_close = close.shift(1)
    data["true_range"] = pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - previous_close).abs(),
            (data["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr_window = windows.volatility.get("atr")
    if atr_window:
        data[f"atr_{atr_window}"] = _rolling_mean_by_ticker(data, "true_range", atr_window)

    realized_vol_window = windows.volatility.get("realized_vol")
    if realized_vol_window:
        data[f"realized_vol_{realized_vol_window}"] = groups["return_1d"].rolling(
            realized_vol_window, min_periods=realized_vol_window
        ).std().reset_index(level=0, drop=True)

    vol_of_vol_window = windows.volatility.get("vol_of_vol")
    if vol_of_vol_window and realized_vol_window:
        data[f"vol_of_vol_{vol_of_vol_window}"] = _rolling_std_by_ticker(
            data, f"realized_vol_{realized_vol_window}", vol_of_vol_window
        )

    rsi_window = windows.indicators.get("rsi")
    if rsi_window:
        data[f"rsi_{rsi_window}"] = _rsi(data, rsi_window)

    stochastic_window = windows.indicators.get("stochastic")
    if stochastic_window:
        high_values = high.rolling(
            stochastic_window, min_periods=stochastic_window
        ).max().reset_index(level=0, drop=True)
        low_values = low.rolling(
            stochastic_window, min_periods=stochastic_window
        ).min().reset_index(level=0, drop=True)
        data[f"stochastic_k_{stochastic_window}"] = _safe_divide(
            (data["close"] - low_values) * 100.0,
            high_values - low_values,
        )

    cci_window = windows.indicators.get("cci")
    if cci_window:
        data[f"cci_{cci_window}"] = _cci(data, cci_window)

    williams_window = windows.indicators.get("williams_r")
    if williams_window:
        high_values = high.rolling(
            williams_window, min_periods=williams_window
        ).max().reset_index(level=0, drop=True)
        low_values = low.rolling(
            williams_window, min_periods=williams_window
        ).min().reset_index(level=0, drop=True)
        data[f"williams_r_{williams_window}"] = _safe_divide(
            (high_values - data["close"]) * -100.0,
            high_values - low_values,
        )

    bollinger_window = windows.indicators.get("bollinger")
    if bollinger_window:
        mid_col = f"bollinger_mid_{bollinger_window}"
        std_col = f"bollinger_std_{bollinger_window}"
        data[mid_col] = _rolling_mean_by_ticker(data, "close", bollinger_window)
        data[std_col] = _rolling_std_by_ticker(data, "close", bollinger_window)
        data[f"bollinger_upper_{bollinger_window}"] = data[mid_col] + 2.0 * data[std_col]
        data[f"bollinger_lower_{bollinger_window}"] = data[mid_col] - 2.0 * data[std_col]
        data[f"bollinger_width_{bollinger_window}"] = _safe_divide(
            data[f"bollinger_upper_{bollinger_window}"]
            - data[f"bollinger_lower_{bollinger_window}"],
            data[mid_col],
        )

    donchian_window = windows.indicators.get("donchian")
    if donchian_window:
        shifted_high = high.shift(1)
        shifted_low = low.shift(1)
        data[f"donchian_high_prior_{donchian_window}"] = shifted_high.groupby(
            data["ticker"], group_keys=False, sort=False
        ).rolling(donchian_window, min_periods=donchian_window).max().reset_index(
            level=0, drop=True
        )
        data[f"donchian_low_prior_{donchian_window}"] = shifted_low.groupby(
            data["ticker"], group_keys=False, sort=False
        ).rolling(donchian_window, min_periods=donchian_window).min().reset_index(
            level=0, drop=True
        )

    cmf_window = windows.indicators.get("cmf")
    if cmf_window:
        data[f"cmf_{cmf_window}"] = _cmf(data, cmf_window)

    _add_macd(data, windows)
    _add_volume_indicators(data, windows)
    _add_statistics(data, windows)

    _assert_no_forbidden_columns(data)
    return data.reset_index(drop=True)


def run_indicator_pipeline_from_config(
    *,
    project_root: str | Path = ".",
    data_config_path: str | Path = "config/data.toml",
    windows_config_path: str | Path = "config/windows.toml",
) -> IndicatorResult:
    """Run Step 7 indicator calculation and write configured artifacts."""

    root = Path(project_root)
    config = load_indicator_config(
        data_config_path=root / data_config_path,
        windows_config_path=root / windows_config_path,
    )
    input_path = _resolve_path(root, config.paths.input_path)
    output_path = _resolve_path(root, config.paths.output_path)
    summary_report_path = _resolve_path(root, config.paths.summary_report_path)
    validation_report_path = _resolve_path(root, config.paths.validation_report_path)

    frame = pd.read_csv(input_path, dtype={"ticker": "string"})
    indicators = calculate_technical_indicators(frame, windows=config.windows)
    summary = _build_summary(
        indicators,
        input_path=config.paths.input_path,
        output_path=config.paths.output_path,
        windows=config.windows,
    )
    validation_summary = _validation_summary_frame(summary)

    _write_csv(indicators, output_path)
    _write_csv(validation_summary, validation_report_path)
    _write_summary_report(summary, summary_report_path)
    return IndicatorResult(
        indicators=indicators,
        validation_summary=validation_summary,
        summary=summary,
        output_path=output_path,
        summary_report_path=summary_report_path,
        validation_report_path=validation_report_path,
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Step 7 technical indicator calculation.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--data-config", default="config/data.toml")
    parser.add_argument("--windows-config", default="config/windows.toml")
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = run_indicator_pipeline_from_config(
        project_root=args.project_root,
        data_config_path=args.data_config,
        windows_config_path=args.windows_config,
    )
    print(
        "Step 7 indicators complete: "
        f"rows={result.summary['row_count']}, "
        f"indicator_columns={result.summary['indicator_column_count']}, "
        f"output={result.output_path}"
    )
    return 0


def _load_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _positive_ints(mapping: object, section: str) -> dict[str, int]:
    if not isinstance(mapping, dict):
        return {}
    values: dict[str, int] = {}
    for key, value in mapping.items():
        if key == "notes":
            continue
        try:
            int_value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"config/windows.toml [{section}] {key} must be a positive integer."
            ) from exc
        if isinstance(value, bool) or int_value <= 0:
            raise ValueError(
                f"config/windows.toml [{section}] {key} must be a positive integer."
            )
        values[str(key)] = int_value
    return values


def _require_ohlcv_columns(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_OHLCV_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required OHLCV columns: {', '.join(missing)}")


def _prepare_ohlcv(
    frame: pd.DataFrame,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None,
) -> pd.DataFrame:
    data = frame.loc[:, list(REQUIRED_OHLCV_COLUMNS)].copy()
    data["ticker"] = data["ticker"].astype("string").str.strip()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    _assert_no_future_dates(data["date"], as_of_date=as_of_date)
    for column in ("open", "high", "low", "close", "volume"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    return data.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)


def _assert_no_future_dates(
    dates: pd.Series,
    *,
    as_of_date: date | datetime | pd.Timestamp | str | None,
) -> None:
    cutoff = _as_timestamp(as_of_date)
    future_mask = dates.dt.normalize() > cutoff
    if not future_mask.any():
        return
    first_future = dates.loc[future_mask].min().date()
    raise ValueError(f"Step 7 input contains future dates after {cutoff.date()}: first={first_future}")


def _as_timestamp(value: date | datetime | pd.Timestamp | str | None) -> pd.Timestamp:
    if value is None:
        return pd.Timestamp(date.today())
    if isinstance(value, pd.Timestamp):
        return pd.Timestamp(value.date())
    if isinstance(value, datetime):
        return pd.Timestamp(value.date())
    return pd.Timestamp(value)


def _add_history_status(data: pd.DataFrame, windows: IndicatorWindows) -> None:
    minimum_history_required = _minimum_history_required(windows)
    history_count = data.groupby("ticker", sort=False).cumcount() + 1
    ticker_history_count = data.groupby("ticker", sort=False)["date"].transform("size")
    state = pd.Series("ready", index=data.index, dtype="string")
    state = state.mask(history_count < minimum_history_required, "warmup")
    state = state.mask(ticker_history_count < minimum_history_required, "insufficient_history")

    data["history_count"] = history_count.astype("int64")
    data["minimum_history_required"] = minimum_history_required
    data["warmup_state"] = state


def _minimum_history_required(windows: IndicatorWindows) -> int:
    configured = list(windows.warmup.values())
    active_windows = (
        list(windows.returns.values())
        + list(windows.volatility.values())
        + list(windows.indicators.values())
        + list(windows.statistics.values())
    )
    return max([1, *configured, *active_windows])


def _rolling_mean_by_ticker(data: pd.DataFrame, column: str, window: int) -> pd.Series:
    return data.groupby("ticker", group_keys=False, sort=False)[column].rolling(
        window, min_periods=window
    ).mean().reset_index(level=0, drop=True)


def _rolling_std_by_ticker(data: pd.DataFrame, column: str, window: int) -> pd.Series:
    return data.groupby("ticker", group_keys=False, sort=False)[column].rolling(
        window, min_periods=window
    ).std().reset_index(level=0, drop=True)


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.where(denominator.ne(0))
    return numerator / denominator


def _rsi(data: pd.DataFrame, window: int) -> pd.Series:
    delta = data.groupby("ticker", group_keys=False, sort=False)["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.groupby(data["ticker"], group_keys=False, sort=False).rolling(
        window, min_periods=window
    ).mean().reset_index(level=0, drop=True)
    avg_loss = loss.groupby(data["ticker"], group_keys=False, sort=False).rolling(
        window, min_periods=window
    ).mean().reset_index(level=0, drop=True)
    rs = _safe_divide(avg_gain, avg_loss)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.where(avg_loss.ne(0), 100.0).where(avg_gain.ne(0), 0.0)


def _cci(data: pd.DataFrame, window: int) -> pd.Series:
    typical_price = (data["high"] + data["low"] + data["close"]) / 3.0
    tp_frame = pd.DataFrame({"ticker": data["ticker"], "typical_price": typical_price})
    rolling_mean = tp_frame.groupby("ticker", group_keys=False, sort=False)[
        "typical_price"
    ].rolling(window, min_periods=window).mean().reset_index(level=0, drop=True)
    mean_abs_deviation = tp_frame.groupby("ticker", group_keys=False, sort=False)[
        "typical_price"
    ].rolling(window, min_periods=window).apply(
        lambda values: float((abs(values - values.mean())).mean()),
        raw=False,
    ).reset_index(level=0, drop=True)
    return _safe_divide(typical_price - rolling_mean, 0.015 * mean_abs_deviation)


def _cmf(data: pd.DataFrame, window: int) -> pd.Series:
    high_low_range = (data["high"] - data["low"]).where((data["high"] - data["low"]).ne(0))
    money_flow_multiplier = (
        (data["close"] - data["low"]) - (data["high"] - data["close"])
    ) / high_low_range
    money_flow_multiplier = money_flow_multiplier.fillna(0.0)
    money_flow_volume = money_flow_multiplier * data["volume"]
    mfv = pd.DataFrame({"ticker": data["ticker"], "money_flow_volume": money_flow_volume})
    volume = pd.DataFrame({"ticker": data["ticker"], "volume": data["volume"]})
    mfv_sum = mfv.groupby("ticker", group_keys=False, sort=False)[
        "money_flow_volume"
    ].rolling(window, min_periods=window).sum().reset_index(level=0, drop=True)
    volume_sum = volume.groupby("ticker", group_keys=False, sort=False)["volume"].rolling(
        window, min_periods=window
    ).sum().reset_index(level=0, drop=True)
    return _safe_divide(mfv_sum, volume_sum)


def _add_macd(data: pd.DataFrame, windows: IndicatorWindows) -> None:
    fast = windows.indicators.get("macd_fast")
    slow = windows.indicators.get("macd_slow")
    trigger = windows.indicators.get("macd_trigger")
    if not fast or not slow or not trigger:
        return
    close = data.groupby("ticker", group_keys=False, sort=False)["close"]
    ema_fast = close.transform(lambda values: values.ewm(span=fast, adjust=False, min_periods=fast).mean())
    ema_slow = close.transform(lambda values: values.ewm(span=slow, adjust=False, min_periods=slow).mean())
    macd_col = f"macd_{fast}_{slow}"
    trigger_col = f"macd_trigger_{trigger}"
    data[f"ema_{fast}"] = ema_fast
    data[f"ema_{slow}"] = ema_slow
    data[macd_col] = ema_fast - ema_slow
    data[trigger_col] = data.groupby("ticker", group_keys=False, sort=False)[macd_col].transform(
        lambda values: values.ewm(span=trigger, adjust=False, min_periods=trigger).mean()
    )
    data[f"macd_hist_{fast}_{slow}_{trigger}"] = data[macd_col] - data[trigger_col]


def _add_volume_indicators(data: pd.DataFrame, windows: IndicatorWindows) -> None:
    obv_window = windows.indicators.get("obv_slope")
    adl_window = windows.indicators.get("adl_slope")
    close_delta = data.groupby("ticker", group_keys=False, sort=False)["close"].diff()
    direction = close_delta.gt(0).astype(int) - close_delta.lt(0).astype(int)
    data["obv"] = (direction * data["volume"]).groupby(
        data["ticker"], group_keys=False, sort=False
    ).cumsum()

    high_low_range = (data["high"] - data["low"]).where((data["high"] - data["low"]).ne(0))
    money_flow_multiplier = (
        (data["close"] - data["low"]) - (data["high"] - data["close"])
    ) / high_low_range
    money_flow_multiplier = money_flow_multiplier.fillna(0.0)
    data["adl"] = (money_flow_multiplier * data["volume"]).groupby(
        data["ticker"], group_keys=False, sort=False
    ).cumsum()

    if obv_window:
        data[f"obv_slope_{obv_window}"] = data.groupby(
            "ticker", group_keys=False, sort=False
        )["obv"].transform(lambda values: (values - values.shift(obv_window)) / obv_window)
    if adl_window:
        data[f"adl_slope_{adl_window}"] = data.groupby(
            "ticker", group_keys=False, sort=False
        )["adl"].transform(lambda values: (values - values.shift(adl_window)) / adl_window)


def _add_statistics(data: pd.DataFrame, windows: IndicatorWindows) -> None:
    autocorr_window = windows.statistics.get("autocorrelation")
    if autocorr_window:
        data[f"return_autocorr_{autocorr_window}"] = data.groupby(
            "ticker", group_keys=False, sort=False
        )["return_1d"].rolling(
            autocorr_window, min_periods=autocorr_window
        ).apply(lambda values: float(pd.Series(values).autocorr(lag=1)), raw=False).reset_index(
            level=0, drop=True
        )

    abs_autocorr_window = windows.statistics.get("abs_return_autocorrelation")
    if abs_autocorr_window:
        data["abs_return_1d"] = data["return_1d"].abs()
        data[f"abs_return_autocorr_{abs_autocorr_window}"] = data.groupby(
            "ticker", group_keys=False, sort=False
        )["abs_return_1d"].rolling(
            abs_autocorr_window, min_periods=abs_autocorr_window
        ).apply(lambda values: float(pd.Series(values).autocorr(lag=1)), raw=False).reset_index(
            level=0, drop=True
        )

    volume_return_window = windows.statistics.get("volume_return_correlation")
    if volume_return_window:
        data["volume_change_1d"] = data.groupby("ticker", group_keys=False, sort=False)[
            "volume"
        ].pct_change()
        data[f"volume_return_corr_{volume_return_window}"] = data.groupby(
            "ticker", group_keys=False, sort=False
        ).apply(
            lambda group: group["return_1d"].rolling(
                volume_return_window, min_periods=volume_return_window
            ).corr(group["volume_change_1d"])
        ).reset_index(level=0, drop=True)

    efficiency_window = windows.statistics.get("efficiency_ratio")
    if efficiency_window:
        endpoint_change = data.groupby("ticker", group_keys=False, sort=False)["close"].diff(
            efficiency_window
        ).abs()
        path_length = data.groupby("ticker", group_keys=False, sort=False)[
            "close"
        ].diff().abs().groupby(data["ticker"], group_keys=False, sort=False).rolling(
            efficiency_window, min_periods=efficiency_window
        ).sum().reset_index(level=0, drop=True)
        data[f"efficiency_ratio_{efficiency_window}"] = _safe_divide(
            endpoint_change, path_length
        )

    noise_window = windows.statistics.get("noise_ratio")
    if noise_window:
        endpoint_change = data.groupby("ticker", group_keys=False, sort=False)["close"].diff(
            noise_window
        ).abs()
        path_length = data.groupby("ticker", group_keys=False, sort=False)[
            "close"
        ].diff().abs().groupby(data["ticker"], group_keys=False, sort=False).rolling(
            noise_window, min_periods=noise_window
        ).sum().reset_index(level=0, drop=True)
        data[f"noise_ratio_{noise_window}"] = _safe_divide(path_length, endpoint_change)


def _assert_no_forbidden_columns(frame: pd.DataFrame) -> None:
    forbidden = [
        column
        for column in frame.columns
        if any(token in column.lower() for token in FORBIDDEN_OUTPUT_TOKENS)
    ]
    if forbidden:
        raise ValueError(
            "Step 7 indicator layer must not emit score/rank/composite/alpha/signal "
            f"columns: {forbidden}"
        )


def _resolve_path(root: Path, path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return root / candidate


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")


def _build_summary(
    indicators: pd.DataFrame,
    *,
    input_path: str,
    output_path: str,
    windows: IndicatorWindows,
) -> dict[str, object]:
    indicator_columns = [
        column
        for column in indicators.columns
        if column not in REQUIRED_OHLCV_COLUMNS and column not in OUTPUT_METADATA_COLUMNS
    ]
    warmup_counts = indicators["warmup_state"].value_counts(dropna=False).to_dict()
    return {
        "step": "Step 7",
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "input_path": input_path,
        "output_path": output_path,
        "row_count": int(len(indicators)),
        "ticker_count": int(indicators["ticker"].nunique()) if not indicators.empty else 0,
        "date_range_start": str(indicators["date"].min().date()) if not indicators.empty else "",
        "date_range_end": str(indicators["date"].max().date()) if not indicators.empty else "",
        "indicator_column_count": len(indicator_columns),
        "indicator_columns": ", ".join(indicator_columns),
        "metadata_columns": ", ".join(OUTPUT_METADATA_COLUMNS),
        "ready_rows": int(warmup_counts.get("ready", 0)),
        "warmup_rows": int(warmup_counts.get("warmup", 0)),
        "insufficient_history_rows": int(warmup_counts.get("insufficient_history", 0)),
        "return_windows": ", ".join(str(value) for value in windows.returns.values()),
        "volatility_windows": ", ".join(str(value) for value in windows.volatility.values()),
        "indicator_windows": ", ".join(str(value) for value in windows.indicators.values()),
        "statistics_windows": ", ".join(str(value) for value in windows.statistics.values()),
        "score_implementation": "not_performed",
        "ranking_generation": "not_performed",
        "composite_generation": "not_performed",
        "backtest": "not_performed",
        "valuation_or_fundamental_scoring": "not_performed",
    }


def _validation_summary_frame(summary: dict[str, object]) -> pd.DataFrame:
    rows = []
    for metric, value in summary.items():
        status = "pass" if metric.endswith(("implementation", "generation", "backtest", "scoring")) else "info"
        rows.append({"metric": metric, "value": value, "status": status})
    return pd.DataFrame(rows, columns=["metric", "value", "status"])


def _write_summary_report(summary: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Step 7 Indicator Summary",
        "",
        "이 보고서는 일봉 OHLCV 기반 technical indicator 계산 결과만 요약합니다.",
        "score 구현, ranking 생성, composite 생성, adoption decision, backtest는 수행하지 않았습니다.",
        "가격 기반 technical indicator는 valuation evidence가 아닙니다.",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- 모든 지표는 Step 6 canonical OHLCV 입력에 의존합니다.",
            "- `history_count`, `minimum_history_required`, `warmup_state`로 warmup/insufficient history 상태를 표시합니다.",
            "- warmup 구간의 NaN은 보수적으로 유지합니다.",
            "- as-of date 이후의 future date 입력은 거부합니다.",
            "- Step 8 normalization protocol 전까지 0-100 normalized score를 생성하지 않습니다.",
            "- Step 9 전까지 candidate score formula를 구현하지 않습니다.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
