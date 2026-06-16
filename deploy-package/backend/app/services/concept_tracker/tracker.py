"""概念板块轮动追踪模块"""
import httpx
import json
from typing import List, Optional
from datetime import datetime
from loguru import logger


class ConceptTracker:
    """概念板块轮动追踪器

    通过新浪概念板块API获取当日热点概念
    API: http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=50&node=gn&sort=changepercent&asc=0
    """

    async def get_hot_concepts(self, num: int = 50) -> List[dict]:
        """获取当日热点概念板块

        Args:
            num: 返回概念数量

        Returns:
            概念列表，包含名称、涨幅、领涨股
        """
        url = (
            "http://vip.stock.finance.sina.com.cn/quotes_service/api/"
            "json_v2.php/Market_Center.getHQNodeData"
        )
        params = {
            "page": "1",
            "num": str(num),
            "node": "gn",
            "sort": "changepercent",
            "asc": "0",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, params=params, headers={
                    "Referer": "https://finance.sina.com.cn",
                    "User-Agent": "Mozilla/5.0"
                })
                text = response.text.strip()

                if not text or text == "null":
                    logger.warning("概念板块API返回空数据")
                    return []

                # 新浪API返回的JSON可能不是标准格式，需要处理
                data = self._parse_sina_json(text)

                if not isinstance(data, list):
                    logger.warning(f"概念板块API返回格式异常: {type(data)}")
                    return []

                concepts = []
                for item in data:
                    try:
                        concept = self._parse_concept_item(item)
                        if concept:
                            concepts.append(concept)
                    except Exception as e:
                        logger.warning(f"解析概念板块数据失败: {e}")
                        continue

                logger.info(f"获取热点概念: {len(concepts)}个")
                return concepts

        except Exception as e:
            logger.error(f"概念板块API请求失败: {e}")
            return []

    def _parse_sina_json(self, text: str) -> Optional[list]:
        """解析新浪返回的JSON数据（可能包含特殊格式）"""
        try:
            # 尝试直接解析
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        try:
            # 处理可能的JSONP格式
            if text.startswith("var ") or text.startswith("callback"):
                json_str = text[text.find("(") + 1:text.rfind(")")]
                return json.loads(json_str)
        except Exception:
            pass

        try:
            # 处理可能的非标准JSON（如单引号等）
            # 新浪API有时会返回类似Python字典的格式
            text = text.replace("'", '"')
            return json.loads(text)
        except Exception:
            pass

        return []

    def _parse_concept_item(self, item: dict) -> Optional[dict]:
        """解析单个概念板块数据"""
        name = item.get("name", "")
        if not name:
            return None

        # 提取涨幅
        change_pct = 0.0
        try:
            change_pct = float(item.get("changepercent", 0))
        except (ValueError, TypeError):
            pass

        # 提取领涨股
        leader_name = item.get("stockname", "")
        leader_code = item.get("stockcode", "")
        leader_change = 0.0
        try:
            leader_change = float(item.get("stockprice", 0))
        except (ValueError, TypeError):
            pass

        # 提取板块内股票数量
        stock_count = 0
        try:
            stock_count = int(item.get("num", 0))
        except (ValueError, TypeError):
            pass

        # 提取上涨家数
        up_count = 0
        try:
            up_count = int(item.get("upnum", 0))
        except (ValueError, TypeError):
            pass

        # 提取下跌家数
        down_count = 0
        try:
            down_count = int(item.get("downnum", 0))
        except (ValueError, TypeError):
            pass

        return {
            "name": name,
            "change_pct": round(change_pct, 2),
            "leader_name": leader_name,
            "leader_code": leader_code,
            "leader_change": round(leader_change, 2),
            "stock_count": stock_count,
            "up_count": up_count,
            "down_count": down_count,
            "timestamp": datetime.now().isoformat(),
        }

    async def get_concept_summary(self) -> dict:
        """获取概念板块概览"""
        concepts = await self.get_hot_concepts(num=20)

        if not concepts:
            return {
                "timestamp": datetime.now().isoformat(),
                "top_concepts": [],
                "rising_count": 0,
                "falling_count": 0,
            }

        # 上涨和下跌的概念数量
        rising = [c for c in concepts if c["change_pct"] > 0]
        falling = [c for c in concepts if c["change_pct"] < 0]

        # 取涨幅前10
        top_concepts = sorted(concepts, key=lambda x: x["change_pct"], reverse=True)[:10]

        return {
            "timestamp": datetime.now().isoformat(),
            "top_concepts": top_concepts,
            "rising_count": len(rising),
            "falling_count": len(falling),
            "total_count": len(concepts),
        }


# 单例
concept_tracker = ConceptTracker()
