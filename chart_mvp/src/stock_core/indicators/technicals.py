"""Public technical indicator interface."""

from __future__ import annotations

import pandas as pd

from stock_core.indicators.technical import add_indicators as _add_indicators


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add the current technical indicators to a normalized price DataFrame."""

    return _add_indicators(df)
