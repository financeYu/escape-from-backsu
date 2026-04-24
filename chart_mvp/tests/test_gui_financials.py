from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
APP_DIR = PROJECT_ROOT / "app"

for path in (SRC_DIR, APP_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from run_gui import Top5App


class GuiFinancialTests(unittest.TestCase):
    def test_build_financial_statement_pivot_creates_metric_rows(self) -> None:
        raw = pd.DataFrame(
            [
                {"metric": "매출액", "period": "2023/12", "value": "100"},
                {"metric": "매출액", "period": "2024/12(E)", "value": "120"},
                {"metric": "영업이익", "period": "2023/12", "value": "10"},
            ]
        )

        pivot = Top5App._build_financial_statement_pivot(raw)

        self.assertEqual(pivot.columns.tolist(), ["metric", "2023/12", "2024/12(E)"])
        self.assertEqual(pivot.iloc[0]["metric"], "매출액")
        self.assertEqual(pivot.iloc[0]["2024/12(E)"], "120")

    def test_find_financial_metric_value_prefers_requested_period(self) -> None:
        raw = pd.DataFrame(
            [
                {"metric": "EPS(원)", "period": "2023/12", "value": "1000"},
                {"metric": "EPS(원)", "period": "2024/12(E)", "value": "1200"},
            ]
        )

        value = Top5App._find_financial_metric_value(raw, ("EPS",), "2024/12(E)")

        self.assertEqual(value, "1200")


if __name__ == "__main__":
    unittest.main()
