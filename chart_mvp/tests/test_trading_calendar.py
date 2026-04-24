from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.utils.trading_calendar import is_trading_day


class TradingCalendarTests(unittest.TestCase):
    def test_weekday_is_trading_day(self) -> None:
        self.assertTrue(is_trading_day(datetime(2026, 4, 20)))

    def test_weekend_is_not_trading_day(self) -> None:
        self.assertFalse(is_trading_day(datetime(2026, 4, 19)))


if __name__ == "__main__":
    unittest.main()

