@echo off
chcp 65001 >nul 2>&1
title A股超短交易系统 - 安装程序
color 0A

echo ╔══════════════════════════════════════════════╗
echo ║       A股超短交易实时监测系统 v2.3           ║
echo ║           一键安装程序                       ║
echo ╚══════════════════════════════════════════════╝
echo.

:: ====== 第1步：检查Python ======
echo [1/5] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ 未检测到Python！
    echo.
    echo 请先安装Python：
    echo 1. 打开浏览器访问 https://www.python.org/downloads/
    echo 2. 下载 Python 3.10 或更高版本
    echo 3. 安装时务必勾选 "Add Python to PATH"
    echo 4. 安装完成后重新运行此脚本
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo ✅ Python %PYVER% 已安装
echo.

:: ====== 第2步：检查Node.js ======
echo [2/5] 检查Node.js环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️ 未检测到Node.js，正在安装...
    echo.
    powershell -Command "Invoke-WebRequest -Uri 'https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi' -OutFile 'node_installer.msi'"
    msiexec /i node_installer.msi /quiet /norestart
    del node_installer.msi
    echo ✅ Node.js 安装完成
) else (
    for /f "tokens=1" %%v in ('node --version 2^>^&1') do echo ✅ Node.js %%v 已安装
)
echo.

:: ====== 第3步：安装后端依赖 ======
echo [3/5] 安装后端Python依赖...
cd /d "%~dp0"
cd backend
pip install -r requirements.txt --quiet 2>nul
if errorlevel 1 (
    echo ⚠️ 部分依赖安装失败，尝试修复...
    pip install -r requirements.txt 2>nul
)
cd ..
echo ✅ 后端依赖安装完成
echo.

:: ====== 第4步：安装前端依赖 ======
echo [4/5] 安装前端Node.js依赖...
cd frontend
if not exist node_modules (
    call npm install --silent 2>nul
    if errorlevel 1 (
        echo ⚠️ npm install 失败，尝试使用cnpm...
        call npm install -g cnpm --silent 2>nul
        call cnpm install --silent 2>nul
    )
) else (
    echo ✅ 前端依赖已存在，跳过安装
)
cd ..
echo.

:: ====== 第5步：构建前端 ======
echo [5/5] 构建前端页面...
cd frontend
call npx vite build 2>nul
if errorlevel 1 (
    echo ⚠️ 前端构建失败，将在首次启动时自动构建
)
cd ..
echo.

:: ====== 创建桌面快捷方式 ======
echo 正在创建桌面快捷方式...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\A股超短交易系统.lnk'); $sc.TargetPath = '%~dp0start.bat'; $sc.WorkingDirectory = '%~dp0'; $sc.Description = 'A股超短交易实时监测系统'; $sc.Save()"
echo ✅ 桌面快捷方式已创建
echo.

:: ====== 安装完成 ======
echo ╔══════════════════════════════════════════════╗
echo ║           安装完成！                         ║
echo ╠══════════════════════════════════════════════╣
echo ║                                              ║
echo ║  启动方式：                                  ║
echo ║  1. 双击桌面快捷方式 "A股超短交易系统"       ║
echo ║  2. 或双击 start.bat                        ║
echo ║                                              ║
echo ║  启动后浏览器会自动打开                      ║
echo ║  如未打开，请手动访问 http://localhost:3000   ║
echo ║                                              ║
echo ╚══════════════════════════════════════════════╝
echo.
pause
