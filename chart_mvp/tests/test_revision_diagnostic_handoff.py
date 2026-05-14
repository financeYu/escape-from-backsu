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

from stock_core.ml.revision_diagnostic_handoff import (  # noqa: E402
    BOUNDARY_NOTICE,
    RevisionDiagnosticHandoffConfig,
    build_revision_diagnostic_handoff,
)


class RevisionDiagnosticHandoffTests(unittest.TestCase):
    def test_builds_diagnostic_rows_from_existing_financial_cache(self) -> None:
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

            result = build_revision_diagnostic_handoff(
                RevisionDiagnosticHandoffConfig(
                    candidate_handoff_path=candidate_handoff,
                    financial_cache_dir=financial_dir,
                    output_dir=output_dir,
                )
            )

            rows = result["rows"]
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["candidate_id"], "sc_v1_4_diag")
            self.assertEqual(row["evidence_id"], "ee_v1_4_diag")
            self.assertEqual(row["source_ticker"], "005930")
            self.assertEqual(row["eps_estimate_current"], "500")
            self.assertEqual(row["diagnostic_sector_id"], "krx_sector:technology")
            self.assertEqual(row["diagnostic_sector_name"], "Technology")
            self.assertEqual(row["fiscal_period"], "최근 분기 실적 2026.06(E) IFRS연결")
            self.assertEqual(row["selection_reference_date"], "2026-05-12")
            self.assertEqual(
                row["selection_reason"],
                "best_matching_eps_estimate_period_for_candidate_row_reference_date",
            )
            self.assertEqual(row["available_at"], "")
            self.assertEqual(row["sector_id"], "")
            self.assertIn("available_at_missing", row["diagnostic_reason_codes"])
            self.assertIn("eps_estimate_1m_ago_missing", row["diagnostic_reason_codes"])
            self.assertIn("sector_id_missing", row["diagnostic_reason_codes"])
            self.assertEqual(row["boundary_notice"], BOUNDARY_NOTICE)
            self.assertTrue(Path(result["output_csv"]).exists())
            self.assertTrue(Path(result["output_manifest"]).exists())

    def test_manifest_records_missing_cache_and_next_required_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            candidate_handoff = root / "candidate_handoff.csv"
            financial_dir = root / "financial"
            output_dir = root / "out"
            financial_dir.mkdir()
            self._write_candidate_handoff(candidate_handoff)

            result = build_revision_diagnostic_handoff(
                RevisionDiagnosticHandoffConfig(
                    candidate_handoff_path=candidate_handoff,
                    financial_cache_dir=financial_dir,
                    output_dir=output_dir,
                )
            )

            manifest = json.loads(Path(result["output_manifest"]).read_text(encoding="utf-8"))
            self.assertFalse(manifest["pit_revision_ready"])
            self.assertEqual(manifest["reason_counts"]["financial_cache_missing"], 1)
            self.assertIn("available_at", manifest["next_required_data"])
            self.assertEqual(manifest["filled_current_data"]["candidate_id"], 1)
            self.assertEqual(manifest["unfilled_required_data"]["available_at"], 1)

            with Path(result["output_csv"]).open(encoding="utf-8-sig", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual(csv_rows[0]["diagnostic_status"], "diagnostic_missing_pit_revision_fields")

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
                    "candidate_id": "sc_v1_4_diag",
                    "evidence_id": "ee_v1_4_diag",
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
                    "metric": "EPS(원)",
                    "period": "최근 분기 실적 2026.03(E) IFRS연결",
                    "value": "300",
                }
            )
            writer.writerow(
                {
                    "code": "005930",
                    "table_index": "4",
                    "metric": "EPS(원)",
                    "period": "최근 분기 실적 2026.06(E) IFRS연결",
                    "value": "500",
                }
            )
            writer.writerow(
                {
                    "code": "005930",
                    "table_index": "4",
                    "metric": "EPS(원)",
                    "period": "최근 연간 실적 2026.12(E) IFRS연결",
                    "value": "1200",
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
                    "candidate_id": "sc_v1_4_diag",
                    "evidence_id": "ee_v1_4_diag",
                    "diagnostic_sector_id": "krx_sector:technology",
                    "diagnostic_sector_name": "Technology",
                    "sector_source_ref": "fixture_sector_source",
                    "sector_source_date": "2026-05-12",
                }
            )


if __name__ == "__main__":
    unittest.main()
