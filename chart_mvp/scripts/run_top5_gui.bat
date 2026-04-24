@echo off
setlocal

chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

pushd "%PROJECT_DIR%"
if defined PYTHON_EXE goto use_configured_python

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python -m app.run_gui
) else (
    py -3 -m app.run_gui
)
goto after_python

:use_configured_python
"%PYTHON_EXE%" -m app.run_gui

:after_python
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
