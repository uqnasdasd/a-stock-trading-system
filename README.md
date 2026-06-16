# A股超短交易实时监测系统

融合4篇"论道至简"短线交易教程操作模式的可执行程序软件。

## 核心功能模块

| 模块 | 功能 | 对应教程 |
|------|------|----------|
| M1 竞价引擎 | 9:15-9:25 板块强度/龙头评分/情绪晴雨表 | 竞价选股 |
| M2 开盘确认 | 9:30-9:35 板块持续性/量比验证 | 竞价选股 |
| M3 持仓监控 | 龙头追踪/分时支撑/量价关系 | 持仓判断 |
| M4 清仓预警 | 炸板检测/量价背离/止盈止损 | 持仓判断 |
| M8 风控中枢 | 仓位/回撤/交易频率/隔夜风控 | 超短交易系统 |

## 技术栈

- **后端**: FastAPI + Python 3.11 + WebSocket
- **前端**: React 18 + TypeScript + Vite
- **数据**: 新浪财经API（免费实时行情）
- **部署**: Docker Compose

## 快速启动

### 方式一：本地开发启动

```bash
# 1. 启动后端
cd backend
pip install -r requirements.txt
python main.py
# 后端运行在 http://localhost:8000

# 2. 启动前端（新终端）
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

### 方式二：Docker Compose 部署

```bash
# 1. 配置环境变量（可选）
cp backend/.env.example backend/.env
# 编辑 .env 填入钉钉/企微Webhook地址

# 2. 启动全部服务
docker-compose up -d

# 3. 访问前端
open http://localhost:5173
```

## 系统界面

- **顶部**: 大盘指数栏（上证/深证/创业板/沪深300/中证500）
- **左侧Tab**: 竞价引擎 / 持仓监控 / 信号列表
- **右侧**: 风控中心面板

## 风控规则（硬编码）

| 规则 | 阈值 | 触发动作 |
|------|------|----------|
| 单票仓位 | ≤ 10% | 超限告警 |
| 总仓位 | ≤ 50% | 禁止开新仓 |
| 止损线 | -2% ~ -3% | 立即清仓 |
| 止盈线 | +4% ~ +6% | 减仓50% |
| 单日回撤 | ≥ 3% | 当日停手 |
| 周度回撤 | ≥ 5% | 暂停1-2天 |
| 交易频率 | 日≤2次 / 周≤5次 | 超限禁止交易 |
| 隔夜风控 | 非涨停股 | 收盘前清仓 |

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/market/indices` | GET | 大盘指数 |
| `/api/auction/analyze` | POST | 竞价分析 |
| `/api/positions` | GET/POST/DELETE | 持仓管理 |
| `/api/risk/status` | GET | 风控状态 |
| `/api/signals` | GET | 信号列表 |
| `/ws` | WebSocket | 实时数据推送 |

## 配置文件

编辑 `backend/.env`：

```env
# 告警推送（可选）
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
WECHAT_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx

# 风控参数
MAX_SINGLE_POSITION=0.10
MAX_TOTAL_POSITION=0.50
STOP_LOSS_PCT=0.03
TAKE_PROFIT_PCT=0.05
DAILY_MAX_LOSS=0.03
WEEKLY_MAX_LOSS=0.05
MAX_TRADES_PER_DAY=2
MAX_TRADES_PER_WEEK=5
```

## 项目结构

```
a-stock-trading-system/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/routes.py         # API路由 + WebSocket
│   │   ├── core/config.py        # 配置管理
│   │   ├── models/schemas.py     # 数据模型
│   │   └── services/
│   │       ├── auction_engine/   # M1 竞价引擎
│   │       ├── position_monitor/ # M3+M4 持仓监控
│   │       ├── risk_control/     # M8 风控中枢
│   │       ├── alert_push/       # 告警推送
│   │       └── data_collector/   # 数据采集
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/             # React 前端
│   ├── src/
│   │   ├── components/   # 面板组件
│   │   ├── pages/        # Dashboard
│   │   └── hooks/        # WebSocket Hook
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
└── README.md
```

## 免责声明

本系统仅供学习研究使用，不构成任何投资建议。股市有风险，投资需谨慎。
