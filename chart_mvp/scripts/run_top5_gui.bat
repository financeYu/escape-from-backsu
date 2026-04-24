@echo off
setlocal

chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
set "PYTHON_EXE=C:\Users\jjaew\AppData\Local\Programs\Python\Python312\python.exe"

pushd "%PROJECT_DIR%"
"%PYTHON_EXE%" -m app.run_gui
set "EXIT_CODE=%ERRORLEVEL%"
popd

exit /b %EXIT_CODE%
