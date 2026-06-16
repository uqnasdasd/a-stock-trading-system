"""持仓监控与清仓预警 - 核心模块M3+M4"""
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
from app.models.schemas import StockQuote, Position, SignalType, AlertLevel
from app.services.data_collector.sina_api import collector
from app.core.config import settings
from app.core.database import (
    db_add_position,
    db_remove_position,
    db_get_positions,
    db_update_position_price,
)


class PositionMonitor:
    """持仓监控器"""

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.signals: List[dict] = []
        # 记录已触发的信号状态（防抖）
        self.triggered_signals: Dict[str, dict] = {}
        # 独立字典存储每只持仓的最高盈利（Pydantic v2兼容）
        self._max_profit_map: Dict[str, float] = {}
        self._loaded = False

    async def _ensure_loaded(self):
        """确保从数据库加载持仓数据"""
        if not self._loaded:
            await self.load_from_db()
            self._loaded = True

    async def load_from_db(self):
        """从数据库加载持仓"""
        rows = await db_get_positions()
        self.positions = {}
        self._max_profit_map = {}
        for row in rows:
            try:
                position = Position(
                    code=row["code"],
                    name=row["name"],
                    buy_price=row["buy_price"],
                    current_price=row["current_price"],
                    volume=row["volume"],
                    sector=row.get("sector", ""),
                    buy_time=datetime.fromisoformat(row["buy_time"]),
                    stop_loss_price=row.get("stop_loss", 0),
                    take_profit_price=row.get("take_profit", 0),
                )
                self.positions[position.code] = position
                # 初始化最高盈利记录
                self._max_profit_map[position.code] = 0.0
            except Exception as e:
                logger.warning(f"加载持仓 {row.get('code')} 失败: {e}")
        logger.info(f"从数据库加载 {len(self.positions)} 条持仓")

    async def add_position(self, position: Position):
        """添加持仓"""
        await self._ensure_loaded()
        self.positions[position.code] = position
        # 初始化最高盈利记录
        self._max_profit_map[position.code] = 0.0
        await db_add_position(
            code=position.code,
            name=position.name,
            buy_price=position.buy_price,
            current_price=position.current_price,
            volume=position.volume,
            sector=position.sector,
            buy_time=position.buy_time.isoformat(),
            stop_loss=position.stop_loss_price,
            take_profit=position.take_profit_price,
        )
        logger.info(f"添加持仓: {position.name}({position.code}) 买入价:{position.buy_price}")

    async def remove_position(self, code: str):
        """移除持仓"""
        await self._ensure_loaded()
        if code in self.positions:
            del self.positions[code]
            # 同时移除最高盈利记录
            if code in self._max_profit_map:
                del self._max_profit_map[code]
            await db_remove_position(code)
            # 清除该持仓的信号记录
            keys_to_remove = [k for k in self.triggered_signals if k.startswith(code)]
            for k in keys_to_remove:
                del self.triggered_signals[k]

    async def monitor(self) -> List[dict]:
        """监控所有持仓，返回信号列表"""
        await self._ensure_loaded()
        if not self.positions:
            return []

        codes = list(self.positions.keys())
        quotes = await collector.get_quotes(codes)

        signals = []
        for code, position in self.positions.items():
            if code not in quotes:
                continue

            quote = quotes[code]
            position.current_price = quote.price
            await db_update_position_price(code, quote.price)

            # 检查各类信号
            signals.extend(self._check_stop_loss(position, quote))
            signals.extend(self._check_take_profit(position, quote))
            signals.extend(self._check_sector_weakness(position, quote))
            signals.extend(self._check_price_volume_divergence(position, quote))
            signals.extend(self._check_support_break(position, quote))

        return signals

    def _check_stop_loss(self, position: Position, quote: StockQuote) -> List[dict]:
        """检查止损信号"""
        signals = []
        loss_pct = (quote.price - position.buy_price) / position.buy_price

        if loss_pct <= -settings.stop_loss_pct:
            signal_key = f"{position.code}_stop_loss"
            if not self._is_triggered(signal_key):
                signals.append({
                    "type": SignalType.STOP_LOSS,
                    "level": AlertLevel.EMERGENCY,
                    "code": position.code,
                    "name": position.name,
                    "message": f"止损触发！{position.name} 亏损{abs(loss_pct)*100:.1f}%，跌破止损线{settings.stop_loss_pct*100}%",
                    "trigger_price": quote.price,
                    "trigger_condition": f"跌幅≥{settings.stop_loss_pct*100}%",
                    "suggested_action": "立即市价清仓",
                    "timestamp": datetime.now().isoformat(),
                    "id": f"{position.code}_sl_{datetime.now().strftime('%H%M%S')}",
                    "is_read": False,
                })
                self._mark_triggered(signal_key)

        return signals

    def _check_take_profit(self, position: Position, quote: StockQuote) -> List[dict]:
        """检查止盈信号"""
        signals = []
        profit_pct = (quote.price - position.buy_price) / position.buy_price

        # 固定止盈
        if profit_pct >= settings.take_profit_pct:
            signal_key = f"{position.code}_take_profit"
            if not self._is_triggered(signal_key):
                signals.append({
                    "type": SignalType.TAKE_PROFIT,
                    "level": AlertLevel.IMPORTANT,
                    "code": position.code,
                    "name": position.name,
                    "message": f"止盈触发！{position.name} 盈利{profit_pct*100:.1f}%，达到目标{settings.take_profit_pct*100}%",
                    "trigger_price": quote.price,
                    "trigger_condition": f"盈利≥{settings.take_profit_pct*100}%",
                    "suggested_action": "卖出50%仓位，剩余设移动止盈",
                    "timestamp": datetime.now().isoformat(),
                    "id": f"{position.code}_tp_{datetime.now().strftime('%H%M%S')}",
                    "is_read": False,
                })
                self._mark_triggered(signal_key)

        # 移动止盈：盈利从高点回落3%
        max_profit = self._max_profit_map.get(position.code, 0.0)

        if max_profit > 0 and max_profit - profit_pct >= 0.03 and profit_pct > 0.02:
            signal_key = f"{position.code}_trailing_stop"
            if not self._is_triggered(signal_key):
                signals.append({
                    "type": SignalType.TAKE_PROFIT,
                    "level": AlertLevel.IMPORTANT,
                    "code": position.code,
                    "name": position.name,
                    "message": f"移动止盈触发！{position.name} 盈利从高点{max_profit*100:.1f}%回落至{profit_pct*100:.1f}%",
                    "trigger_price": quote.price,
                    "trigger_condition": "盈利从高点回落3%",
                    "suggested_action": "清仓剩余仓位",
                    "timestamp": datetime.now().isoformat(),
                    "id": f"{position.code}_ts_{datetime.now().strftime('%H%M%S')}",
                    "is_read": False,
                })
                self._mark_triggered(signal_key)

        # 更新最大盈利
        if profit_pct > max_profit:
            self._max_profit_map[position.code] = profit_pct

        return signals

    def _check_sector_weakness(self, position: Position, quote: StockQuote) -> List[dict]:
        """检查板块走弱信号（简化版，实际需要板块数据）"""
        signals = []
        # 如果个股跌幅超过5%且板块整体走弱
        change_pct = quote.change_pct
        if change_pct <= -5:
            signal_key = f"{position.code}_sector_weak"
            if not self._is_triggered(signal_key):
                signals.append({
                    "type": SignalType.POSITION_SELL,
                    "level": AlertLevel.IMPORTANT,
                    "code": position.code,
                    "name": position.name,
                    "message": f"板块走弱！{position.name} 跌幅{abs(change_pct):.1f}%，可能板块集体回调",
                    "trigger_price": quote.price,
                    "trigger_condition": "个股跌幅≥5%",
                    "suggested_action": "观察板块龙头状态，若龙头也走弱则清仓",
                    "timestamp": datetime.now().isoformat(),
                    "id": f"{position.code}_sw_{datetime.now().strftime('%H%M%S')}",
                    "is_read": False,
                })
                self._mark_triggered(signal_key)

        return signals

    def _check_price_volume_divergence(self, position: Position, quote: StockQuote) -> List[dict]:
        """检查量价背离信号"""
        signals = []
        # 简化判断：价格上涨但成交量萎缩（需要历史数据对比）
        # 实际实现需要与前5分钟/前1小时对比
        change_pct = quote.change_pct

        # 如果涨幅>3%但量比<1（无量上涨）
        if change_pct > 3 and quote.volume < 10000:  # 简化条件
            signal_key = f"{position.code}_pv_divergence"
            if not self._is_triggered(signal_key):
                signals.append({
                    "type": SignalType.POSITION_SELL,
                    "level": AlertLevel.NORMAL,
                    "code": position.code,
                    "name": position.name,
                    "message": f"量价背离警告！{position.name} 涨幅{change_pct:.1f}%但量能不足",
                    "trigger_price": quote.price,
                    "trigger_condition": "涨幅>3%但量能萎缩",
                    "suggested_action": "警惕诱多，考虑减仓",
                    "timestamp": datetime.now().isoformat(),
                    "id": f"{position.code}_pv_{datetime.now().strftime('%H%M%S')}",
                    "is_read": False,
                })
                self._mark_triggered(signal_key)

        return signals

    def _check_support_break(self, position: Position, quote: StockQuote) -> List[dict]:
        """检查支撑位跌破"""
        signals = []
        # 关键支撑位：开盘价、5日均线（简化用买入价）、昨日收盘价
        supports = [
            (quote.open, "开盘价"),
            (position.buy_price, "买入价"),
            (quote.pre_close, "昨日收盘价"),
        ]

        for support_price, support_name in supports:
            if quote.price < support_price * 0.98:  # 跌破2%
                signal_key = f"{position.code}_break_{support_name}"
                if not self._is_triggered(signal_key):
                    signals.append({
                        "type": SignalType.POSITION_SELL,
                        "level": AlertLevel.IMPORTANT,
                        "code": position.code,
                        "name": position.name,
                        "message": f"跌破支撑！{position.name} 跌破{support_name}({support_price:.2f})，当前{quote.price:.2f}",
                        "trigger_price": quote.price,
                        "trigger_condition": f"跌破{support_name}",
                        "suggested_action": "考虑清仓",
                        "timestamp": datetime.now().isoformat(),
                        "id": f"{position.code}_sb_{datetime.now().strftime('%H%M%S')}",
                        "is_read": False,
                    })
                    self._mark_triggered(signal_key)
                break  # 只报第一个跌破的

        return signals

    def _is_triggered(self, signal_key: str) -> bool:
        """检查信号是否已触发（防抖）"""
        if signal_key not in self.triggered_signals:
            return False

        triggered_time = self.triggered_signals[signal_key]["time"]
        # 60分钟冷却期
        if (datetime.now() - triggered_time).total_seconds() > 3600:
            del self.triggered_signals[signal_key]
            return False

        return True

    def _mark_triggered(self, signal_key: str):
        """标记信号已触发"""
        self.triggered_signals[signal_key] = {"time": datetime.now()}

    async def get_position_summary(self) -> dict:
        """获取持仓汇总"""
        await self._ensure_loaded()
        if not self.positions:
            return {"count": 0, "total_value": 0, "total_profit_pct": 0, "positions": []}

        total_value = sum(p.market_value for p in self.positions.values())
        total_cost = sum(p.buy_price * p.volume for p in self.positions.values())
        total_profit_pct = round((total_value - total_cost) / total_cost * 100, 2) if total_cost > 0 else 0

        return {
            "count": len(self.positions),
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_profit_pct": total_profit_pct,
            "positions": [
                {
                    "code": p.code,
                    "name": p.name,
                    "buy_price": p.buy_price,
                    "current_price": p.current_price,
                    "volume": p.volume,
                    "profit_pct": p.profit_pct,
                    "market_value": p.market_value,
                }
                for p in self.positions.values()
            ]
        }


# 单例
position_monitor = PositionMonitor()
