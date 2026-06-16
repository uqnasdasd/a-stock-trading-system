"""龙虎榜数据模块"""
import httpx
import json
from typing import List, Optional
from datetime import datetime
from loguru import logger


class DragonTigerService:
    """龙虎榜数据服务

    通过东方财富API获取当日龙虎榜数据
    """

    async def get_today_dragon_tiger(self) -> List[dict]:
        """获取当日龙虎榜数据

        Returns:
            龙虎榜列表，包含上榜股票、买卖营业部、净买入额
        """
        # 东方财富龙虎榜API
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "sortColumns": "NET_BUY_AMT",
            "sortTypes": "-1",
            "pageSize": "50",
            "pageNumber": "1",
            "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, params=params, headers={
                    "Referer": "https://data.eastmoney.com",
                    "User-Agent": "Mozilla/5.0"
                })
                data = response.json()

                if not isinstance(data, dict):
                    logger.warning("龙虎榜API返回格式异常")
                    return []

                result = data.get("result", {})
                if not result:
                    logger.warning("龙虎榜API返回空数据")
                    return []

                items = result.get("data", [])
                if not items:
                    return []

                dragon_list = []
                for item in items:
                    try:
                        dragon = self._parse_dragon_item(item)
                        if dragon:
                            dragon_list.append(dragon)
                    except Exception as e:
                        logger.warning(f"解析龙虎榜数据失败: {e}")
                        continue

                logger.info(f"获取龙虎榜数据: {len(dragon_list)}条")
                return dragon_list

        except Exception as e:
            logger.error(f"龙虎榜API请求失败: {e}")
            return []

    def _parse_dragon_item(self, item: dict) -> Optional[dict]:
        """解析单条龙虎榜数据"""
        code = item.get("SECURITY_CODE", "")
        name = item.get("SECURITY_NAME_ABBR", "")

        if not code or not name:
            return None

        # 净买入额
        net_buy = 0.0
        try:
            net_buy = float(item.get("NET_BUY_AMT", 0))
        except (ValueError, TypeError):
            pass

        # 买入额
        buy_amt = 0.0
        try:
            buy_amt = float(item.get("BUY_AMT", 0))
        except (ValueError, TypeError):
            pass

        # 卖出额
        sell_amt = 0.0
        try:
            sell_amt = float(item.get("SELL_AMT", 0))
        except (ValueError, TypeError):
            pass

        # 买入营业部
        buy_depts = []
        for i in range(1, 6):
            dept_name = item.get(f"BUY_DEPT_NAME_{i}", "")
            dept_amt = item.get(f"BUY_DEPT_AMT_{i}", 0)
            if dept_name:
                try:
                    buy_depts.append({
                        "name": dept_name,
                        "amount": float(dept_amt),
                    })
                except (ValueError, TypeError):
                    pass

        # 卖出营业部
        sell_depts = []
        for i in range(1, 6):
            dept_name = item.get(f"SELL_DEPT_NAME_{i}", "")
            dept_amt = item.get(f"SELL_DEPT_AMT_{i}", 0)
            if dept_name:
                try:
                    sell_depts.append({
                        "name": dept_name,
                        "amount": float(dept_amt),
                    })
                except (ValueError, TypeError):
                    pass

        # 上榜原因
        reason = item.get("EXPLANATION", "")

        # 收盘价和涨跌幅
        close_price = 0.0
        try:
            close_price = float(item.get("CLOSE_PRICE", 0))
        except (ValueError, TypeError):
            pass

        change_pct = 0.0
        try:
            change_pct = float(item.get("CHANGE_RATE", 0))
        except (ValueError, TypeError):
            pass

        return {
            "code": code,
            "name": name,
            "net_buy": round(net_buy, 2),
            "buy_amount": round(buy_amt, 2),
            "sell_amount": round(sell_amt, 2),
            "close_price": round(close_price, 2),
            "change_pct": round(change_pct, 2),
            "reason": reason,
            "buy_departments": buy_depts,
            "sell_departments": sell_depts,
            "timestamp": datetime.now().isoformat(),
        }

    async def get_dragon_summary(self) -> dict:
        """获取龙虎榜概览"""
        dragons = await self.get_today_dragon_tiger()

        if not dragons:
            return {
                "timestamp": datetime.now().isoformat(),
                "count": 0,
                "total_net_buy": 0,
                "top_stocks": [],
            }

        # 按净买入额排序
        sorted_dragons = sorted(dragons, key=lambda x: x["net_buy"], reverse=True)

        # 总净买入
        total_net_buy = sum(d["net_buy"] for d in dragons)

        # 取净买入前10
        top_stocks = sorted_dragons[:10]

        return {
            "timestamp": datetime.now().isoformat(),
            "count": len(dragons),
            "total_net_buy": round(total_net_buy, 2),
            "top_stocks": top_stocks,
        }


# 单例
dragon_tiger_service = DragonTigerService()
