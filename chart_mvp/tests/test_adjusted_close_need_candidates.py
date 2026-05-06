from __future__ import annotations

from datetime import date, timedelta
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.ml.adjusted_close_need_candidates import (  # noqa: E402
    AdjustedCloseNeedConfig,
    build_adjusted_close_need_candidates,
)


class AdjustedCloseNeedCandidateTests(unittest.TestCase):
    def _write_source_table(self, path: Path) -> None:
        rows = []
        start = date(2026, 1, 1)
        for idx in range(5):
            rows.append(
                {
                    "ticker": "005930",
                    "date": (start + timedelta(days=idx)).isoformat(),
                    "open": 100 + idx,
                    "close": 100 + idx,
                    "volume": 1000 + idx,
                }
            )
            rows.append(
                {
                    "ticker": "000100",
                    "date": (start + timedelta(days=idx)).isoformat(),
                    "open": 100 if idx != 3 else 520,
                    "close": 100 if idx != 3 else 500,
                    "volume": 1000 + idx,
                }
            )
            rows.append(
                {
                    "ticker": "000200",
                    "date": (start + timedelta(days=idx)).isoformat(),
                    "open": 100 if idx != 3 else 125,
                    "close": 100 if idx != 3 else 125,
                    "volume": 1000 + idx,
                }
            )
        pd.DataFrame(rows).to_csv(path, index=False)

    def _write_feature_table(self, path: Path) -> None:
        rows = []
        for ticker in ["005930", "000100", "000200"]:
            rows.append(
                {
                    "ticker": ticker,
                    "label_source": "missing_adjusted_close",
                    "supervised_label_eligible": False,
                }
            )
        pd.DataFrame(rows).to_csv(path, index=False)

    def _write_event_table(self, path: Path) -> None:
        pd.DataFrame(
            [
                {
                    "ticker": "000100",
                    "event_id": "000100_split",
                    "event_type": "stock_split",
                    "adjustment_factor_status": "derived_from_reported_ratio",
                }
            ]
        ).to_csv(path, index=False)

    def test_builds_latest_adjusted_close_need_triage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "source.csv"
            features = root / "features.csv"
            events = root / "events.csv"
            output = root / "adjusted_close_need_candidates.csv"
            summary = root / "adjusted_close_need_summary.json"
            self._write_source_table(source)
            self._write_feature_table(features)
            self._write_event_table(events)

            result = build_adjusted_close_need_candidates(
                config=AdjustedCloseNeedConfig(
                    source_table=source,
                    feature_table=features,
                    event_table=events,
                    output_csv=output,
                    summary_json=summary,
                ),
                generated_at_utc="2026-05-06T00:00:00+00:00",
            )

            candidates = pd.read_csv(output, dtype={"ticker": str})
            by_ticker = candidates.set_index("ticker")

            self.assertEqual(result["unique_tickers"], 3)
            self.assertEqual(result["high_priority_count"], 1)
            self.assertEqual(result["medium_priority_count"], 1)
            self.assertEqual(result["baseline_required_count"], 1)
            self.assertEqual(by_ticker.loc["000100", "review_bucket"], "simple_factor_adjustment_candidate")
            self.assertEqual(by_ticker.loc["000200", "review_bucket"], "medium_jump_source_quality_review")
            self.assertTrue(summary.exists())


if __name__ == "__main__":
    unittest.main()
