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
from stock_core.providers.naver_finance import _make_unique_column_names, extract_financial_statements_from_html


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

HTML_NON_PERIOD_SAMPLE = f"""
<html>
  <body>
    <table>
      <thead>
        <tr>
          <th>{HEADER_MAIN}</th>
          <th>삼성전자*005930</th>
          <th>SK하이닉스*000660</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>PER</td>
          <td>10</td>
          <td>20</td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


class NaverFinanceTests(unittest.TestCase):
    def test_make_unique_column_names_preserves_first_label(self) -> None:
        columns = _make_unique_column_names(["metric", "2024/12", "2024/12", ""])

        self.assertEqual(columns, ["metric", "2024/12", "2024/12__2", "column_3"])

    def test_extract_financial_statements_from_html_returns_tidy_rows(self) -> None:
        frame = extract_financial_statements_from_html(HTML_SAMPLE, code="005930")

        self.assertEqual(frame["code"].unique().tolist(), ["005930"])
        self.assertEqual(
            frame["metric"].tolist(),
            [METRIC_REVENUE, METRIC_REVENUE, METRIC_OPERATING_INCOME, METRIC_OPERATING_INCOME],
        )
        self.assertEqual(frame["period"].tolist(), ["2023/12", "2024/12(E)", "2023/12", "2024/12(E)"])
        self.assertEqual(frame["value"].tolist(), ["100", "120", "10", "15"])

    def test_extract_financial_statements_ignores_non_period_comparison_tables(self) -> None:
        frame = extract_financial_statements_from_html(HTML_NON_PERIOD_SAMPLE, code="005930")

        self.assertTrue(frame.empty)

    def test_save_financial_statements_uses_expected_cache_path(self) -> None:
        frame = pd.DataFrame(
            [{"code": "005930", "table_index": "0", "metric": METRIC_REVENUE, "period": "2023/12", "value": "100"}]
        )

        temp_data_dir = PROJECT_ROOT / "tests" / "_tmp" / "financial_cache"
        with (
            patch("stock_core.cache.csv_cache.DATA_DIR", temp_data_dir),
            patch.object(pd.DataFrame, "to_csv") as mock_to_csv,
        ):
            cache_path = get_financial_statement_cache_path("005930")
            saved_path = save_financial_statements(frame, "005930")

        self.assertEqual(saved_path, cache_path)
        mock_to_csv.assert_called_once_with(cache_path, index=False, encoding="utf-8-sig")

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
