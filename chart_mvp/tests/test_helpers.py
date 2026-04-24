from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.charts.matplotlib_renderer import resolve_font_family
from stock_core.providers.kospi200_universe_provider import normalize_stock_code
from stock_core.ranking.scorer import score_stock


class HelperTests(unittest.TestCase):
    def test_normalize_stock_code_zero_pads(self) -> None:
        self.assertEqual(normalize_stock_code("1234"), "001234")
        self.assertEqual(normalize_stock_code(5930), "005930")

    def test_normalize_stock_code_preserves_alphanumeric(self) -> None:
        self.assertEqual(normalize_stock_code("0126Z0"), "0126Z0")
        self.assertEqual(normalize_stock_code(" 0126z0 "), "0126Z0")

    def test_resolve_font_family_prefers_installed_choice(self) -> None:
        available = {"Segoe UI", "Malgun Gothic", "DejaVu Sans"}
        self.assertEqual(resolve_font_family(available), "Malgun Gothic")

    def test_score_stock_placeholder_returns_zero(self) -> None:
        df = pd.DataFrame({"종가": [1, 2, 3]})
        self.assertEqual(score_stock(df), 0.0)


if __name__ == "__main__":
    unittest.main()
