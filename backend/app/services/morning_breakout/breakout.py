"""早盘突破信号模块 - 核心模块M6

早盘突破信号生成：
- 箱体突破检测（前5日最高价突破）
- 量价齐升验证（成交量>5日均量1.5倍）
- 生成 MORNING_BREAKOUT 信号
"""
from typing import Dict, List, Optional
from datetime import datetime, time
from loguru import logger

from app.models.schemas import StockQuote, SignalType, AlertLevel
from app.services.data_collector.sina_api import collector


class MorningBreakoutSignal:
    """早盘突破信号生成器"""

    # 突破最小涨幅（相对前5日最高价）
    BREAKOUT_MIN_PCT = 0.01  # 1%
    # 成交量放大倍数阈值
    VOLUME_MULTIPLIER = 1.5
    # 信号有效时间段 9:30-11:30
    VALID_START = time(9, 30)
    VALID_END = time(11, 30)
    # 前N日最高价
    LOOKBACK_DAYS = 5

    def __init__(self):
        # 已触发信号的缓存（防抖）
        self._triggered_codes: set = set()
        # 前5日最高价缓存
        self._high_5d_cache: Dict[str, float] = {}
        # 5日均量缓存
        self._avg_volume_5d_cache: Dict[str, float] = {}

    def _is_valid_time(self) -> bool:
        """检查当前是否在有效时间段内"""
        now = datetime.now().time()
        return self.VALID_START <= now <= self.VALID_END

    async def _get_5d_high(self, code: str) -> Optional[float]:
        """获取前5日最高价

        通过日线K线数据获取前5日最高价
        """
        if code in self._high_5d_cache:
            return self._high_5d_cache[code]

        try:
            # 获取日线数据（最近10天，取前5天）
            kline = await collector.get_kline(code, scale=240, datalen=10)
            if len(kline) >= self.LOOKBACK_DAYS + 1:
                # 排除今天，取前5天
                past_5d = kline[-(self.LOOKBACK_DAYS + 1):-1]
                high_5d = max(d["high"] for d in past_5d)
                self._high_5d_cache[code] = high_5d
                return high_5d
            elif kline:
                # 数据不足，用已有数据
                past_data = kline[:-1] if len(kline) > 1 else kline
                if past_data:
                    high_5d = max(d["high"] for d in past_data)
                    self._high_5d_cache[code] = high_5d
                    return high_5d
        except Exception as e:
            logger.warning(f"获取前5日最高价失败 {code}: {e}")

        return None

    async def _get_5d_avg_volume(self, code: str) -> Optional[float]:
        """获取前5日平均成交量

        通过日线K线数据获取前5日平均成交量
        """
        if code in self._avg_volume_5d_cache:
            return self._avg_volume_5d_cache[code]

        try:
            # 获取日线数据
            kline = await collector.get_kline(code, scale=240, datalen=10)
            if len(kline) >= self.LOOKBACK_DAYS + 1:
                # 排除今天，取前5天
                past_5d = kline[-(self.LOOKBACK_DAYS + 1):-1]
                avg_volume = sum(d["volume"] for d in past_5d) / len(past_5d)
                self._avg_volume_5d_cache[code] = avg_volume
                return avg_volume
            elif kline:
                past_data = kline[:-1] if len(kline) > 1 else kline
                if past_data:
                    avg_volume = sum(d["volume"] for d in past_data) / len(past_data)
                    self._avg_volume_5d_cache[code] = avg_volume
                    return avg_volume
        except Exception as e:
            logger.warning(f"获取前5日均量失败 {code}: {e}")

        return None

    async def _check_box_breakout(self, code: str, quote: StockQuote) -> tuple[bool, float, float]:
        """检查是否突破前5日最高价箱体

        Returns:
            (是否突破, 前5日最高价, 突破幅度)
        """
        high_5d = await self._get_5d_high(code)
        if high_5d is None or high_5d <= 0:
            return False, 0.0, 0.0

        breakout_pct = (quote.price - high_5d) / high_5d
        is_breakout = breakout_pct >= self.BREAKOUT_MIN_PCT
        return is_breakout, high_5d, breakout_pct

    async def _check_volume_surge(self, code: str, quote: StockQuote) -> tuple[bool, float, float]:
        """检查成交量是否放量（>5日均量1.5倍）

        Returns:
            (是否放量, 5日均量, 放量倍数)
        """
        avg_volume = await self._get_5d_avg_volume(code)
        if avg_volume is None or avg_volume <= 0:
            # 无法获取均量时，使用简化判断
            # 早盘成交量较大即认为放量
            is_surge = quote.volume > 30000
            return is_surge, 0.0, 0.0

        multiplier = quote.volume / avg_volume
        is_surge = multiplier >= self.VOLUME_MULTIPLIER
        return is_surge, avg_volume, multiplier

    async def analyze_stock(self, code: str, quote: StockQuote) -> Optional[dict]:
        """分析单只股票，生成早盘突破信号

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

        # 1. 箱体突破检测
        breakout_ok, high_5d, breakout_pct = await self._check_box_breakout(code, quote)
        if not breakout_ok:
            return None

        # 2. 量价齐升验证
        volume_ok, avg_volume, multiplier = await self._check_volume_surge(code, quote)
        if not volume_ok:
            return None

        # 两个条件都满足，生成 MORNING_BREAKOUT 信号
        signal = {
            "type": SignalType.MORNING_BREAKOUT,
            "level": AlertLevel.IMPORTANT,
            "code": code,
            "name": quote.name,
            "message": (
                f"早盘突破信号！{quote.name} 突破前5日最高价{high_5d:.2f}，"
                f"突破幅度{breakout_pct*100:.1f}%，成交量放大{multiplier:.1f}倍"
            ),
            "trigger_price": quote.price,
            "trigger_condition": (
                f"突破前{self.LOOKBACK_DAYS}日最高价+{self.BREAKOUT_MIN_PCT*100}% "
                f"且 成交量>{self.VOLUME_MULTIPLIER}倍5日均量"
            ),
            "suggested_action": "箱体突破+量价齐升，可考虑追涨买入",
            "timestamp": datetime.now().isoformat(),
            "id": f"{code}_morning_breakout_{datetime.now().strftime('%H%M%S')}",
            "is_read": False,
            "extra": {
                "high_5d": round(high_5d, 2),
                "breakout_pct": round(breakout_pct * 100, 2),
                "avg_volume_5d": round(avg_volume, 0) if avg_volume else 0,
                "volume_multiplier": round(multiplier, 2),
                "current_volume": quote.volume,
            },
        }

        self._triggered_codes.add(code)
        logger.info(
            f"早盘突破信号: {quote.name}({code}) "
            f"突破{high_5d:.2f}({breakout_pct*100:.1f}%) 量{multiplier:.1f}倍"
        )
        return signal

    async def analyze_stocks(self, codes: List[str]) -> List[dict]:
        """批量分析股票，生成早盘突破信号

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
                logger.warning(f"早盘突破分析失败 {code}: {e}")
                continue

        # 按突破幅度排序
        signals.sort(
            key=lambda s: s.get("extra", {}).get("breakout_pct", 0),
            reverse=True,
        )

        logger.info(f"早盘突破分析完成: {len(signals)}只满足条件")
        return signals

    async def analyze_watchlist(self) -> List[dict]:
        """分析自选股列表

        从自选股管理器获取关注列表进行分析
        """
        from app.services.watchlist.manager import watchlist_manager

        codes = await watchlist_manager.get_codes()
        if not codes:
            logger.info("自选股列表为空，跳过早盘突破分析")
            return []

        return await self.analyze_stocks(codes)

    def reset(self):
        """重置信号状态（每日开盘前调用）"""
        self._triggered_codes.clear()
        self._high_5d_cache.clear()
        self._avg_volume_5d_cache.clear()
        logger.info("早盘突破信号状态已重置")


# 单例
morning_breakout = MorningBreakoutSignal()
