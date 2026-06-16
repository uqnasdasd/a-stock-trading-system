"""数据模型定义"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class SignalType(str, Enum):
    """信号类型"""
    AUCTION_BUY = "auction_buy"           # 竞价买点
    OPEN_CONFIRM = "open_confirm"         # 开盘确认
    MORNING_BREAKOUT = "morning_breakout" # 早盘突破买点
    AFTERNOON_STABLE = "afternoon_stable" # 尾盘稳健买点
    STOP_LOSS = "stop_loss"               # 止损
    TAKE_PROFIT = "take_profit"           # 止盈
    POSITION_HOLD = "position_hold"       # 持仓
    POSITION_SELL = "position_sell"       # 清仓
    RISK_ALERT = "risk_alert"             # 风控告警


class AlertLevel(str, Enum):
    """告警级别"""
    EMERGENCY = "emergency"   # 紧急（红色）
    IMPORTANT = "important"   # 重要（橙色）
    NORMAL = "normal"         # 一般（黄色）
    INFO = "info"             # 信息（蓝色）


class StockQuote(BaseModel):
    """股票行情数据"""
    code: str
    name: str
    price: float
    pre_close: float
    open: float
    high: float
    low: float
    volume: int
    amount: float
    bid1: float = 0
    ask1: float = 0
    bid1_vol: int = 0
    ask1_vol: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def change_pct(self) -> float:
        return round((self.price - self.pre_close) / self.pre_close * 100, 2)

    @property
    def up_down(self) -> str:
        return "up" if self.change_pct > 0 else "down" if self.change_pct < 0 else "flat"


class AuctionData(BaseModel):
    """竞价数据"""
    code: str
    name: str
    auction_price: float
    pre_close: float
    auction_volume: int
    auction_amount: float
    bid_vol: int = 0          # 买一档量
    ask_vol: int = 0          # 卖一档量
    timestamp: datetime
    is_cancelable: bool = True  # 9:15-9:20可撤单

    @property
    def change_pct(self) -> float:
        return round((self.auction_price - self.pre_close) / self.pre_close * 100, 2)


class SectorStrength(BaseModel):
    """板块强度"""
    sector_name: str
    avg_change_pct: float
    up_count: int
    down_count: int
    limit_up_count: int      # 涨停家数
    high_open_count: int     # 高开家数
    total_count: int
    leader_code: Optional[str] = None
    leader_change_pct: float = 0
    score: float = 0         # 综合强度评分


class LeaderScore(BaseModel):
    """龙头竞价评分"""
    code: str
    name: str
    sector: str
    change_pct: float
    bid_vol: int
    score: int               # 0-10分
    score_reason: str


class Position(BaseModel):
    """持仓记录"""
    code: str
    name: str
    buy_price: float
    current_price: float
    volume: int
    sector: str
    buy_time: datetime
    stop_loss_price: float
    take_profit_price: float

    @property
    def profit_pct(self) -> float:
        return round((self.current_price - self.buy_price) / self.buy_price * 100, 2)

    @property
    def market_value(self) -> float:
        return round(self.current_price * self.volume, 2)


class RiskStatus(BaseModel):
    """风控状态"""
    total_position_pct: float      # 总仓位占比
    daily_profit_pct: float        # 当日盈亏
    weekly_profit_pct: float       # 本周盈亏
    daily_trade_count: int         # 当日交易次数
    weekly_trade_count: int        # 本周交易次数
    is_locked: bool = False        # 是否被锁定
    lock_reason: Optional[str] = None
    total_capital: float = 0.0     # 总资金
    used_capital: float = 0.0      # 已用资金
    available_capital: float = 0.0 # 可用资金


class TradingSignal(BaseModel):
    """交易信号"""
    id: str
    type: SignalType
    level: AlertLevel
    code: str
    name: str
    message: str
    trigger_price: Optional[float] = None
    trigger_condition: str
    suggested_action: str
    timestamp: datetime
    is_read: bool = False


class AlertMessage(BaseModel):
    """告警消息"""
    level: AlertLevel
    title: str
    content: str
    code: Optional[str] = None
    signal_type: SignalType
    timestamp: datetime
