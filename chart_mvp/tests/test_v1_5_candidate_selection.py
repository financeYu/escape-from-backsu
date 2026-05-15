from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.ml.v1_5_candidate_selection import (  # noqa: E402
    V15CollectionCandidateSelectionConfig,
    build_v1_5_collection_candidate_selection,
    build_v1_5_collection_candidate_selection_rows,
)


class V15CandidateSelectionTests(unittest.TestCase):
    def test_selects_best_fit_collection_ticker_without_hardcoded_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pending = root / "pending.csv"
            output_csv = root / "selection.csv"
            output_manifest = root / "selection.json"
            self._write_pending_handoff(pending)

            result = build_v1_5_collection_candidate_selection(
                V15CollectionCandidateSelectionConfig(
                    pending_handoff_path=pending,
                    output_csv_path=output_csv,
                    output_manifest_path=output_manifest,
                    selection_purpose="opendart_fundamental_collection",
                    max_codes=1,
                )
            )

            self.assertEqual(result["selected_codes"], ["111111"])
            self.assertTrue(output_csv.exists())
            manifest = json.loads(output_manifest.read_text(encoding="utf-8"))
            self.assertFalse(manifest["hardcoded_tickers_used"])
            self.assertFalse(manifest["scoring_activation_allowed"])
            self.assertEqual(manifest["candidate_generation_mode"], "runtime_from_pending_handoff")
            self.assertEqual(manifest["candidate_selection_mode"], "ranked_best_fit")
            self.assertEqual(manifest["candidate_code_pool"], ["111111", "222222", "333333"])

    def test_per_pbr_collection_can_require_per_or_pbr_need(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = Path(tmpdir) / "pending.csv"
            self._write_pending_handoff(pending)

            rows = build_v1_5_collection_candidate_selection_rows(
                pending,
                selection_purpose="naver_ratio_policy_collection",
                max_codes=0,
                require_per_pbr_need=True,
            )

            by_ticker = {row["ticker"]: row for row in rows}
            self.assertEqual(by_ticker["111111"]["collection_target_status"], "selected")
            self.assertEqual(by_ticker["222222"]["collection_target_status"], "not_selected_no_per_pbr_need")
            self.assertEqual(by_ticker["333333"]["collection_target_status"], "not_selected_no_per_pbr_need")

    def test_source_candidate_rank_breaks_equal_readiness_ties(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pending = root / "pending.csv"
            source_candidates = root / "source_candidates.csv"
            self._write_equal_pending_handoff(pending)
            self._write_source_candidates(source_candidates)

            rows = build_v1_5_collection_candidate_selection_rows(
                pending,
                selection_purpose="opendart_fundamental_collection",
                max_codes=1,
                source_candidate_handoff_path=source_candidates,
            )

            self.assertEqual(rows[0]["ticker"], "222222")
            self.assertEqual(rows[0]["collection_target_status"], "selected")
            self.assertEqual(rows[0]["source_rank_slot_best"], "1")
            self.assertGreater(
                int(rows[0]["source_candidate_priority_score"]),
                int(rows[1]["source_candidate_priority_score"]),
            )

    @staticmethod
    def _write_pending_handoff(path: Path) -> None:
        fieldnames = [
            "candidate_id",
            "ticker",
            "evaluation_date",
            "field_name",
            "source_financial_cache_path",
            "sector_id",
            "industry_name",
        ]
        rows = [
            {
                "candidate_id": "cand_best",
                "ticker": "111111",
                "evaluation_date": "2026-05-15",
                "field_name": "price_to_earnings",
                "source_financial_cache_path": "data/111111_financial_statements.csv",
                "sector_id": "krx_sector:semiconductor",
                "industry_name": "Semiconductor",
            },
            {
                "candidate_id": "cand_best",
                "ticker": "111111",
                "evaluation_date": "2026-05-15",
                "field_name": "price_to_book",
                "source_financial_cache_path": "data/111111_financial_statements.csv",
                "sector_id": "krx_sector:semiconductor",
                "industry_name": "Semiconductor",
            },
            {
                "candidate_id": "cand_quality",
                "ticker": "222222",
                "evaluation_date": "2026-05-15",
                "field_name": "roe",
                "source_financial_cache_path": "data/222222_financial_statements.csv",
                "sector_id": "",
                "industry_name": "",
            },
            {
                "candidate_id": "cand_empty",
                "ticker": "333333",
                "evaluation_date": "2026-05-15",
                "field_name": "",
                "source_financial_cache_path": "",
                "sector_id": "",
                "industry_name": "",
            },
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_equal_pending_handoff(path: Path) -> None:
        fieldnames = [
            "candidate_id",
            "ticker",
            "evaluation_date",
            "field_name",
            "source_financial_cache_path",
            "sector_id",
            "industry_name",
        ]
        rows = []
        for ticker in ("111111", "222222"):
            rows.extend(
                [
                    {
                        "candidate_id": f"cand_{ticker}",
                        "ticker": ticker,
                        "evaluation_date": "2026-05-15",
                        "field_name": "price_to_earnings",
                        "source_financial_cache_path": f"data/{ticker}_financial_statements.csv",
                        "sector_id": "krx_sector:semiconductor",
                        "industry_name": "Semiconductor",
                    },
                    {
                        "candidate_id": f"cand_{ticker}",
                        "ticker": ticker,
                        "evaluation_date": "2026-05-15",
                        "field_name": "price_to_book",
                        "source_financial_cache_path": f"data/{ticker}_financial_statements.csv",
                        "sector_id": "krx_sector:semiconductor",
                        "industry_name": "Semiconductor",
                    },
                ]
            )
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_source_candidates(path: Path) -> None:
        fieldnames = [
            "candidate_id",
            "candidate_ticker",
            "rank_slot",
            "average_traded_value",
            "market_cap_proxy",
        ]
        rows = [
            {
                "candidate_id": "cand_111111",
                "candidate_ticker": "111111",
                "rank_slot": "5",
                "average_traded_value": "1000.0",
                "market_cap_proxy": "10000.0",
            },
            {
                "candidate_id": "cand_222222",
                "candidate_ticker": "222222",
                "rank_slot": "1",
                "average_traded_value": "2000.0",
                "market_cap_proxy": "20000.0",
            },
        ]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
