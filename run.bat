@echo off
chcp 65001 >nul 2>&1
title A股超短交易系统
color 0A

echo.
echo   正在启动A股超短交易系统...
echo   首次运行需要安装依赖，请等待1-2分钟
echo.

cd /d "%~dp0"

python trading_system.py

if errorlevel 1 (
    echo.
    echo   启动失败！可能原因：
    echo   1. 未安装Python - 请先安装 https://www.python.org/downloads/
    echo   2. 未勾选 Add Python to PATH - 重新安装Python并勾选
    echo.
)

pause
