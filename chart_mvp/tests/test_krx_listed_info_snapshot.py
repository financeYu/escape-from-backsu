import json
import tempfile
import unittest
from pathlib import Path

from stock_core.ml.krx_listed_info_snapshot import (
    KRX_LISTED_INFO_API_KEY_ENV_VARS,
    KRX_LISTED_INFO_ENDPOINT_NAME,
    KRX_LISTED_INFO_PROVIDER,
    build_krx_listed_info_raw_snapshot_record,
    check_krx_listed_info_api_key_readiness,
    collect_krx_listed_info_raw_snapshots,
    load_krx_listed_info_api_key_config,
    validate_krx_listed_info_raw_snapshot_record,
)


class KrxListedInfoSnapshotTest(unittest.TestCase):
    def test_api_key_readiness_loads_parent_api_management_without_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root, env_file = self._make_project(tmpdir)
            env_file.write_text(
                "\n".join(
                    [
                        "DATA_GO_KR_API_KEY=data-go-secret",
                        "UNRELATED_SECRET=must-not-load",
                    ]
                ),
                encoding="utf-8",
            )
            env: dict[str, str] = {}

            config = load_krx_listed_info_api_key_config(env=env, project_root=project_root)
            readiness = check_krx_listed_info_api_key_readiness(config)

            self.assertEqual(config.selected_env_var, "DATA_GO_KR_API_KEY")
            self.assertEqual(readiness.status, "ready")
            self.assertEqual(set(env), {"DATA_GO_KR_API_KEY"})
            self.assertNotIn("data-go-secret", str(readiness.to_dict()))
            self.assertEqual(config.checked_env_vars, KRX_LISTED_INFO_API_KEY_ENV_VARS)

    def test_api_key_readiness_can_use_named_krx_listed_info_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root, env_file = self._make_project(tmpdir)
            env_file.write_text("KRX_LISTED_INFO_API_KEY=listed-secret\n", encoding="utf-8")

            config = load_krx_listed_info_api_key_config(env={}, project_root=project_root)

            self.assertTrue(config.api_key_present)
            self.assertEqual(config.selected_env_var, "KRX_LISTED_INFO_API_KEY")

    def test_raw_snapshot_record_validates_hash(self):
        raw_json = {"response": {"body": {"items": {"item": [{"srtnCd": "005930"}]}}}}
        record = build_krx_listed_info_raw_snapshot_record(
            request_date="2026-05-15",
            collected_at="2026-05-15T00:00:00+00:00",
            raw_json=raw_json,
        )

        self.assertEqual(record["provider"], KRX_LISTED_INFO_PROVIDER)
        self.assertEqual(record["endpoint_name"], KRX_LISTED_INFO_ENDPOINT_NAME)
        self.assertEqual(record["code"], "ALL")
        validate_krx_listed_info_raw_snapshot_record(record)
        record["raw_json"] = {"response": {}}
        with self.assertRaises(ValueError):
            validate_krx_listed_info_raw_snapshot_record(record)

    def test_collection_writes_one_page_raw_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root, env_file = self._make_project(tmpdir)
            env_file.write_text("DATA_GO_KR_API_KEY=data-go-secret\n", encoding="utf-8")
            output_dir = Path(tmpdir) / "snapshots"
            calls = []

            def fake_get(url, params, timeout_seconds):
                calls.append((url, params, timeout_seconds))
                self.assertIn("serviceKey", params)
                return {
                    "response": {
                        "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
                        "body": {
                            "pageNo": 1,
                            "numOfRows": 100,
                            "totalCount": 1,
                            "items": {
                                "item": [
                                    {
                                        "basDt": "20260515",
                                        "srtnCd": "005930",
                                        "isinCd": "KR7005930003",
                                        "mrktCtg": "KOSPI",
                                        "itmsNm": "삼성전자",
                                        "crno": "1301110006246",
                                        "corpNm": "삼성전자",
                                    }
                                ]
                            },
                        },
                    }
                }

            result = collect_krx_listed_info_raw_snapshots(
                output_dir=output_dir,
                page_count=100,
                max_pages=1,
                env={},
                project_root=project_root,
                get_json=fake_get,
            )

            self.assertEqual(len(calls), 1)
            self.assertEqual(result.records_written, 1)
            self.assertEqual(result.total_count, 1)
            record = json.loads(Path(result.output_path).read_text(encoding="utf-8").strip())
            validate_krx_listed_info_raw_snapshot_record(record)
            self.assertEqual(record["raw_json"]["_request_context"]["page_count"], 100)
            self.assertNotIn("data-go-secret", json.dumps(record, ensure_ascii=False))

    def test_collection_can_supplement_existing_codes_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root, env_file = self._make_project(tmpdir)
            env_file.write_text("DATA_GO_KR_API_KEY=data-go-secret\n", encoding="utf-8")
            output_dir = Path(tmpdir) / "snapshots"
            calls = []

            def fake_get(url, params, timeout_seconds):
                calls.append((url, params, timeout_seconds))
                return {
                    "response": {
                        "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
                        "body": {
                            "pageNo": 1,
                            "numOfRows": 1,
                            "totalCount": 10,
                            "items": {
                                "item": [
                                    {
                                        "basDt": "20260515",
                                        "srtnCd": f"A{params['likeSrtnCd']}",
                                        "isinCd": "KR7005930003",
                                        "mrktCtg": "KOSPI",
                                        "itmsNm": "Samsung Electronics",
                                        "crno": "1301110006246",
                                        "corpNm": "Samsung Electronics",
                                    }
                                ]
                            },
                        },
                    }
                }

            result = collect_krx_listed_info_raw_snapshots(
                codes=["005930", "A005930", "000660"],
                output_dir=output_dir,
                env={},
                project_root=project_root,
                get_json=fake_get,
            )

            self.assertEqual([call[1]["likeSrtnCd"] for call in calls], ["005930", "000660"])
            self.assertEqual([call[1]["numOfRows"] for call in calls], ["1", "1"])
            self.assertEqual(result.records_written, 2)
            self.assertEqual(result.codes_requested, 2)
            self.assertEqual(result.query_mode, "code_supplement_latest")
            records = [
                json.loads(line)
                for line in Path(result.output_path).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual([record["code"] for record in records], ["005930", "000660"])
            self.assertEqual(records[0]["raw_json"]["_request_context"]["query_mode"], "code_supplement_latest")

    def test_empty_code_list_does_not_collect_all_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root, env_file = self._make_project(tmpdir)
            env_file.write_text("DATA_GO_KR_API_KEY=data-go-secret\n", encoding="utf-8")
            output_path = Path(tmpdir) / "snapshots" / "empty.jsonl"
            calls = []

            def fake_get(url, params, timeout_seconds):
                calls.append((url, params, timeout_seconds))
                return {"response": {"body": {"totalCount": 1}}}

            result = collect_krx_listed_info_raw_snapshots(
                codes=[],
                output_path=output_path,
                env={},
                project_root=project_root,
                get_json=fake_get,
            )

            self.assertEqual(calls, [])
            self.assertEqual(result.records_written, 0)
            self.assertEqual(result.codes_requested, 0)
            self.assertEqual(result.query_mode, "code_supplement_latest")
            self.assertFalse(output_path.exists())

    def test_code_supplement_failure_does_not_leave_partial_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root, env_file = self._make_project(tmpdir)
            env_file.write_text("DATA_GO_KR_API_KEY=data-go-secret\n", encoding="utf-8")
            output_path = Path(tmpdir) / "snapshots" / "partial.jsonl"
            calls = []

            def fake_get(url, params, timeout_seconds):
                calls.append((url, params, timeout_seconds))
                if len(calls) == 2:
                    raise RuntimeError("temporary gateway failure")
                return {
                    "response": {
                        "body": {
                            "pageNo": 1,
                            "numOfRows": 1,
                            "totalCount": 1,
                            "items": {"item": [{"basDt": "20260515", "srtnCd": f"A{params['likeSrtnCd']}"}]},
                        }
                    }
                }

            with self.assertRaises(RuntimeError):
                collect_krx_listed_info_raw_snapshots(
                    codes=["005930", "000660"],
                    output_path=output_path,
                    env={},
                    project_root=project_root,
                    get_json=fake_get,
                )

            self.assertEqual(len(calls), 2)
            self.assertFalse(output_path.exists())

    def _make_project(self, tmpdir):
        project_root = Path(tmpdir) / "Project" / "master_mvp" / "chart_mvp"
        api_management = Path(tmpdir) / "Project" / "api_management"
        project_root.mkdir(parents=True)
        api_management.mkdir(parents=True)
        return project_root, api_management / "api_keys.env"


if __name__ == "__main__":
    unittest.main()
