"""Simple trading-calendar helpers for local weekday-based refresh logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class TradingCalendarPolicy:
    """Minimal local trading-calendar policy."""

    calendar_id: str = "weekday_only"
    trading_weekdays: frozenset[int] = field(default_factory=lambda: frozenset(range(5)))
    holiday_dates: frozenset[date] = field(default_factory=frozenset)


DEFAULT_TRADING_CALENDAR_POLICY = TradingCalendarPolicy()


def is_trading_day(
    target: Optional[datetime] = None,
    *,
    calendar_policy: TradingCalendarPolicy = DEFAULT_TRADING_CALENDAR_POLICY,
) -> bool:
    """Return True for Monday-Friday.

    This intentionally preserves the current repository behavior and does not
    model exchange holidays unless a policy supplies explicit holiday dates.
    """

    current = target or datetime.now()
    return current.weekday() in calendar_policy.trading_weekdays and current.date() not in calendar_policy.holiday_dates
