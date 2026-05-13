from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path


IMPORT_NAME_BY_PACKAGE = {
    "scikit-learn": "sklearn",
    "sklearn": "sklearn",
    "numpy": "numpy",
    "pandas": "pandas",
    "lightgbm": "lightgbm",
    "xgboost": "xgboost",
    "catboost": "catboost",
}


PINNED_THREAD_ENV = {
    "PROJECT_ML_THREAD_COUNT": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "LOKY_MAX_CPU_COUNT": "1",
}


def _split_packages(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _available(package: str) -> bool:
    import_name = IMPORT_NAME_BY_PACKAGE.get(package, package.replace("-", "_"))
    return importlib.util.find_spec(import_name) is not None


def _status(packages: list[str]) -> dict[str, str]:
    return {package: "present" if _available(package) else "missing" for package in packages}


def _env_status(root: Path) -> dict[str, str]:
    expected_python = str(root / ".venv" / "Scripts" / "python.exe")
    return {
        "PROJECT_ML_PYTHON": os.environ.get("PROJECT_ML_PYTHON", ""),
        "PROJECT_ML_PYTHON_expected": expected_python,
        "PROJECT_ML_THREAD_COUNT": os.environ.get("PROJECT_ML_THREAD_COUNT", ""),
        "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", ""),
        "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS", ""),
        "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS", ""),
        "NUMEXPR_NUM_THREADS": os.environ.get("NUMEXPR_NUM_THREADS", ""),
        "LOKY_MAX_CPU_COUNT": os.environ.get("LOKY_MAX_CPU_COUNT", ""),
    }


def _same_path(left: str, right: str) -> bool:
    if not left or not right:
        return False
    try:
        return Path(left).resolve() == Path(right).resolve()
    except OSError:
        return os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--require-optional", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[4]
    required = _split_packages(os.environ.get("PROJECT_ML_REQUIRED_PACKAGES", "numpy,pandas,sklearn"))
    optional = _split_packages(os.environ.get("PROJECT_ML_OPTIONAL_PACKAGES", "lightgbm,xgboost,catboost"))
    required_status = _status(required)
    optional_status = _status(optional)
    missing_required = [name for name, status in required_status.items() if status != "present"]
    missing_optional = [name for name, status in optional_status.items() if status != "present"]
    env_status = _env_status(root)
    expected_python = env_status["PROJECT_ML_PYTHON_expected"]
    missing_env = [
        name
        for name in ("PROJECT_ML_PYTHON", *PINNED_THREAD_ENV)
        if not env_status.get(name)
    ]
    mismatched_env = []
    if env_status.get("PROJECT_ML_PYTHON") and not _same_path(env_status["PROJECT_ML_PYTHON"], expected_python):
        mismatched_env.append("PROJECT_ML_PYTHON")
    for name, expected in PINNED_THREAD_ENV.items():
        if env_status.get(name) and env_status[name] != expected:
            mismatched_env.append(name)
    python_executable_matches_root = _same_path(sys.executable, expected_python)
    ok = (
        not missing_required
        and not missing_env
        and not mismatched_env
        and python_executable_matches_root
        and (not args.require_optional or not missing_optional)
    )
    payload = {
        "status": "pass" if ok else "fail",
        "required_packages": required_status,
        "optional_packages": optional_status,
        "missing_required_packages": missing_required,
        "missing_optional_packages": missing_optional,
        "environment": env_status,
        "missing_environment_variables": missing_env,
        "mismatched_environment_variables": mismatched_env,
        "require_optional": args.require_optional,
        "python_executable": sys.executable,
        "python_executable_matches_root": python_executable_matches_root,
    }
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"workspace_ml_env: {payload['status']}")
        print(f"required_packages: {required_status}")
        print(f"optional_packages: {optional_status}")
        print(f"missing_environment_variables: {missing_env}")
        print(f"mismatched_environment_variables: {mismatched_env}")
        print(f"python_executable_matches_root: {python_executable_matches_root}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
