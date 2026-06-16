"""多数据源股票API数据采集 - 新浪/腾讯/东方财富自动切换"""
import httpx
import asyncio
import json
import time
from typing import Dict, List, Optional
from loguru import logger
from app.models.schemas import StockQuote


class DataCollector:
    """多数据源股票数据采集器（新浪/腾讯/东方财富自动切换）"""

    # 新浪配置
    SINA_BASE_URL = "https://hq.sinajs.cn"
    SINA_KLINE_URL = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
    SINA_MINUTE_URL = "https://quotes.sina.cn/cn/api/quotes.php"

    # 腾讯配置
    TENCENT_BASE_URL = "http://qt.gtimg.cn/q="

    # 东方财富配置
    EASTMONEY_QUOTE_URL = "http://push2.eastmoney.com/api/qt/ulist.np/get"
    EASTMONEY_STOCK_URL = "http://push2.eastmoney.com/api/qt/stock/get"

    def __init__(self):
        self.timeout = 5.0
        self.max_retries = 3

    async def _request_with_retry(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        encoding: Optional[str] = None,
    ) -> Optional[str]:
        """带重试机制的HTTP请求"""
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params, headers=headers)
                    if encoding:
                        response.encoding = encoding
                    response.raise_for_status()
                    return response.text
            except httpx.TimeoutException:
                logger.warning(f"请求超时 [{attempt}/{self.max_retries}]: {url}")
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP错误 [{attempt}/{self.max_retries}]: {e.response.status_code} - {url}")
            except Exception as e:
                logger.warning(f"请求失败 [{attempt}/{self.max_retries}]: {e} - {url}")

            if attempt < self.max_retries:
                wait_time = attempt * 0.5
                await asyncio.sleep(wait_time)

        logger.error(f"请求最终失败（已重试{self.max_retries}次）: {url}")
        return None

    # ==================== 新浪数据源 ====================

    async def _get_quotes_sina(self, codes: List[str]) -> Dict[str, StockQuote]:
        """通过新浪API批量获取股票行情"""
        if not codes:
            return {}

        code_str = ",".join(codes)
        url = f"{self.SINA_BASE_URL}/list={code_str}"
        headers = {
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        text = await self._request_with_retry(url, headers=headers, encoding="gb2312")
        if text is None:
            return {}

        return self._parse_sina_quotes(text, codes)

    def _parse_sina_quotes(self, text: str, codes: List[str]) -> Dict[str, StockQuote]:
        """解析新浪返回的行情数据"""
        result = {}
        lines = text.strip().split(";")

        for i, line in enumerate(lines):
            if i >= len(codes):
                break
            if not line.strip():
                continue

            code = codes[i]
            try:
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
                logger.warning(f"解析新浪股票 {code} 数据失败: {e}")
                continue

        return result

    # ==================== 腾讯数据源 ====================

    async def _get_quotes_tencent(self, codes: List[str]) -> Dict[str, StockQuote]:
        """通过腾讯API批量获取股票行情
        API: http://qt.gtimg.cn/q=sh000001,sz399001
        返回格式: v_sh000001="1~上证指数~..."
        """
        if not codes:
            return {}

        # 腾讯格式兼容处理
        tencent_codes = []
        for code in codes:
            code_lower = code.lower()
            if code_lower.startswith("sh"):
                tencent_codes.append(code_lower)
            elif code_lower.startswith("sz"):
                tencent_codes.append(code_lower)
            elif code_lower.startswith("bj"):
                tencent_codes.append(code_lower)
            else:
                tencent_codes.append(code_lower)

        code_str = ",".join(tencent_codes)
        url = f"{self.TENCENT_BASE_URL}{code_str}"
        headers = {
            "Referer": "https://finance.qq.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        text = await self._request_with_retry(url, headers=headers)
        if text is None:
            return {}

        return self._parse_tencent_quotes(text, codes)

    def _parse_tencent_quotes(self, text: str, codes: List[str]) -> Dict[str, StockQuote]:
        """解析腾讯返回的行情数据
        格式: v_sh600000="1~浦发银行~600000~..."
        字段: 0=市场 1=名称 2=代码 3=当前价 4=昨收 5=今开 6=成交量 7=外盘 8=内盘
              9=买一价 10=买一量 11=卖一价 12=卖一量 ... 33=最高价 34=最低价 36=成交额
        """
        result = {}
        lines = text.strip().split(";")
        code_map = {c.lower(): c for c in codes}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                # v_sh600000="1~浦发银行~600000~..."
                if "=" not in line:
                    continue

                key_part, value_part = line.split("=", 1)
                value_part = value_part.strip().strip('"')

                # 提取代码
                key_lower = key_part.lower()
                if key_lower.startswith("v_"):
                    raw_code = key_lower[2:]
                else:
                    continue

                # 匹配原始代码
                original_code = code_map.get(raw_code)
                if not original_code:
                    continue

                parts = value_part.split("~")
                if len(parts) < 45:
                    continue

                quote = StockQuote(
                    code=original_code,
                    name=parts[1],
                    price=float(parts[3]) if parts[3] else 0,
                    pre_close=float(parts[4]) if parts[4] else 0,
                    open=float(parts[5]) if parts[5] else 0,
                    high=float(parts[33]) if parts[33] else 0,
                    low=float(parts[34]) if parts[34] else 0,
                    volume=int(float(parts[6])) if parts[6] else 0,
                    amount=float(parts[36]) if parts[36] else 0,
                    bid1=float(parts[9]) if parts[9] else 0,
                    ask1=float(parts[11]) if parts[11] else 0,
                    bid1_vol=int(float(parts[10])) if parts[10] else 0,
                    ask1_vol=int(float(parts[12])) if parts[12] else 0,
                )
                result[original_code] = quote
            except Exception as e:
                logger.warning(f"解析腾讯股票数据失败: {e}")
                continue

        return result

    # ==================== 东方财富数据源 ====================

    async def _get_quotes_eastmoney(self, codes: List[str]) -> Dict[str, StockQuote]:
        """通过东方财富API批量获取股票行情
        API: http://push2.eastmoney.com/api/qt/ulist.np/get
        """
        if not codes:
            return {}

        # 东方财富代码格式: 1.000001 (上海), 0.000001 (深圳), 0.430047 (北交所)
        em_codes = []
        for code in codes:
            code_lower = code.lower()
            if code_lower.startswith("sh"):
                em_codes.append(f"1.{code_lower[2:]}")
            elif code_lower.startswith("sz"):
                em_codes.append(f"0.{code_lower[2:]}")
            elif code_lower.startswith("bj"):
                em_codes.append(f"0.{code_lower[2:]}")
            else:
                em_codes.append(f"1.{code_lower}")

        code_str = ",".join(em_codes)
        url = self.EASTMONEY_QUOTE_URL
        params = {
            "fltt": "2",
            "invt": "2",
            "fields": "f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f17,f18,f15,f16,f33,f34,f35,f36,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90,f91",
            "secids": code_str,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "_": str(int(time.time() * 1000)),
        }
        headers = {
            "Referer": "https://quote.eastmoney.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        text = await self._request_with_retry(url, params=params, headers=headers)
        if text is None:
            return {}

        return self._parse_eastmoney_quotes(text, codes)

    def _parse_eastmoney_quotes(self, text: str, codes: List[str]) -> Dict[str, StockQuote]:
        """解析东方财富返回的行情数据"""
        result = {}
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                return result

            diff = data.get("data", {}).get("diff", [])
            if not diff:
                return result

            # 构建代码映射
            code_map = {}
            for c in codes:
                cl = c.lower()
                if cl.startswith("sh"):
                    code_map[cl[2:]] = c
                elif cl.startswith("sz"):
                    code_map[cl[2:]] = c
                elif cl.startswith("bj"):
                    code_map[cl[2:]] = c
                else:
                    code_map[cl] = c

            for item in diff:
                try:
                    raw_code = str(item.get("f12", ""))
                    original_code = code_map.get(raw_code.lower())
                    if not original_code:
                        continue

                    # 东方财富字段映射
                    # f2=最新价 f3=涨跌幅 f4=涨跌额 f5=成交量 f6=成交额
                    # f7=振幅 f8=换手率 f9=市盈率 f10=量比 f11=5分钟涨跌
                    # f15=最高 f16=最低 f17=今开 f18=昨收
                    # f33=委比 f34=委差 f35=卖一价 f36=卖一量 f37=卖二价 ...
                    # f57=名称
                    price = float(item.get("f2", 0)) if item.get("f2") else 0
                    pre_close = float(item.get("f18", 0)) if item.get("f18") else 0
                    if price == 0 and pre_close == 0:
                        continue

                    quote = StockQuote(
                        code=original_code,
                        name=item.get("f14", ""),
                        price=price,
                        pre_close=pre_close,
                        open=float(item.get("f17", 0)) if item.get("f17") else 0,
                        high=float(item.get("f15", 0)) if item.get("f15") else 0,
                        low=float(item.get("f16", 0)) if item.get("f16") else 0,
                        volume=int(float(item.get("f5", 0))) if item.get("f5") else 0,
                        amount=float(item.get("f6", 0)) if item.get("f6") else 0,
                        bid1=float(item.get("f19", 0)) if item.get("f19") else 0,
                        ask1=float(item.get("f31", 0)) if item.get("f31") else 0,
                        bid1_vol=int(float(item.get("f20", 0))) if item.get("f20") else 0,
                        ask1_vol=int(float(item.get("f32", 0))) if item.get("f32") else 0,
                    )
                    result[original_code] = quote
                except Exception as e:
                    logger.warning(f"解析东方财富单条数据失败: {e}")
                    continue

        except json.JSONDecodeError as e:
            logger.warning(f"解析东方财富JSON失败: {e}")
        except Exception as e:
            logger.warning(f"解析东方财富数据失败: {e}")

        return result

    # ==================== 统一入口 ====================

    async def get_quotes(self, codes: List[str]) -> Dict[str, StockQuote]:
        """批量获取股票行情（自动切换数据源: 新浪 -> 腾讯 -> 东方财富）"""
        if not codes:
            return {}

        # 1. 尝试新浪
        result = await self._get_quotes_sina(codes)
        if result and len(result) >= len(codes) * 0.5:
            logger.debug(f"新浪数据源成功获取 {len(result)}/{len(codes)} 只股票")
            return result

        logger.warning(f"新浪数据源获取不完整 ({len(result)}/{len(codes)})，尝试腾讯数据源")

        # 2. 尝试腾讯
        result = await self._get_quotes_tencent(codes)
        if result and len(result) >= len(codes) * 0.5:
            logger.debug(f"腾讯数据源成功获取 {len(result)}/{len(codes)} 只股票")
            return result

        logger.warning(f"腾讯数据源获取不完整 ({len(result)}/{len(codes)})，尝试东方财富数据源")

        # 3. 尝试东方财富
        result = await self._get_quotes_eastmoney(codes)
        if result:
            logger.debug(f"东方财富数据源成功获取 {len(result)}/{len(codes)} 只股票")
            return result

        logger.error(f"所有数据源均失败，无法获取 {len(codes)} 只股票的行情")
        return {}

    async def get_index_quotes(self) -> Dict[str, StockQuote]:
        """获取大盘指数行情"""
        index_codes = ["sh000001", "sz399001", "sz399006", "sh000300", "sh000905"]
        return await self.get_quotes(index_codes)

    async def get_auction_data(self, codes: List[str]) -> Dict[str, dict]:
        """获取竞价数据（复用行情接口，9:15-9:25时段）"""
        return await self.get_quotes(codes)

    # ==================== K线数据 ====================

    async def get_kline(self, code: str, scale: int = 5, datalen: int = 100) -> List[dict]:
        """获取K线数据
        scale: 周期 1=1分钟 5=5分钟 15=15分钟 30=30分钟 60=60分钟 240=日线
        datalen: 数据条数，最大1023
        """
        url = self.SINA_KLINE_URL
        params = {
            "symbol": code,
            "scale": scale,
            "ma": "no",
            "datalen": min(datalen, 1023),
        }
        headers = {
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0",
        }

        text = await self._request_with_retry(url, params=params, headers=headers, timeout=15)
        if text is None:
            return []

        try:
            data = json.loads(text)
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
        except Exception as e:
            logger.error(f"K线数据解析失败 {code}: {e}")

        return []

    # ==================== 分时数据 ====================

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
        url = self.SINA_MINUTE_URL
        params = {"symbol": code, "__s": "1"}
        headers = {
            "Referer": "https://finance.sina.com.cn",
            "User-Agent": "Mozilla/5.0",
        }

        text = await self._request_with_retry(url, params=params, headers=headers)
        if text is None:
            return None

        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                return None

            result = data.get("result", {})
            if not result:
                return None

            data_list = result.get("data", [])
            if not data_list:
                return None

            return [
                {
                    "time": item.get("t", ""),
                    "price": float(item.get("p", 0)),
                    "avg_price": float(item.get("avg_p", 0)),
                    "volume": int(item.get("v", 0)),
                }
                for item in data_list
            ]
        except Exception as e:
            logger.warning(f"新浪分时图API解析失败: {e}")
            return None

    # ==================== 东方财富专用接口 ====================

    async def get_all_a_stocks_from_eastmoney(self) -> List[dict]:
        """从东方财富获取全部A股列表
        API: http://push2.eastmoney.com/api/qt/clist/get
        """
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": "1",
            "pz": "5000",
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f12",
            "fs": "m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23",
            "fields": "f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152",
            "_": str(int(time.time() * 1000)),
        }
        headers = {
            "Referer": "https://quote.eastmoney.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        text = await self._request_with_retry(url, params=params, headers=headers)
        if text is None:
            return []

        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                return []

            diff = data.get("data", {}).get("diff", [])
            stocks = []
            for item in diff:
                try:
                    code = str(item.get("f12", ""))
                    market = str(item.get("f13", ""))
                    # 构建标准代码
                    if market == "1":
                        std_code = f"sh{code}"
                    elif market == "0":
                        std_code = f"sz{code}"
                    else:
                        std_code = f"sz{code}"

                    stocks.append({
                        "code": std_code,
                        "name": item.get("f14", ""),
                        "price": float(item.get("f2", 0)) if item.get("f2") else 0,
                        "change_pct": float(item.get("f3", 0)) if item.get("f3") else 0,
                        "change_amount": float(item.get("f4", 0)) if item.get("f4") else 0,
                        "volume": int(float(item.get("f5", 0))) if item.get("f5") else 0,
                        "amount": float(item.get("f6", 0)) if item.get("f6") else 0,
                        "amplitude": float(item.get("f7", 0)) if item.get("f7") else 0,
                        "turnover": float(item.get("f8", 0)) if item.get("f8") else 0,
                        "pe": float(item.get("f9", 0)) if item.get("f9") else 0,
                        "volume_ratio": float(item.get("f10", 0)) if item.get("f10") else 0,
                        "high": float(item.get("f15", 0)) if item.get("f15") else 0,
                        "low": float(item.get("f16", 0)) if item.get("f16") else 0,
                        "open": float(item.get("f17", 0)) if item.get("f17") else 0,
                        "pre_close": float(item.get("f18", 0)) if item.get("f18") else 0,
                        "total_market_cap": float(item.get("f20", 0)) if item.get("f20") else 0,
                        "circulating_market_cap": float(item.get("f21", 0)) if item.get("f21") else 0,
                        "pb": float(item.get("f23", 0)) if item.get("f23") else 0,
                    })
                except Exception as e:
                    logger.warning(f"解析单只股票数据失败: {e}")
                    continue

            logger.info(f"从东方财富获取到 {len(stocks)} 只A股")
            return stocks
        except Exception as e:
            logger.error(f"解析东方财富A股列表失败: {e}")
            return []

    async def get_sector_stocks_from_eastmoney(self, sector_code: str) -> List[dict]:
        """从东方财富获取板块成分股
        sector_code: 板块代码，如 BK0477（光伏设备）
        """
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": "1",
            "pz": "500",
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f12",
            "fs": f"b:{sector_code}",
            "fields": "f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18,f20,f21",
            "_": str(int(time.time() * 1000)),
        }
        headers = {
            "Referer": "https://quote.eastmoney.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        text = await self._request_with_retry(url, params=params, headers=headers)
        if text is None:
            return []

        try:
            data = json.loads(text)
            diff = data.get("data", {}).get("diff", [])
            stocks = []
            for item in diff:
                try:
                    code = str(item.get("f12", ""))
                    market = str(item.get("f13", ""))
                    if market == "1":
                        std_code = f"sh{code}"
                    elif market == "0":
                        std_code = f"sz{code}"
                    else:
                        std_code = f"sz{code}"

                    stocks.append({
                        "code": std_code,
                        "name": item.get("f14", ""),
                        "price": float(item.get("f2", 0)) if item.get("f2") else 0,
                        "change_pct": float(item.get("f3", 0)) if item.get("f3") else 0,
                        "volume": int(float(item.get("f5", 0))) if item.get("f5") else 0,
                        "amount": float(item.get("f6", 0)) if item.get("f6") else 0,
                    })
                except Exception:
                    continue
            return stocks
        except Exception as e:
            logger.error(f"获取板块成分股失败 {sector_code}: {e}")
            return []

    async def get_hot_sectors_from_eastmoney(self) -> List[dict]:
        """从东方财富获取热门板块排行"""
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": "1",
            "pz": "100",
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:90+t:2",
            "fields": "f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f20,f21",
            "_": str(int(time.time() * 1000)),
        }
        headers = {
            "Referer": "https://quote.eastmoney.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        text = await self._request_with_retry(url, params=params, headers=headers)
        if text is None:
            return []

        try:
            data = json.loads(text)
            diff = data.get("data", {}).get("diff", [])
            sectors = []
            for item in diff:
                try:
                    sectors.append({
                        "code": str(item.get("f12", "")),
                        "name": item.get("f14", ""),
                        "price": float(item.get("f2", 0)) if item.get("f2") else 0,
                        "change_pct": float(item.get("f3", 0)) if item.get("f3") else 0,
                        "change_amount": float(item.get("f4", 0)) if item.get("f4") else 0,
                        "volume": int(float(item.get("f5", 0))) if item.get("f5") else 0,
                        "amount": float(item.get("f6", 0)) if item.get("f6") else 0,
                        "total_market_cap": float(item.get("f20", 0)) if item.get("f20") else 0,
                    })
                except Exception:
                    continue
            return sectors
        except Exception as e:
            logger.error(f"获取热门板块失败: {e}")
            return []


# 单例（保持向后兼容）
collector = DataCollector()
