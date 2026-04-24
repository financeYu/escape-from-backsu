from __future__ import annotations

from datetime import date
import sys
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocess.schema_validator import validate_standard_ohlcv_schema


AS_OF_DATE = date(2026, 4, 24)


def frame(**overrides: object) -> pd.DataFrame:
    row = {
        "ticker": "005930",
        "date": "2026-04-23",
        "open": 100,
        "high": 110,
        "low": 90,
        "close": 105,
        "volume": 1000,
    }
    row.update(overrides)
    return pd.DataFrame([row])


class DataValidationContractTests(unittest.TestCase):
    def statuses(self, data: pd.DataFrame) -> dict[str, str]:
        checks = validate_standard_ohlcv_schema(data, as_of_date=AS_OF_DATE)
        return {check.check: check.status for check in checks}

    def test_valid_canonical_ohlcv_passes_schema_contract(self) -> None:
        statuses = self.statuses(frame())

        self.assertEqual(statuses["schema_validation_summary"], "pass")

    def test_ticker_leading_zero_loss_candidate_fails_contract(self) -> None:
        statuses = self.statuses(frame(ticker=5930))

        self.assertEqual(statuses["ticker_string_like"], "fail")
        self.assertEqual(statuses["ticker_leading_zero_preserved"], "fail")

    def test_future_date_fails_contract(self) -> None:
        statuses = self.statuses(frame(date="2026-04-25"))

        self.assertEqual(statuses["future_dates_absent"], "fail")

    def test_duplicate_ticker_date_fails_contract(self) -> None:
        data = pd.concat([frame(), frame(close=106)], ignore_index=True)
        statuses = self.statuses(data)

        self.assertEqual(statuses["duplicate_ticker_date_absent"], "fail")


if __name__ == "__main__":
    unittest.main()
