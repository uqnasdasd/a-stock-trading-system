"""策略回测引擎 - 基于真实K线数据"""
import json
import math
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from loguru import logger

from app.services.data_collector.sina_api import collector
from app.core.database import get_db


@dataclass
class BacktestParams:
    """回测参数"""
    code: str = "sh000001"           # 股票代码
    buy_condition: str = "ma_break"  # 买入条件类型
    sell_condition: str = "stop_profit_loss"  # 卖出条件类型
    hold_period: int = 5             # 最大持仓周期(天)
    start_date: str = "2024-01-01"
    end_date: str = "2024-06-01"
    initial_capital: float = 100000.0
    position_ratio: float = 0.20     # 单次仓位比例
    stop_loss_pct: float = 0.03      # 止损比例
    take_profit_pct: float = 0.05    # 止盈比例
    ma_period: int = 5               # 均线周期
    volume_ratio_threshold: float = 1.5  # 量比阈值


@dataclass
class TradeRecord:
    """交易记录"""
    date: str
    code: str
    name: str
    action: str  # buy / sell
    price: float
    volume: int
    pnl: float = 0.0
    pnl_pct: float = 0.0
    reason: str = ""


@dataclass
class BacktestResult:
    """回测结果"""
    total_return: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    trade_count: int = 0
    profit_trades: int = 0
    loss_trades: int = 0
    final_capital: float = 0.0
    equity_curve: List[Dict] = field(default_factory=list)
    drawdown_curve: List[Dict] = field(default_factory=list)
    trades: List[TradeRecord] = field(default_factory=list)
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0


class BacktestEngine:
    """回测引擎"""

    def __init__(self):
        self.params: Optional[BacktestParams] = None
        self.capital: float = 0.0
        self.position: Optional[Dict] = None
        self.trades: List[TradeRecord] = []
        self.equity_curve: List[Dict] = []
        self.drawdown_curve: List[Dict] = []
        self.daily_klines: List[Dict] = []
        self.name: str = ""

    async def run(self, params: BacktestParams) -> BacktestResult:
        """运行回测"""
        self.params = params
        self.capital = params.initial_capital
        self.trades = []
        self.equity_curve = []
        self.drawdown_curve = []
        self.position = None

        # 获取K线数据（日线）
        self.daily_klines = await self._fetch_kline_data(params.code, params.start_date, params.end_date)
        if len(self.daily_klines) < params.ma_period + 5:
            logger.warning(f"K线数据不足: {len(self.daily_klines)} 条")
            return self._build_result()

        # 计算均线
        self._calc_ma()

        # 计算量比（5日均量）
        self._calc_volume_ratio()

        # 逐日回测
        for i in range(params.ma_period, len(self.daily_klines)):
            day = self.daily_klines[i]
            date_str = day["day"]

            # 更新持仓市值
            if self.position:
                self.position["current_price"] = day["close"]
                self.position["days_held"] += 1

            # 检查卖出条件
            sell_reason = self._check_sell(day, i)
            if sell_reason and self.position:
                self._execute_sell(day, sell_reason)
                continue

            # 检查买入条件
            if not self.position:
                buy_reason = self._check_buy(day, i)
                if buy_reason:
                    self._execute_buy(day, buy_reason)

            # 记录每日权益
            equity = self.capital
            if self.position:
                equity += self.position["current_price"] * self.position["volume"]
            self.equity_curve.append({"date": date_str, "value": round(equity, 2)})

        # 强制平仓最后一天
        if self.position and self.daily_klines:
            last_day = self.daily_klines[-1]
            self._execute_sell(last_day, "回测结束强制平仓")

        return self._build_result()

    async def _fetch_kline_data(self, code: str, start_date: str, end_date: str) -> List[Dict]:
        """获取K线数据并过滤日期范围"""
        # 标准化代码
        code = code.strip().lower()
        if not code.startswith(("sh", "sz", "bj")):
            if code.startswith("6"):
                code = "sh" + code
            elif code.startswith(("0", "3")):
                code = "sz" + code
            elif code.startswith("8"):
                code = "bj" + code

        # 获取日线数据 (scale=240)
        kline = await collector.get_kline(code, scale=240, datalen=1023)
        if not kline:
            logger.warning(f"未获取到K线数据: {code}")
            return []

        # 过滤日期范围
        filtered = [item for item in kline if start_date <= item["day"] <= end_date]
        # 获取股票名称
        quotes = await collector.get_quotes([code])
        if code in quotes:
            self.name = quotes[code].name
        else:
            self.name = code

        logger.info(f"回测数据: {code} {self.name}, 共 {len(filtered)} 个交易日")
        return filtered

    def _calc_ma(self):
        """计算移动平均线"""
        period = self.params.ma_period if self.params else 5
        for i in range(len(self.daily_klines)):
            if i < period - 1:
                self.daily_klines[i]["ma"] = self.daily_klines[i]["close"]
            else:
                total = sum(self.daily_klines[j]["close"] for j in range(i - period + 1, i + 1))
                self.daily_klines[i]["ma"] = round(total / period, 4)

    def _calc_volume_ratio(self):
        """计算量比（当日成交量 / 前5日平均成交量）"""
        for i in range(len(self.daily_klines)):
            if i < 5:
                self.daily_klines[i]["volume_ratio"] = 1.0
            else:
                avg_vol = sum(self.daily_klines[j]["volume"] for j in range(i - 5, i)) / 5
                if avg_vol > 0:
                    self.daily_klines[i]["volume_ratio"] = round(self.daily_klines[i]["volume"] / avg_vol, 2)
                else:
                    self.daily_klines[i]["volume_ratio"] = 1.0

    def _check_buy(self, day: Dict, index: int) -> Optional[str]:
        """检查买入条件"""
        params = self.params
        if not params:
            return None

        condition = params.buy_condition

        if condition == "ma_break":
            # 突破均线 + 放量
            if day["close"] > day["ma"] and day["volume_ratio"] >= params.volume_ratio_threshold:
                prev_day = self.daily_klines[index - 1]
                if prev_day["close"] <= prev_day["ma"]:
                    return f"突破{params.ma_period}日均线且放量(量比{day['volume_ratio']})"

        elif condition == "ma_support":
            # 回踩均线支撑
            if abs(day["close"] - day["ma"]) / day["ma"] < 0.01 and day["volume_ratio"] >= 1.0:
                return f"回踩{params.ma_period}日均线支撑"

        elif condition == "limit_up_break":
            # 涨停突破
            if day["close"] == day["high"] and day["change_pct"] >= 9.5:
                return "涨停突破"

        elif condition == "volume_price_rise":
            # 量价齐升
            if day["change_pct"] >= 3 and day["volume_ratio"] >= params.volume_ratio_threshold:
                return f"量价齐升(涨{day['change_pct']:.1f}%,量比{day['volume_ratio']})"

        return None

    def _check_sell(self, day: Dict, index: int) -> Optional[str]:
        """检查卖出条件"""
        params = self.params
        if not params or not self.position:
            return None

        pos = self.position
        buy_price = pos["buy_price"]
        current_price = day["close"]
        profit_pct = (current_price - buy_price) / buy_price

        condition = params.sell_condition

        # 止损
        if profit_pct <= -params.stop_loss_pct:
            return f"止损触发(亏损{abs(profit_pct)*100:.1f}%)"

        # 止盈
        if profit_pct >= params.take_profit_pct:
            return f"止盈触发(盈利{profit_pct*100:.1f}%)"

        # 持仓周期
        if pos["days_held"] >= params.hold_period:
            return f"持仓周期到期({pos['days_held']}天)"

        if condition == "ma_break":
            # 跌破均线
            if current_price < day["ma"]:
                return f"跌破{params.ma_period}日均线"

        elif condition == "trailing_stop":
            # 移动止盈：从高点回落3%
            high_since_buy = max(self.daily_klines[j]["high"] for j in range(pos["buy_index"], index + 1))
            high_pct = (high_since_buy - buy_price) / buy_price
            if high_pct > 0.05 and (high_since_buy - current_price) / high_since_buy >= 0.03:
                return f"移动止盈(从高点{high_pct*100:.1f}%回落)"

        return None

    def _execute_buy(self, day: Dict, reason: str):
        """执行买入"""
        params = self.params
        if not params:
            return

        price = day["close"]
        buy_amount = self.capital * params.position_ratio
        volume = int(buy_amount / price / 100) * 100
        if volume < 100:
            return

        cost = price * volume
        if cost > self.capital:
            return

        self.capital -= cost
        self.position = {
            "code": params.code,
            "buy_price": price,
            "current_price": price,
            "volume": volume,
            "days_held": 0,
            "buy_index": self.daily_klines.index(day),
        }

        self.trades.append(TradeRecord(
            date=day["day"],
            code=params.code,
            name=self.name,
            action="buy",
            price=price,
            volume=volume,
            reason=reason,
        ))
        logger.debug(f"买入 {self.name} @ {price}, 数量{volume}, 原因:{reason}")

    def _execute_sell(self, day: Dict, reason: str):
        """执行卖出"""
        if not self.position:
            return

        price = day["close"]
        pos = self.position
        sell_amount = price * pos["volume"]
        cost = pos["buy_price"] * pos["volume"]
        pnl = sell_amount - cost
        pnl_pct = (price - pos["buy_price"]) / pos["buy_price"] * 100

        self.capital += sell_amount

        self.trades.append(TradeRecord(
            date=day["day"],
            code=pos["code"],
            name=self.name,
            action="sell",
            price=price,
            volume=pos["volume"],
            pnl=round(pnl, 2),
            pnl_pct=round(pnl_pct, 2),
            reason=reason,
        ))

        self.position = None
        logger.debug(f"卖出 {self.name} @ {price}, 盈亏{pnl:.2f}, 原因:{reason}")

    def _build_result(self) -> BacktestResult:
        """构建回测结果"""
        params = self.params
        if not params:
            return BacktestResult()

        final_capital = self.capital
        if self.position and self.daily_klines:
            final_capital += self.position["current_price"] * self.position["volume"]

        total_return = (final_capital - params.initial_capital) / params.initial_capital * 100

        # 最大回撤
        max_drawdown = 0.0
        peak = params.initial_capital
        for point in self.equity_curve:
            if point["value"] > peak:
                peak = point["value"]
            dd = (peak - point["value"]) / peak * 100
            if dd > max_drawdown:
                max_drawdown = dd
            self.drawdown_curve.append({"date": point["date"], "value": round(dd, 2)})

        # 胜率 & 盈亏比
        sell_trades = [t for t in self.trades if t.action == "sell"]
        profit_trades = [t for t in sell_trades if t.pnl > 0]
        loss_trades = [t for t in sell_trades if t.pnl <= 0]

        win_rate = (len(profit_trades) / len(sell_trades) * 100) if sell_trades else 0.0
        avg_profit = sum(t.pnl for t in profit_trades) / len(profit_trades) if profit_trades else 0
        avg_loss = abs(sum(t.pnl for t in loss_trades) / len(loss_trades)) if loss_trades else 0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0.0

        # 年化收益率
        days = len(self.daily_klines)
        annualized_return = 0.0
        if days > 0:
            annualized_return = ((1 + total_return / 100) ** (252 / days) - 1) * 100

        # 夏普比率（简化，假设无风险利率2%）
        sharpe = 0.0
        if len(self.equity_curve) > 1:
            daily_returns = []
            for i in range(1, len(self.equity_curve)):
                ret = (self.equity_curve[i]["value"] - self.equity_curve[i - 1]["value"]) / self.equity_curve[i - 1]["value"]
                daily_returns.append(ret)
            if daily_returns:
                avg_ret = sum(daily_returns) / len(daily_returns)
                variance = sum((r - avg_ret) ** 2 for r in daily_returns) / len(daily_returns)
                std_dev = math.sqrt(variance) if variance > 0 else 0
                if std_dev > 0:
                    sharpe = (avg_ret * 252 - 0.02) / (std_dev * math.sqrt(252))

        return BacktestResult(
            total_return=round(total_return, 2),
            max_drawdown=round(max_drawdown, 2),
            win_rate=round(win_rate, 2),
            profit_loss_ratio=round(profit_loss_ratio, 2),
            trade_count=len(sell_trades),
            profit_trades=len(profit_trades),
            loss_trades=len(loss_trades),
            final_capital=round(final_capital, 2),
            equity_curve=self.equity_curve,
            drawdown_curve=self.drawdown_curve,
            trades=self.trades,
            annualized_return=round(annualized_return, 2),
            sharpe_ratio=round(sharpe, 2),
        )

    async def run_multi_strategy(
        self,
        code: str,
        start_date: str,
        end_date: str,
        strategies: List[Dict],
    ) -> List[Dict]:
        """多策略对比回测"""
        results = []
        for strat in strategies:
            params = BacktestParams(
                code=code,
                start_date=start_date,
                end_date=end_date,
                buy_condition=strat.get("buy_condition", "ma_break"),
                sell_condition=strat.get("sell_condition", "stop_profit_loss"),
                hold_period=strat.get("hold_period", 5),
                initial_capital=strat.get("initial_capital", 100000),
                stop_loss_pct=strat.get("stop_loss_pct", 0.03),
                take_profit_pct=strat.get("take_profit_pct", 0.05),
                ma_period=strat.get("ma_period", 5),
                volume_ratio_threshold=strat.get("volume_ratio_threshold", 1.5),
            )
            result = await self.run(params)
            results.append({
                "strategy_name": strat.get("name", "未命名策略"),
                "params": strat,
                "result": {
                    "total_return": result.total_return,
                    "max_drawdown": result.max_drawdown,
                    "win_rate": result.win_rate,
                    "profit_loss_ratio": result.profit_loss_ratio,
                    "trade_count": result.trade_count,
                    "profit_trades": result.profit_trades,
                    "loss_trades": result.loss_trades,
                    "final_capital": result.final_capital,
                    "annualized_return": result.annualized_return,
                    "sharpe_ratio": result.sharpe_ratio,
                    "equity_curve": result.equity_curve,
                    "drawdown_curve": result.drawdown_curve,
                },
            })
            # 重置引擎状态
            self.__init__()
        return results


# 单例
backtest_engine = BacktestEngine()
