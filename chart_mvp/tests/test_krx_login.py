from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stock_core.providers.krx_login import (  # noqa: E402
    check_krx_api_key_readiness,
    check_krx_login_readiness,
    load_krx_api_key_config,
    load_krx_login_config,
    run_krx_login_session,
)
from stock_core.utils.local_env import load_local_env_for_project  # noqa: E402


class KrxLoginReadinessTests(unittest.TestCase):
    def test_missing_credentials_are_reported_without_secret_values(self) -> None:
        config = load_krx_login_config(env={})
        readiness = check_krx_login_readiness(config, module_available={"playwright": False})

        self.assertEqual(readiness.status, "blocked")
        self.assertIn("KRX_ID", " ".join(readiness.missing_materials))
        self.assertIn("KRX_PASSWORD", " ".join(readiness.missing_materials))
        self.assertIn("playwright python package", readiness.missing_materials)
        self.assertTrue(readiness.config_summary["secret_values_redacted"])

    def test_ready_when_local_materials_are_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {
                "KRX_ID": "user",
                "KRX_PASSWORD": "top-password",
                "KRX_LOGIN_AUTOMATION_ALLOWED": "true",
                "KRX_SESSION_STATE_PATH": "data/krx/session_state.json",
                "KRX_BROWSER_USER_DATA_DIR": "data/krx/browser_profile",
            }
            config = load_krx_login_config(env=env, project_root=Path(tmpdir))
            readiness = check_krx_login_readiness(config, module_available={"playwright": True})

            self.assertEqual(readiness.status, "ready")
            self.assertEqual(readiness.missing_materials, ())
            self.assertNotIn("top-password", str(readiness.to_dict()))
            self.assertTrue(str(config.session_state_path).startswith(tmpdir))

    def test_naver_linked_login_materials_are_supported_without_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {
                "KRX_LOGIN_METHOD": "naver",
                "KRX_NAVER_ID": "naver-user",
                "KRX_NAVER_PASSWORD": "naver-password",
                "KRX_LOGIN_AUTOMATION_ALLOWED": "true",
            }
            config = load_krx_login_config(env=env, project_root=Path(tmpdir))
            readiness = check_krx_login_readiness(config, module_available={"playwright": True})

            self.assertEqual(readiness.status, "ready")
            self.assertEqual(readiness.config_summary["login_method"], "naver")
            self.assertEqual(readiness.config_summary["checked_id_env_vars"], ["KRX_NAVER_ID", "NAVER_ID"])
            self.assertNotIn("naver-password", str(readiness.to_dict()))

    def test_naver_linked_login_reports_naver_env_names_when_missing(self) -> None:
        env = {
            "KRX_LOGIN_METHOD": "naver",
            "KRX_LOGIN_AUTOMATION_ALLOWED": "true",
        }
        config = load_krx_login_config(env=env)
        readiness = check_krx_login_readiness(config, module_available={"playwright": True})

        self.assertEqual(readiness.status, "blocked")
        self.assertIn("KRX_NAVER_ID or NAVER_ID", readiness.missing_materials)
        self.assertIn("KRX_NAVER_PASSWORD or NAVER_PASSWORD", readiness.missing_materials)

    def test_login_session_blocks_before_browser_when_materials_missing(self) -> None:
        result = run_krx_login_session(env={"KRX_LOGIN_METHOD": "naver"})

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.login_method, "naver")
        self.assertTrue(result.to_dict()["secret_values_redacted"])

    def test_challenge_bypass_policy_is_blocked(self) -> None:
        env = {
            "KRX_ID": "user",
            "KRX_PASSWORD": "secret",
            "KRX_LOGIN_AUTOMATION_ALLOWED": "true",
            "KRX_CAPTCHA_POLICY": "bypass",
        }
        config = load_krx_login_config(env=env)
        readiness = check_krx_login_readiness(config, module_available={"playwright": True})

        self.assertEqual(readiness.status, "blocked")
        self.assertIn("KRX_CAPTCHA_POLICY=manual_stop", readiness.missing_materials)

    def test_parent_api_management_file_loads_krx_open_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "Project" / "master_mvp" / "chart_mvp"
            api_management = Path(tmpdir) / "Project" / "api_management"
            project_root.mkdir(parents=True)
            api_management.mkdir(parents=True)
            (api_management / ".env").write_text(
                "\n".join(
                    [
                        "KRX_OPEN_API_KEY=krx-test-key",
                        "UNRELATED_SECRET=must-not-load",
                    ]
                ),
                encoding="utf-8",
            )
            env: dict[str, str] = {}

            result = load_local_env_for_project(project_root, env)
            config = load_krx_api_key_config(env=env, project_root=project_root)
            readiness = check_krx_api_key_readiness(config)

            self.assertEqual(result.loaded_env_vars, ("KRX_OPEN_API_KEY",))
            self.assertEqual(readiness.status, "ready")
            self.assertEqual(readiness.config_summary["selected_env_var"], "KRX_OPEN_API_KEY")
            self.assertNotIn("krx-test-key", str(readiness.to_dict()))
            self.assertNotIn("UNRELATED_SECRET", env)

    def test_master_project_env_is_not_loaded_for_api_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "Project" / "master_mvp" / "chart_mvp"
            project_root.mkdir(parents=True)
            (project_root.parent / "docs").mkdir()
            (project_root.parent / "docs" / "root_hard_stops.md").write_text("root", encoding="utf-8")
            (project_root.parent / ".env").write_text("KRX_OPEN_API_KEY=master-key", encoding="utf-8")
            env: dict[str, str] = {}

            config = load_krx_api_key_config(env=env, project_root=project_root)
            readiness = check_krx_api_key_readiness(config)

            self.assertNotIn("KRX_OPEN_API_KEY", env)
            self.assertEqual(readiness.status, "blocked")
            self.assertEqual(readiness.config_summary["source_paths"], [])
            self.assertNotIn("master-key", str(readiness.to_dict()))

    def test_local_chart_env_is_not_loaded_for_api_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "Project" / "master_mvp" / "chart_mvp"
            api_management = Path(tmpdir) / "Project" / "api_management"
            project_root.mkdir(parents=True)
            api_management.mkdir(parents=True)
            (project_root / ".env").write_text("KRX_OPEN_API_KEY=local-key", encoding="utf-8")
            (api_management / ".env").write_text("KRX_OPEN_API_KEY=parent-key", encoding="utf-8")
            env: dict[str, str] = {}

            load_local_env_for_project(project_root, env)

            self.assertEqual(env["KRX_OPEN_API_KEY"], "parent-key")


if __name__ == "__main__":
    unittest.main()
