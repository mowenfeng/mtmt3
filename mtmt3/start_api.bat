@echo off
chcp 65001 >nul
echo ========================================
echo 启动FastAPI服务器
echo ========================================
cd /d %~dp0
set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
if not exist "%PYTHON_EXE%" (
  set "PYTHON_EXE=python"
)
"%PYTHON_EXE%" -m uvicorn backend.main:app --reload --port 8000
pause
