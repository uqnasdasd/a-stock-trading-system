# A股超短交易实时监测系统 - 部署说明

## 系统架构

- **Backend**: FastAPI + Python 3.11（端口 8000）
- **Frontend**: React + Nginx（端口 80）
- **Redis**: 缓存服务（端口 6379）
- **Database**: SQLite（持久化存储）

## 快速部署（Docker Compose）

### 前置要求

- Docker >= 20.10
- Docker Compose >= 2.0
- 开放端口: 80（前端）、8000（后端）、6379（Redis）

### 部署步骤

1. 解压部署包

```bash
unzip a-stock-trading-system-deploy.zip
cd deploy-package
```

2. 启动服务

```bash
docker-compose up -d --build
```

3. 查看服务状态

```bash
docker-compose ps
docker-compose logs -f backend
```

4. 访问系统

- 前端界面: http://localhost
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

### 停止服务

```bash
docker-compose down
```

### 完全清理（包括数据卷）

```bash
docker-compose down -v
```

## 环境变量配置

可通过以下方式配置环境变量：

### 方式一：docker-compose.yml 中直接修改

编辑 `docker-compose.yml` 中的 `environment` 部分。

### 方式二：使用 .env 文件

在项目根目录创建 `.env` 文件：

```env
# Redis 配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# 数据库配置
DATABASE_URL=sqlite:///./data/trading_system.db

# 告警推送（可选）
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
WECHAT_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx

# 数据源配置
DATA_SOURCE_PRIMARY=sina
DATA_SOURCE_BACKUP=tencent
POLL_INTERVAL=3
```

### 方式三：命令行传入

```bash
DINGTALK_WEBHOOK=xxx WECHAT_WEBHOOK=xxx docker-compose up -d
```

## 配置说明

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| REDIS_HOST | redis | Redis 主机地址（Docker 内使用服务名） |
| REDIS_PORT | 6379 | Redis 端口 |
| REDIS_DB | 0 | Redis 数据库编号 |
| DATABASE_URL | sqlite:///./data/trading_system.db | SQLite 数据库路径 |
| DINGTALK_WEBHOOK | - | 钉钉机器人 Webhook（可选） |
| WECHAT_WEBHOOK | - | 企业微信机器人 Webhook（可选） |
| DATA_SOURCE_PRIMARY | sina | 主要数据源 |
| DATA_SOURCE_BACKUP | tencent | 备用数据源 |
| POLL_INTERVAL | 3 | 数据轮询间隔（秒） |

## 目录结构

```
deploy-package/
├── backend/              # 后端代码
│   ├── app/             # 应用模块
│   ├── main.py          # 入口文件
│   ├── requirements.txt # Python 依赖
│   ├── Dockerfile       # 后端镜像构建
│   └── .env             # 环境变量模板
├── frontend/
│   └── dist/            # 前端构建产物（静态文件）
├── docker-compose.yml   # Docker Compose 配置
├── nginx.conf           # Nginx 反向代理配置
└── README-deploy.md     # 本文件
```

## 数据持久化

- **SQLite 数据库**: 挂载到 `./backend/data/` 目录
- **日志文件**: 挂载到 `./backend/logs/` 目录
- **Redis 数据**: 使用 Docker Volume `redis_data`

## 常见问题

### 1. 前端无法连接后端

检查 nginx.conf 中的 proxy_pass 配置是否正确，确保 backend 服务名可解析。

### 2. WebSocket 连接失败

确保 Nginx 配置中已正确配置 WebSocket 代理（Upgrade 和 Connection 头）。

### 3. 数据源获取失败

系统依赖外部股票数据 API（新浪、东方财富等），请确保部署服务器可以访问以下域名：
- hq.sinajs.cn
- money.finance.sina.com.cn
- vip.stock.finance.sina.com.cn
- datacenter-web.eastmoney.com

### 4. 修改配置后生效

```bash
docker-compose down
docker-compose up -d
```

## 手动部署（非 Docker）

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 前端

将 `frontend/dist` 目录下的文件部署到任意 Web 服务器（Nginx、Apache、Caddy 等）。

注意：需要配置反向代理，将 `/api` 和 `/ws` 请求转发到后端 8000 端口。

## 技术支持

如有问题，请查看后端日志：

```bash
docker-compose logs -f backend
```
