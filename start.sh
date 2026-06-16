#!/bin/bash
# A股超短交易实时监测系统 - 一键启动脚本

echo "=========================================="
echo "   A股超短交易实时监测系统"
echo "=========================================="
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3，请先安装Python 3.10+"
    exit 1
fi

# 检查pip
if ! command -v pip3 &> /dev/null; then
    echo "[错误] 未找到pip3，请检查Python安装"
    exit 1
fi

# 安装依赖
echo "[1/3] 正在安装后端依赖..."
cd backend
pip3 install -r requirements.txt > /dev/null 2>&1
cd ..

# 启动后端
echo "[2/3] 正在启动后端服务..."
cd backend
nohup python3 main.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# 等待后端启动
sleep 5

# 检查后端是否启动成功
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "[警告] 后端启动可能有问题，查看 logs/backend.log"
fi

# 启动前端
echo "[3/3] 正在启动前端界面..."
cd frontend
nohup npx vite --port 3000 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

sleep 3

echo ""
echo "=========================================="
echo "   系统启动完成！"
echo "   请打开浏览器访问: http://localhost:3000"
echo "=========================================="
echo ""
echo "后端PID: $BACKEND_PID"
echo "前端PID: $FRONTEND_PID"
echo ""
echo "按回车键关闭所有服务..."
read

# 关闭进程
kill $BACKEND_PID 2>/dev/null
kill $FRONTEND_PID 2>/dev/null

echo "服务已关闭"
