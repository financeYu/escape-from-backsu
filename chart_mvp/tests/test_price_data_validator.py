from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from preprocess.price_data_validator import PriceValidationConfig, validate_price_frame


class PriceDataValidatorTests(unittest.TestCase):
    def test_validate_price_frame_detects_core_quality_issues(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "ticker": "005930",
                    "date": "2026-04-23",
                    "open": 100,
                    "high": 90,
                    "low": 95,
                    "close": 100,
                    "volume": 1000,
                    "source": "fixture",
                },
                {
                    "ticker": "005930",
                    "date": "2026-04-23",
                    "open": 100,
                    "high": 110,
                    "low": 90,
                    "close": None,
                    "volume": -1,
                    "source": "fixture",
                },
                {
                    "ticker": "BAD",
                    "date": "not-a-date",
                    "open": 100,
                    "high": 110,
                    "low": 90,
                    "close": 105,
                    "volume": 1000,
                    "source": "fixture",
                },
            ]
        )

        issues, summary, _ = validate_price_frame(
            frame,
            config=PriceValidationConfig(min_history_length=4, warmup_min_history_length=3),
        )
        checks = set(issues["check"].tolist())

        self.assertIn("ticker_format", checks)
        self.assertIn("date_parseability", checks)
        self.assertIn("duplicate_ticker_date", checks)
        self.assertIn("high_less_than_open", checks)
        self.assertIn("missing_close", checks)
        self.assertIn("negative_volume", checks)
        self.assertFalse(summary.empty)

    def test_validate_price_frame_detects_unsorted_dates_and_warmup(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "ticker": "005930",
                    "date": "2026-04-23",
                    "open": 100,
                    "high": 110,
                    "low": 90,
                    "close": 105,
                    "volume": 1000,
                    "source": "fixture",
                },
                {
                    "ticker": "005930",
                    "date": "2026-04-22",
                    "open": 100,
                    "high": 110,
                    "low": 90,
                    "close": 105,
                    "volume": 1000,
                    "source": "fixture",
                },
            ]
        )

        issues, _, _ = validate_price_frame(
            frame,
            config=PriceValidationConfig(min_history_length=3, warmup_min_history_length=3),
        )
        checks = set(issues["check"].tolist())

        self.assertIn("per_ticker_date_ordering", checks)
        self.assertIn("warmup_eligibility", checks)


if __name__ == "__main__":
    unittest.main()

