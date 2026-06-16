"""新浪财经API数据采集"""
import httpx
import asyncio
from typing import Dict, List, Optional
from loguru import logger
from app.models.schemas import StockQuote


class SinaDataCollector:
    """新浪财经数据采集器"""

    BASE_URL = "https://hq.sinajs.cn"

    async def get_quotes(self, codes: List[str]) -> Dict[str, StockQuote]:
        """批量获取股票行情"""
        if not codes:
            return {}

        # 新浪API格式: sh600000,sz000001
        code_str = ",".join(codes)
        url = f"{self.BASE_URL}/list={code_str}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers={
                    "Referer": "https://finance.sina.com.cn",
                    "User-Agent": "Mozilla/5.0"
                })
                response.encoding = "gb2312"
                return self._parse_quotes(response.text, codes)
        except Exception as e:
            logger.error(f"新浪API请求失败: {e}")
            return {}

    def _parse_quotes(self, text: str, codes: List[str]) -> Dict[str, StockQuote]:
        """解析新浪返回数据"""
        result = {}
        lines = text.strip().split(";")

        for i, line in enumerate(lines):
            if i >= len(codes):
                break
            if not line.strip():
                continue

            code = codes[i]
            try:
                # 格式: var hq_str_sh600000="名称,今日开盘价,昨日收盘价,当前价,最高价,最低价,竞买价,竞卖价,成交量,成交额,..."
                data_str = line.split('="')[1].rstrip('"')
                parts = data_str.split(",")

                if len(parts) < 33:
                    continue

                quote = StockQuote(
                    code=code,
                    name=parts[0],
                    open=float(parts[1]),
                    pre_close=float(parts[2]),
                    price=float(parts[3]),
                    high=float(parts[4]),
                    low=float(parts[5]),
                    volume=int(parts[8]),
                    amount=float(parts[9]),
                    bid1=float(parts[11]) if parts[11] else 0,
                    ask1=float(parts[21]) if parts[21] else 0,
                    bid1_vol=int(parts[10]) if parts[10] else 0,
                    ask1_vol=int(parts[20]) if parts[20] else 0,
                )
                result[code] = quote
            except Exception as e:
                logger.warning(f"解析股票 {code} 数据失败: {e}")
                continue

        return result

    async def get_index_quotes(self) -> Dict[str, StockQuote]:
        """获取大盘指数行情"""
        index_codes = ["sh000001", "sz399001", "sz399006", "sh000300", "sh000905"]
        return await self.get_quotes(index_codes)

    async def get_auction_data(self, codes: List[str]) -> Dict[str, dict]:
        """获取竞价数据（复用行情接口，9:15-9:25时段）"""
        return await self.get_quotes(codes)

    async def get_kline(self, code: str, scale: int = 5, datalen: int = 100) -> List[dict]:
        """获取K线数据
        scale: 周期 1=1分钟 5=5分钟 15=15分钟 30=30分钟 60=60分钟 240=日线
        datalen: 数据条数，最大1023
        """
        url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
        params = {
            "symbol": code,
            "scale": scale,
            "ma": "no",
            "datalen": min(datalen, 1023),
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, params=params, headers={
                    "Referer": "https://finance.sina.com.cn",
                    "User-Agent": "Mozilla/5.0"
                })
                data = response.json()
                if isinstance(data, list):
                    return [
                        {
                            "day": item.get("day", ""),
                            "open": float(item.get("open", 0)),
                            "high": float(item.get("high", 0)),
                            "low": float(item.get("low", 0)),
                            "close": float(item.get("close", 0)),
                            "volume": int(item.get("volume", 0)),
                        }
                        for item in data
                    ]
                return []
        except Exception as e:
            logger.error(f"K线数据请求失败 {code}: {e}")
            return []

    async def get_minute_data(self, code: str) -> List[dict]:
        """获取分时图数据
        通过新浪分时图API或1分钟K线数据获取
        """
        # 方法1: 尝试新浪分时图API
        try:
            minute_data = await self._get_sina_minute_data(code)
            if minute_data:
                return minute_data
        except Exception as e:
            logger.warning(f"新浪分时图API请求失败，回退到K线数据: {e}")

        # 方法2: 回退到1分钟K线数据
        kline = await self.get_kline(code, scale=1, datalen=240)
        return [
            {
                "time": item["day"],
                "price": item["close"],
                "avg_price": round((item["open"] + item["high"] + item["low"] + item["close"]) / 4, 2),
                "volume": item["volume"],
            }
            for item in kline
        ]

    async def _get_sina_minute_data(self, code: str) -> Optional[List[dict]]:
        """通过新浪分时图API获取数据
        API: https://quotes.sina.cn/cn/api/quotes.php?symbol=sh600519&__s=1
        """
        url = f"https://quotes.sina.cn/cn/api/quotes.php"
        params = {
            "symbol": code,
            "__s": "1",
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params, headers={
                    "Referer": "https://finance.sina.com.cn",
                    "User-Agent": "Mozilla/5.0"
                })
                data = response.json()

                if not isinstance(data, dict):
                    return None

                result = data.get("result", {})
                if not result:
                    return None

                # 解析分时数据
                data_list = result.get("data", [])
                if not data_list:
                    return None

                minute_data = []
                for item in data_list:
                    minute_data.append({
                        "time": item.get("t", ""),
                        "price": float(item.get("p", 0)),
                        "avg_price": float(item.get("avg_p", 0)),
                        "volume": int(item.get("v", 0)),
                    })

                return minute_data
        except Exception as e:
            logger.warning(f"新浪分时图API解析失败: {e}")
            return None


# 单例
collector = SinaDataCollector()
