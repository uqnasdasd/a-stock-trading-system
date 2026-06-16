#!/bin/bash
# GitHub 部署脚本
# 使用方法：
# 1. 在 GitHub 创建空仓库（不要初始化 README）
# 2. 修改下面的 GITHUB_USER 和 REPO_NAME
# 3. 运行: bash deploy-to-github.sh

GITHUB_USER="你的GitHub用户名"
REPO_NAME="a-stock-trading-system"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "A股超短交易实时监测系统 - GitHub部署脚本"
echo "=========================================="
echo ""

# 检查 git
if ! command -v git &> /dev/null; then
    echo -e "${RED}错误: 未安装 git${NC}"
    exit 1
fi

# 检查是否修改了用户名
if [ "$GITHUB_USER" = "你的GitHub用户名" ]; then
    echo -e "${RED}请先在脚本中修改 GITHUB_USER 变量为你的GitHub用户名！${NC}"
    echo "编辑命令: nano deploy-to-github.sh"
    exit 1
fi

cd "$(dirname "$0")"

# 初始化 git（如果没有）
if [ ! -d .git ]; then
    git init
fi

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: A股超短交易实时监测系统 v1.0

核心功能:
- M1 竞价引擎 (9:15-9:25 板块强度/龙头评分)
- M2 开盘确认 (9:30-9:35 量比验证)
- M3 持仓监控 (龙头追踪/分时支撑)
- M4 清仓预警 (炸板检测/止盈止损)
- M8 风控中枢 (仓位/回撤/交易频率)
- 涨跌停监控 + 连板追踪
- 自选股管理
- K线图 + 分时图
- 概念板块轮动
- 龙虎榜数据
- 多股对比
- 策略回测
- 多账户管理
- 交易日志 + 复盘报告

技术栈: FastAPI + React + WebSocket + SQLite"

# 添加远程仓库
git remote remove origin 2>/dev/null
git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"

# 推送
echo ""
echo "正在推送到 GitHub..."
git push -u origin main || git push -u origin master

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}仓库地址: https://github.com/$GITHUB_USER/$REPO_NAME${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo "下一步: 部署到 Vercel"
echo "1. 访问 https://vercel.com"
echo "2. 点击 'Add New Project'"
echo "3. 导入刚才创建的 GitHub 仓库"
echo "4. 框架预设选择 'Other'"
echo "5. 构建命令留空，输出目录填: frontend/dist"
echo "6. 点击 Deploy"
