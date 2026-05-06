from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.ml.price_feature_table import (
    MASTER_MVP_CONTEXT_MARKER,
    ML_PRICE_FEATURE_TABLE_KIND,
    MlPriceFeatureConfig,
    build_ml_price_feature_table,
)


class MlPriceFeatureTableTests(unittest.TestCase):
    def _fixture_frame(self) -> pd.DataFrame:
        rows = []
        for idx in range(25):
            close = 100.0 + idx
            rows.append(
                {
                    "ticker": "005930",
                    "date": f"2026-04-{idx + 1:02d}",
                    "open": close - 1,
                    "high": close + 1,
                    "low": close - 2,
                    "close": close,
                    "adjusted_close": close,
                    "volume": 1000 + idx,
                    "source": "fixture",
                }
            )
        return pd.DataFrame(rows)

    def test_builds_master_marked_ml_feature_rows(self) -> None:
        table = build_ml_price_feature_table(
            self._fixture_frame(),
            config=MlPriceFeatureConfig(min_history_length=20),
            generated_at_utc="2026-05-05T00:00:00+00:00",
        )

        latest = table.iloc[-2]
        self.assertEqual(latest["feature_table_kind"], ML_PRICE_FEATURE_TABLE_KIND)
        self.assertEqual(latest["master_mvp_context_marker"], MASTER_MVP_CONTEXT_MARKER)
        self.assertEqual(latest["source_project"], "chart_mvp")
        self.assertEqual(latest["source_universe"], "KOSPI200_candidate_only")
        self.assertEqual(latest["label_source"], "adjusted_close")
        self.assertTrue(bool(latest["supervised_label_eligible"]))
        self.assertIn("not a runtime ranking input", latest["row_boundary"])
        self.assertEqual(latest["split_policy"], "time_order_required_before_training")
        self.assertFalse(bool(latest["random_split_allowed"]))
        self.assertGreater(float(latest["return_1d"]), 0.0)
        self.assertGreater(float(latest["label_forward_return_1d"]), 0.0)

    def test_missing_adjusted_close_blocks_supervised_label_eligibility(self) -> None:
        frame = self._fixture_frame().drop(columns=["adjusted_close"])

        table = build_ml_price_feature_table(frame, config=MlPriceFeatureConfig(min_history_length=20))

        latest = table.iloc[-2]
        self.assertEqual(latest["label_source"], "missing_adjusted_close")
        self.assertFalse(bool(latest["supervised_label_eligible"]))
        self.assertTrue(pd.isna(latest["label_forward_return_1d"]))

    def test_rejects_non_1d_label_horizon_until_contract_columns_change(self) -> None:
        with self.assertRaisesRegex(ValueError, "label_horizon_days must be 1"):
            build_ml_price_feature_table(
                self._fixture_frame(),
                config=MlPriceFeatureConfig(label_horizon_days=5, min_history_length=20),
            )

    def test_rejects_duplicate_ticker_dates(self) -> None:
        frame = pd.concat([self._fixture_frame(), self._fixture_frame().head(1)], ignore_index=True)

        with self.assertRaisesRegex(ValueError, "duplicate_ticker_date"):
            build_ml_price_feature_table(frame, config=MlPriceFeatureConfig(min_history_length=20))


if __name__ == "__main__":
    unittest.main()
