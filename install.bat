@echo off
chcp 65001 >nul 2>&1
title A股超短交易系统 - 安装程序
color 0A

echo ╔══════════════════════════════════════════════╗
echo ║       A股超短交易实时监测系统 v2.3           ║
echo ║           一键安装程序                       ║
echo ╚══════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

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
    echo 3. 安装时务必勾选 "Add Python to PATH"  ← 这一步很重要！
    echo 4. 安装完成后，关闭所有窗口，重新双击 install.bat
    echo.
    echo 按任意键退出...
    pause >nul
    exit
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo ✅ Python %PYVER% 已安装
echo.

:: ====== 第2步：检查pip ======
echo [2/5] 检查pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️ pip未找到，尝试安装...
    python -m ensurepip --default-pip
    if errorlevel 1 (
        echo ❌ pip安装失败，请重新安装Python并勾选pip选项
        echo 按任意键退出...
        pause >nul
        exit
    )
)
echo ✅ pip 已就绪
echo.

:: ====== 第3步：安装后端依赖 ======
echo [3/5] 安装后端Python依赖（可能需要1-2分钟）...
if exist backend\requirements.txt (
    cd backend
    pip install -r requirements.txt 2>&1
    cd ..
    echo ✅ 后端依赖安装完成
) else (
    echo ❌ 找不到 backend\requirements.txt
    echo 请确认解压后的文件夹结构正确
    echo 文件夹内应该有 backend 和 frontend 两个子文件夹
)
echo.

:: ====== 第4步：检查Node.js ======
echo [4/5] 检查Node.js环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️ 未检测到Node.js
    echo.
    echo 请安装Node.js：
    echo 1. 打开 https://nodejs.org/
    echo 2. 下载 LTS 版本（左边那个）
    echo 3. 安装时一路默认即可
    echo 4. 安装完成后关闭所有窗口，重新双击 install.bat
    echo.
    echo 按任意键退出...
    pause >nul
    exit
)
for /f "tokens=1" %%v in ('node --version 2^>^&1') do echo ✅ Node.js %%v 已安装
echo.

:: ====== 第5步：安装前端依赖并构建 ======
echo [5/5] 安装前端依赖并构建（可能需要1-2分钟）...
if exist frontend\package.json (
    cd frontend
    call npm install 2>&1
    echo.
    echo 正在构建前端页面...
    call npx vite build 2>&1
    cd ..
    echo ✅ 前端构建完成
) else (
    echo ❌ 找不到 frontend\package.json
    echo 请确认解压后的文件夹结构正确
)
echo.

:: ====== 创建桌面快捷方式 ======
echo 正在创建桌面快捷方式...
powershell -Command "try { $ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\A股超短交易系统.lnk'); $sc.TargetPath = '%~dp0start.bat'; $sc.WorkingDirectory = '%~dp0'; $sc.Description = 'A股超短交易实时监测系统'; $sc.Save(); Write-Host '✅ 桌面快捷方式已创建' } catch { Write-Host '⚠️ 快捷方式创建失败' }"
echo.

:: ====== 安装完成 ======
echo.
echo ╔══════════════════════════════════════════════╗
echo ║           ✅ 安装完成！                      ║
echo ╠══════════════════════════════════════════════╣
echo ║                                              ║
echo ║  启动方式：                                  ║
echo ║  → 双击桌面 "A股超短交易系统" 快捷方式       ║
echo ║  → 或双击 start.bat                         ║
echo ║                                              ║
echo ║  启动后浏览器会自动打开                      ║
echo ║  如未打开，手动访问 http://localhost:3000     ║
echo ║                                              ║
echo ╚══════════════════════════════════════════════╝
echo.
echo 按任意键关闭...
pause >nul
