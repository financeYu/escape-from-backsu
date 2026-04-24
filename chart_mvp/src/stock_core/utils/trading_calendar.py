"""Simple trading-calendar helpers for local weekday-based refresh logic."""

from __future__ import annotations

from datetime import datetime
from typing import Optional


def is_trading_day(target: Optional[datetime] = None) -> bool:
    """Return True for Monday-Friday.

    This intentionally preserves the current repository behavior and does not
    model Korean exchange holidays yet.
    """

    current = target or datetime.now()
    return current.weekday() < 5
