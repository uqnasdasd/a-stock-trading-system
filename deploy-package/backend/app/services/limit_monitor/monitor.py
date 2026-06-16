"""涨跌停监控模块 - 实时检测全市场涨跌停与炸板信号"""
import httpx
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
from app.services.data_collector.sina_api import collector


class LimitMonitor:
    """涨跌停监控器"""

    # 热门股票池（用于批量查询判断涨跌停）
    HOT_STOCKS = [
        # 创业板热门
        "sz300750", "sz300059", "sz300760", "sz300274", "sz300003",
        "sz300033", "sz300142", "sz300285", "sz300413", "sz300431",
        # 科创板热门
        "sh688981", "sh688036", "sh688012", "sh688111", "sh688005",
        "sh688396", "sh688256", "sh688009", "sh688187", "sh688599",
        # 主板热门
        "sh600519", "sh600036", "sh601318", "sh600900", "sh600276",
        "sz000858", "sz000001", "sz002475", "sz002594", "sz002230",
        "sh600809", "sh601012", "sh600585", "sh601888", "sh600031",
        "sz002415", "sz002607", "sz000333", "sz002352", "sz002049",
        "sh603259", "sh600745", "sh601127", "sh600570", "sh603288",
        "sz300888", "sz300782", "sz300496", "sz300661", "sz300711",
        "sh688169", "sh688188", "sh688099", "sh688516", "sh688266",
        "sz002812", "sz002371", "sz002916", "sz000651", "sz002241",
        "sh601899", "sh600030", "sh601166", "sh600887", "sh600690",
        # 北交所热门
        "bj430047", "bj835305", "bj832735", "bj430198", "bj835185",
        "bj836077", "bj835174", "bj430489", "bj835640", "bj836263",
    ]

    def __init__(self):
        self.limit_up_stocks: List[dict] = []
        self.limit_down_stocks: List[dict] = []
        self.broken_board_stocks: List[dict] = []  # 炸板股
        self._prev_limit_up_codes: set = set()  # 上一轮涨停股代码（用于检测炸板）
        self._last_update: Optional[datetime] = None

    def _get_limit_threshold(self, code: str) -> float:
        """获取涨跌停阈值

        - 科创板(688开头): 20%
        - 北交所(8开头): 30%
        - 创业板(300/301开头): 20%
        - 主板: 10%
        """
        code_lower = code.lower()
        if code_lower.startswith("sh688") or code_lower.startswith("sz300") or code_lower.startswith("sz301"):
            return 19.9  # 科创板/创业板 20%
        if code_lower.startswith("bj") or code_lower.startswith("sh8") or code_lower.startswith("sz8"):
            return 29.9  # 北交所 30%
        return 9.9  # 主板 10%

    def _get_limit_down_threshold(self, code: str) -> float:
        """获取跌停阈值"""
        code_lower = code.lower()
        if code_lower.startswith("sh688") or code_lower.startswith("sz300") or code_lower.startswith("sz301"):
            return -19.9  # 科创板/创业板 20%
        if code_lower.startswith("bj") or code_lower.startswith("sh8") or code_lower.startswith("sz8"):
            return -29.9  # 北交所 30%
        return -9.9  # 主板 10%

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

    async def fetch_limit_data(self) -> dict:
        """获取涨跌停数据（通过新浪API + 批量查询）"""
        result = {
            "limit_up": [],
            "limit_down": [],
            "broken_board": [],
            "timestamp": datetime.now().isoformat(),
        }

        # 1. 尝试通过新浪排行榜API获取涨幅榜
        rank_data = await self._fetch_sina_rank()
        if rank_data:
            result["limit_up"] = rank_data["limit_up"]
            result["limit_down"] = rank_data["limit_down"]
        else:
            # 2. 回退到批量查询热门股票
            result["limit_up"], result["limit_down"] = await self._scan_hot_stocks()

        # 3. 检测炸板信号
        result["broken_board"] = self._detect_broken_board(result["limit_up"])

        # 更新缓存
        self.limit_up_stocks = result["limit_up"]
        self.limit_down_stocks = result["limit_down"]
        self.broken_board_stocks = result["broken_board"]
        self._prev_limit_up_codes = {s["code"] for s in result["limit_up"]}
        self._last_update = datetime.now()

        logger.info(
            f"涨跌停扫描完成: 涨停{len(result['limit_up'])}只, "
            f"跌停{len(result['limit_down'])}只, 炸板{len(result['broken_board'])}只"
        )

        return result

    async def _fetch_sina_rank(self) -> Optional[dict]:
        """通过新浪排行榜API获取涨跌幅数据"""
        url = (
            "http://vip.stock.finance.sina.com.cn/quotes_service/api/"
            "json_v2.php/Market_Center.getHQNodeStockCountSimple"
        )
        params = {
            "node": "hs_a",
            "num": "50",
            "_s_r_a": "auto",
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params, headers={
                    "Referer": "https://finance.sina.com.cn",
                    "User-Agent": "Mozilla/5.0",
                })

                # 新浪API可能返回JSONP格式或直接JSON
                text = response.text.strip()
                if not text or text == "null":
                    return None

                # 尝试解析JSON
                import json
                if text.startswith("var ") or text.startswith("callback"):
                    # JSONP格式，提取JSON部分
                    json_str = text[text.find("(") + 1:text.rfind(")")]
                    data = json.loads(json_str)
                else:
                    data = json.loads(text)

                if not isinstance(data, list):
                    return None

                limit_up = []
                limit_down = []

                for item in data:
                    try:
                        change_pct = float(item.get("changepercent", 0))
                        code = item.get("code", "")
                        name = item.get("name", "")
                        price = float(item.get("trade", 0))
                        board_type = self._get_board_type(code)
                        up_threshold = self._get_limit_threshold(code)
                        down_threshold = self._get_limit_down_threshold(code)

                        if change_pct >= up_threshold:
                            limit_up.append({
                                "code": code,
                                "name": name,
                                "price": price,
                                "change_pct": change_pct,
                                "type": "涨停",
                                "board_type": board_type,
                            })
                        elif change_pct <= down_threshold:
                            limit_down.append({
                                "code": code,
                                "name": name,
                                "price": price,
                                "change_pct": change_pct,
                                "type": "跌停",
                                "board_type": board_type,
                            })
                    except (ValueError, TypeError):
                        continue

                return {"limit_up": limit_up, "limit_down": limit_down}

        except Exception as e:
            logger.warning(f"新浪排行榜API请求失败: {e}")
            return None

    async def _scan_hot_stocks(self) -> tuple:
        """批量查询热门股票判断涨跌停"""
        limit_up = []
        limit_down = []

        # 分批查询（新浪API单次最多约50只）
        batch_size = 40
        for i in range(0, len(self.HOT_STOCKS), batch_size):
            batch = self.HOT_STOCKS[i:i + batch_size]
            quotes = await collector.get_quotes(batch)

            for code, quote in quotes.items():
                change_pct = quote.change_pct
                board_type = self._get_board_type(code)
                up_threshold = self._get_limit_threshold(code)
                down_threshold = self._get_limit_down_threshold(code)

                if change_pct >= up_threshold:
                    limit_up.append({
                        "code": code,
                        "name": quote.name,
                        "price": quote.price,
                        "change_pct": change_pct,
                        "type": "涨停",
                        "board_type": board_type,
                    })
                elif change_pct <= down_threshold:
                    limit_down.append({
                        "code": code,
                        "name": quote.name,
                        "price": quote.price,
                        "change_pct": change_pct,
                        "type": "跌停",
                        "board_type": board_type,
                    })

        return limit_up, limit_down

    def _detect_broken_board(self, current_limit_up: List[dict]) -> List[dict]:
        """检测炸板信号（上一轮涨停但本轮未涨停的股票）"""
        broken = []
        current_codes = {s["code"] for s in current_limit_up}

        for code in self._prev_limit_up_codes:
            if code not in current_codes:
                # 上一轮涨停但本轮不在涨停列表中
                # 查找该股票当前数据判断是否炸板
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
                        "signal": "炸板",
                        "message": f"{prev_stock.get('name', '')} 从涨停回落，疑似炸板",
                        "timestamp": datetime.now().isoformat(),
                    })

        return broken

    async def check_broken_board_realtime(self, code: str) -> Optional[dict]:
        """实时检测单只股票是否炸板（从涨停回落到涨幅<7%）"""
        quotes = await collector.get_quotes([code])
        if code not in quotes:
            return None

        quote = quotes[code]
        change_pct = quote.change_pct

        # 如果之前是涨停但现在涨幅<7%，视为炸板
        if code in self._prev_limit_up_codes and change_pct < 7.0:
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

    def get_summary(self) -> dict:
        """获取涨跌停概览"""
        # 按板块分类统计
        board_stats = {}
        for s in self.limit_up_stocks:
            bt = s.get("board_type", "主板")
            if bt not in board_stats:
                board_stats[bt] = {"limit_up": 0, "limit_down": 0}
            board_stats[bt]["limit_up"] += 1

        for s in self.limit_down_stocks:
            bt = s.get("board_type", "主板")
            if bt not in board_stats:
                board_stats[bt] = {"limit_up": 0, "limit_down": 0}
            board_stats[bt]["limit_down"] += 1

        return {
            "limit_up_count": len(self.limit_up_stocks),
            "limit_down_count": len(self.limit_down_stocks),
            "broken_board_count": len(self.broken_board_stocks),
            "limit_up_stocks": self.limit_up_stocks,
            "limit_down_stocks": self.limit_down_stocks,
            "broken_board_stocks": self.broken_board_stocks,
            "board_stats": board_stats,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }


# 单例
limit_monitor = LimitMonitor()
