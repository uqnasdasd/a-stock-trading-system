"""风控中枢 - 核心模块M8"""
import json
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from loguru import logger
from app.models.schemas import Position, RiskStatus, AlertLevel, SignalType
from app.core.config import settings
from app.core.database import (
    db_set_setting,
    db_get_setting,
    db_save_risk_control,
    db_get_risk_control,
    db_get_latest_risk_control,
    db_get_risk_control_by_week,
)


class RiskController:
    """风控控制器"""

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.daily_trades: List[dict] = []      # 当日交易记录
        self.weekly_trades: List[dict] = []     # 本周交易记录
        self.daily_pnl: float = 0               # 当日盈亏金额
        self.weekly_pnl: float = 0              # 本周盈亏金额
        self.total_capital: float = 100000      # 总资金（默认10万，可配置）
        self.is_locked: bool = False
        self.lock_reason: Optional[str] = None
        self.lock_until: Optional[datetime] = None
        self._loaded = False
        self._current_date: str = date.today().isoformat()
        self._current_week_start: str = self._get_week_start().isoformat()

    @staticmethod
    def _get_week_start(d: Optional[date] = None) -> date:
        """获取指定日期所在周的周一"""
        if d is None:
            d = date.today()
        # weekday(): Monday=0, Sunday=6
        days_since_monday = d.weekday()
        return d - timedelta(days=days_since_monday)

    async def _ensure_loaded(self):
        """确保从数据库加载配置"""
        if not self._loaded:
            await self.load_from_db()
            self._loaded = True

    async def load_from_db(self):
        """从数据库加载风控配置和状态"""
        # 1. 加载总资金
        capital_str = await db_get_setting("total_capital")
        if capital_str:
            try:
                self.total_capital = float(capital_str)
                logger.info(f"从数据库加载总资金: {self.total_capital}")
            except ValueError:
                pass

        # 2. 加载最新的风控状态
        latest = await db_get_latest_risk_control()
        today = date.today().isoformat()
        week_start = self._get_week_start().isoformat()

        if latest:
            record_date = latest.get("date", "")
            record_week_start = latest.get("week_start", "")

            # 检查日期变化，自动重置日度数据
            if record_date == today:
                # 同一天，恢复日度数据
                self.daily_trades = latest.get("daily_trades", [])
                self.daily_pnl = latest.get("daily_pnl", 0)
                logger.info(f"恢复当日风控数据: 交易{len(self.daily_trades)}次, 盈亏{self.daily_pnl:.2f}")
            else:
                # 日期变化，重置日度数据
                self.daily_trades = []
                self.daily_pnl = 0
                logger.info(f"检测到日期变化 ({record_date} -> {today})，重置日度数据")

            # 检查周变化，自动重置周度数据
            if record_week_start == week_start:
                # 同一周，恢复周度数据
                self.weekly_trades = latest.get("weekly_trades", [])
                self.weekly_pnl = latest.get("weekly_pnl", 0)
                logger.info(f"恢复本周风控数据: 交易{len(self.weekly_trades)}次, 盈亏{self.weekly_pnl:.2f}")
            else:
                # 周变化（新的一周），重置周度数据
                self.weekly_trades = []
                self.weekly_pnl = 0
                logger.info(f"检测到新的一周 ({record_week_start} -> {week_start})，重置周度数据")

            # 恢复锁定状态
            self.is_locked = latest.get("is_locked", False)
            self.lock_reason = latest.get("lock_reason")
            lock_until_str = latest.get("lock_until")
            if lock_until_str:
                try:
                    self.lock_until = datetime.fromisoformat(lock_until_str)
                except (ValueError, TypeError):
                    self.lock_until = None

            # 检查锁定是否已过期
            if self.is_locked and self.lock_until and datetime.now() >= self.lock_until:
                self.is_locked = False
                self.lock_reason = None
                self.lock_until = None
                logger.info("锁定状态已过期，自动解锁")
        else:
            logger.info("数据库无历史风控数据，使用初始状态")

        self._current_date = today
        self._current_week_start = week_start
        self._loaded = True

    async def _persist_state(self):
        """持久化当前风控状态到数据库"""
        today = date.today().isoformat()
        week_start = self._get_week_start().isoformat()
        lock_until_str = self.lock_until.isoformat() if self.lock_until else None

        await db_save_risk_control(
            date=today,
            week_start=week_start,
            daily_trades=self.daily_trades,
            weekly_trades=self.weekly_trades,
            daily_pnl=self.daily_pnl,
            weekly_pnl=self.weekly_pnl,
            is_locked=self.is_locked,
            lock_reason=self.lock_reason,
            lock_until=lock_until_str,
        )

    async def _check_date_reset(self):
        """检查日期变化，自动重置日度/周度数据"""
        today = date.today().isoformat()
        week_start = self._get_week_start().isoformat()

        # 日度重置
        if today != self._current_date:
            self.daily_trades = []
            self.daily_pnl = 0
            self._current_date = today
            logger.info(f"日期变化，自动重置日度交易数据: {today}")

        # 周度重置（周一）
        if week_start != self._current_week_start:
            self.weekly_trades = []
            self.weekly_pnl = 0
            self._current_week_start = week_start
            logger.info(f"新的一周开始，自动重置周度交易数据: {week_start}")

    async def set_capital(self, capital: float):
        """设置总资金"""
        await self._ensure_loaded()
        self.total_capital = capital
        await db_set_setting("total_capital", str(capital))
        logger.info(f"设置总资金: {capital}")

    def add_position(self, position: Position):
        """添加持仓"""
        self.positions[position.code] = position

    def remove_position(self, code: str):
        """移除持仓"""
        if code in self.positions:
            del self.positions[code]

    async def record_trade(self, code: str, name: str, action: str, price: float, volume: int, pnl: float = 0):
        """记录交易"""
        await self._ensure_loaded()
        await self._check_date_reset()

        trade = {
            "code": code,
            "name": name,
            "action": action,
            "price": price,
            "volume": volume,
            "pnl": pnl,
            "time": datetime.now().isoformat(),
        }
        self.daily_trades.append(trade)
        self.weekly_trades.append(trade)

        if pnl != 0:
            self.daily_pnl += pnl
            self.weekly_pnl += pnl

        logger.info(f"记录交易: {name} {action} {volume}股 @ {price}, 盈亏:{pnl}")

        # 持久化到数据库
        await self._persist_state()

    def check_all(self) -> List[dict]:
        """检查所有风控规则，返回告警列表"""
        signals = []

        # 1. 仓位检查
        signals.extend(self._check_position_limit())

        # 2. 单日回撤检查
        signals.extend(self._check_daily_drawdown())

        # 3. 周度回撤检查
        signals.extend(self._check_weekly_drawdown())

        # 4. 交易频率检查
        signals.extend(self._check_trade_frequency())

        # 5. 隔夜风控检查（收盘前）
        signals.extend(self._check_overnight_risk())

        return signals

    def _check_position_limit(self) -> List[dict]:
        """检查仓位限制"""
        signals = []
        total_value = sum(p.market_value for p in self.positions.values())
        total_pct = total_value / self.total_capital if self.total_capital > 0 else 0

        # 总仓位检查
        if total_pct >= settings.max_total_position:
            signals.append({
                "type": SignalType.RISK_ALERT,
                "level": AlertLevel.IMPORTANT,
                "code": None,
                "name": "风控",
                "message": f"总仓位已达{total_pct*100:.1f}%，超过上限{settings.max_total_position*100}%",
                "trigger_condition": f"总仓位≥{settings.max_total_position*100}%",
                "suggested_action": "禁止开新仓，可考虑减仓",
                "timestamp": datetime.now().isoformat(),
                "id": f"risk_poslimit_{datetime.now().strftime('%H%M%S')}",
                "is_read": False,
            })

        # 单票仓位检查
        for code, position in self.positions.items():
            single_pct = position.market_value / self.total_capital
            if single_pct > settings.max_single_position:
                signals.append({
                    "type": SignalType.RISK_ALERT,
                    "level": AlertLevel.IMPORTANT,
                    "code": code,
                    "name": position.name,
                    "message": f"单票仓位{single_pct*100:.1f}%，超过上限{settings.max_single_position*100}%",
                    "trigger_condition": f"单票仓位>{settings.max_single_position*100}%",
                    "suggested_action": "减仓至10%以下",
                    "timestamp": datetime.now().isoformat(),
                    "id": f"{code}_singlelimit_{datetime.now().strftime('%H%M%S')}",
                    "is_read": False,
                })

        return signals

    def _check_daily_drawdown(self) -> List[dict]:
        """检查单日回撤"""
        signals = []
        daily_pnl_pct = self.daily_pnl / self.total_capital if self.total_capital > 0 else 0

        if daily_pnl_pct <= -settings.daily_max_loss:
            if not self.is_locked:
                self.is_locked = True
                self.lock_reason = f"单日亏损达{abs(daily_pnl_pct)*100:.1f}%，超过{settings.daily_max_loss*100}%上限"
                self.lock_until = datetime.now() + timedelta(days=1)

                signals.append({
                    "type": SignalType.RISK_ALERT,
                    "level": AlertLevel.EMERGENCY,
                    "code": None,
                    "name": "风控锁定",
                    "message": self.lock_reason,
                    "trigger_condition": f"单日亏损≥{settings.daily_max_loss*100}%",
                    "suggested_action": "今日停止交易，冷静复盘",
                    "timestamp": datetime.now().isoformat(),
                    "id": f"risk_daily_{datetime.now().strftime('%H%M%S')}",
                    "is_read": False,
                })

        return signals

    def _check_weekly_drawdown(self) -> List[dict]:
        """检查周度回撤"""
        signals = []
        weekly_pnl_pct = self.weekly_pnl / self.total_capital if self.total_capital > 0 else 0

        if weekly_pnl_pct <= -settings.weekly_max_loss:
            if not self.is_locked:
                self.is_locked = True
                self.lock_reason = f"周度亏损达{abs(weekly_pnl_pct)*100:.1f}%，超过{settings.weekly_max_loss*100}%上限"
                self.lock_until = datetime.now() + timedelta(days=2)

                signals.append({
                    "type": SignalType.RISK_ALERT,
                    "level": AlertLevel.EMERGENCY,
                    "code": None,
                    "name": "风控暂停",
                    "message": self.lock_reason,
                    "trigger_condition": f"周度亏损≥{settings.weekly_max_loss*100}%",
                    "suggested_action": "暂停1-2天交易，复盘问题",
                    "timestamp": datetime.now().isoformat(),
                    "id": f"risk_weekly_{datetime.now().strftime('%H%M%S')}",
                    "is_read": False,
                })

        return signals

    def _check_trade_frequency(self) -> List[dict]:
        """检查交易频率"""
        signals = []

        # 当日交易次数
        daily_count = len(self.daily_trades)
        if daily_count >= settings.max_trades_per_day:
            signals.append({
                "type": SignalType.RISK_ALERT,
                "level": AlertLevel.NORMAL,
                "code": None,
                "name": "交易频率",
                "message": f"今日已交易{daily_count}次，达到上限{settings.max_trades_per_day}次",
                "trigger_condition": f"日交易次数≥{settings.max_trades_per_day}",
                "suggested_action": "今日不再开新仓",
                "timestamp": datetime.now().isoformat(),
                "id": f"risk_dayfreq_{datetime.now().strftime('%H%M%S')}",
                "is_read": False,
            })

        # 本周交易次数
        weekly_count = len(self.weekly_trades)
        if weekly_count >= settings.max_trades_per_week:
            signals.append({
                "type": SignalType.RISK_ALERT,
                "level": AlertLevel.NORMAL,
                "code": None,
                "name": "交易频率",
                "message": f"本周已交易{weekly_count}次，达到上限{settings.max_trades_per_week}次",
                "trigger_condition": f"周交易次数≥{settings.max_trades_per_week}",
                "suggested_action": "本周不再开新仓",
                "timestamp": datetime.now().isoformat(),
                "id": f"risk_weekfreq_{datetime.now().strftime('%H%M%S')}",
                "is_read": False,
            })

        return signals

    def _check_overnight_risk(self) -> List[dict]:
        """检查隔夜风险（收盘前30分钟提醒）- 只对盈利持仓告警"""
        signals = []
        now = datetime.now()

        # 只在收盘前30分钟检查 (14:30-15:00)
        if now.hour == 14 and now.minute >= 30:
            for code, position in self.positions.items():
                profit_pct = position.profit_pct
                # 修复：只对盈利持仓进行隔夜风控告警
                # 亏损持仓已在止损逻辑中处理，不应重复告警
                if profit_pct > 0 and profit_pct < 9.5:
                    signals.append({
                        "type": SignalType.RISK_ALERT,
                        "level": AlertLevel.NORMAL,
                        "code": code,
                        "name": position.name,
                        "message": f"隔夜风险提示：{position.name} 当前盈利{profit_pct:.1f}%，未涨停，建议收盘前清仓锁定利润",
                        "trigger_condition": "盈利持仓+未涨停+收盘前30分钟",
                        "suggested_action": "收盘前清仓，规避隔夜风险",
                        "timestamp": datetime.now().isoformat(),
                        "id": f"{code}_overnight_{datetime.now().strftime('%H%M%S')}",
                        "is_read": False,
                    })

        return signals

    async def can_trade(self) -> tuple[bool, Optional[str]]:
        """检查是否可以交易"""
        await self._ensure_loaded()
        await self._check_date_reset()

        if self.is_locked:
            if self.lock_until and datetime.now() < self.lock_until:
                return False, f"交易已锁定: {self.lock_reason}，解锁时间: {self.lock_until.strftime('%Y-%m-%d %H:%M')}"
            else:
                # 解锁
                self.is_locked = False
                self.lock_reason = None
                self.lock_until = None
                await self._persist_state()

        # 检查日交易次数
        if len(self.daily_trades) >= settings.max_trades_per_day:
            return False, f"今日交易次数已达上限{settings.max_trades_per_day}次"

        # 检查周交易次数
        if len(self.weekly_trades) >= settings.max_trades_per_week:
            return False, f"本周交易次数已达上限{settings.max_trades_per_week}次"

        return True, None

    async def reset_daily(self):
        """重置每日数据（收盘后调用）"""
        await self._ensure_loaded()
        self.daily_trades = []
        self.daily_pnl = 0
        logger.info("重置每日交易数据")
        await self._persist_state()

    async def reset_weekly(self):
        """重置每周数据（周一开盘前调用）"""
        await self._ensure_loaded()
        self.weekly_trades = []
        self.weekly_pnl = 0
        logger.info("重置每周交易数据")
        await self._persist_state()

    def get_status(self) -> RiskStatus:
        """获取风控状态"""
        total_value = sum(p.market_value for p in self.positions.values())
        total_pct = total_value / self.total_capital if self.total_capital > 0 else 0
        daily_pnl_pct = self.daily_pnl / self.total_capital if self.total_capital > 0 else 0
        weekly_pnl_pct = self.weekly_pnl / self.total_capital if self.total_capital > 0 else 0

        return RiskStatus(
            total_position_pct=round(total_pct, 4),
            daily_profit_pct=round(daily_pnl_pct, 4),
            weekly_profit_pct=round(weekly_pnl_pct, 4),
            daily_trade_count=len(self.daily_trades),
            weekly_trade_count=len(self.weekly_trades),
            is_locked=self.is_locked,
            lock_reason=self.lock_reason,
        )

    def get_available_capital(self) -> float:
        """获取可用资金（总资金 - 已用仓位市值）"""
        total_value = sum(p.market_value for p in self.positions.values())
        available = self.total_capital - total_value
        return round(max(available, 0), 2)

    def calculate_buy_volume(
        self,
        price: float,
        position_ratio: float = 0.10,
    ) -> int:
        """根据总资金和仓位限制计算可买股数

        Args:
            price: 买入价格
            position_ratio: 仓位占比（默认10%，即单票最大仓位）

        Returns:
            可买入股数（A股最小单位100股，向下取整到100的整数倍）
        """
        if price <= 0:
            return 0

        # 可用资金
        available = self.get_available_capital()
        if available <= 0:
            return 0

        # 按仓位比例计算最大买入金额
        max_buy_amount = self.total_capital * position_ratio

        # 取可用资金和仓位限制的较小值
        buy_amount = min(available, max_buy_amount)

        # 计算股数（向下取整到100股）
        volume = int(buy_amount / price / 100) * 100

        return max(volume, 0)


# 单例
risk_controller = RiskController()
