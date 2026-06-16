@echo off
chcp 65001 >nul 2>&1
title A股超短交易系统
color 0A

echo.
echo   A股超短交易实时监测系统 v2.4
echo   正在启动...
echo.

cd /d "%~dp0"

:: ===== 检查Python =====
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python！
    echo 请先安装Python: https://www.python.org/downloads/
    echo 安装时务必勾选 "Add Python to PATH"
    echo.
    pause
    exit
)

:: ===== 检查后端依赖 =====
echo [1/3] 检查后端依赖...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo 后端依赖未安装，正在安装...
    cd backend
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 后端依赖安装失败！
        echo 请截图此窗口发给我
        pause
        exit
    )
    cd ..
    echo 后端依赖安装完成
)

:: ===== 检查前端依赖 =====
echo [2/3] 检查前端依赖...
if not exist frontend\node_modules\vite (
    echo 前端依赖未安装，正在安装（可能需要几分钟）...
    cd frontend
    call npm install
    if errorlevel 1 (
        echo [错误] 前端依赖安装失败！
        echo 请确认已安装Node.js: https://nodejs.org/
        pause
        exit
    )
    cd ..
    echo 前端依赖安装完成
)

:: ===== 启动后端 =====
echo [3/3] 启动服务...
echo.
echo 正在启动后端（新窗口）...
cd backend
start "A股后端" cmd /k "python main.py 2>&1"
cd ..
echo 等待后端启动（8秒）...
timeout /t 8 /nobreak >nul

:: 检查后端
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo.
    echo [警告] 后端可能启动失败
    echo 请查看 "A股后端" 窗口中的错误信息
    echo 如果提示缺少模块，请在该窗口中运行: pip install 模块名
    echo.
) else (
    echo 后端启动成功！
)

:: ===== 启动前端 =====
echo 正在启动前端...
cd frontend
start "A股前端" cmd /k "npx vite --port 3000"
cd ..
timeout /t 5 /nobreak >nul

:: ===== 打开浏览器 =====
echo 正在打开浏览器...
start http://localhost:3000

echo.
echo ========================================
echo   系统已启动！
echo   浏览器地址: http://localhost:3000
echo
echo   关闭方式:
echo   - 关闭 "A股后端" 窗口
echo   - 关闭 "A股前端" 窗口
echo   - 或直接关闭本窗口
echo ========================================
echo.
pause
