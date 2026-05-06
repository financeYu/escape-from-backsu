from __future__ import annotations

from datetime import date
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.pipeline.historical_kospi200_collection import (
    HistoricalCollectionConfig,
    build_execution_plan,
    build_security_collection_plan,
    check_required_krx_api_key,
    collect_historical_kospi200_naver_data,
    filter_membership_for_lookback,
)
from stock_core.utils.constants import CLOSE_COLUMN, DATE_COLUMN, HIGH_COLUMN, LOW_COLUMN, OPEN_COLUMN, PREV_DIFF_COLUMN, VOLUME_COLUMN


class HistoricalKospi200CollectionTests(unittest.TestCase):
    def _membership(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "index_code": "KOSPI200",
                    "security_id": "krx:005930",
                    "ticker": "005930",
                    "company_name": "Samsung",
                    "effective_start": "2010-01-01",
                    "effective_end": "",
                    "listing_status": "listed",
                },
                {
                    "index_code": "KOSPI200",
                    "security_id": "krx:123450",
                    "ticker": "123450",
                    "company_name": "Old Member",
                    "effective_start": "2018-01-01",
                    "effective_end": "2020-01-31",
                    "listing_status": "delisted",
                },
                {
                    "index_code": "KOSPI200",
                    "security_id": "krx:222222",
                    "ticker": "222222",
                    "company_name": "Too Old",
                    "effective_start": "2010-01-01",
                    "effective_end": "2011-01-01",
                    "listing_status": "delisted",
                },
            ]
        )

    def _price_fetcher(self, *, code: str, pages: int, sleep_seconds: float) -> pd.DataFrame:
        _ = (pages, sleep_seconds)
        if code == "123450":
            raise ValueError("No stock data was collected")
        return pd.DataFrame(
            [
                {
                    DATE_COLUMN: "2026-04-01",
                    CLOSE_COLUMN: "100",
                    PREV_DIFF_COLUMN: "0",
                    OPEN_COLUMN: "99",
                    HIGH_COLUMN: "101",
                    LOW_COLUMN: "98",
                    VOLUME_COLUMN: "1000",
                },
                {
                    DATE_COLUMN: "2026-04-02",
                    CLOSE_COLUMN: "101",
                    PREV_DIFF_COLUMN: "1",
                    OPEN_COLUMN: "100",
                    HIGH_COLUMN: "102",
                    LOW_COLUMN: "99",
                    VOLUME_COLUMN: "1100",
                },
            ]
        )

    def _financial_fetcher(self, *, code: str) -> pd.DataFrame:
        if code == "123450":
            raise ValueError("financials unavailable")
        return pd.DataFrame([{"code": code, "metric": "EPS", "period": "2025.12", "value": "1"}])

    def test_filters_lookback_and_marks_delisted_separately(self) -> None:
        scoped = filter_membership_for_lookback(
            self._membership(),
            decision_date=date(2026, 5, 5),
            lookback_years=10,
        )
        plan = build_security_collection_plan(scoped, decision_date=date(2026, 5, 5))

        self.assertEqual(set(plan["ticker"]), {"005930", "123450"})
        delisted = plan[plan["delisted_or_inactive"]]
        self.assertEqual(delisted.iloc[0]["ticker"], "123450")

    def test_execution_plan_supports_forward_and_reverse_shards(self) -> None:
        plan = pd.DataFrame(
            [
                {"ticker": "000001"},
                {"ticker": "000002"},
                {"ticker": "000003"},
                {"ticker": "000004"},
                {"ticker": "000005"},
            ]
        )

        front = build_execution_plan(
            plan,
            config=HistoricalCollectionConfig(
                decision_date=date(2026, 5, 5),
                shard_count=2,
                shard_index=0,
                execution_order="forward",
            ),
        )
        reverse = build_execution_plan(
            plan,
            config=HistoricalCollectionConfig(
                decision_date=date(2026, 5, 5),
                shard_count=2,
                shard_index=1,
                execution_order="reverse",
            ),
        )

        self.assertEqual(front["ticker"].tolist(), ["000001", "000002"])
        self.assertEqual(reverse["ticker"].tolist(), ["000005", "000004", "000003"])
        self.assertEqual(set(front["ticker"]).intersection(reverse["ticker"]), set())

    def test_execution_plan_validates_shard_bounds(self) -> None:
        plan = pd.DataFrame([{"ticker": "000001"}])

        with self.assertRaisesRegex(ValueError, "less than shard_count"):
            build_execution_plan(
                plan,
                config=HistoricalCollectionConfig(
                    decision_date=date(2026, 5, 5),
                    shard_count=2,
                    shard_index=2,
                ),
            )

    def test_collects_available_data_and_records_unavailable_delisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = collect_historical_kospi200_naver_data(
                self._membership(),
                config=HistoricalCollectionConfig(
                    decision_date=date(2026, 5, 5),
                    lookback_years=10,
                    pages=1,
                    output_dir=Path(tmpdir),
                ),
                price_fetcher=self._price_fetcher,
                financial_fetcher=self._financial_fetcher,
            )
            status = pd.read_csv(result["status_path"], dtype=str)

            self.assertEqual(int(result["security_count"]), 2)
            self.assertEqual(int(result["delisted_or_inactive_count"]), 1)
            self.assertTrue((Path(tmpdir) / "prices" / "005930_daily_prices.csv").exists())
            failed = status[status["ticker"] == "123450"].iloc[0]
            self.assertEqual(failed["price_status"], "delisted_or_unavailable")
            self.assertEqual(failed["financial_status"], "delisted_or_unavailable")

    def test_dry_run_does_not_write_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = collect_historical_kospi200_naver_data(
                self._membership(),
                config=HistoricalCollectionConfig(
                    decision_date=date(2026, 5, 5),
                    lookback_years=10,
                    pages=1,
                    output_dir=Path(tmpdir),
                    dry_run=True,
                ),
                price_fetcher=self._price_fetcher,
                financial_fetcher=self._financial_fetcher,
            )

            self.assertEqual(int(result["security_count"]), 2)
            self.assertFalse((Path(tmpdir) / "collection_status.csv").exists())

    def test_resume_existing_refetches_price_file_below_min_rows(self) -> None:
        calls: list[str] = []

        def price_fetcher(*, code: str, pages: int, sleep_seconds: float) -> pd.DataFrame:
            calls.append(code)
            return self._price_fetcher(code=code, pages=pages, sleep_seconds=sleep_seconds)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            price_dir = output_dir / "prices"
            price_dir.mkdir(parents=True)
            (price_dir / "005930_daily_prices.csv").write_text(
                f"{DATE_COLUMN},{CLOSE_COLUMN}\n2026-05-04,100\n",
                encoding="utf-8-sig",
            )

            result = collect_historical_kospi200_naver_data(
                self._membership().head(1),
                config=HistoricalCollectionConfig(
                    decision_date=date(2026, 5, 5),
                    lookback_years=10,
                    pages=1,
                    output_dir=output_dir,
                    refresh_financials=False,
                    resume_existing=True,
                    resume_min_price_rows=2,
                ),
                price_fetcher=price_fetcher,
                financial_fetcher=self._financial_fetcher,
            )
            status = pd.read_csv(result["status_path"], dtype=str)

            self.assertEqual(calls, ["005930"])
            self.assertEqual(status.iloc[0]["existing_price_rows"], "1")
            self.assertEqual(status.iloc[0]["price_status"], "collected")

    def test_krx_api_key_preflight_uses_parent_api_management(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "Project" / "master_mvp" / "chart_mvp"
            api_management = Path(tmpdir) / "Project" / "api_management"
            project_root.mkdir(parents=True)
            api_management.mkdir(parents=True)
            (api_management / "api_keys.env").write_text("KRX_API_KEY=secret-value", encoding="utf-8")

            readiness = check_required_krx_api_key(env={}, project_root=project_root)

            self.assertEqual(readiness["status"], "ready")
            self.assertEqual(readiness["config_summary"]["selected_env_var"], "KRX_API_KEY")
            self.assertNotIn("secret-value", str(readiness))

    def test_krx_api_key_preflight_reports_missing_without_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "Project" / "master_mvp" / "chart_mvp"
            project_root.mkdir(parents=True)

            readiness = check_required_krx_api_key(env={}, project_root=project_root)

            self.assertEqual(readiness["status"], "blocked")
            self.assertIn("KRX_API_KEY", str(readiness["missing_materials"]))


if __name__ == "__main__":
    unittest.main()
