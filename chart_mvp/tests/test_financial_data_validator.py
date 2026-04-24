from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from preprocess.financial_data_validator import validate_financial_frame


class FinancialDataValidatorTests(unittest.TestCase):
    def test_collected_at_does_not_verify_point_in_time_safety(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "code": "005930",
                    "table_index": "0",
                    "metric": "EPS",
                    "period": "2024/12",
                    "value": "1000",
                    "collected_at": "2026-04-25",
                }
            ]
        )

        result = validate_financial_frame(frame)
        checks = set(result.issues["check"].tolist())

        self.assertEqual(result.point_in_time_status, "unverified")
        self.assertEqual(result.future_valuation_safety, "unsafe_without_availability_dates")
        self.assertIn("collection_timestamp_is_not_pit", checks)

    def test_availability_date_can_verify_point_in_time_safety(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "code": "005930",
                    "table_index": "0",
                    "metric": "EPS",
                    "period": "2024/12",
                    "value": "1000",
                    "availability_date": "2025-03-31",
                }
            ]
        )

        result = validate_financial_frame(frame)

        self.assertEqual(result.point_in_time_status, "verified")
        self.assertEqual(result.future_valuation_safety, "safe_with_disclosure_dates")

    def test_partial_pit_coverage_requires_row_level_filter(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "code": "005930",
                    "table_index": "0",
                    "metric": "EPS",
                    "period": "2024/12",
                    "value": "1000",
                    "filing_date": "2025-03-31",
                },
                {
                    "code": "005930",
                    "table_index": "0",
                    "metric": "BPS",
                    "period": "2024/12",
                    "value": "50000",
                    "filing_date": "",
                },
            ]
        )

        result = validate_financial_frame(frame)

        self.assertEqual(result.point_in_time_status, "partially_verified")
        self.assertEqual(result.future_valuation_safety, "partial_requires_row_level_filter")

    def test_invalid_fiscal_period_and_missing_columns_are_reported(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "code": "005930",
                    "metric": "EPS",
                    "period": "bad-period",
                    "value": "1000",
                }
            ]
        )

        result = validate_financial_frame(frame)
        warnings = result.issues[result.issues["severity"] == "warning"]
        checks = set(warnings["check"].tolist())

        self.assertIn("available_column:table_index", checks)
        self.assertIn("fiscal_period_column:period", checks)


if __name__ == "__main__":
    unittest.main()
