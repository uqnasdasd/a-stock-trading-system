"""历史数据回放引擎"""
import json
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from loguru import logger

from app.services.data_collector.sina_api import collector


@dataclass
class ReplayParams:
    """回放参数"""
    code: str = "sh000001"
    date: str = "2024-01-15"       # 回放日期
    speed: float = 1.0             # 倍速 1x/2x/5x/10x
    include_auction: bool = True   # 是否包含竞价阶段


@dataclass
class ReplayTick:
    """回放Tick数据"""
    time: str
    phase: str                     # auction / open / intraday / close
    price: float
    open: float
    high: float
    low: float
    volume: int
    amount: float
    change_pct: float = 0.0
    avg_price: float = 0.0
    signals: List[str] = field(default_factory=list)


@dataclass
class ReplayReport:
    """复盘报告"""
    code: str
    name: str
    date: str
    total_ticks: int
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    total_volume: int
    total_amount: float
    change_pct: float
    amplitude: float
    key_signals: List[str]
    phase_summary: Dict


class HistoryReplayEngine:
    """历史数据回放引擎"""

    def __init__(self):
        self.params: Optional[ReplayParams] = None
        self.ticks: List[ReplayTick] = []
        self.current_index: int = 0
        self.is_playing: bool = False
        self.name: str = ""
        self._task: Optional[asyncio.Task] = None
        self._listeners: List[callable] = []

    async def load_day_data(self, params: ReplayParams) -> Dict:
        """加载指定日期的历史数据"""
        self.params = params
        self.ticks = []
        self.current_index = 0
        self.is_playing = False

        code = params.code.strip().lower()
        if not code.startswith(("sh", "sz", "bj")):
            if code.startswith("6"):
                code = "sh" + code
            elif code.startswith(("0", "3")):
                code = "sz" + code
            elif code.startswith("8"):
                code = "bj" + code

        # 获取分时数据（1分钟K线模拟）
        kline = await collector.get_kline(code, scale=1, datalen=240)
        if not kline:
            logger.warning(f"未获取到历史数据: {code} {params.date}")
            return {"success": False, "message": "未获取到数据"}

        # 获取股票名称
        quotes = await collector.get_quotes([code])
        self.name = quotes[code].name if code in quotes else code

        # 过滤指定日期（day字段格式: "2024-01-15 09:30:00"）
        date_prefix = params.date
        day_kline = [item for item in kline if item["day"].startswith(date_prefix)]

        if not day_kline:
            # 如果指定日期没有数据，使用全部数据作为演示
            day_kline = kline[:240]
            logger.info(f"指定日期无数据，使用最近数据演示: {code}")

        pre_close = day_kline[0]["open"] if day_kline else 0

        for item in day_kline:
            time_str = item["day"].split(" ")[1] if " " in item["day"] else item["day"]
            hour = int(time_str.split(":")[0])
            minute = int(time_str.split(":")[1])

            # 判断交易阶段
            if hour == 9 and minute < 30:
                phase = "auction"
            elif hour == 9 and minute == 30:
                phase = "open"
            elif hour == 14 and minute >= 55:
                phase = "close"
            else:
                phase = "intraday"

            price = item["close"]
            change_pct = round((price - pre_close) / pre_close * 100, 2) if pre_close > 0 else 0
            avg_price = round((item["open"] + item["high"] + item["low"] + item["close"]) / 4, 2)

            # 生成信号
            signals = []
            if phase == "open" and change_pct > 2:
                signals.append("开盘强势")
            if phase == "intraday" and item["high"] == price and change_pct > 5:
                signals.append("盘中冲高")
            if phase == "close" and change_pct > 7:
                signals.append("尾盘拉升")
            if item["volume"] > 0 and item["volume"] < 100:
                signals.append("量能萎缩")

            self.ticks.append(ReplayTick(
                time=time_str,
                phase=phase,
                price=price,
                open=item["open"],
                high=item["high"],
                low=item["low"],
                volume=item["volume"],
                amount=round(price * item["volume"], 2),
                change_pct=change_pct,
                avg_price=avg_price,
                signals=signals,
            ))

        logger.info(f"历史回放数据加载完成: {code} {self.name}, 共 {len(self.ticks)} 个Tick")
        return {
            "success": True,
            "code": code,
            "name": self.name,
            "date": params.date,
            "total_ticks": len(self.ticks),
        }

    def get_current_tick(self) -> Optional[Dict]:
        """获取当前Tick"""
        if 0 <= self.current_index < len(self.ticks):
            tick = self.ticks[self.current_index]
            return {
                "index": self.current_index,
                "time": tick.time,
                "phase": tick.phase,
                "price": tick.price,
                "open": tick.open,
                "high": tick.high,
                "low": tick.low,
                "volume": tick.volume,
                "amount": tick.amount,
                "change_pct": tick.change_pct,
                "avg_price": tick.avg_price,
                "signals": tick.signals,
            }
        return None

    def get_all_ticks(self) -> List[Dict]:
        """获取所有Tick数据"""
        return [
            {
                "time": t.time,
                "phase": t.phase,
                "price": t.price,
                "volume": t.volume,
                "change_pct": t.change_pct,
                "signals": t.signals,
            }
            for t in self.ticks
        ]

    async def play(self, callback: Optional[callable] = None):
        """开始回放"""
        if self.is_playing:
            return
        self.is_playing = True

        speed = self.params.speed if self.params else 1.0
        # 1分钟数据，每tick间隔 60秒 / speed
        interval = 60.0 / speed / 10  # 每tick 0.1分钟数据

        while self.is_playing and self.current_index < len(self.ticks):
            tick_data = self.get_current_tick()
            if tick_data and callback:
                await callback(tick_data)
            self.current_index += 1
            await asyncio.sleep(interval)

        self.is_playing = False
        logger.info("历史回放结束")

    def pause(self):
        """暂停回放"""
        self.is_playing = False

    def resume(self):
        """恢复回放"""
        if not self.is_playing and self.current_index < len(self.ticks):
            asyncio.create_task(self.play())

    def stop(self):
        """停止回放"""
        self.is_playing = False
        self.current_index = 0

    def set_speed(self, speed: float):
        """设置回放速度"""
        if self.params:
            self.params.speed = speed

    def seek(self, index: int):
        """跳转到指定位置"""
        if 0 <= index < len(self.ticks):
            self.current_index = index

    def generate_report(self) -> ReplayReport:
        """生成复盘报告"""
        if not self.ticks:
            return ReplayReport(
                code=self.params.code if self.params else "",
                name=self.name,
                date=self.params.date if self.params else "",
                total_ticks=0,
                open_price=0,
                close_price=0,
                high_price=0,
                low_price=0,
                total_volume=0,
                total_amount=0,
                change_pct=0,
                amplitude=0,
                key_signals=[],
                phase_summary={},
            )

        prices = [t.price for t in self.ticks]
        volumes = [t.volume for t in self.ticks]
        open_price = self.ticks[0].price if self.ticks else 0
        close_price = self.ticks[-1].price if self.ticks else 0
        high_price = max(t.high for t in self.ticks) if self.ticks else 0
        low_price = min(t.low for t in self.ticks) if self.ticks else 0
        total_volume = sum(volumes)
        total_amount = sum(t.amount for t in self.ticks)
        change_pct = round((close_price - open_price) / open_price * 100, 2) if open_price > 0 else 0
        amplitude = round((high_price - low_price) / open_price * 100, 2) if open_price > 0 else 0

        # 收集所有信号
        all_signals = []
        for t in self.ticks:
            all_signals.extend(t.signals)
        key_signals = list(set(all_signals))

        # 阶段统计
        phase_summary = {}
        for phase in ["auction", "open", "intraday", "close"]:
            phase_ticks = [t for t in self.ticks if t.phase == phase]
            if phase_ticks:
                phase_summary[phase] = {
                    "tick_count": len(phase_ticks),
                    "volume": sum(t.volume for t in phase_ticks),
                    "amount": round(sum(t.amount for t in phase_ticks), 2),
                    "price_change": round(phase_ticks[-1].price - phase_ticks[0].price, 2),
                }

        return ReplayReport(
            code=self.params.code if self.params else "",
            name=self.name,
            date=self.params.date if self.params else "",
            total_ticks=len(self.ticks),
            open_price=open_price,
            close_price=close_price,
            high_price=high_price,
            low_price=low_price,
            total_volume=total_volume,
            total_amount=round(total_amount, 2),
            change_pct=change_pct,
            amplitude=amplitude,
            key_signals=key_signals,
            phase_summary=phase_summary,
        )


# 单例
history_replay_engine = HistoryReplayEngine()
