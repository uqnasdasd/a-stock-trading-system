"""A股超短交易实时监测系统 - 后端入口"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from app.api.routes import router, background_monitor_task
from app.core.database import init_db

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/trading_system.log", rotation="10 MB", retention="7 days", level="DEBUG")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("=" * 50)
    logger.info("A股超短交易实时监测系统启动")
    logger.info("=" * 50)

    # 初始化数据库
    await init_db()

    # 启动后台监控任务
    monitor_task = asyncio.create_task(background_monitor_task())

    yield

    # 关闭时清理
    monitor_task.cancel()
    logger.info("系统关闭")


app = FastAPI(
    title="A股超短交易实时监测系统",
    description="融合竞价选股/持仓判断/突破主升/超短交易的综合实时监测平台",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "A股超短交易实时监测系统",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
