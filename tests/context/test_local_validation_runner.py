from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_local_validation import (  # noqa: E402
    LOCAL_TEMP_ROOT,
    build_validation_command,
    build_validation_env,
)


def test_pytest_suite_uses_workspace_local_basetemp() -> None:
    command = build_validation_command("context", python_executable="python")

    assert command[:6] == ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    assert "tests/context" in command
    assert "--basetemp" in command
    assert str(LOCAL_TEMP_ROOT / "context-manual" / "basetemp") in command


def test_smoke_suite_covers_context_and_mvp_reproducibility_checks() -> None:
    command = build_validation_command("smoke", python_executable="python")

    assert "tests/context" in command
    assert "tests/scanner/test_run_mvp_latest_ranking_cli.py" in command
    assert "tests/scanner/test_step20_ranking_regression.py" in command
    assert "tests/validation/test_step20_mvp_scope_guardrails.py" in command
    assert str(LOCAL_TEMP_ROOT / "smoke-manual" / "basetemp") in command


def test_chart_suite_covers_runtime_and_gui_compatibility() -> None:
    command = build_validation_command("chart", python_executable="python")

    assert command[:6] == ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    assert "chart_mvp/tests" in command
    assert "tests/gui_mvp/test_chart_gui_compat.py" in command
    assert "--basetemp" in command
    assert str(LOCAL_TEMP_ROOT / "chart-manual" / "basetemp") in command


def test_gui_suite_covers_chart_and_backtest_viewers() -> None:
    command = build_validation_command("gui", python_executable="python")

    assert "tests/gui_mvp" in command
    assert "chart_mvp/tests/test_gui_financials.py" in command
    assert str(LOCAL_TEMP_ROOT / "gui-manual" / "basetemp") in command


def test_backtest_suite_covers_core_gui_and_pipeline_guardrails() -> None:
    command = build_validation_command("backtest", python_executable="python")

    assert "tests/backtest" in command
    assert "tests/gui_mvp/test_backtest_viewer.py" in command
    assert "tests/validation/test_step19_pipeline_guardrails.py" in command
    assert str(LOCAL_TEMP_ROOT / "backtest-manual" / "basetemp") in command


def test_validation_env_routes_global_temp_to_workspace() -> None:
    env = build_validation_env(suite="context", base_env={"PATH": "example"})

    assert env["PATH"] == "example"
    assert env["TMP"].startswith(str(LOCAL_TEMP_ROOT))
    assert env["TEMP"] == env["TMP"]
    assert env["PYTEST_DEBUG_TEMPROOT"] == env["TMP"]
