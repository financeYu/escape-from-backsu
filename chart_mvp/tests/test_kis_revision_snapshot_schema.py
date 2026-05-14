import unittest
import tempfile
from pathlib import Path

from stock_core.ml.kis_revision_snapshot_schema import (
    BLOCKED_UNTIL_HISTORY_AVAILABLE_MANIFEST,
    KIS_REQUIRED_ENV_VARS,
    KIS_REVISION_ENDPOINTS,
    RAW_SNAPSHOT_REQUIRED_FIELDS,
    build_raw_snapshot_record,
    check_kis_api_key_readiness,
    compute_raw_hash,
    load_kis_api_key_config,
    validate_raw_snapshot_record,
)


class KisRevisionSnapshotSchemaTest(unittest.TestCase):
    def test_endpoint_metadata_covers_requested_kis_apis(self):
        self.assertEqual(
            set(KIS_REVISION_ENDPOINTS),
            {"estimate_perform", "invest_opinion", "invest_opbysec"},
        )
        self.assertEqual(
            KIS_REVISION_ENDPOINTS["estimate_perform"]["api_path"],
            "/uapi/domestic-stock/v1/quotations/estimate-perform",
        )
        self.assertEqual(
            KIS_REVISION_ENDPOINTS["invest_opinion"]["tr_id"],
            "FHKST663300C0",
        )
        self.assertEqual(
            KIS_REVISION_ENDPOINTS["invest_opbysec"]["tr_id"],
            "FHKST663400C0",
        )

    def test_env_contract_uses_placeholders_only(self):
        self.assertEqual(
            KIS_REQUIRED_ENV_VARS,
            ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCESS_TOKEN"),
        )

    def test_parent_api_management_file_loads_kis_credentials_without_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "Project" / "master_mvp" / "chart_mvp"
            api_management = Path(tmpdir) / "Project" / "api_management"
            project_root.mkdir(parents=True)
            api_management.mkdir(parents=True)
            (api_management / "api_keys.env").write_text(
                "\n".join(
                    [
                        "KIS_APP_KEY=kis-app-key",
                        "KIS_APP_SECRET=kis-app-secret",
                        "KIS_ACCESS_TOKEN=kis-access-token",
                        "UNRELATED_SECRET=must-not-load",
                    ]
                ),
                encoding="utf-8",
            )
            env: dict[str, str] = {}

            config = load_kis_api_key_config(env=env, project_root=project_root)
            readiness = check_kis_api_key_readiness(config)

            self.assertEqual(readiness.status, "ready")
            self.assertTrue(config.app_key_present)
            self.assertTrue(config.app_secret_present)
            self.assertTrue(config.access_token_present)
            self.assertEqual(set(env), set(KIS_REQUIRED_ENV_VARS))
            self.assertNotIn("UNRELATED_SECRET", env)
            self.assertNotIn("kis-app-secret", str(readiness.to_dict()))
            self.assertTrue(readiness.config_summary["secret_values_redacted"])

    def test_kis_readiness_reports_missing_without_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "Project" / "master_mvp" / "chart_mvp"
            project_root.mkdir(parents=True)
            env: dict[str, str] = {"KIS_APP_KEY": "kis-app-key"}

            config = load_kis_api_key_config(env=env, project_root=project_root)
            readiness = check_kis_api_key_readiness(config)

            self.assertEqual(readiness.status, "blocked")
            self.assertEqual(
                readiness.missing_materials,
                ("KIS_APP_SECRET", "KIS_ACCESS_TOKEN"),
            )
            self.assertNotIn("kis-app-key", str(readiness.to_dict()))

    def test_raw_hash_is_canonical(self):
        left = {"output": [{"b": 2, "a": 1}]}
        right = {"output": [{"a": 1, "b": 2}]}
        self.assertEqual(compute_raw_hash(left), compute_raw_hash(right))

    def test_build_raw_snapshot_record_has_required_fields(self):
        raw_json = {"output": [{"stck_bsop_date": "20250102"}]}
        record = build_raw_snapshot_record(
            endpoint_name="invest_opinion",
            code="005930",
            collected_at="2025-01-02T15:00:00+00:00",
            request_date="20250102",
            raw_json=raw_json,
            source_ref=KIS_REVISION_ENDPOINTS["invest_opinion"]["source_ref"],
        )

        self.assertEqual(tuple(record.keys()), RAW_SNAPSHOT_REQUIRED_FIELDS)
        self.assertEqual(record["raw_hash"], compute_raw_hash(raw_json))
        validate_raw_snapshot_record(record)

    def test_hash_validation_rejects_mutated_payload(self):
        record = build_raw_snapshot_record(
            endpoint_name="invest_opbysec",
            code="005930",
            collected_at="2025-01-02T15:00:00+00:00",
            request_date="20250102",
            raw_json={"output": [{"stck_bsop_date": "20250102"}]},
            source_ref=KIS_REVISION_ENDPOINTS["invest_opbysec"]["source_ref"],
        )
        record["raw_json"] = {"output": [{"stck_bsop_date": "20250103"}]}

        with self.assertRaises(ValueError):
            validate_raw_snapshot_record(record)

    def test_manifest_keeps_revision_features_blocked(self):
        manifest = BLOCKED_UNTIL_HISTORY_AVAILABLE_MANIFEST
        self.assertEqual(manifest["status"], "blocked_candidate_only")
        self.assertFalse(manifest["usable_for_v1_4_feature_manifest"])
        self.assertFalse(manifest["auto_reference_allowed"])
        self.assertIn("must_not_feed_v1_4_features", manifest["downstream_consumption_policy"])
        self.assertIn("eps_estimate_1m_ago", manifest["blocked_features"])
        self.assertIn(
            "no_feature_allowlist_promotion_before_pit_validation",
            manifest["unlock_requirements"],
        )


if __name__ == "__main__":
    unittest.main()
