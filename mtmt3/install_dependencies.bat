@echo off
chcp 65001 >nul
echo ========================================
echo 安装项目依赖
echo ========================================
echo.
cd /d %~dp0backend
echo 正在安装依赖包...
echo.
pip install -r requirements.txt
echo.
echo ========================================
echo ✅ 依赖安装完成！
echo ========================================
pause
