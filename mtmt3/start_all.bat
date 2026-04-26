@echo off
chcp 65001 >nul
cd /d %~dp0

set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
if not exist "%PYTHON_EXE%" (
  set "PYTHON_EXE=python"
)

echo ========================================
echo 启动音乐转谱服务（API + Worker）
echo ========================================
echo.
echo 正在启动API服务器和Worker...
echo.

start "API服务器" cmd /k "cd /d %~dp0 && ""%PYTHON_EXE%"" -m uvicorn backend.main:app --reload --port 8000"
timeout /t 3 /nobreak >nul
start "Worker" cmd /k "cd /d %~dp0 && ""%PYTHON_EXE%"" -m backend.worker"

echo.
echo ========================================
echo ✅ 服务已启动！
echo ========================================
echo 📡 API服务器: http://127.0.0.1:8000
echo 📄 API文档: http://127.0.0.1:8000/docs
echo ⚙️  Worker: 后台运行中
echo.
echo 关闭窗口即可停止服务
echo.
pause
