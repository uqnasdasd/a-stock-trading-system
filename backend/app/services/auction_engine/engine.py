"""竞价引擎 - 核心模块M1（板块映射动态化版）"""
from typing import Dict, List, Optional
from datetime import datetime, time
from loguru import logger
from app.models.schemas import StockQuote, SectorStrength, LeaderScore
from app.services.data_collector.sina_api import collector
from app.core.database import (
    db_save_auction_volume,
    db_get_auction_volume,
)


# 默认板块映射（作为回退，当东方财富接口不可用时使用）
DEFAULT_SECTOR_MAP = {
    # 新能源
    "光伏": ["sh600438", "sz002459", "sh601012", "sz300274", "sh688599", "sz002129", "sh600732"],
    "锂电池": ["sz002594", "sz300014", "sz002709", "sh603659", "sz002460", "sh600884", "sz300073"],
    "储能": ["sz300274", "sh688063", "sz002335", "sh601222", "sz300068"],
    # 科技
    "芯片": ["sh603501", "sz002371", "sh688981", "sz300782", "sh600584", "sz000938", "sh603893"],
    "AI算力": ["sz000938", "sh603019", "sz002230", "sh601138", "sz300308", "sh600845"],
    "机器人": ["sz002050", "sh603486", "sz002747", "sh688017", "sz300124"],
    # 消费
    "白酒": ["sh600519", "sz000858", "sz000568", "sh600809", "sz002304", "sh600702"],
    "医药": ["sh600276", "sz000538", "sh603259", "sz300122", "sh600196", "sh600436", "sz000963"],
    # 金融地产
    "银行": ["sh601398", "sh601288", "sh601939", "sh601988", "sh600036", "sh601166"],
    "地产": ["sh600048", "sz000002", "sh601155", "sh600383", "sz001979", "sh600606"],
    "券商": ["sh600030", "sh601688", "sh600837", "sz000776", "sh601211"],
    # 周期
    "电力": ["sh600027", "sh600795", "sh600011", "sz000027", "sh600021", "sh600900"],
    "煤炭": ["sh601088", "sh601225", "sh600188", "sh601699", "sh600546"],
    "有色": ["sh601899", "sh600362", "sh603993", "sz000878", "sh600111"],
    "化工": ["sh600309", "sz002812", "sh601233", "sh600143", "sz002064", "sh600426"],
    # 制造
    "汽车": ["sh601633", "sz002594", "sh600104", "sz000625", "sh601127", "sh600660"],
    "军工": ["sh600893", "sh600372", "sz000768", "sh600760", "sh600482"],
    "机械": ["sh600031", "sz000425", "sh601766", "sh601100", "sz000157"],
    # 其他
    "传媒": ["sz002027", "sh600088", "sz300413", "sh600373", "sz002517"],
    "通信": ["sh600050", "sh600498", "sz000063", "sh600487", "sz300502"],
    "计算机": ["sh600570", "sz000977", "sh600728", "sz300033", "sh600536"],
}


class AuctionEngine:
    """竞价引擎 - 支持动态板块映射"""

    def __init__(self):
        self.sector_data: Dict[str, List[StockQuote]] = {}
        self.leader_scores: List[LeaderScore] = []
        self.sector_strengths: List[SectorStrength] = []
        self.yesterday_limit_up: List[str] = []  # 昨日涨停股列表
        # 动态板块数据
        self._sector_map: Dict[str, List[str]] = {}
        self._sector_map_cache_time: Optional[datetime] = None
        self._hot_sectors: List[dict] = []
        self._hot_sectors_cache_time: Optional[datetime] = None

    async def _get_sector_map(self) -> Dict[str, List[str]]:
        """获取板块映射（优先从东方财富动态获取，失败时使用默认映射）"""
        now = datetime.now()
        if (self._sector_map and self._sector_map_cache_time and
            (now - self._sector_map_cache_time).seconds < 600):
            return self._sector_map

        # 尝试从东方财富获取热门板块及其成分股
        try:
            hot_sectors = await collector.get_hot_sectors_from_eastmoney()
            if hot_sectors:
                sector_map = {}
                # 取涨幅前20的板块
                top_sectors = sorted(hot_sectors, key=lambda x: x.get("change_pct", 0), reverse=True)[:20]

                for sector in top_sectors:
                    sector_code = sector.get("code", "")
                    sector_name = sector.get("name", "")
                    if not sector_code or not sector_name:
                        continue

                    # 获取板块成分股
                    stocks = await collector.get_sector_stocks_from_eastmoney(sector_code)
                    if stocks:
                        codes = [s["code"] for s in stocks if s.get("code")]
                        if codes:
                            sector_map[sector_name] = codes

                if sector_map:
                    self._sector_map = sector_map
                    self._sector_map_cache_time = now
                    logger.info(f"动态获取板块映射成功: {len(sector_map)} 个板块")
                    return sector_map
        except Exception as e:
            logger.warning(f"动态获取板块映射失败: {e}")

        # 回退到默认映射
        self._sector_map = DEFAULT_SECTOR_MAP.copy()
        self._sector_map_cache_time = now
        logger.info("使用默认板块映射")
        return self._sector_map

    async def _get_hot_sectors(self) -> List[dict]:
        """获取热门板块排行（带缓存）"""
        now = datetime.now()
        if (self._hot_sectors and self._hot_sectors_cache_time and
            (now - self._hot_sectors_cache_time).seconds < 300):
            return self._hot_sectors

        try:
            sectors = await collector.get_hot_sectors_from_eastmoney()
            if sectors:
                # 按涨跌幅排序，取前15
                self._hot_sectors = sorted(
                    sectors, key=lambda x: x.get("change_pct", 0), reverse=True
                )[:15]
                self._hot_sectors_cache_time = now
                return self._hot_sectors
        except Exception as e:
            logger.warning(f"获取热门板块失败: {e}")

        return []

    async def run_auction_analysis(self, watchlist: List[str]) -> dict:
        """运行竞价分析"""
        logger.info("开始竞价分析...")

        # 1. 获取板块映射（动态化）
        sector_map = await self._get_sector_map()

        # 2. 获取所有关注股票的竞价数据
        all_codes = self._get_all_codes(watchlist, sector_map)
        quotes = await collector.get_quotes(all_codes)

        if not quotes:
            logger.warning("未获取到竞价数据")
            return {"error": "无数据"}

        # 3. 按板块分组
        self._group_by_sector(quotes, sector_map)

        # 4. 计算板块强度
        self.sector_strengths = self._calculate_sector_strength()

        # 5. 计算龙头评分
        self.leader_scores = self._calculate_leader_scores()

        # 6. 计算情绪晴雨表
        emotion = self._calculate_emotion(quotes)

        # 7. 筛选潜力标的
        candidates = self._filter_candidates()

        # 8. 获取竞价量能数据
        auction_volume_data = await self._get_auction_volume_data(quotes)

        # 9. 获取热门板块信息
        hot_sectors = await self._get_hot_sectors()

        return {
            "timestamp": datetime.now().isoformat(),
            "sector_strengths": [s.model_dump() for s in sorted(
                self.sector_strengths, key=lambda x: x.score, reverse=True
            )[:5]],
            "leader_scores": [l.model_dump() for l in sorted(
                self.leader_scores, key=lambda x: x.score, reverse=True
            )[:10]],
            "emotion": emotion,
            "candidates": candidates,
            "auction_volume": auction_volume_data,
            "hot_sectors": hot_sectors[:10],
        }

    def _get_all_codes(self, watchlist: List[str], sector_map: Dict[str, List[str]]) -> List[str]:
        """获取所有需要监控的股票代码"""
        all_codes = set(watchlist)
        for codes in sector_map.values():
            all_codes.update(codes)
        return list(all_codes)

    def _group_by_sector(self, quotes: Dict[str, StockQuote], sector_map: Dict[str, List[str]]):
        """按板块分组"""
        self.sector_data = {}
        for sector_name, codes in sector_map.items():
            self.sector_data[sector_name] = []
            for code in codes:
                if code in quotes:
                    self.sector_data[sector_name].append(quotes[code])

    def _calculate_sector_strength(self) -> List[SectorStrength]:
        """计算板块强度"""
        results = []

        for sector_name, quotes in self.sector_data.items():
            if not quotes:
                continue

            total = len(quotes)
            up_count = sum(1 for q in quotes if q.change_pct > 0)
            down_count = sum(1 for q in quotes if q.change_pct < 0)
            limit_up_count = sum(1 for q in quotes if q.change_pct >= 9.5)
            high_open_count = sum(1 for q in quotes if q.open > q.pre_close)
            avg_change = sum(q.change_pct for q in quotes) / total

            # 找龙头（涨幅最高的）
            leader = max(quotes, key=lambda q: q.change_pct) if quotes else None

            # 计算综合评分 (0-100)
            score = 0
            if avg_change > 2:
                score += 30
            elif avg_change > 0:
                score += 15

            if limit_up_count >= 3:
                score += 30
            elif limit_up_count >= 1:
                score += 15

            high_open_rate = high_open_count / total if total > 0 else 0
            if high_open_rate >= 0.7:
                score += 20
            elif high_open_rate >= 0.5:
                score += 10

            if leader and leader.change_pct >= 7:
                score += 20
            elif leader and leader.change_pct >= 3:
                score += 10

            results.append(SectorStrength(
                sector_name=sector_name,
                avg_change_pct=round(avg_change, 2),
                up_count=up_count,
                down_count=down_count,
                limit_up_count=limit_up_count,
                high_open_count=high_open_count,
                total_count=total,
                leader_code=leader.code if leader else None,
                leader_change_pct=leader.change_pct if leader else 0,
                score=score,
            ))

        return results

    def _calculate_leader_scores(self) -> List[LeaderScore]:
        """计算龙头竞价评分"""
        results = []

        for sector_name, quotes in self.sector_data.items():
            if not quotes:
                continue

            # 取板块内涨幅前3作为龙头候选
            leaders = sorted(quotes, key=lambda q: q.change_pct, reverse=True)[:3]

            for leader in leaders:
                score = 0
                reasons = []

                # 评分逻辑
                if leader.change_pct >= 9.9:
                    score = 10
                    reasons.append("一字涨停")
                elif leader.change_pct >= 7:
                    score = 8
                    reasons.append(f"高开{leader.change_pct}%抢筹")
                elif leader.change_pct >= 3:
                    score = 5
                    reasons.append(f"高开{leader.change_pct}%")
                else:
                    score = 0
                    reasons.append("低开/平开")

                # 封单量加分
                if leader.bid1_vol >= 100000:
                    score = min(10, score + 1)
                    reasons.append("封单量>=10万手")

                results.append(LeaderScore(
                    code=leader.code,
                    name=leader.name,
                    sector=sector_name,
                    change_pct=leader.change_pct,
                    bid_vol=leader.bid1_vol,
                    score=score,
                    score_reason=";".join(reasons),
                ))

        return results

    def _calculate_emotion(self, quotes: Dict[str, StockQuote]) -> dict:
        """计算市场情绪晴雨表"""
        all_quotes = list(quotes.values())
        total = len(all_quotes)

        if total == 0:
            return {"level": "unknown", "score": 0}

        up_count = sum(1 for q in all_quotes if q.change_pct > 0)
        down_count = sum(1 for q in all_quotes if q.change_pct < 0)
        limit_up = sum(1 for q in all_quotes if q.change_pct >= 9.5)
        limit_down = sum(1 for q in all_quotes if q.change_pct <= -9.5)

        # 昨日涨停股高开率（简化，实际需要昨日数据）
        high_open_rate = 0.5

        # 情绪评分
        emotion_score = 50
        if up_count / total > 0.7:
            emotion_score += 30
        elif up_count / total > 0.5:
            emotion_score += 10
        elif up_count / total < 0.3:
            emotion_score -= 30

        if limit_up >= 50:
            emotion_score += 20
        if limit_down >= 30:
            emotion_score -= 20

        level = "火爆" if emotion_score >= 80 else \
                "活跃" if emotion_score >= 60 else \
                "平稳" if emotion_score >= 40 else \
                "低迷" if emotion_score >= 20 else "恐慌"

        return {
            "level": level,
            "score": emotion_score,
            "up_count": up_count,
            "down_count": down_count,
            "limit_up": limit_up,
            "limit_down": limit_down,
            "high_open_rate": high_open_rate,
        }

    def _filter_candidates(self) -> List[dict]:
        """筛选潜力标的"""
        candidates = []

        # 取板块强度前3的板块
        top_sectors = sorted(
            self.sector_strengths, key=lambda x: x.score, reverse=True
        )[:3]

        for sector in top_sectors:
            if sector.score < 40:
                continue

            # 在该板块找龙头评分>=5的标的
            sector_leaders = [
                l for l in self.leader_scores
                if l.sector == sector.sector_name and l.score >= 5
            ]

            for leader in sorted(sector_leaders, key=lambda x: x.score, reverse=True)[:2]:
                candidates.append({
                    "code": leader.code,
                    "name": leader.name,
                    "sector": leader.sector,
                    "score": leader.score,
                    "change_pct": leader.change_pct,
                    "reason": leader.score_reason,
                })

        return candidates

    async def _get_auction_volume_data(self, quotes: Dict[str, StockQuote]) -> List[dict]:
        """获取竞价量能数据并计算变化率

        获取9:15-9:25每分钟的竞价成交量，计算量能变化率
        """
        auction_data = []
        now = datetime.now()
        current_date = now.date().isoformat()

        for code, quote in quotes.items():
            try:
                # 获取该股票今日已保存的竞价量能数据
                db_data = await db_get_auction_volume(code, current_date)

                if db_data:
                    # 计算量能变化率
                    volumes = [d["volume"] for d in db_data]
                    if len(volumes) >= 2:
                        # 计算每分钟的变化率
                        volume_changes = []
                        for i in range(1, len(volumes)):
                            prev = volumes[i - 1]
                            curr = volumes[i]
                            change_rate = round((curr - prev) / prev * 100, 2) if prev > 0 else 0
                            volume_changes.append({
                                "minute": db_data[i]["minute"],
                                "volume": curr,
                                "prev_volume": prev,
                                "change_rate": change_rate,
                            })

                        # 计算总变化率（最后一分钟相比第一分钟）
                        total_change_rate = round(
                            (volumes[-1] - volumes[0]) / volumes[0] * 100, 2
                        ) if volumes[0] > 0 else 0

                        auction_data.append({
                            "code": code,
                            "name": quote.name,
                            "total_volume": sum(volumes),
                            "volume_changes": volume_changes,
                            "total_change_rate": total_change_rate,
                            "minute_data": db_data,
                        })
                else:
                    # 如果没有数据库数据，使用当前行情数据作为简化版
                    auction_data.append({
                        "code": code,
                        "name": quote.name,
                        "total_volume": quote.volume,
                        "volume_changes": [],
                        "total_change_rate": 0,
                        "minute_data": [],
                    })
            except Exception as e:
                logger.warning(f"获取竞价量能数据失败 {code}: {e}")
                continue

        # 按总成交量排序，取前20
        auction_data.sort(key=lambda x: x["total_volume"], reverse=True)
        return auction_data[:20]

    async def record_auction_volume(self, code: str, name: str, minute: str, volume: int, amount: float = 0):
        """记录竞价量能数据

        在9:15-9:25期间，每分钟调用一次记录竞价成交量
        """
        try:
            await db_save_auction_volume(
                code=code,
                name=name,
                minute=minute,
                volume=volume,
                amount=amount,
            )
            logger.debug(f"记录竞价量能: {name}({code}) {minute} 成交量:{volume}")
        except Exception as e:
            logger.warning(f"记录竞价量能失败 {code}: {e}")

    async def get_sector_detail(self, sector_name: str) -> Optional[dict]:
        """获取板块详细信息（含实时成分股）"""
        sector_map = await self._get_sector_map()
        codes = sector_map.get(sector_name, [])
        if not codes:
            return None

        quotes = await collector.get_quotes(codes)
        stocks = []
        for code in codes:
            if code in quotes:
                q = quotes[code]
                stocks.append({
                    "code": q.code,
                    "name": q.name,
                    "price": q.price,
                    "change_pct": q.change_pct,
                    "volume": q.volume,
                    "amount": q.amount,
                })

        stocks.sort(key=lambda x: x["change_pct"], reverse=True)

        return {
            "sector_name": sector_name,
            "stock_count": len(stocks),
            "stocks": stocks,
            "avg_change_pct": round(sum(s["change_pct"] for s in stocks) / len(stocks), 2) if stocks else 0,
            "leader": stocks[0] if stocks else None,
        }

    async def refresh_sector_map(self):
        """手动刷新板块映射"""
        self._sector_map = {}
        self._sector_map_cache_time = None
        self._hot_sectors = []
        self._hot_sectors_cache_time = None
        await self._get_sector_map()
        await self._get_hot_sectors()
        logger.info("板块映射已手动刷新")


# 单例
auction_engine = AuctionEngine()
