"""Technical indicator calculations."""

from __future__ import annotations

import pandas as pd

from stock_core.utils.constants import CLOSE_COLUMN, VOLUME_COLUMN


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add moving averages, Bollinger Bands, volume average, and RSI."""

    if CLOSE_COLUMN not in df.columns:
        raise ValueError(f"The DataFrame does not contain the '{CLOSE_COLUMN}' column.")

    result = df.copy()
    close = pd.to_numeric(result[CLOSE_COLUMN], errors="coerce")
    result["MA5"] = close.rolling(window=5).mean()
    result["MA20"] = close.rolling(window=20).mean()

    rolling_std = close.rolling(window=20).std()
    result["BB_MID"] = result["MA20"]
    result["BB_UPPER"] = result["MA20"] + (rolling_std * 2)
    result["BB_LOWER"] = result["MA20"] - (rolling_std * 2)

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain.divide(avg_loss.where(avg_loss != 0))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    rsi = rsi.mask((avg_loss == 0) & (avg_gain == 0), 50.0)
    result["RSI14"] = rsi
    result["RSI_SIGNAL"] = result["RSI14"].rolling(window=14).mean()
    if VOLUME_COLUMN in result.columns:
        volume = pd.to_numeric(result[VOLUME_COLUMN], errors="coerce")
        result["VOLUME_MA20"] = volume.rolling(window=20).mean()
    else:
        result["VOLUME_MA20"] = pd.NA
    return result
