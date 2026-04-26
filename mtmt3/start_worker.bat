@echo off
chcp 65001 >nul
echo ========================================
echo 启动后台Worker
echo ========================================
cd /d %~dp0
set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
if not exist "%PYTHON_EXE%" (
  set "PYTHON_EXE=python"
)
"%PYTHON_EXE%" -m backend.worker
pause
