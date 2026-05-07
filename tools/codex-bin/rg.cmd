@echo off
setlocal
set "REPO_ROOT=%~dp0..\.."
set "PYTHON_EXE=%REPO_ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
"%PYTHON_EXE%" "%REPO_ROOT%\scripts\run_rg.py" %*
exit /b %ERRORLEVEL%
