from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.cache.csv_cache import get_financial_statement_cache_path, save_financial_statements
from stock_core.providers.naver_finance import extract_financial_statements_from_html


METRIC_REVENUE = "\ub9e4\ucd9c\uc561"
METRIC_OPERATING_INCOME = "\uc601\uc5c5\uc774\uc775"
HEADER_MAIN = "\uc8fc\uc694\uc7ac\ubb34\uc815\ubcf4"

HTML_SAMPLE = f"""
<html>
  <body>
    <table>
      <thead>
        <tr>
          <th>{HEADER_MAIN}</th>
          <th>2023/12</th>
          <th>2024/12(E)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>{METRIC_REVENUE}</td>
          <td>100</td>
          <td>120</td>
        </tr>
        <tr>
          <td>{METRIC_OPERATING_INCOME}</td>
          <td>10</td>
          <td>15</td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


class NaverFinanceTests(unittest.TestCase):
    def test_extract_financial_statements_from_html_returns_tidy_rows(self) -> None:
        frame = extract_financial_statements_from_html(HTML_SAMPLE, code="005930")

        self.assertEqual(frame["code"].unique().tolist(), ["005930"])
        self.assertEqual(
            frame["metric"].tolist(),
            [METRIC_REVENUE, METRIC_REVENUE, METRIC_OPERATING_INCOME, METRIC_OPERATING_INCOME],
        )
        self.assertEqual(frame["period"].tolist(), ["2023/12", "2024/12(E)", "2023/12", "2024/12(E)"])
        self.assertEqual(frame["value"].tolist(), ["100", "120", "10", "15"])

    def test_save_financial_statements_uses_expected_cache_path(self) -> None:
        frame = pd.DataFrame(
            [{"code": "005930", "table_index": "0", "metric": METRIC_REVENUE, "period": "2023/12", "value": "100"}]
        )
        cache_path = get_financial_statement_cache_path("005930")

        try:
            saved_path = save_financial_statements(frame, "005930")
            self.assertEqual(saved_path, cache_path)
            self.assertTrue(saved_path.exists())
        finally:
            if cache_path.exists():
                cache_path.unlink()

    def test_refresh_stock_data_saves_financial_statements_when_fetching(self) -> None:
        from stock_core.cache import csv_cache

        price_df = pd.DataFrame({"x": [1]})
        statement_df = pd.DataFrame(
            [{"code": "005930", "table_index": "0", "metric": METRIC_REVENUE, "period": "2023/12", "value": "100"}]
        )

        with (
            patch("stock_core.cache.csv_cache.get_cache_path", return_value=PROJECT_ROOT / "data" / "__missing__.csv"),
            patch("stock_core.cache.csv_cache.crawl_stock_data", return_value=price_df),
            patch("stock_core.cache.csv_cache.clean_stock_data", return_value=price_df),
            patch("stock_core.cache.csv_cache.add_indicators", return_value=price_df),
            patch("stock_core.cache.csv_cache.save_stock_data"),
            patch("stock_core.cache.csv_cache.crawl_financial_statements", return_value=statement_df),
            patch("stock_core.cache.csv_cache.save_financial_statements") as mock_save_financials,
        ):
            _, source = csv_cache.refresh_stock_data(code="005930", pages=1)

        self.assertEqual(source, "fetched")
        mock_save_financials.assert_called_once_with(statement_df, "005930")


if __name__ == "__main__":
    unittest.main()
