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
TMP=C:\Users\jjaew\Project\master_mvp\.pytest_tmp\codex_shell
TEMP=C:\Users\jjaew\Project\master_mvp\.pytest_tmp\codex_shell
PYTEST_DEBUG_TEMPROOT=C:\Users\jjaew\Project\master_mvp\.pytest_tmp\codex_shell
```

The shell `Path` should put `.venv\Scripts` before system Python and
`tools\rg` before bundled WindowsApps `rg`.

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

If a check fails because `python` resolves to system Python or cannot import
`pandas`, record it as an environment blocker, not as test evidence. Retry once
with the root `.venv` command above. If the retry is still blocked, route the
blocked check through `.agents/skills/cost-aware-review-refactor/SKILL.md` and
keep the blocker separate from validation status.
