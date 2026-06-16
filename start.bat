@echo off
chcp 65001 >nul
echo ==========================================
echo    A股超短交易实时监测系统
echo ==========================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

:: 检查pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到pip，请检查Python安装
    pause
    exit /b 1
)

:: 安装依赖
echo [1/3] 正在安装后端依赖...
cd backend
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo [警告] 依赖安装可能有问题，尝试继续...
)
cd ..

:: 启动后端
echo [2/3] 正在启动后端服务...
start "A股超短交易-后端" cmd /k "cd backend && python main.py"

:: 等待后端启动
timeout /t 5 /nobreak >nul

:: 启动前端
echo [3/3] 正在启动前端界面...
start "A股超短交易-前端" cmd /k "cd frontend && npx vite --port 3000"

timeout /t 3 /nobreak >nul

:: 打开浏览器
echo.
echo ==========================================
echo    系统启动完成！
echo    正在打开浏览器...
echo ==========================================
start http://localhost:3000

echo.
echo 按任意键关闭所有服务...
pause >nul

:: 关闭进程
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1

echo 服务已关闭
