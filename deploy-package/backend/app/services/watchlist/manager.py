"""自选股管理模块 - SQLite持久化存储"""
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from app.core.database import (
    db_add_watchlist,
    db_remove_watchlist,
    db_get_watchlist,
)


class WatchlistManager:
    """自选股管理器"""

    def __init__(self):
        self._watchlist: Dict[str, dict] = {}
        self._loaded = False

    async def _ensure_loaded(self):
        """确保从数据库加载"""
        if not self._loaded:
            await self.load_from_db()
            self._loaded = True

    async def load_from_db(self):
        """从数据库加载自选股"""
        rows = await db_get_watchlist()
        self._watchlist = {}
        for row in rows:
            self._watchlist[row["code"]] = {
                "code": row["code"],
                "name": row["name"],
                "add_time": row["add_time"],
            }
        logger.info(f"从数据库加载 {len(self._watchlist)} 条自选股")

    async def add(self, code: str, name: str) -> dict:
        """添加自选股"""
        await self._ensure_loaded()
        code = code.strip().lower()
        if code in self._watchlist:
            return {
                "status": "exists",
                "message": f"{name}({code}) 已在自选股列表中",
                "stock": self._watchlist[code],
            }

        result = await db_add_watchlist(code, name)
        if result["status"] == "success":
            stock = {
                "code": code,
                "name": name,
                "add_time": result.get("add_time", datetime.now().isoformat()),
            }
            self._watchlist[code] = stock
            logger.info(f"添加自选股: {name}({code})")
            return {
                "status": "success",
                "message": f"已添加自选股: {name}({code})",
                "stock": stock,
            }
        return result

    async def remove(self, code: str) -> dict:
        """删除自选股"""
        await self._ensure_loaded()
        code = code.strip().lower()
        if code not in self._watchlist:
            return {
                "status": "not_found",
                "message": f"{code} 不在自选股列表中",
            }

        removed = self._watchlist.pop(code)
        await db_remove_watchlist(code)
        logger.info(f"删除自选股: {removed['name']}({code})")
        return {
            "status": "success",
            "message": f"已删除自选股: {removed['name']}({code})",
            "stock": removed,
        }

    async def get_all(self) -> dict:
        """获取所有自选股"""
        await self._ensure_loaded()
        stocks = list(self._watchlist.values())
        # 按添加时间倒序
        stocks.sort(key=lambda x: x["add_time"], reverse=True)
        return {
            "count": len(stocks),
            "stocks": stocks,
        }

    async def get_codes(self) -> List[str]:
        """获取所有自选股代码"""
        await self._ensure_loaded()
        return list(self._watchlist.keys())

    async def contains(self, code: str) -> bool:
        """检查是否在自选股中"""
        await self._ensure_loaded()
        return code.strip().lower() in self._watchlist

    async def clear(self) -> dict:
        """清空自选股"""
        await self._ensure_loaded()
        count = len(self._watchlist)
        for code in list(self._watchlist.keys()):
            await db_remove_watchlist(code)
        self._watchlist.clear()
        logger.info(f"清空自选股列表，共{count}只")
        return {
            "status": "success",
            "message": f"已清空自选股列表，共{count}只",
        }


# 单例
watchlist_manager = WatchlistManager()
