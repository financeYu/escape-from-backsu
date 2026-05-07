"""Project-local rg wrapper with a Python fallback.

Codex on Windows can resolve ``rg`` to a WindowsApps packaged executable whose
ACL denies execution inside this workspace. This wrapper first tries an
explicit project-approved ripgrep binary, then falls back to a small subset
that covers the project gates' common uses: ``rg --files`` and text search.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
BLOCKED_EXIT = 125
TEXT_EXTENSIONS = {
    ".bat",
    ".cmd",
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".pytest_tmp",
    "__pycache__",
    "node_modules",
}


def main(argv: list[str]) -> int:
    real_rg = _resolve_real_rg()
    if real_rg is not None:
        try:
            completed = subprocess.run([str(real_rg), *argv], cwd=REPO_ROOT, check=False)
        except OSError as exc:
            print(f"BLOCKED_RG_EXECUTION: {real_rg}: {exc}", file=sys.stderr)
        else:
            return int(completed.returncode)

    if os.environ.get("PROJECT_RG_FALLBACK", "1").lower() not in {"1", "true", "yes"}:
        print("BLOCKED_RG_EXECUTION: no executable project-approved rg found", file=sys.stderr)
        return BLOCKED_EXIT
    return _fallback_rg(argv)


def _resolve_real_rg() -> Path | None:
    candidates: list[Path] = []
    env_candidate = os.environ.get("PROJECT_RG")
    if env_candidate:
        candidates.append(Path(env_candidate))
    candidates.extend(
        [
            REPO_ROOT / "tools" / "rg" / "rg.exe",
            Path("C:/ProgramData/chocolatey/bin/rg.exe"),
            Path("C:/Program Files/ripgrep/rg.exe"),
        ]
    )
    for candidate in candidates:
        if candidate.is_file() and "windowsapps" not in str(candidate).lower():
            return candidate
    return None


def _fallback_rg(argv: list[str]) -> int:
    if not argv:
        print("usage: rg [--files] [options] <pattern> [path ...]", file=sys.stderr)
        return 2

    options, values = _split_args(argv)
    if "--files" in options:
        paths = [Path(value) for value in values] or [REPO_ROOT]
        for path in _iter_files(paths, include_hidden="--hidden" in options):
            print(_display_path(path))
        return 0

    pattern = _extract_pattern(options, values)
    if pattern is None:
        print("run_rg fallback requires a search pattern", file=sys.stderr)
        return 2

    paths = [Path(value) for value in values[1:]] or [REPO_ROOT]
    ignore_case = "-i" in options or "--ignore-case" in options
    fixed_strings = "-F" in options or "--fixed-strings" in options
    list_files = "-l" in options or "--files-with-matches" in options
    matched = False
    for path in _iter_files(paths, include_hidden="--hidden" in options):
        file_matched = False
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, start=1):
            if _matches(line, pattern, ignore_case=ignore_case, fixed_strings=fixed_strings):
                matched = True
                file_matched = True
                if list_files:
                    print(_display_path(path))
                    break
                print(f"{_display_path(path)}:{line_number}:{line}")
        if list_files and file_matched:
            continue
    return 0 if matched else 1


def _split_args(argv: list[str]) -> tuple[set[str], list[str]]:
    options: set[str] = set()
    values: list[str] = []
    skip_next = False
    for index, arg in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        if arg == "-e" and index + 1 < len(argv):
            options.add(arg)
            values.insert(0, argv[index + 1])
            skip_next = True
            continue
        if arg.startswith("-"):
            options.add(arg)
            continue
        values.append(arg)
    return options, values


def _extract_pattern(options: set[str], values: list[str]) -> str | None:
    if "-e" in options and values:
        return values[0]
    if values:
        return values[0]
    return None


def _iter_files(paths: list[Path], *, include_hidden: bool) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = raw_path if raw_path.is_absolute() else REPO_ROOT / raw_path
        if path.is_file():
            if _is_searchable(path):
                files.append(path)
            continue
        if not path.exists():
            continue
        for candidate in path.rglob("*"):
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(REPO_ROOT)
            if not include_hidden and any(part.startswith(".") for part in relative.parts):
                continue
            if any(part in SKIP_DIRS for part in relative.parts):
                continue
            if _is_searchable(candidate):
                files.append(candidate)
    return sorted(set(files))


def _is_searchable(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS or path.name in {"AGENTS.md", "Dockerfile", "Makefile"}


def _matches(line: str, pattern: str, *, ignore_case: bool, fixed_strings: bool) -> bool:
    haystack = line.lower() if ignore_case else line
    needle = pattern.lower() if ignore_case else pattern
    if fixed_strings:
        return needle in haystack
    flags = re.IGNORECASE if ignore_case else 0
    try:
        return re.search(pattern, line, flags=flags) is not None
    except re.error:
        return needle in haystack


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
