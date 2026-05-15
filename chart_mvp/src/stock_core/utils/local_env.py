"""Local-only environment loading helpers for chart runtime tools."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import MutableMapping

from stock_core.utils.paths import PROJECT_ROOT


DEFAULT_ENV_ALLOWLIST = (
    "KRX_OPEN_API_KEY",
    "KRX_API_KEY",
    "KRX_SERVICE_KEY",
    "KRX_LISTED_INFO_API_KEY",
    "DATA_GO_KR_API_KEY",
    "KRX_ACCESS_TOKEN",
    "KRX_ID",
    "KRX_PASSWORD",
    "KRX_PW",
    "KRX_LOGIN_METHOD",
    "KRX_NAVER_ID",
    "KRX_NAVER_PASSWORD",
    "NAVER_ID",
    "NAVER_PASSWORD",
    "KRX_LOGIN_URL",
    "KRX_OPEN_API_USAGE_URL",
    "KRX_LOGIN_AUTOMATION_ALLOWED",
    "KRX_LOGIN_DRIVER",
    "KRX_LOGIN_HEADLESS",
    "KRX_LOGIN_TIMEOUT_SECONDS",
    "KRX_SESSION_STATE_PATH",
    "KRX_BROWSER_USER_DATA_DIR",
    "KRX_CAPTCHA_POLICY",
    "KRX_TWO_FACTOR_POLICY",
    "KRX_LOGIN_SUCCESS_URL_CONTAINS",
    "KIS_APP_KEY",
    "KIS_APP_SECRET",
    "KIS_ACCESS_TOKEN",
    "KIS_ACCESS_TOKEN_EXPIRES_AT",
    "KIS_ENV_DV",
    "KIS_BASE_URL",
    "OPENDART_API_KEY",
)
ENV_FILE_NAMES = (
    ".env",
    "api_keys.env",
    "api-keys.env",
    "keys.env",
)
AUTOLOAD_ENV_VAR = "MASTER_MVP_API_KEYS_AUTOLOAD"
EXTRA_ALLOWED_ENV_VARS = "MASTER_MVP_API_KEY_ENV_VARS"


@dataclass(frozen=True)
class LocalEnvLoadResult:
    source_paths: tuple[Path, ...]
    loaded_env_vars: tuple[str, ...]
    skipped_existing_env_vars: tuple[str, ...]
    attempted_paths: tuple[Path, ...]
    disabled_reason: str | None = None


@dataclass(frozen=True)
class LocalEnvPresenceResult:
    present_env_vars: tuple[str, ...]
    missing_env_vars: tuple[str, ...]
    source_paths: tuple[Path, ...]
    attempted_paths: tuple[Path, ...]
    disabled_reason: str | None = None


def load_local_env_for_project(
    project_root: Path = PROJECT_ROOT,
    environ: MutableMapping[str, str] | None = None,
    *,
    override: bool = False,
) -> LocalEnvLoadResult:
    """Load allowlisted local env values without returning secret values."""

    env = os.environ if environ is None else environ
    if _autoload_disabled(env):
        return LocalEnvLoadResult(
            source_paths=(),
            loaded_env_vars=(),
            skipped_existing_env_vars=(),
            attempted_paths=(),
            disabled_reason="autoload_disabled",
        )

    candidates = _candidate_env_files(project_root)
    allowed_names = _allowed_env_names(env)
    source_paths: list[Path] = []
    loaded: list[str] = []
    skipped_existing: list[str] = []

    for path in candidates:
        if not path.is_file():
            continue
        source_paths.append(path)
        for name, value in _parse_env_file(path).items():
            if name not in allowed_names:
                continue
            if not override and env.get(name):
                skipped_existing.append(name)
                continue
            env[name] = value
            loaded.append(name)

    return LocalEnvLoadResult(
        source_paths=tuple(source_paths),
        loaded_env_vars=tuple(sorted(set(loaded))),
        skipped_existing_env_vars=tuple(sorted(set(skipped_existing))),
        attempted_paths=tuple(candidates),
    )


def check_local_env_presence(
    env_var_names: tuple[str, ...],
    project_root: Path = PROJECT_ROOT,
    environ: MutableMapping[str, str] | None = None,
) -> LocalEnvPresenceResult:
    """Check whether local API env vars are available without exposing values."""

    env = os.environ if environ is None else environ
    load_result = load_local_env_for_project(project_root, env)
    present = tuple(name for name in env_var_names if env.get(name))
    missing = tuple(name for name in env_var_names if not env.get(name))
    return LocalEnvPresenceResult(
        present_env_vars=present,
        missing_env_vars=missing,
        source_paths=load_result.source_paths,
        attempted_paths=load_result.attempted_paths,
        disabled_reason=load_result.disabled_reason,
    )


def _autoload_disabled(env: MutableMapping[str, str]) -> bool:
    value = env.get(AUTOLOAD_ENV_VAR, "").strip().lower()
    return value in {"0", "false", "no", "off"}


def _allowed_env_names(env: MutableMapping[str, str]) -> set[str]:
    names = set(DEFAULT_ENV_ALLOWLIST)
    names.update(item.strip() for item in env.get(EXTRA_ALLOWED_ENV_VARS, "").split(",") if item.strip())
    return names


def _candidate_env_files(project_root: Path) -> tuple[Path, ...]:
    api_management_dir = _project_collection_root(project_root.resolve()) / "api_management"
    candidates = [api_management_dir / filename for filename in ENV_FILE_NAMES]
    return tuple(_dedupe_paths(candidates))


def _project_collection_root(project_root: Path) -> Path:
    for candidate in (project_root, *project_root.parents):
        if candidate.name.lower() == "project":
            return candidate
    return project_root.parent


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        result.append(resolved)
    return result


def _parse_env_file(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if not name or not name.replace("_", "").isalnum() or name[0].isdigit():
            continue
        parsed[name] = _strip_env_value(value.strip())
    return parsed


def _strip_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
