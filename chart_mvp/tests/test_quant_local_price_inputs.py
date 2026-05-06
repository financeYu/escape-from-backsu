from __future__ import annotations

from datetime import datetime, timedelta
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.ml.quant_local_price_inputs import (  # noqa: E402
    TARGET_QUANT_LOCAL_PRICE_INPUTS,
    QuantLocalPriceInputConfig,
    build_quant_local_price_input_tables,
    split_forward_reverse,
)


class QuantLocalPriceInputTests(unittest.TestCase):
    def _write_price_csv(self, directory: Path, ticker: str) -> None:
        rows = []
        start = datetime(2026, 1, 1)
        for idx in range(25):
            close = 100 + idx
            rows.append(
                {
                    "날짜": (start + timedelta(days=idx)).strftime("%Y-%m-%d"),
                    "종가": close,
                    "전일비": 0,
                    "시가": close - 1,
                    "고가": close + 1,
                    "저가": close - 2,
                    "거래량": 1000 + idx,
                }
            )
        pd.DataFrame(rows).to_csv(directory / f"{ticker}_daily_prices.csv", index=False)

    def test_split_forward_reverse_does_not_duplicate_paths(self) -> None:
        paths = [Path(f"{idx:06d}_daily_prices.csv") for idx in range(5)]

        shards = split_forward_reverse(paths)

        merged = shards["forward"] + shards["reverse"]
        self.assertEqual(set(merged), set(paths))
        self.assertEqual(len(merged), len(paths))
        self.assertEqual(shards["reverse"], list(reversed(sorted(paths)[3:])))

    def test_builds_source_and_feature_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self._write_price_csv(root, "005930")
            self._write_price_csv(root, "000660")

            manifest = build_quant_local_price_input_tables(
                config=QuantLocalPriceInputConfig(
                    input_dir=root,
                    output_dir=root,
                    min_history_length=20,
                    workers=1,
                ),
                generated_at_utc="2026-05-06T00:00:00+00:00",
            )

            source = pd.read_csv(root / "quant_local_price_source_rows.csv", dtype={"ticker": str})
            features = pd.read_csv(root / "kospi200_price_ml_feature_table.csv", dtype={"ticker": str})

            self.assertEqual(manifest["target_quant_path"], TARGET_QUANT_LOCAL_PRICE_INPUTS)
            self.assertEqual(int(manifest["file_count"]), 2)
            self.assertEqual(set(source["ticker"]), {"005930", "000660"})
            self.assertIn("target_quant_path", source.columns)
            self.assertIn("master_mvp_context_marker", features.columns)
            self.assertTrue((root / "local_price_input_manifest.json").exists())
            self.assertTrue((root / "README.generated.md").exists())

    def test_syncs_price_files_to_quant_output_and_reuses_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            input_dir = root / "chart_prices"
            output_dir = root / "quant_price_inputs"
            input_dir.mkdir()
            output_dir.mkdir()
            self._write_price_csv(input_dir, "005930")
            self._write_price_csv(input_dir, "000660")
            self._write_price_csv(output_dir, "005930")

            manifest = build_quant_local_price_input_tables(
                config=QuantLocalPriceInputConfig(
                    input_dir=input_dir,
                    output_dir=output_dir,
                    min_history_length=20,
                    workers=1,
                    sync_price_files=True,
                    reuse_existing=True,
                ),
                generated_at_utc="2026-05-06T00:00:00+00:00",
            )

            source = pd.read_csv(output_dir / "quant_local_price_source_rows.csv", dtype={"ticker": str})

            self.assertEqual(int(manifest["price_files_copied"]), 1)
            self.assertEqual(int(manifest["price_files_reused"]), 1)
            self.assertTrue((output_dir / "000660_daily_prices.csv").exists())
            self.assertTrue((output_dir / "005930_daily_prices.csv").exists())
            self.assertTrue(source["source_file"].str.startswith(str(output_dir)).all())


if __name__ == "__main__":
    unittest.main()
