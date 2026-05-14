import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
import zipfile

from stock_core.ml.opendart_v1_4_snapshot import (
    OPENDART_API_KEY_ENV_VAR,
    OPENDART_V1_4_ENDPOINTS,
    build_opendart_raw_snapshot_record,
    check_opendart_api_key_readiness,
    collect_opendart_v1_4_raw_snapshots,
    load_opendart_api_key_config,
    validate_opendart_raw_snapshot_record,
)


class OpenDartV14SnapshotTest(unittest.TestCase):
    def test_endpoint_contract_covers_v1_4_supplement_sources(self):
        self.assertEqual(
            set(OPENDART_V1_4_ENDPOINTS),
            {"corp_code", "disclosure_list", "single_account"},
        )
        self.assertEqual(OPENDART_V1_4_ENDPOINTS["corp_code"]["api_path"], "/api/corpCode.xml")
        self.assertEqual(OPENDART_V1_4_ENDPOINTS["disclosure_list"]["api_path"], "/api/list.json")
        self.assertEqual(OPENDART_V1_4_ENDPOINTS["single_account"]["api_path"], "/api/fnlttSinglAcnt.json")

    def test_api_key_readiness_loads_parent_api_management_without_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root, env_file = self._make_project(tmpdir)
            env_file.write_text(
                "\n".join(
                    [
                        "OPENDART_API_KEY=opendart-secret",
                        "UNRELATED_SECRET=must-not-load",
                    ]
                ),
                encoding="utf-8",
            )
            env: dict[str, str] = {}

            config = load_opendart_api_key_config(env=env, project_root=project_root)
            readiness = check_opendart_api_key_readiness(config)

            self.assertEqual(readiness.status, "ready")
            self.assertTrue(config.api_key_present)
            self.assertEqual(set(env), {OPENDART_API_KEY_ENV_VAR})
            self.assertNotIn("opendart-secret", str(readiness.to_dict()))
            self.assertTrue(readiness.config_summary["secret_values_redacted"])

    def test_raw_snapshot_record_validates_hash_and_endpoint(self):
        raw_json = {"status": "000", "list": [{"rcept_dt": "20250318"}]}
        record = build_opendart_raw_snapshot_record(
            endpoint_name="disclosure_list",
            code="005930",
            collected_at="2026-05-14T00:00:00+00:00",
            request_date="20250101:20260514",
            raw_json=raw_json,
        )

        self.assertEqual(record["provider"], "opendart")
        validate_opendart_raw_snapshot_record(record)
        record["raw_json"] = {"status": "000"}
        with self.assertRaises(ValueError):
            validate_opendart_raw_snapshot_record(record)

    def test_collection_writes_corp_disclosure_and_financial_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root, env_file = self._make_project(tmpdir)
            env_file.write_text("OPENDART_API_KEY=opendart-secret\n", encoding="utf-8")
            output_dir = Path(tmpdir) / "snapshots"
            json_calls = []

            def fake_bytes(url, params, timeout_seconds):
                self.assertIn("corpCode.xml", url)
                self.assertIn("crtfc_key", params)
                return self._corp_code_zip_bytes()

            def fake_json(url, params, timeout_seconds):
                json_calls.append((url, params, timeout_seconds))
                if "list.json" in url:
                    return {
                        "status": "000",
                        "page_no": "1",
                        "total_page": "1",
                        "list": [
                            {
                                "corp_code": params["corp_code"],
                                "stock_code": "005930",
                                "report_nm": "사업보고서",
                                "rcept_no": "20250318000001",
                                "rcept_dt": "20250318",
                            }
                        ],
                    }
                if "fnlttSinglAcnt.json" in url:
                    return {
                        "status": "000",
                        "list": [
                            {
                                "rcept_no": "20250318000001",
                                "bsns_year": params["bsns_year"],
                                "stock_code": "005930",
                                "reprt_code": params["reprt_code"],
                                "account_nm": "매출액",
                            }
                        ],
                    }
                raise AssertionError(url)

            result = collect_opendart_v1_4_raw_snapshots(
                codes=["005930"],
                bgn_de="20250101",
                end_de="20260514",
                bsns_year="2025",
                reprt_code="11011",
                output_dir=output_dir,
                env={},
                project_root=project_root,
                get_json=fake_json,
                get_bytes=fake_bytes,
            )

            self.assertEqual(result.records_written, 3)
            self.assertEqual(result.endpoint_counts["corp_code"], 1)
            self.assertEqual(result.endpoint_counts["disclosure_list"], 1)
            self.assertEqual(result.endpoint_counts["single_account"], 1)
            self.assertEqual(result.missing_codes, ())
            self.assertEqual(len(json_calls), 2)
            records = [
                json.loads(line)
                for line in Path(result.output_path).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            for record in records:
                validate_opendart_raw_snapshot_record(record)
            self.assertEqual([record["endpoint_name"] for record in records], ["corp_code", "disclosure_list", "single_account"])
            self.assertEqual(records[1]["raw_json"]["_request_context"]["corp_code"], "00126380")

    def _make_project(self, tmpdir):
        project_root = Path(tmpdir) / "Project" / "master_mvp" / "chart_mvp"
        api_management = Path(tmpdir) / "Project" / "api_management"
        project_root.mkdir(parents=True)
        api_management.mkdir(parents=True)
        return project_root, api_management / "api_keys.env"

    def _corp_code_zip_bytes(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<result>
  <list>
    <corp_code>00126380</corp_code>
    <corp_name>삼성전자</corp_name>
    <corp_eng_name>SAMSUNG ELECTRONICS</corp_eng_name>
    <stock_code>005930</stock_code>
    <modify_date>20240101</modify_date>
  </list>
</result>
"""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("CORPCODE.xml", xml)
        return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
