"""开盘确认信号模块 - 核心模块M5

9:30-9:35 开盘确认信号生成：
- 量比验证（量比>2为强势）
- 价格突破昨日收盘价验证
- 生成 OPEN_CONFIRM 信号
"""
from typing import Dict, List, Optional
from datetime import datetime, time
from loguru import logger

from app.models.schemas import StockQuote, SignalType, AlertLevel
from app.services.data_collector.sina_api import collector


class OpenConfirmSignal:
    """开盘确认信号生成器"""

    # 量比强势阈值
    VOLUME_RATIO_THRESHOLD = 2.0
    # 价格突破最小涨幅（相对昨日收盘价）
    PRICE_BREAK_MIN_PCT = 0.01  # 1%
    # 信号有效时间段 9:30-9:35
    VALID_START = time(9, 30)
    VALID_END = time(9, 35)

    def __init__(self):
        # 已触发信号的缓存（防抖）
        self._triggered_codes: set = set()
        # 量比缓存（简化：通过东方财富接口获取量比）
        self._volume_ratio_cache: Dict[str, float] = {}

    def _is_valid_time(self) -> bool:
        """检查当前是否在有效时间段内"""
        now = datetime.now().time()
        return self.VALID_START <= now <= self.VALID_END

    def _get_volume_ratio(self, code: str, quote: StockQuote) -> float:
        """获取股票量比

        量比 = 现成交总手数 / (过去5日平均每分钟成交量 * 当日累计开市时间分钟数)
        简化计算：使用当前成交量与历史均量对比
        """
        # 优先使用缓存
        if code in self._volume_ratio_cache:
            return self._volume_ratio_cache[code]

        # 简化计算：假设开盘5分钟，量比约等于当前成交量 / 前5日同期均量
        # 实际应从数据源获取量比字段（东方财富接口有f10字段）
        # 这里使用简化逻辑：成交量相对昨日同期放大倍数
        # 由于没有历史同期数据，使用一个基于当前成交量的估算
        # 实际生产环境应从数据源获取真实量比

        # 使用成交量作为参考：如果成交量已经很大，认为量比较高
        # 这是一个简化逻辑，实际应接入真实量比数据
        estimated_ratio = 1.0
        if quote.volume > 50000:
            estimated_ratio = 2.5
        elif quote.volume > 20000:
            estimated_ratio = 1.8
        elif quote.volume > 10000:
            estimated_ratio = 1.3

        self._volume_ratio_cache[code] = estimated_ratio
        return estimated_ratio

    def _check_volume_ratio(self, code: str, quote: StockQuote) -> tuple[bool, float]:
        """检查量比是否满足强势条件

        Returns:
            (是否满足, 量比值)
        """
        volume_ratio = self._get_volume_ratio(code, quote)
        is_strong = volume_ratio >= self.VOLUME_RATIO_THRESHOLD
        return is_strong, volume_ratio

    def _check_price_break(self, quote: StockQuote) -> tuple[bool, float]:
        """检查价格是否突破昨日收盘价

        Returns:
            (是否突破, 涨幅百分比)
        """
        if quote.pre_close <= 0:
            return False, 0.0

        change_pct = (quote.price - quote.pre_close) / quote.pre_close
        is_break = change_pct >= self.PRICE_BREAK_MIN_PCT
        return is_break, change_pct

    async def analyze_stock(self, code: str, quote: StockQuote) -> Optional[dict]:
        """分析单只股票，生成开盘确认信号

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

        # 1. 量比验证
        volume_ok, volume_ratio = self._check_volume_ratio(code, quote)
        if not volume_ok:
            return None

        # 2. 价格突破验证
        price_ok, change_pct = self._check_price_break(quote)
        if not price_ok:
            return None

        # 两个条件都满足，生成 OPEN_CONFIRM 信号
        signal = {
            "type": SignalType.OPEN_CONFIRM,
            "level": AlertLevel.IMPORTANT,
            "code": code,
            "name": quote.name,
            "message": (
                f"开盘确认信号！{quote.name} 量比{volume_ratio:.1f}（>2强势），"
                f"价格突破昨日收盘，涨幅{change_pct*100:.1f}%"
            ),
            "trigger_price": quote.price,
            "trigger_condition": f"量比>{self.VOLUME_RATIO_THRESHOLD} 且 价格突破昨日收盘+{self.PRICE_BREAK_MIN_PCT*100}%",
            "suggested_action": "强势开盘确认，可考虑追涨买入",
            "timestamp": datetime.now().isoformat(),
            "id": f"{code}_open_confirm_{datetime.now().strftime('%H%M%S')}",
            "is_read": False,
            "extra": {
                "volume_ratio": round(volume_ratio, 2),
                "change_pct": round(change_pct * 100, 2),
                "pre_close": quote.pre_close,
                "open": quote.open,
            },
        }

        self._triggered_codes.add(code)
        logger.info(f"开盘确认信号: {quote.name}({code}) 量比{volume_ratio:.1f} 涨幅{change_pct*100:.1f}%")
        return signal

    async def analyze_stocks(self, codes: List[str]) -> List[dict]:
        """批量分析股票，生成开盘确认信号

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
                logger.warning(f"开盘确认分析失败 {code}: {e}")
                continue

        # 按量比排序
        signals.sort(
            key=lambda s: s.get("extra", {}).get("volume_ratio", 0),
            reverse=True,
        )

        logger.info(f"开盘确认分析完成: {len(signals)}只满足条件")
        return signals

    async def analyze_watchlist(self) -> List[dict]:
        """分析自选股列表

        从自选股管理器获取关注列表进行分析
        """
        from app.services.watchlist.manager import watchlist_manager

        codes = await watchlist_manager.get_codes()
        if not codes:
            logger.info("自选股列表为空，跳过开盘确认分析")
            return []

        return await self.analyze_stocks(codes)

    def reset(self):
        """重置信号状态（每日开盘前调用）"""
        self._triggered_codes.clear()
        self._volume_ratio_cache.clear()
        logger.info("开盘确认信号状态已重置")


# 单例
open_confirm = OpenConfirmSignal()
