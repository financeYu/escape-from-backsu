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

from stock_core.ml.revision_sector_supplement import (  # noqa: E402
    BOUNDARY_NOTICE,
    RevisionSectorSupplementConfig,
    build_revision_sector_supplement,
)


class RevisionSectorSupplementTests(unittest.TestCase):
    def test_builds_diagnostic_sector_rows_without_pit_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            candidate_handoff = root / "candidate_handoff.csv"
            output_dir = root / "out"
            self._write_candidate_handoff(candidate_handoff)

            result = build_revision_sector_supplement(
                RevisionSectorSupplementConfig(
                    candidate_handoff_path=candidate_handoff,
                    output_dir=output_dir,
                ),
                sector_fetcher=lambda _source_date, _market: [
                    {"종목코드": "005930", "업종명": "전기전자"},
                ],
            )

            rows = result["rows"]
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["candidate_id"], "sc_v1_4_diag")
            self.assertEqual(row["diagnostic_sector_id"], "krx_sector:전기전자")
            self.assertEqual(row["diagnostic_sector_name"], "전기전자")
            self.assertEqual(row["pit_revision_usable"], "false")
            self.assertEqual(row["sector_revision_percentile_usable"], "false")
            self.assertIn("krx_sector_classification_not_revision_history", row["diagnostic_reason_codes"])
            self.assertEqual(row["boundary_notice"], BOUNDARY_NOTICE)

            manifest = json.loads(Path(result["output_manifest"]).read_text(encoding="utf-8"))
            self.assertFalse(manifest["pit_revision_ready"])
            self.assertFalse(manifest["usable_for_v1_4_feature_manifest"])
            self.assertEqual(manifest["matched_sector_count"], 1)
            self.assertIn("sector_revision_percentile", manifest["still_required_for_completion"])

    def test_records_missing_sector_without_filling_revision_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            candidate_handoff = root / "candidate_handoff.csv"
            output_dir = root / "out"
            self._write_candidate_handoff(candidate_handoff)

            result = build_revision_sector_supplement(
                RevisionSectorSupplementConfig(
                    candidate_handoff_path=candidate_handoff,
                    output_dir=output_dir,
                    sector_source_date="2026-05-12",
                ),
                sector_fetcher=lambda _source_date, _market: [],
            )

            with Path(result["output_csv"]).open(encoding="utf-8-sig", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual(csv_rows[0]["diagnostic_status"], "diagnostic_sector_missing")
            self.assertEqual(csv_rows[0]["diagnostic_sector_id"], "")
            self.assertIn("krx_sector_missing_for_ticker", csv_rows[0]["diagnostic_reason_codes"])

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
                    "company_name": "삼성전자",
                    "as_of_date": "2026-05-12",
                }
            )


if __name__ == "__main__":
    unittest.main()
