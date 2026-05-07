"""Run repository validation with a workspace-local pytest temp root.

Windows local and sandboxed environments can leave pytest basetemp directories
that the next run cannot inspect. This runner keeps temp paths under
`.pytest_tmp/local_validation/` and passes an explicit `--basetemp` for pytest
suites so validation evidence is reproducible without touching global Temp.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_TEMP_ROOT = REPO_ROOT / ".pytest_tmp" / "local_validation"
WORKSPACE_VENV = REPO_ROOT / ".venv"
WORKSPACE_PYTHON = WORKSPACE_VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
WORKSPACE_RG = REPO_ROOT / "tools" / "rg"
WORKSPACE_BIN = REPO_ROOT / "tools" / "codex-bin"
DEFAULT_GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
DEFAULT_GIT = Path("C:/Program Files/Git/cmd/git.exe")

PYTEST_SUITES: dict[str, tuple[str, ...]] = {
    "smoke": (
        "tests/context",
        "tests/scanner/test_run_mvp_latest_ranking_cli.py",
        "tests/scanner/test_step20_ranking_regression.py",
        "tests/validation/test_step20_mvp_scope_guardrails.py",
    ),
    "chart": (
        "chart_mvp/tests",
        "tests/gui_mvp/test_chart_gui_compat.py",
    ),
    "context": ("tests/context",),
    "gui": (
        "tests/gui_mvp",
        "chart_mvp/tests/test_gui_financials.py",
    ),
    "backtest": (
        "tests/backtest",
        "tests/gui_mvp/test_backtest_viewer.py",
        "tests/validation/test_step19_pipeline_guardrails.py",
    ),
    "reports-backtest": ("tests/reports", "tests/backtest"),
    "scanner-validation": ("tests/scanner", "tests/reports", "tests/validation"),
    "integration": ("tests/integration",),
    "full": (),
}

UNITTEST_SUITES: dict[str, tuple[str, ...]] = {
    "review-mvp": ("review_mvp/tests",),
}


def build_validation_command(
    suite: str,
    *,
    python_executable: str | None = None,
    run_id: str = "manual",
) -> list[str]:
    """Return the command used for one named validation suite."""

    resolved_python = python_executable or resolve_workspace_python()
    if suite in PYTEST_SUITES:
        basetemp = _suite_temp_root(suite, run_id=run_id) / "basetemp"
        targets = PYTEST_SUITES[suite]
        return [
            resolved_python,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            *targets,
            "--basetemp",
            str(basetemp),
        ]
    if suite in UNITTEST_SUITES:
        (target,) = UNITTEST_SUITES[suite]
        return [
            resolved_python,
            "-m",
            "unittest",
            "discover",
            "-s",
            target,
            "-v",
        ]
    raise ValueError(f"Unknown validation suite: {suite}")


def build_validation_env(
    *,
    suite: str,
    base_env: dict[str, str] | None = None,
    run_id: str = "manual",
) -> dict[str, str]:
    """Return an environment that routes temp files into this workspace."""

    env = dict(os.environ if base_env is None else base_env)
    temp_dir = _suite_temp_root(suite, run_id=run_id) / "env"
    resolved_python = resolve_workspace_python()
    env["PYTHON"] = resolved_python
    env["VIRTUAL_ENV"] = str(WORKSPACE_VENV)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if DEFAULT_GIT.exists():
        env["PROJECT_GIT"] = str(DEFAULT_GIT)
    project_rg = WORKSPACE_RG / "rg.exe"
    if project_rg.exists():
        env["PROJECT_RG"] = str(project_rg)
    env["PROJECT_RG_FALLBACK"] = "1"
    if DEFAULT_GIT_BASH.exists():
        env["PROJECT_BASH"] = str(DEFAULT_GIT_BASH)
    env["PROJECT_ALLOW_WSL_BASH"] = "0"
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["PROJECT_ALLOW_GIT_INDEX_WRITE"] = "0"
    env["TMP"] = str(temp_dir)
    env["TEMP"] = str(temp_dir)
    env["PYTEST_DEBUG_TEMPROOT"] = str(temp_dir)
    _normalize_path_env(env)
    _prepend_pythonpath(env)
    return env


def run_suite(suite: str, *, python_executable: str | None = None) -> int:
    """Run one validation suite and return its process exit code."""

    run_id = str(os.getpid())
    command = build_validation_command(
        suite,
        python_executable=python_executable,
        run_id=run_id,
    )
    env = build_validation_env(suite=suite, run_id=run_id)
    Path(env["TMP"]).mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, cwd=REPO_ROOT, env=env, check=False)
    return int(completed.returncode)


def _suite_temp_root(suite: str, *, run_id: str) -> Path:
    safe_suite = "".join(character if character.isalnum() or character in ("-", "_") else "_" for character in suite)
    safe_run_id = "".join(character if character.isalnum() or character in ("-", "_") else "_" for character in run_id)
    return LOCAL_TEMP_ROOT / f"{safe_suite}-{safe_run_id}"


def resolve_workspace_python() -> str:
    """Return the root venv interpreter, falling back only if it is unavailable."""

    if WORKSPACE_PYTHON.exists():
        return str(WORKSPACE_PYTHON)
    return sys.executable


def _normalize_path_env(env: dict[str, str]) -> None:
    path_key = "Path" if "Path" in env else "PATH"
    existing_path = env.get(path_key) or env.get("PATH") or env.get("Path") or ""
    for duplicate_key in ("PATH", "Path"):
        if duplicate_key != path_key:
            env.pop(duplicate_key, None)
    preferred_entries = [WORKSPACE_VENV / "Scripts", WORKSPACE_BIN]
    existing_entries = [entry for entry in existing_path.split(os.pathsep) if entry]
    normalized_entries = [str(entry) for entry in preferred_entries if entry.exists()]
    normalized_entries.extend(
        entry for entry in existing_entries if entry.lower() not in {item.lower() for item in normalized_entries}
    )
    env[path_key] = os.pathsep.join(normalized_entries)


def _prepend_pythonpath(env: dict[str, str]) -> None:
    preferred_entries = [
        REPO_ROOT,
        REPO_ROOT / "chart_mvp" / "src",
        REPO_ROOT / "Quant_mvp" / "research_mvp" / "src",
    ]
    existing_entries = [entry for entry in env.get("PYTHONPATH", "").split(os.pathsep) if entry]
    normalized_entries = [str(entry) for entry in preferred_entries if entry.exists()]
    normalized_entries.extend(
        entry for entry in existing_entries if entry.lower() not in {item.lower() for item in normalized_entries}
    )
    env["PYTHONPATH"] = os.pathsep.join(normalized_entries)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local validation with repository-local temp paths.")
    parser.add_argument(
        "suites",
        nargs="+",
        choices=sorted((*PYTEST_SUITES.keys(), *UNITTEST_SUITES.keys())),
        help="Validation suite name(s) to run.",
    )
    parser.add_argument(
        "--python",
        default=None,
        help="Python executable to use for subprocess validation. Defaults to the repository root .venv.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    exit_code = 0
    for suite in args.suites:
        result = run_suite(suite, python_executable=args.python)
        if result != 0 and exit_code == 0:
            exit_code = result
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
