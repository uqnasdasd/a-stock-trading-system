@echo off
chcp 65001 >nul 2>&1
title A股超短交易系统
color 0A

echo ╔══════════════════════════════════════════════╗
echo ║       A股超短交易实时监测系统 v2.3           ║
echo ║           正在启动...                        ║
echo ╚══════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: 检查是否首次运行（需要安装依赖）
if not exist backend\__pycache__ (
    echo 首次运行，正在安装依赖...
    call install.bat
    echo.
)

:: 启动后端
echo [1/2] 启动后端服务...
cd backend
start "A股超短交易-后端" /min cmd /c "python main.py 2>&1 | more"
cd ..
timeout /t 5 /nobreak >nul

:: 启动前端
echo [2/2] 启动前端界面...
cd frontend
start "A股超短交易-前端" /min cmd /c "npx vite --port 3000 --open"
cd ..

timeout /t 3 /nobreak >nul

echo.
echo ╔══════════════════════════════════════════════╗
echo ║  系统已启动！浏览器将自动打开               ║
echo ║  如未打开，请访问: http://localhost:3000     ║
echo ║                                              ║
echo ║  关闭此窗口将停止所有服务                    ║
echo ╚══════════════════════════════════════════════╝
echo.
echo 按任意键关闭系统...
pause >nul

:: 关闭所有服务
taskkill /f /fi "WINDOWTITLE eq A股超短交易-后端" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq A股超短交易-前端" >nul 2>&1
echo 系统已关闭
