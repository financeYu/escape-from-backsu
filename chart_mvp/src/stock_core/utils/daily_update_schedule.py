"""Business-day daily update due-check helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
from typing import Optional

from stock_core.utils.trading_calendar import is_trading_day


DEFAULT_DAILY_UPDATE_TIME = time(hour=21, minute=0)


@dataclass(frozen=True)
class DailyUpdateDueStatus:
    """Decision result for the business-day update schedule."""

    is_due: bool
    now: datetime
    due_at: Optional[datetime]
    last_successful_update_date: Optional[date]
    reason: str


def _previous_calendar_day(target: date) -> date:
    return target - timedelta(days=1)


def find_latest_due_datetime(
    now: Optional[datetime] = None,
    update_time: time = DEFAULT_DAILY_UPDATE_TIME,
) -> Optional[datetime]:
    """Return the latest business-day update deadline that has already passed."""

    current = now or datetime.now()
    candidate = datetime.combine(current.date(), update_time)
    if candidate > current:
        candidate = datetime.combine(_previous_calendar_day(current.date()), update_time)

    while not is_trading_day(candidate):
        candidate = datetime.combine(_previous_calendar_day(candidate.date()), update_time)

    return candidate


def read_last_successful_update_date(meta_path: Path) -> Optional[date]:
    """Read the latest successful update date from the persisted run metadata."""

    if not meta_path.exists():
        return None

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    for key in ("last_successful_update_date", "as_of"):
        raw_value = meta.get(key)
        if not raw_value:
            continue
        try:
            return datetime.strptime(str(raw_value)[:10], "%Y-%m-%d").date()
        except ValueError:
            continue

    return None


def get_daily_update_due_status(
    meta_path: Path,
    now: Optional[datetime] = None,
    update_time: time = DEFAULT_DAILY_UPDATE_TIME,
) -> DailyUpdateDueStatus:
    """Return whether the daily batch should run for the latest due business day."""

    current = now or datetime.now()
    due_at = find_latest_due_datetime(now=current, update_time=update_time)
    last_update_date = read_last_successful_update_date(meta_path)

    if due_at is None:
        return DailyUpdateDueStatus(
            is_due=False,
            now=current,
            due_at=None,
            last_successful_update_date=last_update_date,
            reason="아직 갱신 기준 시간이 도래하지 않았습니다.",
        )

    if last_update_date is not None and last_update_date >= due_at.date():
        return DailyUpdateDueStatus(
            is_due=False,
            now=current,
            due_at=due_at,
            last_successful_update_date=last_update_date,
            reason="최신 영업일 갱신이 이미 완료되었습니다.",
        )

    return DailyUpdateDueStatus(
        is_due=True,
        now=current,
        due_at=due_at,
        last_successful_update_date=last_update_date,
        reason="영업일 21시 기준 갱신이 필요합니다.",
    )
