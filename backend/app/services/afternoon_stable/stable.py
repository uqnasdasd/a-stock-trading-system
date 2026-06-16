"""尾盘稳健信号模块 - 核心模块M7

尾盘稳健信号生成（14:30-15:00）：
- 分时均线支撑检测
- 量能萎缩检测（避免放量下跌）
- 生成 AFTERNOON_STABLE 信号
"""
from typing import Dict, List, Optional
from datetime import datetime, time
from loguru import logger

from app.models.schemas import StockQuote, SignalType, AlertLevel
from app.services.data_collector.sina_api import collector


class AfternoonStableSignal:
    """尾盘稳健信号生成器"""

    # 信号有效时间段 14:30-15:00
    VALID_START = time(14, 30)
    VALID_END = time(15, 0)
    # 分时均线支撑偏离阈值（价格在均线上方或偏离不超过1%）
    MA_SUPPORT_THRESHOLD = 0.01  # 1%
    # 量能萎缩阈值（相对早盘均量）
    VOLUME_SHRINK_THRESHOLD = 0.7  # 尾盘成交量 < 早盘均量 * 0.7
    # 最小涨幅要求（避免选到弱势股）
    MIN_CHANGE_PCT = -1.0  # 允许微跌
    # 最大跌幅限制
    MAX_CHANGE_PCT = 5.0   # 涨幅不超过5%（避免追高）

    def __init__(self):
        # 已触发信号的缓存（防抖）
        self._triggered_codes: set = set()
        # 分时数据缓存
        self._minute_data_cache: Dict[str, List[dict]] = {}
        # 早盘均量缓存
        self._morning_avg_volume_cache: Dict[str, float] = {}

    def _is_valid_time(self) -> bool:
        """检查当前是否在有效时间段内"""
        now = datetime.now().time()
        return self.VALID_START <= now <= self.VALID_END

    async def _get_minute_data(self, code: str) -> List[dict]:
        """获取分时数据"""
        if code in self._minute_data_cache:
            return self._minute_data_cache[code]

        try:
            minute_data = await collector.get_minute_data(code)
            self._minute_data_cache[code] = minute_data
            return minute_data
        except Exception as e:
            logger.warning(f"获取分时数据失败 {code}: {e}")
            return []

    def _calculate_ma(self, minute_data: List[dict]) -> Optional[float]:
        """计算分时均线（均价线）

        分时均线 = 累计成交额 / 累计成交量
        """
        if not minute_data:
            return None

        total_amount = sum(d.get("amount", 0) for d in minute_data)
        total_volume = sum(d.get("volume", 0) for d in minute_data)

        if total_volume <= 0:
            # 没有金额数据时，用价格平均
            prices = [d.get("price", 0) for d in minute_data if d.get("price", 0) > 0]
            if prices:
                return sum(prices) / len(prices)
            return None

        return total_amount / total_volume

    async def _check_ma_support(self, code: str, quote: StockQuote) -> tuple[bool, float, float]:
        """检查价格是否在分时均线附近获得支撑

        Returns:
            (是否支撑, 分时均线价格, 偏离幅度)
        """
        minute_data = await self._get_minute_data(code)
        if not minute_data:
            # 无分时数据时，使用简化判断
            # 价格相对开盘价不跌太多即认为有支撑
            if quote.open > 0:
                deviation = (quote.price - quote.open) / quote.open
                is_support = deviation >= -self.MA_SUPPORT_THRESHOLD
                return is_support, quote.open, deviation
            return False, 0.0, 0.0

        ma_price = self._calculate_ma(minute_data)
        if ma_price is None or ma_price <= 0:
            return False, 0.0, 0.0

        deviation = (quote.price - ma_price) / ma_price
        # 价格在均线上方，或偏离不超过阈值（下方不超过1%）
        is_support = deviation >= -self.MA_SUPPORT_THRESHOLD
        return is_support, ma_price, deviation

    def _calculate_morning_avg_volume(self, minute_data: List[dict]) -> Optional[float]:
        """计算早盘（9:30-11:30）平均每分钟成交量"""
        if not minute_data:
            return None

        morning_data = []
        for d in minute_data:
            time_str = d.get("time", "")
            if not time_str:
                continue
            # 提取小时部分
            try:
                # time格式可能是 "09:30" 或 "2024-01-01 09:30:00"
                if " " in time_str:
                    time_part = time_str.split(" ")[1][:5]
                else:
                    time_part = time_str[:5]

                hour = int(time_part[:2])
                minute = int(time_part[3:5])

                # 早盘 9:30-11:30
                if (hour == 9 and minute >= 30) or (hour == 10) or (hour == 11 and minute <= 30):
                    morning_data.append(d)
            except (ValueError, IndexError):
                continue

        if not morning_data:
            return None

        total_volume = sum(d.get("volume", 0) for d in morning_data)
        return total_volume / len(morning_data)

    async def _check_volume_shrink(self, code: str, quote: StockQuote) -> tuple[bool, float, float]:
        """检查尾盘是否量能萎缩（避免放量下跌）

        Returns:
            (是否萎缩, 早盘均量, 当前量比）
        """
        minute_data = await self._get_minute_data(code)
        if not minute_data:
            # 无分时数据时，使用简化判断
            # 尾盘成交量不过大即认为合格
            is_shrink = quote.volume < 50000
            return is_shrink, 0.0, 0.0

        morning_avg = self._calculate_morning_avg_volume(minute_data)
        if morning_avg is None or morning_avg <= 0:
            return True, 0.0, 0.0  # 无法计算时默认通过

        # 获取最近几笔成交量
        recent_data = minute_data[-5:] if len(minute_data) >= 5 else minute_data
        recent_avg_volume = sum(d.get("volume", 0) for d in recent_data) / len(recent_data)

        volume_ratio = recent_avg_volume / morning_avg if morning_avg > 0 else 0
        is_shrink = volume_ratio <= self.VOLUME_SHRINK_THRESHOLD

        return is_shrink, morning_avg, volume_ratio

    async def analyze_stock(self, code: str, quote: StockQuote) -> Optional[dict]:
        """分析单只股票，生成尾盘稳健信号

        Args:
            code: 股票代码
            quote: 股票行情

        Returns:
            信号字典或None
        """
        # 检查时间窗口
        if not self._is_valid_time():
            return None

        # 检查是否已触发过
        if code in self._triggered_codes:
            return None

        # 检查涨跌幅范围
        change_pct = quote.change_pct
        if change_pct < self.MIN_CHANGE_PCT or change_pct > self.MAX_CHANGE_PCT:
            return None

        # 1. 分时均线支撑检测
        ma_ok, ma_price, ma_deviation = await self._check_ma_support(code, quote)
        if not ma_ok:
            return None

        # 2. 量能萎缩检测
        volume_ok, morning_avg, volume_ratio = await self._check_volume_shrink(code, quote)
        if not volume_ok:
            return None

        # 两个条件都满足，生成 AFTERNOON_STABLE 信号
        signal = {
            "type": SignalType.AFTERNOON_STABLE,
            "level": AlertLevel.NORMAL,
            "code": code,
            "name": quote.name,
            "message": (
                f"尾盘稳健信号！{quote.name} 分时均线支撑良好"
                f"（均线{ma_price:.2f}，偏离{ma_deviation*100:.1f}%），"
                f"尾盘量能萎缩（量比{volume_ratio:.1f}），走势稳健"
            ),
            "trigger_price": quote.price,
            "trigger_condition": (
                f"14:30-15:00 分时均线支撑（偏离≤{self.MA_SUPPORT_THRESHOLD*100}%）"
                f"且 尾盘量能萎缩（≤{self.VOLUME_SHRINK_THRESHOLD*100}%早盘均量）"
            ),
            "suggested_action": "尾盘走势稳健，可考虑低吸或持仓过夜",
            "timestamp": datetime.now().isoformat(),
            "id": f"{code}_afternoon_stable_{datetime.now().strftime('%H%M%S')}",
            "is_read": False,
            "extra": {
                "ma_price": round(ma_price, 2),
                "ma_deviation_pct": round(ma_deviation * 100, 2),
                "morning_avg_volume": round(morning_avg, 0) if morning_avg else 0,
                "volume_ratio": round(volume_ratio, 2),
                "change_pct": change_pct,
            },
        }

        self._triggered_codes.add(code)
        logger.info(
            f"尾盘稳健信号: {quote.name}({code}) "
            f"均线{ma_price:.2f}({ma_deviation*100:.1f}%) 量比{volume_ratio:.1f}"
        )
        return signal

    async def analyze_stocks(self, codes: List[str]) -> List[dict]:
        """批量分析股票，生成尾盘稳健信号

        Args:
            codes: 股票代码列表

        Returns:
            信号列表
        """
        if not self._is_valid_time():
            return []

        if not codes:
            return []

        quotes = await collector.get_quotes(codes)
        signals = []

        for code, quote in quotes.items():
            try:
                signal = await self.analyze_stock(code, quote)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.warning(f"尾盘稳健分析失败 {code}: {e}")
                continue

        # 按均线偏离度排序（越接近均线越稳健）
        signals.sort(
            key=lambda s: abs(s.get("extra", {}).get("ma_deviation_pct", 999)),
        )

        logger.info(f"尾盘稳健分析完成: {len(signals)}只满足条件")
        return signals

    async def analyze_watchlist(self) -> List[dict]:
        """分析自选股列表

        从自选股管理器获取关注列表进行分析
        """
        from app.services.watchlist.manager import watchlist_manager

        codes = await watchlist_manager.get_codes()
        if not codes:
            logger.info("自选股列表为空，跳过尾盘稳健分析")
            return []

        return await self.analyze_stocks(codes)

    def reset(self):
        """重置信号状态（每日开盘前调用）"""
        self._triggered_codes.clear()
        self._minute_data_cache.clear()
        self._morning_avg_volume_cache.clear()
        logger.info("尾盘稳健信号状态已重置")


# 单例
afternoon_stable = AfternoonStableSignal()
