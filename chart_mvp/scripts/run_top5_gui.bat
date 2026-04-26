@echo off
setlocal

chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "SCRIPT_DIR=%~dp0"
set "CHART_PROJECT_DIR=%SCRIPT_DIR%.."
for %%I in ("%CHART_PROJECT_DIR%\..") do set "REPO_ROOT=%%~fI"

pushd "%REPO_ROOT%"
if defined PYTHON_EXE goto use_configured_python

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python -m gui_mvp chart
) else (
    py -3 -m gui_mvp chart
)
goto after_python

:use_configured_python
"%PYTHON_EXE%" -m gui_mvp chart

:after_python
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
