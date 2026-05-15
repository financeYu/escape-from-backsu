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

from stock_core.ml.v1_5_valuation_quality_handoff import (  # noqa: E402
    BOUNDARY_NOTICE,
    V15ValuationQualityHandoffConfig,
    build_v1_5_valuation_quality_handoff,
)


class V15ValuationQualityHandoffTests(unittest.TestCase):
    def test_builds_pending_data_rows_from_existing_financial_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            candidate_handoff = root / "candidate_handoff.csv"
            financial_dir = root / "financial"
            output_dir = root / "out"
            financial_dir.mkdir()
            output_dir.mkdir()
            self._write_candidate_handoff(candidate_handoff)
            self._write_financial_cache(financial_dir / "005930_financial_statements.csv")
            self._write_sector_supplement(output_dir / "v1_4_krx_sector_supplement_latest.csv")

            result = build_v1_5_valuation_quality_handoff(
                V15ValuationQualityHandoffConfig(
                    candidate_handoff_path=candidate_handoff,
                    financial_cache_dir=financial_dir,
                    output_dir=output_dir,
                    sector_supplement_path=output_dir / "v1_4_krx_sector_supplement_latest.csv",
                )
            )

            rows = result["rows"]
            self.assertEqual(len(rows), 3)
            by_field = {row["field_name"]: row for row in rows}
            self.assertEqual(by_field["price_to_earnings"]["value"], "10.5")
            self.assertEqual(by_field["price_to_book"]["value"], "1.2")
            self.assertEqual(by_field["roe"]["value"], "8.1")
            self.assertEqual(by_field["roe"]["report_period_end_date"], "2025-12-31")
            self.assertEqual(by_field["roe"]["sector_id"], "krx_sector:technology")
            self.assertEqual(by_field["roe"]["pit_validation_status"], "pending_data")
            self.assertEqual(by_field["roe"]["coverage_status"], "pending_data")
            self.assertEqual(by_field["roe"]["availability_date"], "")
            self.assertIn("availability_date_missing", by_field["roe"]["pending_reason"])
            self.assertEqual(by_field["roe"]["boundary_notice"], BOUNDARY_NOTICE)
            self.assertTrue(Path(result["output_csv"]).exists())
            self.assertTrue(Path(result["output_manifest"]).exists())

    def test_manifest_records_remaining_external_data_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            candidate_handoff = root / "candidate_handoff.csv"
            financial_dir = root / "financial"
            output_dir = root / "out"
            financial_dir.mkdir()
            self._write_candidate_handoff(candidate_handoff)
            self._write_financial_cache(financial_dir / "005930_financial_statements.csv")

            result = build_v1_5_valuation_quality_handoff(
                V15ValuationQualityHandoffConfig(
                    candidate_handoff_path=candidate_handoff,
                    financial_cache_dir=financial_dir,
                    output_dir=output_dir,
                )
            )

            manifest = json.loads(Path(result["output_manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["v1_5_status"], "pending_data_only")
            self.assertFalse(manifest["usable_as_available_v1_5_fundamentals"])
            self.assertIn("availability_date", manifest["still_required_external_data"])
            self.assertEqual(manifest["pending_reason_counts"]["availability_date_missing"], 3)

            with Path(result["output_csv"]).open(encoding="utf-8-sig", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual(csv_rows[0]["coverage_status"], "pending_data")

    @staticmethod
    def _write_candidate_handoff(path: Path) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "candidate_id",
                    "evidence_id",
                    "candidate_ticker",
                    "company_name",
                    "as_of_date",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "candidate_id": "sc_v1_5_diag",
                    "evidence_id": "ee_v1_5_diag",
                    "candidate_ticker": "005930",
                    "company_name": "Samsung Electronics",
                    "as_of_date": "2026-05-12",
                }
            )

    @staticmethod
    def _write_financial_cache(path: Path) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["code", "table_index", "metric", "period", "value"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "code": "005930",
                    "table_index": "4",
                    "metric": "PER(배)",
                    "period": "최근 연간 실적 2025.12 IFRS연결",
                    "value": "10.5",
                }
            )
            writer.writerow(
                {
                    "code": "005930",
                    "table_index": "4",
                    "metric": "PBR(배)",
                    "period": "최근 연간 실적 2025.12 IFRS연결",
                    "value": "1.2",
                }
            )
            writer.writerow(
                {
                    "code": "005930",
                    "table_index": "4",
                    "metric": "ROE(지배주주)",
                    "period": "최근 연간 실적 2025.12 IFRS연결",
                    "value": "8.1",
                }
            )
            writer.writerow(
                {
                    "code": "005930",
                    "table_index": "4",
                    "metric": "ROE(지배주주)",
                    "period": "최근 연간 실적 2026.12(E) IFRS연결",
                    "value": "9.9",
                }
            )

    @staticmethod
    def _write_sector_supplement(path: Path) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "candidate_id",
                    "evidence_id",
                    "diagnostic_sector_id",
                    "diagnostic_sector_name",
                    "sector_source_ref",
                    "sector_source_date",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "candidate_id": "sc_v1_5_diag",
                    "evidence_id": "ee_v1_5_diag",
                    "diagnostic_sector_id": "krx_sector:technology",
                    "diagnostic_sector_name": "Technology",
                    "sector_source_ref": "fixture_sector_source",
                    "sector_source_date": "2026-05-12",
                }
            )


if __name__ == "__main__":
    unittest.main()
