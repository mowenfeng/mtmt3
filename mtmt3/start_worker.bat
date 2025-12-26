@echo off
chcp 65001 >nul
echo ========================================
echo 启动后台Worker
echo ========================================
cd /d %~dp0
python -m backend.worker
pause
