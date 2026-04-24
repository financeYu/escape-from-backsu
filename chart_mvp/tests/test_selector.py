from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.ranking.selector import select_top_stocks


class SelectorTests(unittest.TestCase):
    def test_selector_keeps_deterministic_order_when_scores_match(self) -> None:
        rankings = pd.DataFrame(
            [
                {"종목코드": "000300", "종목명": "C", "점수": 0.0, "최신일": "2026-04-17", "종가": 30.0, "전일대비": 1.0, "거래량": 300.0, "RSI14": 50.0, "데이터소스": "x"},
                {"종목코드": "000100", "종목명": "A", "점수": 0.0, "최신일": "2026-04-17", "종가": 10.0, "전일대비": -2.0, "거래량": 100.0, "RSI14": 40.0, "데이터소스": "x"},
                {"종목코드": "000200", "종목명": "B", "점수": 0.0, "최신일": "2026-04-16", "종가": 20.0, "전일대비": 3.0, "거래량": 200.0, "RSI14": 45.0, "데이터소스": "x"},
            ]
        )

        top = select_top_stocks(rankings, top_n=3)

        self.assertEqual(top["종목코드"].tolist(), ["000100", "000300", "000200"])
        self.assertEqual(top["순위"].tolist(), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
