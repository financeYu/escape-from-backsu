from __future__ import annotations

import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.utils.daily_update_schedule import (
    find_latest_due_datetime,
    get_daily_update_due_status,
)
from stock_core.utils.trading_calendar import TradingCalendarPolicy, is_trading_day


class TradingCalendarTests(unittest.TestCase):
    def test_weekday_is_trading_day(self) -> None:
        self.assertTrue(is_trading_day(datetime(2026, 4, 20)))

    def test_weekend_is_not_trading_day(self) -> None:
        self.assertFalse(is_trading_day(datetime(2026, 4, 19)))

    def test_calendar_policy_can_override_holidays(self) -> None:
        calendar_policy = TradingCalendarPolicy(holiday_dates=frozenset({date(2026, 4, 20)}))

        self.assertFalse(is_trading_day(datetime(2026, 4, 20), calendar_policy=calendar_policy))

    def test_latest_due_datetime_uses_current_business_day_after_21(self) -> None:
        due_at = find_latest_due_datetime(datetime(2026, 4, 20, 21, 1))

        self.assertEqual(due_at, datetime(2026, 4, 20, 21, 0))

    def test_latest_due_datetime_catches_friday_before_monday_21(self) -> None:
        due_at = find_latest_due_datetime(datetime(2026, 4, 20, 20, 59))

        self.assertEqual(due_at, datetime(2026, 4, 17, 21, 0))

    def test_latest_due_datetime_catches_previous_business_day_after_midnight(self) -> None:
        due_at = find_latest_due_datetime(datetime(2026, 4, 21, 0, 30))

        self.assertEqual(due_at, datetime(2026, 4, 20, 21, 0))

    def test_latest_due_datetime_catches_friday_on_weekend(self) -> None:
        due_at = find_latest_due_datetime(datetime(2026, 4, 25, 21, 1))

        self.assertEqual(due_at, datetime(2026, 4, 24, 21, 0))

    def test_due_status_catches_missed_friday_on_monday_before_21(self) -> None:
        meta_path = Path("last_run_meta.json")
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value='{"last_successful_update_date": "2026-04-16"}'),
        ):
            status = get_daily_update_due_status(meta_path, now=datetime(2026, 4, 20, 20, 59))

        self.assertTrue(status.is_due)
        self.assertEqual(status.due_at, datetime(2026, 4, 17, 21, 0))

    def test_due_status_is_due_when_latest_business_day_was_not_updated(self) -> None:
        meta_path = Path("last_run_meta.json")
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value='{"last_successful_update_date": "2026-04-17"}'),
        ):
            status = get_daily_update_due_status(meta_path, now=datetime(2026, 4, 20, 21, 1))

        self.assertTrue(status.is_due)
        self.assertEqual(status.due_at, datetime(2026, 4, 20, 21, 0))

    def test_due_status_skips_when_latest_business_day_was_updated(self) -> None:
        meta_path = Path("last_run_meta.json")
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "read_text", return_value='{"last_successful_update_date": "2026-04-20"}'),
        ):
            status = get_daily_update_due_status(meta_path, now=datetime(2026, 4, 20, 21, 1))

        self.assertFalse(status.is_due)
        self.assertEqual(status.reason, "최신 영업일 갱신이 이미 완료되었습니다.")


if __name__ == "__main__":
    unittest.main()
