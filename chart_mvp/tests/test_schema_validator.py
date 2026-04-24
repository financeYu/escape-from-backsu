from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from preprocess.schema_validator import normalize_price_columns, validate_standard_price_schema


class SchemaValidatorTests(unittest.TestCase):
    def test_normalize_price_columns_maps_korean_cache_columns(self) -> None:
        frame = pd.DataFrame(
            {
                "날짜": ["2026-04-23"],
                "시가": [100],
                "고가": [110],
                "저가": [90],
                "종가": [105],
                "거래량": [1000],
            }
        )

        normalized = normalize_price_columns(frame, ticker="005930", source="cache")

        self.assertEqual(
            normalized[["ticker", "date", "open", "high", "low", "close", "volume", "source"]].iloc[0].to_dict(),
            {
                "ticker": "005930",
                "date": "2026-04-23",
                "open": 100,
                "high": 110,
                "low": 90,
                "close": 105,
                "volume": 1000,
                "source": "cache",
            },
        )

    def test_validate_standard_price_schema_reports_missing_required_columns(self) -> None:
        checks = validate_standard_price_schema(pd.DataFrame({"ticker": ["005930"]}))
        failed = [check.check for check in checks if check.status == "fail"]

        self.assertIn("required_column:date", failed)
        self.assertIn("required_column:close", failed)

    def test_validate_standard_price_schema_reports_ticker_leading_zero_loss(self) -> None:
        frame = pd.DataFrame(
            {
                "ticker": [5930],
                "date": ["2026-04-23"],
                "open": [100],
                "high": [110],
                "low": [90],
                "close": [105],
                "volume": [1000],
                "source": ["cache"],
            }
        )

        checks = validate_standard_price_schema(frame)
        failed = {check.check for check in checks if check.status == "fail"}

        self.assertIn("ticker_string_like", failed)
        self.assertIn("ticker_leading_zero_preserved", failed)

    def test_validate_standard_price_schema_reports_bad_dates_and_numbers(self) -> None:
        frame = pd.DataFrame(
            {
                "ticker": ["005930"],
                "date": ["not-a-date"],
                "open": ["not-a-number"],
                "high": [110],
                "low": [90],
                "close": [105],
                "volume": [1000],
                "source": ["cache"],
            }
        )

        checks = validate_standard_price_schema(frame)
        failed = {check.check for check in checks if check.status == "fail"}

        self.assertIn("date_parseable", failed)
        self.assertIn("numeric_columns_convertible:open", failed)

    def test_validate_standard_price_schema_reports_duplicate_ticker_date(self) -> None:
        frame = pd.DataFrame(
            {
                "ticker": ["005930", "005930"],
                "date": ["2026-04-23", "2026-04-23"],
                "open": [100, 101],
                "high": [110, 111],
                "low": [90, 91],
                "close": [105, 106],
                "volume": [1000, 1001],
                "source": ["cache", "cache"],
            }
        )

        checks = validate_standard_price_schema(frame)
        failed = {check.check for check in checks if check.status == "fail"}

        self.assertIn("duplicate_ticker_date_absent", failed)


if __name__ == "__main__":
    unittest.main()
