---
name: workspace-python-env
description: Use when running Python, pytest, unittest, validation scripts, or Codex shell commands in master_mvp or its subprojects; pins commands to the repository root .venv so pandas and shared dev dependencies are available and system Python is avoided.
---

# Workspace Python Environment

Use the repository root virtual environment for all Python validation in
`master_mvp`, including subprojects such as `chart_mvp`, `gui_mvp`,
`Quant_mvp`, `Quant_mvp/research_mvp`, and `review_mvp`.

## Required Interpreter

From the repository root, prefer:

```powershell
.venv\Scripts\python.exe
```

Do not run pytest or pandas-dependent checks with bare `python` unless the
current Codex shell has already been normalized by the project `.codex/config.toml`
or by `scripts/run_local_validation.py`.

## Environment Contract

For Codex shell subprocesses, the project config must keep these variables
pointed at the root workspace:

```text
PYTHON=C:\Users\jjaew\Project\master_mvp\.venv\Scripts\python.exe
VIRTUAL_ENV=C:\Users\jjaew\Project\master_mvp\.venv
PYTHONUTF8=1
PYTHONIOENCODING=utf-8
PROJECT_GIT=C:\Program Files\Git\cmd\git.exe
PROJECT_RG=C:\Users\jjaew\Project\master_mvp\tools\rg\rg.exe
PROJECT_RG_FALLBACK=1
PROJECT_BASH=C:\Program Files\Git\bin\bash.exe
PROJECT_ALLOW_WSL_BASH=0
GIT_OPTIONAL_LOCKS=0
GIT_TERMINAL_PROMPT=0
PROJECT_ALLOW_GIT_INDEX_WRITE=0
TMP=C:\Users\jjaew\Project\master_mvp\.pytest_tmp\codex_shell
TEMP=C:\Users\jjaew\Project\master_mvp\.pytest_tmp\codex_shell
PYTEST_DEBUG_TEMPROOT=C:\Users\jjaew\Project\master_mvp\.pytest_tmp\codex_shell
```

The shell `Path` should put `.venv\Scripts` before system Python and
`tools\codex-bin` before bundled WindowsApps `rg` or system Git.

Project-local text search should resolve `rg` through `tools\codex-bin\rg.ps1`
in PowerShell or `tools\codex-bin\rg.cmd` in cmd.exe. If the local
`PROJECT_RG` binary is unavailable or blocked, the wrapper falls back to
`scripts\run_rg.py` for common gate checks such as `rg --files` and line-number
text search. Treat `BLOCKED_RG_EXECUTION` as an environment blocker, not
validation evidence. `tools\rg` remains a local ignored binary cache and should
not hold tracked wrapper scripts.

Project-local Git commands should resolve `git` through
`tools\codex-bin\git.ps1` in PowerShell or `tools\codex-bin\git.cmd` in cmd.exe.
The wrapper sets
`GIT_OPTIONAL_LOCKS=0` for read-only commands and blocks index-writing commands
such as `git add` unless
`PROJECT_ALLOW_GIT_INDEX_WRITE=1` is explicitly set for an approved finalize
operation. Treat `BLOCKED_GIT_INDEX_WRITE` and `BLOCKED_GIT_INDEX_LOCK` as
environment or policy blockers, not test evidence.

Project-local bash validators should use `PROJECT_BASH` through
`scripts\run_bash_validator.ps1`. Keep `PROJECT_ALLOW_WSL_BASH=0` by default so
an unavailable WSL install is reported as a validator execution environment
blocker, not as test or contract validation evidence. Set
`PROJECT_ALLOW_WSL_BASH=1` only for an explicitly WSL-enabled local run.

## Validation Pattern

For repository suites, prefer the wrapper because it also routes temp files
under `.pytest_tmp/local_validation` and dispatches pytest through the root
`.venv` even if the wrapper itself was launched by system Python:

```powershell
.venv\Scripts\python.exe scripts\run_local_validation.py <suite>
```

For direct focused checks, use:

```powershell
.venv\Scripts\python.exe -m pytest -q <targets>
.venv\Scripts\python.exe -m unittest discover -s <tests> -v
```

## Blocker Handling

If a check fails because `python` resolves to system Python, cannot import
`pandas`, `rg` resolves to a denied WindowsApps binary, or Git index writes hit
`.git/index.lock` or `.git` ACL blockers, record it as an environment blocker,
not as test evidence. Retry once with the project wrapper or root `.venv`
command above. If the retry is still blocked, route the blocked check through
`.agents/skills/cost-aware-review-refactor/SKILL.md` and keep the blocker
separate from validation status.
