@echo off
chcp 65001 >nul 2>&1
title A股超短交易系统
color 0A

echo.
echo   A股超短交易实时监测系统 v2.4
echo.
echo   只需要Python，无需Node.js
echo.

cd /d "%~dp0"

:: ===== 检查Python =====
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [错误] 未找到Python！
    echo.
    echo   请安装Python:
    echo   1. 打开 https://www.python.org/downloads/
    echo   2. 下载 Python 3.10+
    echo   3. 安装时务必勾选 [Add Python to PATH]
    echo   4. 安装完成后重新双击本文件
    echo.
    pause
    exit
)

:: ===== 检查前端是否已构建 =====
if not exist frontend\dist\index.html (
    echo   [提示] 前端未构建，使用演示模式
    echo   （完整版需要Node.js构建前端，请运行 install.bat）
    echo.
)

:: ===== 检查后端依赖 =====
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo   [1/2] 正在安装后端依赖（首次运行，需要1-2分钟）...
    cd backend
    pip install -r requirements.txt
    if errorlevel 1 (
        echo   [错误] 依赖安装失败！
        echo   请将此窗口截图发给我
        pause
        exit
    )
    cd ..
    echo   依赖安装完成
    echo.
) else (
    echo   [1/2] 后端依赖已就绪
)

:: ===== 启动后端 =====
echo   [2/2] 正在启动系统...
echo.
cd backend
start "A股超短交易系统" cmd /k "python main.py"
cd ..
timeout /t 5 /nobreak >nul

:: ===== 打开浏览器 =====
start http://localhost:8000

echo.
echo   ========================================
echo     系统已启动！
echo     浏览器地址: http://localhost:8000
echo
echo     关闭 "A股超短交易系统" 窗口即可停止
echo   ========================================
echo.
echo   按任意键关闭此窗口...
pause >nul
