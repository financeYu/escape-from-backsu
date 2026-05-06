from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.ml.corporate_action_events import (  # noqa: E402
    DEFAULT_EVENT_SOURCE,
    EVENT_SCHEMA_VERSION,
    EVENT_TABLE_FILE,
    EVENT_SUMMARY_FILE,
    CorporateActionEventConfig,
    build_corporate_action_event_inputs,
    read_corporate_action_events,
    validate_corporate_action_events,
)
from stock_core.ml.price_feature_table import MASTER_MVP_CONTEXT_MARKER  # noqa: E402


class CorporateActionEventTests(unittest.TestCase):
    def test_seed_file_validates(self) -> None:
        events = read_corporate_action_events(DEFAULT_EVENT_SOURCE)

        validate_corporate_action_events(events)

        self.assertEqual(set(events["schema_version"]), {EVENT_SCHEMA_VERSION})
        self.assertTrue((events["master_mvp_context_marker"] == MASTER_MVP_CONTEXT_MARKER).all())
        self.assertIn("005930_20180504_stock_split", set(events["event_id"]))
        self.assertIn("factor_requires_official_terms", set(events["adjustment_factor_status"]))

    def test_build_writes_events_summary_and_updates_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "local_price_input_manifest.json").write_text('{"existing": true}\n', encoding="utf-8")

            summary = build_corporate_action_event_inputs(
                config=CorporateActionEventConfig(source_csv=DEFAULT_EVENT_SOURCE, output_dir=root),
                generated_at_utc="2026-05-06T00:00:00+00:00",
            )

            events = pd.read_csv(root / EVENT_TABLE_FILE, dtype={"ticker": str})
            manifest_text = (root / "local_price_input_manifest.json").read_text(encoding="utf-8")

            self.assertEqual(int(summary["event_count"]), len(events))
            self.assertGreater(int(summary["simple_factor_event_count"]), 0)
            self.assertGreater(int(summary["official_terms_required_event_count"]), 0)
            self.assertTrue((root / EVENT_SUMMARY_FILE).exists())
            self.assertTrue((root / "README.generated.md").exists())
            self.assertIn("corporate_action_events", manifest_text)


if __name__ == "__main__":
    unittest.main()
