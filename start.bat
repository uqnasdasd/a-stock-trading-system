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

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python！请先运行 install.bat 安装依赖
    echo.
    echo 按任意键退出...
    pause >nul
    exit
)

:: 检查Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Node.js！请先运行 install.bat 安装依赖
    echo.
    echo 按任意键退出...
    pause >nul
    exit
)

:: 检查前端是否已构建
if not exist frontend\dist\index.html (
    echo ⚠️ 前端未构建，正在构建...
    cd frontend
    call npx vite build 2>&1
    cd ..
    echo ✅ 前端构建完成
    echo.
)

:: 启动后端
echo [1/2] 启动后端服务...
cd backend
start "A股超短交易-后端" /min cmd /c "python main.py"
cd ..
echo 等待后端启动...
timeout /t 5 /nobreak >nul

:: 检查后端是否启动成功
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo ⚠️ 后端可能启动失败，但继续尝试启动前端...
) else (
    echo ✅ 后端启动成功
)
echo.

:: 启动前端
echo [2/2] 启动前端界面...
cd frontend
start "A股超短交易-前端" cmd /c "npx vite --port 3000 --open"
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
timeout /t 2 /nobreak >nul
