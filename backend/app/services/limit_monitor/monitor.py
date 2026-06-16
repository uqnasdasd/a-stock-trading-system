"""涨跌停监控模块 - 实时检测全市场涨跌停与炸板信号（覆盖全部A股5000+）"""
import httpx
import asyncio
import json
import time
from typing import Dict, List, Optional, Set
from datetime import datetime
from loguru import logger
from app.services.data_collector.sina_api import collector


class LimitMonitor:
    """涨跌停监控器 - 覆盖全部A股5000+"""

    # 批量查询大小
    BATCH_SIZE = 40
    # 全市场扫描间隔（秒）
    SCAN_INTERVAL = 30

    def __init__(self):
        self.limit_up_stocks: List[dict] = []
        self.limit_down_stocks: List[dict] = []
        self.broken_board_stocks: List[dict] = []  # 炸板股
        self._prev_limit_up_codes: set = set()  # 上一轮涨停股代码（用于检测炸板）
        self._last_update: Optional[datetime] = None
        # 连板数追踪: {code: consecutive_limit_up_count}
        self._consecutive_limit_up: Dict[str, int] = {}
        # 昨日涨停列表（用于计算连板）
        self._yesterday_limit_up: Set[str] = set()
        # 全市场股票缓存
        self._all_stocks_cache: List[dict] = []
        self._all_stocks_cache_time: Optional[datetime] = None

    def _get_limit_pct(self, code: str) -> float:
        """获取涨停百分比阈值

        - 科创板(sh688开头): 20%
        - 创业板(sz300/301开头): 20%
        - 北交所(bj开头): 30%
        - 主板: 10%
        """
        code_lower = code.lower()
        if code_lower.startswith("sh688") or code_lower.startswith("sz300") or code_lower.startswith("sz301"):
            return 20.0
        if code_lower.startswith("bj") or code_lower.startswith("sh8") or code_lower.startswith("sz8"):
            return 30.0
        return 10.0

    def _get_limit_threshold(self, code: str) -> float:
        """获取涨停判断阈值（考虑实际交易精度）"""
        limit_pct = self._get_limit_pct(code)
        # 实际判断时允许微小误差
        return limit_pct - 0.1

    def _get_limit_down_threshold(self, code: str) -> float:
        """获取跌停判断阈值"""
        limit_pct = self._get_limit_pct(code)
        return -(limit_pct - 0.1)

    def _get_board_type(self, code: str) -> str:
        """获取板块类型"""
        code_lower = code.lower()
        if code_lower.startswith("sh688"):
            return "科创板"
        if code_lower.startswith("sz300") or code_lower.startswith("sz301"):
            return "创业板"
        if code_lower.startswith("bj") or code_lower.startswith("sh8") or code_lower.startswith("sz8"):
            return "北交所"
        return "主板"

    def _calculate_limit_price(self, pre_close: float, code: str) -> tuple:
        """计算涨停价和跌停价"""
        limit_pct = self._get_limit_pct(code)
        limit_up_price = round(pre_close * (1 + limit_pct / 100), 2)
        limit_down_price = round(pre_close * (1 - limit_pct / 100), 2)
        return limit_up_price, limit_down_price

    def _calculate_seal_amount(self, stock: dict) -> float:
        """计算封单金额（万元）
        涨停时取买一量 * 涨停价，跌停时取卖一量 * 跌停价
        """
        price = stock.get("price", 0)
        bid1_vol = stock.get("bid1_vol", 0)
        ask1_vol = stock.get("ask1_vol", 0)

        if stock.get("type") == "涨停":
            # 涨停时买一量即为封单量
            return round(bid1_vol * price / 10000, 2)
        elif stock.get("type") == "跌停":
            # 跌停时卖一量即为封单量
            return round(ask1_vol * price / 10000, 2)
        return 0.0

    def _update_consecutive_count(self, code: str, is_limit_up: bool) -> int:
        """更新连板数"""
        if is_limit_up:
            if code in self._consecutive_limit_up:
                self._consecutive_limit_up[code] += 1
            else:
                # 如果昨日涨停，今天继续涨停则连板+1
                if code in self._yesterday_limit_up:
                    self._consecutive_limit_up[code] = 2
                else:
                    self._consecutive_limit_up[code] = 1
        else:
            # 不再涨停，重置连板数
            if code in self._consecutive_limit_up:
                del self._consecutive_limit_up[code]
        return self._consecutive_limit_up.get(code, 0)

    async def _get_all_a_stocks(self) -> List[dict]:
        """获取全部A股列表（带缓存）"""
        now = datetime.now()
        if (self._all_stocks_cache and self._all_stocks_cache_time and
            (now - self._all_stocks_cache_time).seconds < 300):
            return self._all_stocks_cache

        stocks = await collector.get_all_a_stocks_from_eastmoney()
        if stocks:
            self._all_stocks_cache = stocks
            self._all_stocks_cache_time = now
        return stocks

    async def fetch_limit_data(self) -> dict:
        """获取涨跌停数据（覆盖全部A股5000+）"""
        result = {
            "limit_up": [],
            "limit_down": [],
            "broken_board": [],
            "timestamp": datetime.now().isoformat(),
        }

        # 1. 获取全部A股列表
        all_stocks = await self._get_all_a_stocks()
        if not all_stocks:
            logger.warning("无法获取A股列表，回退到热门股票扫描")
            result["limit_up"], result["limit_down"] = await self._scan_hot_stocks()
            result["broken_board"] = self._detect_broken_board(result["limit_up"])
            return result

        # 2. 从东方财富数据中直接筛选涨跌停（数据已包含涨跌幅）
        limit_up, limit_down = self._filter_limit_from_eastmoney(all_stocks)

        # 如果东方财富数据不完整，补充查询
        if len(limit_up) + len(limit_down) < 10:
            logger.warning("东方财富数据不完整，补充查询实时行情")
            limit_up, limit_down = await self._scan_all_stocks_by_batch(all_stocks)

        # 3. 检测炸板信号
        broken_board = self._detect_broken_board(limit_up)

        # 4. 更新连板数
        for stock in limit_up:
            code = stock["code"]
            stock["consecutive_count"] = self._update_consecutive_count(code, True)

        # 更新缓存
        self.limit_up_stocks = limit_up
        self.limit_down_stocks = limit_down
        self.broken_board_stocks = broken_board
        self._prev_limit_up_codes = {s["code"] for s in limit_up}
        self._last_update = datetime.now()

        result["limit_up"] = limit_up
        result["limit_down"] = limit_down
        result["broken_board"] = broken_board

        logger.info(
            f"涨跌停扫描完成: 涨停{len(limit_up)}只, "
            f"跌停{len(limit_down)}只, 炸板{len(broken_board)}只, "
            f"覆盖{len(all_stocks)}只A股"
        )

        return result

    def _filter_limit_from_eastmoney(self, stocks: List[dict]) -> tuple:
        """从东方财富数据中筛选涨跌停股票"""
        limit_up = []
        limit_down = []

        for stock in stocks:
            try:
                code = stock.get("code", "")
                change_pct = stock.get("change_pct", 0)
                if change_pct == 0:
                    continue

                up_threshold = self._get_limit_threshold(code)
                down_threshold = self._get_limit_down_threshold(code)
                board_type = self._get_board_type(code)
                pre_close = stock.get("pre_close", 0)
                limit_up_price, limit_down_price = self._calculate_limit_price(pre_close, code)

                stock_info = {
                    "code": code,
                    "name": stock.get("name", ""),
                    "price": stock.get("price", 0),
                    "change_pct": change_pct,
                    "type": "涨停" if change_pct > 0 else "跌停",
                    "board_type": board_type,
                    "limit_pct": self._get_limit_pct(code),
                    "limit_up_price": limit_up_price,
                    "limit_down_price": limit_down_price,
                    "pre_close": pre_close,
                    "volume": stock.get("volume", 0),
                    "amount": stock.get("amount", 0),
                    "turnover": stock.get("turnover", 0),
                    "bid1_vol": 0,  # 东方财富批量接口不返回档位数据
                    "ask1_vol": 0,
                    "seal_amount": 0.0,  # 封单金额待后续补充
                    "consecutive_count": 0,
                }

                if change_pct >= up_threshold:
                    limit_up.append(stock_info)
                elif change_pct <= down_threshold:
                    limit_down.append(stock_info)
            except Exception as e:
                logger.warning(f"筛选涨跌停数据失败: {e}")
                continue

        return limit_up, limit_down

    async def _scan_all_stocks_by_batch(self, stocks: List[dict]) -> tuple:
        """分批查询全部A股实时行情判断涨跌停"""
        limit_up = []
        limit_down = []

        codes = [s["code"] for s in stocks if s.get("code")]
        total = len(codes)

        for i in range(0, total, self.BATCH_SIZE):
            batch = codes[i:i + self.BATCH_SIZE]
            quotes = await collector.get_quotes(batch)

            for code, quote in quotes.items():
                change_pct = quote.change_pct
                up_threshold = self._get_limit_threshold(code)
                down_threshold = self._get_limit_down_threshold(code)
                board_type = self._get_board_type(code)
                limit_up_price, limit_down_price = self._calculate_limit_price(quote.pre_close, code)

                stock_info = {
                    "code": code,
                    "name": quote.name,
                    "price": quote.price,
                    "change_pct": change_pct,
                    "type": "涨停" if change_pct > 0 else "跌停",
                    "board_type": board_type,
                    "limit_pct": self._get_limit_pct(code),
                    "limit_up_price": limit_up_price,
                    "limit_down_price": limit_down_price,
                    "pre_close": quote.pre_close,
                    "volume": quote.volume,
                    "amount": quote.amount,
                    "turnover": 0,
                    "bid1_vol": quote.bid1_vol,
                    "ask1_vol": quote.ask1_vol,
                    "seal_amount": self._calculate_seal_amount({
                        "price": quote.price,
                        "bid1_vol": quote.bid1_vol,
                        "ask1_vol": quote.ask1_vol,
                        "type": "涨停" if change_pct > 0 else "跌停",
                    }),
                    "consecutive_count": 0,
                }

                if change_pct >= up_threshold:
                    limit_up.append(stock_info)
                elif change_pct <= down_threshold:
                    limit_down.append(stock_info)

            # 短暂休眠避免请求过快
            if i + self.BATCH_SIZE < total:
                await asyncio.sleep(0.2)

        return limit_up, limit_down

    async def _scan_hot_stocks(self) -> tuple:
        """回退方案：批量查询热门股票判断涨跌停"""
        # 热门股票池（用于新浪API故障时的回退）
        hot_stocks = [
            "sh600519", "sh600036", "sh601318", "sh600900", "sh600276",
            "sz000858", "sz000001", "sz002475", "sz002594", "sz002230",
            "sz300750", "sz300059", "sz300760", "sz300274", "sz300003",
            "sh688981", "sh688036", "sh688012", "sh688111", "sh688005",
        ]
        limit_up = []
        limit_down = []

        for i in range(0, len(hot_stocks), self.BATCH_SIZE):
            batch = hot_stocks[i:i + self.BATCH_SIZE]
            quotes = await collector.get_quotes(batch)

            for code, quote in quotes.items():
                change_pct = quote.change_pct
                up_threshold = self._get_limit_threshold(code)
                down_threshold = self._get_limit_down_threshold(code)
                board_type = self._get_board_type(code)
                limit_up_price, limit_down_price = self._calculate_limit_price(quote.pre_close, code)

                stock_info = {
                    "code": code,
                    "name": quote.name,
                    "price": quote.price,
                    "change_pct": change_pct,
                    "type": "涨停" if change_pct > 0 else "跌停",
                    "board_type": board_type,
                    "limit_pct": self._get_limit_pct(code),
                    "limit_up_price": limit_up_price,
                    "limit_down_price": limit_down_price,
                    "pre_close": quote.pre_close,
                    "volume": quote.volume,
                    "amount": quote.amount,
                    "turnover": 0,
                    "bid1_vol": quote.bid1_vol,
                    "ask1_vol": quote.ask1_vol,
                    "seal_amount": self._calculate_seal_amount({
                        "price": quote.price,
                        "bid1_vol": quote.bid1_vol,
                        "ask1_vol": quote.ask1_vol,
                        "type": "涨停" if change_pct > 0 else "跌停",
                    }),
                    "consecutive_count": 0,
                }

                if change_pct >= up_threshold:
                    limit_up.append(stock_info)
                elif change_pct <= down_threshold:
                    limit_down.append(stock_info)

        return limit_up, limit_down

    def _detect_broken_board(self, current_limit_up: List[dict]) -> List[dict]:
        """检测炸板信号（上一轮涨停但本轮未涨停的股票）"""
        broken = []
        current_codes = {s["code"] for s in current_limit_up}

        for code in self._prev_limit_up_codes:
            if code not in current_codes:
                # 上一轮涨停但本轮不在涨停列表中
                prev_stock = None
                for s in self.limit_up_stocks:
                    if s["code"] == code:
                        prev_stock = s
                        break

                if prev_stock:
                    broken.append({
                        "code": code,
                        "name": prev_stock.get("name", "未知"),
                        "prev_price": prev_stock.get("price", 0),
                        "prev_change_pct": prev_stock.get("change_pct", 0),
                        "signal": "炸板",
                        "message": f"{prev_stock.get('name', '')} 从涨停回落，疑似炸板",
                        "timestamp": datetime.now().isoformat(),
                    })

        return broken

    async def check_broken_board_realtime(self, code: str) -> Optional[dict]:
        """实时检测单只股票是否炸板（从涨停回落到涨幅<阈值）"""
        quotes = await collector.get_quotes([code])
        if code not in quotes:
            return None

        quote = quotes[code]
        change_pct = quote.change_pct
        limit_pct = self._get_limit_pct(code)
        broken_threshold = limit_pct * 0.7  # 炸板阈值：回落到涨停幅度的70%以下

        # 如果之前是涨停但现在涨幅<炸板阈值，视为炸板
        if code in self._prev_limit_up_codes and change_pct < broken_threshold:
            return {
                "code": code,
                "name": quote.name,
                "price": quote.price,
                "change_pct": change_pct,
                "signal": "炸板",
                "message": f"{quote.name} 从涨停回落至{change_pct:.2f}%，炸板信号",
                "timestamp": datetime.now().isoformat(),
            }

        return None

    async def get_stock_detail(self, code: str) -> Optional[dict]:
        """获取单只股票的涨跌停详细信息"""
        quotes = await collector.get_quotes([code])
        if code not in quotes:
            return None

        quote = quotes[code]
        change_pct = quote.change_pct
        limit_pct = self._get_limit_pct(code)
        limit_up_price, limit_down_price = self._calculate_limit_price(quote.pre_close, code)
        board_type = self._get_board_type(code)

        is_limit_up = change_pct >= self._get_limit_threshold(code)
        is_limit_down = change_pct <= self._get_limit_down_threshold(code)
        consecutive = self._consecutive_limit_up.get(code, 0)

        seal_amount = 0.0
        if is_limit_up:
            seal_amount = round(quote.bid1_vol * quote.price / 10000, 2)
        elif is_limit_down:
            seal_amount = round(quote.ask1_vol * quote.price / 10000, 2)

        return {
            "code": code,
            "name": quote.name,
            "price": quote.price,
            "pre_close": quote.pre_close,
            "change_pct": change_pct,
            "board_type": board_type,
            "limit_pct": limit_pct,
            "limit_up_price": limit_up_price,
            "limit_down_price": limit_down_price,
            "is_limit_up": is_limit_up,
            "is_limit_down": is_limit_down,
            "volume": quote.volume,
            "amount": quote.amount,
            "bid1_vol": quote.bid1_vol,
            "ask1_vol": quote.ask1_vol,
            "seal_amount": seal_amount,
            "consecutive_count": consecutive,
            "timestamp": datetime.now().isoformat(),
        }

    def get_summary(self) -> dict:
        """获取涨跌停概览"""
        # 按板块分类统计
        board_stats = {}
        for s in self.limit_up_stocks:
            bt = s.get("board_type", "主板")
            if bt not in board_stats:
                board_stats[bt] = {"limit_up": 0, "limit_down": 0, "seal_amount": 0.0}
            board_stats[bt]["limit_up"] += 1
            board_stats[bt]["seal_amount"] += s.get("seal_amount", 0)

        for s in self.limit_down_stocks:
            bt = s.get("board_type", "主板")
            if bt not in board_stats:
                board_stats[bt] = {"limit_up": 0, "limit_down": 0, "seal_amount": 0.0}
            board_stats[bt]["limit_down"] += 1

        # 连板统计
        consecutive_stats = {}
        for s in self.limit_up_stocks:
            count = s.get("consecutive_count", 0)
            if count >= 2:
                key = f"{count}连板"
                if key not in consecutive_stats:
                    consecutive_stats[key] = []
                consecutive_stats[key].append({
                    "code": s["code"],
                    "name": s["name"],
                    "change_pct": s["change_pct"],
                    "seal_amount": s.get("seal_amount", 0),
                })

        # 封单金额排行
        seal_amount_rank = sorted(
            [s for s in self.limit_up_stocks if s.get("seal_amount", 0) > 0],
            key=lambda x: x.get("seal_amount", 0),
            reverse=True,
        )[:20]

        return {
            "limit_up_count": len(self.limit_up_stocks),
            "limit_down_count": len(self.limit_down_stocks),
            "broken_board_count": len(self.broken_board_stocks),
            "limit_up_stocks": self.limit_up_stocks,
            "limit_down_stocks": self.limit_down_stocks,
            "broken_board_stocks": self.broken_board_stocks,
            "board_stats": board_stats,
            "consecutive_stats": consecutive_stats,
            "seal_amount_rank": seal_amount_rank,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    async def set_yesterday_limit_up(self, codes: List[str]):
        """设置昨日涨停列表（用于计算连板数）"""
        self._yesterday_limit_up = set(codes)
        logger.info(f"设置昨日涨停股 {len(codes)} 只")


# 单例
limit_monitor = LimitMonitor()
