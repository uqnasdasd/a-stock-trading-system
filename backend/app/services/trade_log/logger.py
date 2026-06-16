"""交易日志模块 - SQLite持久化存储"""
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from app.core.database import (
    db_add_trade_log,
    db_get_trade_logs,
    db_get_trade_log_stats,
)


class TradeLogger:
    """交易日志记录器"""

    def __init__(self):
        # 交易记录列表（内存缓存）
        self._logs: List[dict] = []
        # 最大记录数（防止内存溢出）
        self._max_logs: int = 1000
        self._loaded = False

    async def _ensure_loaded(self):
        """确保从数据库加载"""
        if not self._loaded:
            await self.load_from_db()
            self._loaded = True

    async def load_from_db(self):
        """从数据库加载最近的交易日志到内存缓存"""
        result = await db_get_trade_logs(limit=self._max_logs)
        self._logs = list(reversed(result.get("logs", [])))
        logger.info(f"从数据库加载 {len(self._logs)} 条交易日志")

    async def add_log(
        self,
        code: str,
        name: str,
        action: str,
        price: float,
        volume: int,
        reason: str = "",
    ) -> dict:
        """添加交易日志

        Args:
            code: 股票代码
            name: 股票名称
            action: 操作类型 (buy/sell/cancel)
            price: 价格
            volume: 数量
            reason: 操作原因
        """
        log_time = datetime.now().isoformat()
        log_entry = {
            "time": log_time,
            "code": code,
            "name": name,
            "action": action,
            "price": price,
            "volume": volume,
            "reason": reason,
        }

        self._logs.append(log_entry)

        # 超出最大记录数时，移除最早的记录
        if len(self._logs) > self._max_logs:
            self._logs = self._logs[-self._max_logs:]

        # 写入数据库
        await db_add_trade_log(
            code=code,
            name=name,
            action=action,
            price=price,
            volume=volume,
            reason=reason,
            time=log_time,
        )

        logger.info(
            f"交易日志: [{action}] {name}({code}) "
            f"{volume}股 @ {price:.2f} - {reason}"
        )

        return log_entry

    async def get_logs(
        self,
        code: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """获取交易日志

        Args:
            code: 按股票代码筛选
            action: 按操作类型筛选
            limit: 返回条数
            offset: 偏移量
        """
        # 优先从数据库查询
        return await db_get_trade_logs(code=code, action=action, limit=limit, offset=offset)

    async def get_today_logs(self) -> List[dict]:
        """获取今日交易日志"""
        today = datetime.now().date().isoformat()
        return [
            l for l in self._logs
            if l["time"].startswith(today)
        ]

    async def get_stats(self) -> dict:
        """获取交易统计"""
        return await db_get_trade_log_stats()

    async def clear(self) -> dict:
        """清空交易日志（仅内存缓存，数据库保留）"""
        count = len(self._logs)
        self._logs.clear()
        logger.info(f"清空交易日志内存缓存，共{count}条")
        return {
            "status": "success",
            "message": f"已清空交易日志内存缓存，共{count}条",
        }


# 单例
trade_logger = TradeLogger()
