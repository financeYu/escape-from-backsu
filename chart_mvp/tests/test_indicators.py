from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.indicators.technical import add_indicators
from stock_core.utils.constants import CLOSE_COLUMN, VOLUME_COLUMN


class IndicatorTests(unittest.TestCase):
    def test_rsi_handles_flat_prices_without_replace_exception(self) -> None:
        frame = pd.DataFrame(
            {
                CLOSE_COLUMN: [100.0] * 20,
                VOLUME_COLUMN: [1000.0] * 20,
            }
        )

        result = add_indicators(frame)

        self.assertEqual(float(result.iloc[-1]["RSI14"]), 50.0)

    def test_rsi_handles_zero_average_loss_as_overbought(self) -> None:
        frame = pd.DataFrame(
            {
                CLOSE_COLUMN: [float(value) for value in range(1, 22)],
                VOLUME_COLUMN: [1000.0] * 21,
            }
        )

        result = add_indicators(frame)

        self.assertEqual(float(result.iloc[-1]["RSI14"]), 100.0)


if __name__ == "__main__":
    unittest.main()
