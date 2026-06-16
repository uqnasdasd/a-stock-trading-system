@echo off
chcp 65001 >nul 2>&1
title A股超短交易系统 - 更新程序
color 0B

echo ╔══════════════════════════════════════════════╗
echo ║       A股超短交易系统 - 更新程序              ║
echo ╚══════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: 拉取最新代码
echo [1/3] 正在拉取最新代码...
git pull origin master
if errorlevel 1 (
    echo ❌ 更新失败！请检查网络连接
    pause
    exit /b 1
)
echo ✅ 代码已更新
echo.

:: 安装新依赖
echo [2/3] 检查新依赖...
cd backend
pip install -r requirements.txt --quiet 2>nul
cd ..
cd frontend
call npm install --silent 2>nul
cd ..
echo ✅ 依赖检查完成
echo.

:: 重新构建前端
echo [3/3] 重新构建前端...
cd frontend
call npx vite build 2>nul
cd ..
echo ✅ 前端构建完成
echo.

echo ╔══════════════════════════════════════════════╗
echo ║  更新完成！请重新运行 start.bat 启动系统     ║
echo ╚══════════════════════════════════════════════╝
echo.
pause
