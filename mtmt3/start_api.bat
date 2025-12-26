@echo off
chcp 65001 >nul
echo ========================================
echo 启动FastAPI服务器
echo ========================================
cd /d %~dp0
python -m uvicorn backend.main:app --reload --port 8000
pause
