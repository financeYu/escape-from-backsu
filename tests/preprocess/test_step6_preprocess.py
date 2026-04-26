from __future__ import annotations

from datetime import date
import sys
import textwrap
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocess.daily_ohlcv import load_preprocess_config, preprocess_ohlcv_frame, run_preprocessing_from_config
from src.preprocess.schema_validator import validate_non_negative_volume, validate_standard_ohlcv_schema


AS_OF_DATE = date(2026, 4, 24)


def valid_frame(**overrides: object) -> pd.DataFrame:
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


class Step6PreprocessTests(unittest.TestCase):
    def test_valid_ticker_with_leading_zero_is_preserved(self) -> None:
        processed, invalid_rows, _, summary = preprocess_ohlcv_frame(
            valid_frame(ticker="005930"),
            as_of_date=AS_OF_DATE,
        )

        self.assertEqual(processed.loc[0, "ticker"], "005930")
        self.assertTrue(invalid_rows.empty)
        self.assertEqual(summary["row_count_after"], 1)

    def test_valid_alphanumeric_ticker_is_uppercased_and_preserved(self) -> None:
        processed, invalid_rows, _, summary = preprocess_ohlcv_frame(
            valid_frame(ticker="0126z0"),
            as_of_date=AS_OF_DATE,
        )

        self.assertEqual(processed.loc[0, "ticker"], "0126Z0")
        self.assertTrue(invalid_rows.empty)
        self.assertEqual(summary["row_count_after"], 1)

    def test_invalid_integer_ticker_is_rejected(self) -> None:
        processed, invalid_rows, _, summary = preprocess_ohlcv_frame(
            valid_frame(ticker=5930),
            as_of_date=AS_OF_DATE,
        )

        self.assertTrue(processed.empty)
        self.assertEqual(summary["invalid_ticker_count"], 1)
        self.assertIn("ticker_leading_zero_loss_candidate", invalid_rows.loc[0, "invalid_reason"])

    def test_invalid_short_string_ticker_is_rejected(self) -> None:
        processed, invalid_rows, _, summary = preprocess_ohlcv_frame(
            valid_frame(ticker="5930"),
            as_of_date=AS_OF_DATE,
        )

        self.assertTrue(processed.empty)
        self.assertEqual(summary["invalid_ticker_count"], 1)
        self.assertIn("invalid_ticker", invalid_rows.loc[0, "invalid_reason"])

    def test_invalid_date_is_rejected(self) -> None:
        processed, invalid_rows, _, summary = preprocess_ohlcv_frame(
            valid_frame(date="2024-13-40"),
            as_of_date=AS_OF_DATE,
        )

        self.assertTrue(processed.empty)
        self.assertEqual(summary["invalid_date_count"], 1)
        self.assertIn("invalid_date", invalid_rows.loc[0, "invalid_reason"])

    def test_future_date_is_rejected(self) -> None:
        processed, invalid_rows, _, summary = preprocess_ohlcv_frame(
            valid_frame(date="2026-04-25"),
            as_of_date=AS_OF_DATE,
        )

        self.assertTrue(processed.empty)
        self.assertEqual(summary["future_date_count"], 1)
        self.assertIn("future_date", invalid_rows.loc[0, "invalid_reason"])

    def test_invalid_numeric_string_is_rejected(self) -> None:
        processed, invalid_rows, _, summary = preprocess_ohlcv_frame(
            valid_frame(open="1,000원"),
            as_of_date=AS_OF_DATE,
        )

        self.assertTrue(processed.empty)
        self.assertEqual(summary["invalid_numeric_count"], 1)
        self.assertIn("invalid_numeric:open", invalid_rows.loc[0, "invalid_reason"])

    def test_duplicate_ticker_date_rows_are_rejected(self) -> None:
        frame = pd.concat([valid_frame(), valid_frame(close=106)], ignore_index=True)

        processed, invalid_rows, _, summary = preprocess_ohlcv_frame(frame, as_of_date=AS_OF_DATE)

        self.assertTrue(processed.empty)
        self.assertEqual(len(invalid_rows), 2)
        self.assertEqual(summary["duplicate_count"], 2)
        self.assertTrue(invalid_rows["invalid_reason"].str.contains("duplicate_ticker_date").all())

    def test_negative_volume_validation_is_explicit(self) -> None:
        checks = validate_non_negative_volume(valid_frame(volume=-1))
        processed, invalid_rows, _, summary = preprocess_ohlcv_frame(
            valid_frame(volume=-1),
            as_of_date=AS_OF_DATE,
        )

        self.assertEqual(checks[0].status, "fail")
        self.assertTrue(processed.empty)
        self.assertEqual(summary["negative_volume_count"], 1)
        self.assertIn("negative_volume", invalid_rows.loc[0, "invalid_reason"])

    def test_schema_validator_reports_step6_checks(self) -> None:
        checks = validate_standard_ohlcv_schema(valid_frame(volume=-1))
        failed = {check.check for check in checks if check.status == "fail"}

        self.assertIn("non_negative_volume", failed)

    def test_config_driven_pipeline_writes_outputs(self) -> None:
        root = Path.cwd() / "tests" / "_tmp" / "step6_preprocess_fixture"
        (root / "config").mkdir(parents=True, exist_ok=True)
        (root / "chart_mvp" / "data").mkdir(parents=True, exist_ok=True)
        (root / "chart_mvp" / "data" / "005930_daily_prices.csv").write_text(
            textwrap.dedent(
                """\
                날짜,시가,고가,저가,종가,거래량
                2026-04-23,100,110,90,105,1000
                """
            ),
            encoding="utf-8",
        )
        (root / "config" / "data.toml").write_text(
            textwrap.dedent(
                """\
                [preprocess]
                raw_price_input_glob = "chart_mvp/data/*_daily_prices.csv"
                processed_price_output_path = "data/processed/daily_ohlcv.csv"
                summary_report_path = "reports/preprocess/preprocess_summary.md"
                validation_summary_path = "reports/preprocess/preprocess_validation_summary.csv"
                invalid_rows_report_path = "reports/preprocess/preprocess_invalid_rows.csv"

                [financial_data]
                status = "valuation_deferred"
                """
            ),
            encoding="utf-8",
        )

        result = run_preprocessing_from_config(project_root=root, as_of_date=AS_OF_DATE)

        self.assertTrue(result.output_path.exists())
        self.assertTrue(result.summary_report_path.exists())
        self.assertTrue(result.validation_summary_path.exists())
        self.assertEqual(result.processed.loc[0, "ticker"], "005930")
        self.assertEqual(result.summary["financial_data_status"], "valuation_deferred")

    def test_unsupported_preprocess_policy_fails_fast(self) -> None:
        root = Path.cwd() / "tests" / "_tmp" / "step6_bad_policy_fixture"
        (root / "config").mkdir(parents=True, exist_ok=True)
        config_path = root / "config" / "data.toml"
        config_path.write_text(
            textwrap.dedent(
                """\
                [preprocess]
                future_date_policy = "allow"
                invalid_row_policy = "reject_and_report"
                financial_data_status = "valuation_deferred"
                """
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "preprocess.future_date_policy"):
            load_preprocess_config(config_path)


if __name__ == "__main__":
    unittest.main()
