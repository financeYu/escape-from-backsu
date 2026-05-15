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
from stock_core.providers.naver_finance import (
    _make_unique_column_names,
    extract_financial_statements_from_html,
    extract_ratio_policy_snapshot_from_html,
)


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

HTML_RATIO_POLICY_SAMPLE = """
<html>
  <body>
    종목 시세 정보 2026년 05월 15일 16시 10분 기준 장마감
    날짜 2026.05.15 기준(KRX 장마감)
    현재가 270,500
    투자정보
    상장주식수 5,846,278,608
    PER/EPS PER l EPS(2025.12)
    PER = 현재가 ÷ EPS EPS는 지배기업귀속 최근 4분기 합산 순이익을 수정평균발행주식수로 나눈 값이며,
    보통주와 우선주를 합산해서 계산합니다.
    41.21 배 l 6,564 원
    PBR l BPS (2025.12)
    PBR= 현재가 ÷ BPS BPS는 최근 분기 자본총계를 수정기말유통주식수로 나눈 값이며,
    보통주와 우선주를 합산해서 계산합니다.
    4.23 배 l 63,997 원
    배당수익률 = (배당금 / 현재가) x 100
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

    def test_extract_ratio_policy_snapshot_from_html_records_reference_policy(self) -> None:
        row = extract_ratio_policy_snapshot_from_html(
            HTML_RATIO_POLICY_SAMPLE,
            code="005930",
            fetched_at="2026-05-15T11:00:00+00:00",
            raw_html_path="raw.html",
        )

        self.assertEqual(row["ticker"], "005930")
        self.assertEqual(row["vendor_snapshot_date"], "2026-05-15T11:00:00+00:00")
        self.assertEqual(row["price_date"], "2026-05-15")
        self.assertEqual(row["price_value"], "270,500")
        self.assertEqual(row["price_policy"], "naver_main_current_price")
        self.assertEqual(row["adjusted_price_policy"], "not_disclosed_by_naver_main")
        self.assertIn("modified_average_issued_shares", row["eps_policy"])
        self.assertIn("modified_period_end_floating_shares", row["bps_policy"])
        self.assertEqual(row["per_formula"], "current_price_divided_by_eps_vendor_reported")
        self.assertEqual(row["pbr_formula"], "current_price_divided_by_bps_vendor_reported")
        self.assertIn("adjusted_price_policy", row["missing_policy_fields"])

    def test_ratio_policy_source_available_date_uses_kst_crawl_date(self) -> None:
        row = extract_ratio_policy_snapshot_from_html(
            HTML_RATIO_POLICY_SAMPLE,
            code="005930",
            fetched_at="2026-05-15T15:30:00+00:00",
            raw_html_path="raw.html",
        )

        self.assertEqual(row["source_available_date"], "2026-05-16")

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

    def test_refresh_stock_data_skips_financial_statements_by_default(self) -> None:
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
        mock_save_financials.assert_not_called()

    def test_refresh_stock_data_saves_financial_statements_when_requested(self) -> None:
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
            _, source = csv_cache.refresh_stock_data(code="005930", pages=1, refresh_financials=True)

        self.assertEqual(source, "fetched")
        mock_save_financials.assert_called_once_with(statement_df, "005930")

    def test_naver_price_provider_normalizes_lowercase_alphanumeric_code(self) -> None:
        from stock_core.providers import naver_price_provider

        raw_df = pd.DataFrame(
            {
                "날짜": ["2026.04.24"],
                "종가": [574000],
                "전일비": [13000],
                "시가": [598000],
                "고가": [600000],
                "저가": [573000],
                "거래량": [74904],
            }
        )

        with patch("stock_core.providers.naver_price_provider.crawl_stock_data", return_value=raw_df) as mock_fetch:
            frame = naver_price_provider.get_price_df("0126z0", pages=1, use_cache=False)

        mock_fetch.assert_called_once()
        self.assertEqual(mock_fetch.call_args.kwargs["code"], "0126Z0")
        self.assertEqual(frame["날짜"].iloc[0].strftime("%Y-%m-%d"), "2026-04-24")


if __name__ == "__main__":
    unittest.main()
