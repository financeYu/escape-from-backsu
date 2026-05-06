from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import MutableMapping


DEFAULT_API_KEY_ENV_VARS = (
    "OPENALEX_API_KEY",
    "OPENALEX_MAILTO",
    "SEMANTIC_SCHOLAR_API_KEY",
    "CROSSREF_PLUS_API_TOKEN",
    "CROSSREF_MAILTO",
)
API_KEY_FILE_NAMES = (
    ".env",
    "api_keys.env",
    "api-keys.env",
    "keys.env",
)
AUTOLOAD_ENV_VAR = "MASTER_MVP_API_KEYS_AUTOLOAD"
EXTRA_ALLOWED_ENV_VARS = "MASTER_MVP_API_KEY_ENV_VARS"


@dataclass(frozen=True)
class ApiKeyLoadResult:
    source_path: Path | None
    loaded_env_vars: tuple[str, ...]
    skipped_existing_env_vars: tuple[str, ...]
    attempted_paths: tuple[Path, ...]
    disabled_reason: str | None = None


def load_api_keys_for_project(
    root: Path,
    environ: MutableMapping[str, str] | None = None,
    *,
    override: bool = False,
) -> ApiKeyLoadResult:
    """Load allowlisted API env vars from C:/Users/jjaew/Project/api_management.

    Values are copied only into the current process environment and are never
    returned by this function.
    """

    env = environ if environ is not None else os.environ
    if _autoload_disabled(env):
        return ApiKeyLoadResult(
            source_path=None,
            loaded_env_vars=(),
            skipped_existing_env_vars=(),
            attempted_paths=(),
            disabled_reason="autoload_disabled",
        )

    candidates = _candidate_api_key_files(root)
    existing = next((path for path in candidates if path and path.is_file()), None)
    if existing is None:
        return ApiKeyLoadResult(
            source_path=None,
            loaded_env_vars=(),
            skipped_existing_env_vars=(),
            attempted_paths=tuple(path for path in candidates if path is not None),
        )

    allowed_names = _allowed_env_var_names(env)
    parsed = _parse_env_file(existing)
    loaded: list[str] = []
    skipped_existing: list[str] = []
    for name, value in parsed.items():
        if name not in allowed_names:
            continue
        if not override and env.get(name):
            skipped_existing.append(name)
            continue
        env[name] = value
        loaded.append(name)

    return ApiKeyLoadResult(
        source_path=existing,
        loaded_env_vars=tuple(sorted(loaded)),
        skipped_existing_env_vars=tuple(sorted(skipped_existing)),
        attempted_paths=tuple(path for path in candidates if path is not None),
    )


def _autoload_disabled(env: MutableMapping[str, str]) -> bool:
    value = env.get(AUTOLOAD_ENV_VAR, "").strip().lower()
    if value in {"0", "false", "no", "off"}:
        return True
    return "PYTEST_CURRENT_TEST" in env


def _allowed_env_var_names(env: MutableMapping[str, str]) -> set[str]:
    values = set(DEFAULT_API_KEY_ENV_VARS)
    extra = env.get(EXTRA_ALLOWED_ENV_VARS, "")
    values.update(item.strip() for item in extra.split(",") if item.strip())
    return values


def _candidate_api_key_files(root: Path) -> tuple[Path, ...]:
    api_management_dir = _project_collection_root(root.resolve()) / "api_management"
    candidates = [api_management_dir / filename for filename in API_KEY_FILE_NAMES]
    return tuple(_dedupe_paths(candidates))


def _project_collection_root(root: Path) -> Path:
    for candidate in (root, *root.parents):
        if candidate.name.lower() == "project":
            return candidate
    return root.parents[2] if len(root.parents) > 2 else root.parent


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
