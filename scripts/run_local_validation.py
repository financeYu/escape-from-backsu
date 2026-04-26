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

PYTEST_SUITES: dict[str, tuple[str, ...]] = {
    "smoke": (
        "tests/context",
        "tests/scanner/test_run_mvp_latest_ranking_cli.py",
        "tests/scanner/test_step20_ranking_regression.py",
        "tests/validation/test_step20_mvp_scope_guardrails.py",
    ),
    "context": ("tests/context",),
    "reports-backtest": ("tests/reports", "tests/backtest"),
    "scanner-validation": ("tests/scanner", "tests/reports", "tests/validation"),
    "integration": ("tests/integration",),
    "full": (),
}

UNITTEST_SUITES: dict[str, tuple[str, ...]] = {
    "chart": ("chart_mvp/tests",),
    "review-mvp": ("review_mvp/tests",),
}


def build_validation_command(
    suite: str,
    *,
    python_executable: str = sys.executable,
    run_id: str = "manual",
) -> list[str]:
    """Return the command used for one named validation suite."""

    if suite in PYTEST_SUITES:
        basetemp = _suite_temp_root(suite, run_id=run_id) / "basetemp"
        targets = PYTEST_SUITES[suite]
        return [
            python_executable,
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
            python_executable,
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
    env["TMP"] = str(temp_dir)
    env["TEMP"] = str(temp_dir)
    env["PYTEST_DEBUG_TEMPROOT"] = str(temp_dir)
    return env


def run_suite(suite: str, *, python_executable: str = sys.executable) -> int:
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
        default=sys.executable,
        help="Python executable to use for subprocess validation.",
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
