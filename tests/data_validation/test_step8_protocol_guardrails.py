from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = PROJECT_ROOT / "docs" / "step8_testing_normalization_protocol.md"


class Step8ProtocolGuardrailTests(unittest.TestCase):
    def test_protocol_document_exists_with_required_contract_sections(self) -> None:
        content = PROTOCOL_PATH.read_text(encoding="utf-8")

        required_phrases = [
            "Step 7 raw technical indicator output",
            "Downstream Handoff Contract",
            "No-Lookahead and Time Alignment Tests",
            "Time-Series Normalization",
            "Cross-Sectional Normalization",
            "Robust Z-Score Policy",
            "Diagnostics output schema draft",
            "Step 9 Research Tester Checklist",
        ]
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, content)

    def test_protocol_keeps_step8_hard_stops_explicit(self) -> None:
        content = PROTOCOL_PATH.read_text(encoding="utf-8")

        hard_stop_phrases = [
            "score formula implementation",
            "production `raw_score` generation",
            "`normalized_score_time_series`",
            "`rank`, `ranking`, latest ranking output",
            "`technical_composite_score`",
            "`final_composite_score`",
            "backtest",
            "valuation/fundamental scoring",
            "Step 9 remains WAITING",
        ]
        for phrase in hard_stop_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, content)

    def test_protocol_preserves_data_quality_semantics(self) -> None:
        content = PROTOCOL_PATH.read_text(encoding="utf-8")

        required_flags = [
            "`coverage_status`",
            "`warmup_status`",
            "`data_quality_flag`",
            "`leading_zero_lost`",
            "`duplicate_ticker_date`",
            "`insufficient_history`",
            "`zero_dispersion`",
            "`blocked_by_missing_config`",
        ]
        for flag in required_flags:
            with self.subTest(flag=flag):
                self.assertIn(flag, content)


if __name__ == "__main__":
    unittest.main()
