import json
import tempfile
import unittest
from pathlib import Path

from stock_core.ml.kis_revision_snapshot_collector import (
    build_kis_revision_request_params,
    collect_kis_revision_raw_snapshots,
    ensure_kis_access_token,
)
from stock_core.ml.kis_revision_snapshot_schema import validate_raw_snapshot_record


class KisRevisionSnapshotCollectorTest(unittest.TestCase):
    def test_token_reuses_valid_local_token_without_refresh(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root, env_file = self._make_project(tmpdir)
            env_file.write_text(
                "\n".join(
                    [
                        "KIS_APP_KEY=app-key",
                        "KIS_APP_SECRET=app-secret",
                        "KIS_ACCESS_TOKEN=existing-token",
                        "KIS_ACCESS_TOKEN_EXPIRES_AT=2999-01-01 00:00:00",
                    ]
                ),
                encoding="utf-8",
            )

            def fail_post(*_args):
                raise AssertionError("token refresh should not be called")

            state = ensure_kis_access_token(
                env={},
                project_root=project_root,
                post_json=fail_post,
            )

            self.assertEqual(state.status, "ready")
            self.assertFalse(state.refreshed)
            self.assertEqual(state.token, "existing-token")
            self.assertNotIn("existing-token", str(state.redacted_summary()))

    def test_token_refresh_writes_token_and_expiry_to_api_management_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root, env_file = self._make_project(tmpdir)
            env_file.write_text(
                "\n".join(
                    [
                        "KIS_APP_KEY=app-key",
                        "KIS_APP_SECRET=app-secret",
                    ]
                ),
                encoding="utf-8",
            )
            calls = []

            def fake_post(url, headers, payload, timeout_seconds):
                calls.append((url, headers, payload, timeout_seconds))
                return {
                    "access_token": "new-token",
                    "access_token_token_expired": "2999-01-02 03:04:05",
                }

            env = {}
            state = ensure_kis_access_token(
                env=env,
                project_root=project_root,
                post_json=fake_post,
            )

            self.assertEqual(state.status, "ready")
            self.assertTrue(state.refreshed)
            self.assertEqual(env["KIS_ACCESS_TOKEN"], "new-token")
            self.assertEqual(env["KIS_ACCESS_TOKEN_EXPIRES_AT"], "2999-01-02 03:04:05")
            self.assertEqual(len(calls), 1)
            saved = env_file.read_text(encoding="utf-8")
            self.assertIn("KIS_ACCESS_TOKEN=new-token", saved)
            self.assertIn('KIS_ACCESS_TOKEN_EXPIRES_AT="2999-01-02 03:04:05"', saved)

    def test_token_inspection_can_block_without_refreshing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root, env_file = self._make_project(tmpdir)
            env_file.write_text(
                "\n".join(
                    [
                        "KIS_APP_KEY=app-key",
                        "KIS_APP_SECRET=app-secret",
                    ]
                ),
                encoding="utf-8",
            )

            def fail_post(*_args):
                raise AssertionError("dry inspection should not refresh")

            state = ensure_kis_access_token(
                env={},
                project_root=project_root,
                refresh_allowed=False,
                post_json=fail_post,
            )

            self.assertEqual(state.status, "blocked")
            self.assertFalse(state.refreshed)
            self.assertEqual(state.warnings, ("token_refresh_required",))
            self.assertNotIn("KIS_ACCESS_TOKEN=", env_file.read_text(encoding="utf-8"))

    def test_request_params_match_endpoint_contracts(self):
        self.assertEqual(
            build_kis_revision_request_params(
                "estimate_perform",
                code="005930",
                start_date="20250101",
                end_date="20250131",
            ),
            {"SHT_CD": "005930"},
        )
        self.assertEqual(
            build_kis_revision_request_params(
                "invest_opinion",
                code="005930",
                start_date="20250101",
                end_date="20250131",
            )["FID_COND_SCR_DIV_CODE"],
            "16633",
        )
        self.assertEqual(
            build_kis_revision_request_params(
                "invest_opbysec",
                code="005930",
                start_date="20250101",
                end_date="20250131",
            )["FID_DIV_CLS_CODE"],
            "0",
        )

    def test_collection_writes_raw_jsonl_records_with_fake_http(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root, env_file = self._make_project(tmpdir)
            env_file.write_text(
                "\n".join(
                    [
                        "KIS_APP_KEY=app-key",
                        "KIS_APP_SECRET=app-secret",
                        "KIS_ACCESS_TOKEN=existing-token",
                        "KIS_ACCESS_TOKEN_EXPIRES_AT=2999-01-01 00:00:00",
                    ]
                ),
                encoding="utf-8",
            )
            output_dir = Path(tmpdir) / "snapshots"
            calls = []

            def fake_get(url, headers, params, timeout_seconds):
                calls.append((url, headers, params, timeout_seconds))
                return (
                    {
                        "rt_cd": "0",
                        "output": [{"stck_bsop_date": "20250131", "value": params.get("FID_INPUT_ISCD", params.get("SHT_CD"))}],
                    },
                    {},
                )

            result = collect_kis_revision_raw_snapshots(
                codes=["005930"],
                endpoints=["invest_opinion"],
                start_date="20250101",
                end_date="20250131",
                output_dir=output_dir,
                env={},
                project_root=project_root,
                get_json=fake_get,
            )

            self.assertEqual(result.records_written, 1)
            self.assertFalse(result.token_refreshed)
            self.assertEqual(len(calls), 1)
            record = json.loads(Path(result.output_path).read_text(encoding="utf-8").strip())
            validate_raw_snapshot_record(record)
            self.assertEqual(record["provider"], "kis_open_api")
            self.assertEqual(record["endpoint_name"], "invest_opinion")
            self.assertEqual(record["code"], "005930")
            self.assertEqual(record["request_date"], "20250101:20250131")
            self.assertEqual(record["raw_json"]["rt_cd"], "0")

    def _make_project(self, tmpdir):
        project_root = Path(tmpdir) / "Project" / "master_mvp" / "chart_mvp"
        api_management = Path(tmpdir) / "Project" / "api_management"
        project_root.mkdir(parents=True)
        api_management.mkdir(parents=True)
        return project_root, api_management / "api_keys.env"


if __name__ == "__main__":
    unittest.main()
