"""A股超短交易实时监测系统 - 后端入口"""
import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger
import sys

from app.api.routes import router, background_monitor_task
from app.core.database import init_db

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/trading_system.log", rotation="10 MB", retention="7 days", level="DEBUG")

# 前端静态文件目录
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")


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
    version="2.4",
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

# 注册API路由
app.include_router(router)

# 健康检查（必须在SPA fallback之前）
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

# 托管前端静态文件（如果存在）
if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """SPA fallback: 所有未匹配路径返回index.html"""
        file_path = os.path.join(FRONTEND_DIR, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
