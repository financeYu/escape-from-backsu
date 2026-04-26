"""Step 7 raw technical indicator calculation engine."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from .indicator_config import IndicatorWindows


REQUIRED_OHLCV_COLUMNS = ("ticker", "date", "open", "high", "low", "close", "volume")
OUTPUT_METADATA_COLUMNS = ("history_count", "minimum_history_required", "warmup_state")
FORBIDDEN_OUTPUT_TOKENS = ("score", "rank", "ranking", "composite", "alpha", "signal")


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
    raise ValueError(
        f"Step 7 input contains future dates after {cutoff.date()}: first={first_future}"
    )


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
    ema_fast = close.transform(
        lambda values: values.ewm(span=fast, adjust=False, min_periods=fast).mean()
    )
    ema_slow = close.transform(
        lambda values: values.ewm(span=slow, adjust=False, min_periods=slow).mean()
    )
    macd_col = f"macd_{fast}_{slow}"
    trigger_col = f"macd_trigger_{trigger}"
    data[f"ema_{fast}"] = ema_fast
    data[f"ema_{slow}"] = ema_slow
    data[macd_col] = ema_fast - ema_slow
    data[trigger_col] = data.groupby("ticker", group_keys=False, sort=False)[
        macd_col
    ].transform(lambda values: values.ewm(span=trigger, adjust=False, min_periods=trigger).mean())
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
        endpoint_change = data.groupby("ticker", group_keys=False, sort=False)[
            "close"
        ].diff(efficiency_window).abs()
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
        endpoint_change = data.groupby("ticker", group_keys=False, sort=False)[
            "close"
        ].diff(noise_window).abs()
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


__all__ = [
    "FORBIDDEN_OUTPUT_TOKENS",
    "OUTPUT_METADATA_COLUMNS",
    "REQUIRED_OHLCV_COLUMNS",
    "calculate_technical_indicators",
]
