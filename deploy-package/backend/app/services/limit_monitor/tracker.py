"""连板股追踪模块 - SQLite持久化存储"""
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from loguru import logger

from app.services.limit_monitor.monitor import limit_monitor
from app.core.database import (
    db_save_limit_tracker,
    db_get_limit_tracker,
    db_get_all_limit_trackers,
    db_reset_limit_tracker,
)


class LimitTracker:
    """连板股追踪器"""

    def __init__(self):
        # {code: {"name": str, "continuous_days": int, "last_limit_date": str, "history": list}}
        self._tracking: Dict[str, dict] = {}
        # 昨日涨停列表缓存（简化版，实际应从数据库获取）
        self._yesterday_limit_up: Dict[str, str] = {}  # {code: name}
        self._today_limit_up: Dict[str, str] = {}       # {code: name}
        self._last_scan_date: Optional[str] = None
        self._loaded = False

    async def _ensure_loaded(self):
        """确保从数据库加载"""
        if not self._loaded:
            await self.load_from_db()
            self._loaded = True

    async def load_from_db(self):
        """从数据库加载连板追踪数据"""
        rows = await db_get_all_limit_trackers(min_days=1)
        self._tracking = {}
        for row in rows:
            self._tracking[row["code"]] = {
                "name": row["name"],
                "continuous_days": row["continuous_days"],
                "last_limit_date": row["last_limit_date"],
                "history": row.get("history", []),
            }
        logger.info(f"从数据库加载 {len(self._tracking)} 条连板追踪数据")
        self._loaded = True

    def set_yesterday_limit_up(self, stocks: List[dict]):
        """设置昨日涨停列表（外部导入）"""
        self._yesterday_limit_up = {s["code"]: s.get("name", "") for s in stocks}
        logger.info(f"设置昨日涨停列表: {len(stocks)}只")

    async def update_today_limit_up(self, stocks: List[dict]):
        """更新今日涨停列表"""
        await self._ensure_loaded()
        self._today_limit_up = {s["code"]: s.get("name", "") for s in stocks}
        self._last_scan_date = date.today().isoformat()

        # 更新连板追踪
        await self._update_tracking()

    async def _update_tracking(self):
        """根据今日涨停数据更新连板统计"""
        for code, name in self._today_limit_up.items():
            if code in self._tracking:
                # 已在追踪列表中
                record = self._tracking[code]
                last_date = record["last_limit_date"]

                # 如果上次涨停是昨天，则连板天数+1
                if last_date == self._get_yesterday_date():
                    record["continuous_days"] += 1
                    record["last_limit_date"] = self._last_scan_date
                    record["history"].append({
                        "date": self._last_scan_date,
                        "days": record["continuous_days"],
                    })
                    logger.info(
                        f"连板更新: {name}({code}) 连续{record['continuous_days']}天涨停"
                    )
                elif last_date != self._last_scan_date:
                    # 连板中断，重新开始
                    record["continuous_days"] = 1
                    record["last_limit_date"] = self._last_scan_date
                    record["history"] = [{
                        "date": self._last_scan_date,
                        "days": 1,
                    }]
            else:
                # 新增追踪
                self._tracking[code] = {
                    "name": name,
                    "continuous_days": 1,
                    "last_limit_date": self._last_scan_date,
                    "history": [{
                        "date": self._last_scan_date,
                        "days": 1,
                    }],
                }

            # 保存到数据库
            record = self._tracking[code]
            await db_save_limit_tracker(
                code=code,
                name=record["name"],
                continuous_days=record["continuous_days"],
                last_limit_date=record["last_limit_date"],
                history=record["history"],
            )

        # 检查昨日涨停但今日未涨停的（连板中断）
        broken_codes = set(self._yesterday_limit_up.keys()) - set(self._today_limit_up.keys())
        for code in broken_codes:
            if code in self._tracking:
                record = self._tracking[code]
                if record["last_limit_date"] == self._get_yesterday_date():
                    logger.info(
                        f"连板中断: {record['name']}({code}) "
                        f"{record['continuous_days']}连板终止"
                    )

    def _get_yesterday_date(self) -> str:
        """获取昨日日期字符串"""
        yesterday = date.today()
        # 简化处理：直接减1天（实际应跳过周末）
        yesterday -= timedelta(days=1)
        return yesterday.isoformat()

    async def get_continuous_boards(self, min_days: int = 2) -> List[dict]:
        """获取连板股列表"""
        await self._ensure_loaded()
        result = []
        for code, record in self._tracking.items():
            if record["continuous_days"] >= min_days:
                result.append({
                    "code": code,
                    "name": record["name"],
                    "continuous_days": record["continuous_days"],
                    "last_limit_date": record["last_limit_date"],
                    "history": record["history"],
                })

        # 按连板天数倒序
        result.sort(key=lambda x: x["continuous_days"], reverse=True)
        return result

    async def get_stock_tracking(self, code: str) -> Optional[dict]:
        """获取单只股票的连板追踪"""
        await self._ensure_loaded()
        return self._tracking.get(code)

    async def get_summary(self) -> dict:
        """获取连板概览"""
        await self._ensure_loaded()
        boards = await self.get_continuous_boards(min_days=1)
        multi_boards = [b for b in boards if b["continuous_days"] >= 2]

        # 统计各连板天数数量
        days_count = {}
        for b in boards:
            days = b["continuous_days"]
            days_count[days] = days_count.get(days, 0) + 1

        return {
            "total_limit_up_today": len(self._today_limit_up),
            "total_tracking": len(self._tracking),
            "continuous_boards": multi_boards,
            "days_distribution": days_count,
            "last_scan_date": self._last_scan_date,
        }

    async def reset(self):
        """重置追踪数据（新交易日开始时调用）"""
        await self._ensure_loaded()
        # 将今日涨停移到昨日
        if self._last_scan_date != date.today().isoformat():
            self._yesterday_limit_up = self._today_limit_up.copy()
            self._today_limit_up = {}
            logger.info("连板追踪数据已重置，进入新交易日")


# 单例
limit_tracker = LimitTracker()
