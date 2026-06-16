"""每日复盘报告生成器 - SQLite持久化存储"""
from typing import Dict, List, Optional
from datetime import datetime, date
from loguru import logger

from app.services.trade_log.logger import trade_logger
from app.services.position_monitor.monitor import position_monitor
from app.services.risk_control.controller import risk_controller
from app.core.database import (
    db_save_daily_report,
    db_get_daily_report,
    db_get_last_daily_report,
)


class DailyReportGenerator:
    """每日复盘报告生成器

    汇总当日交易数据，生成复盘报告，包含：
    - 当日盈亏、收益率
    - 交易次数统计
    - 持仓变化
    - 信号统计（止损/止盈/风控）
    - 板块表现TOP3
    - 风控触发记录
    - 明日操作建议
    """

    def __init__(self):
        self._last_report: Optional[dict] = None
        self._report_date: Optional[str] = None

    async def generate_report(self) -> dict:
        """生成当日复盘报告"""
        today = datetime.now().date().isoformat()
        now = datetime.now()

        # 1. 交易日志统计
        today_logs = await trade_logger.get_today_logs()
        trade_count = len(today_logs)
        buy_logs = [l for l in today_logs if l["action"] == "buy"]
        sell_logs = [l for l in today_logs if l["action"] == "sell"]

        # 估算当日盈亏（基于卖出日志的pnl + 持仓浮动盈亏）
        realized_pnl = sum(
            l.get("pnl", 0) for l in today_logs if l["action"] == "sell"
        )

        # 持仓浮动盈亏
        position_summary = await position_monitor.get_position_summary()
        unrealized_pnl = 0.0
        if position_summary.get("total_cost", 0) > 0:
            unrealized_pnl = position_summary.get("total_value", 0) - position_summary.get("total_cost", 0)

        total_pnl = realized_pnl + unrealized_pnl
        total_capital = risk_controller.total_capital or 100000
        return_pct = round(total_pnl / total_capital * 100, 2) if total_capital > 0 else 0

        # 2. 持仓变化
        position_changes = self._analyze_position_changes(today_logs, position_summary)

        # 3. 信号统计
        signal_stats = self._analyze_signals()

        # 4. 板块表现（简化版，基于持仓和交易日志推断）
        sector_performance = self._analyze_sector_performance(position_summary, today_logs)

        # 5. 风控触发记录
        risk_records = self._get_risk_records()

        # 6. 明日操作建议
        suggestions = self._generate_suggestions(
            total_pnl=total_pnl,
            return_pct=return_pct,
            trade_count=trade_count,
            signal_stats=signal_stats,
            risk_records=risk_records,
            position_summary=position_summary,
        )

        report = {
            "date": today,
            "generated_at": now.isoformat(),
            "summary": {
                "total_pnl": round(total_pnl, 2),
                "return_pct": return_pct,
                "total_capital": total_capital,
                "trade_count": trade_count,
                "buy_count": len(buy_logs),
                "sell_count": len(sell_logs),
                "realized_pnl": round(realized_pnl, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
            },
            "trades": today_logs,
            "position_changes": position_changes,
            "signal_stats": signal_stats,
            "sector_performance": sector_performance,
            "risk_records": risk_records,
            "suggestions": suggestions,
        }

        self._last_report = report
        self._report_date = today

        # 保存到数据库
        await db_save_daily_report(today, report)

        logger.info(f"生成每日复盘报告: 盈亏{total_pnl:.2f} 收益率{return_pct:.2f}% 交易{trade_count}次")
        return report

    def _analyze_position_changes(self, today_logs: List[dict], position_summary: dict) -> List[dict]:
        """分析持仓变化"""
        changes = []

        # 新增持仓（今日买入且当前仍持仓）
        current_codes = {p["code"] for p in position_summary.get("positions", [])}
        for log in today_logs:
            if log["action"] == "buy":
                changes.append({
                    "code": log["code"],
                    "name": log["name"],
                    "action": "买入",
                    "price": log["price"],
                    "volume": log["volume"],
                    "time": log["time"],
                    "is_new_position": log["code"] in current_codes,
                })
            elif log["action"] == "sell":
                changes.append({
                    "code": log["code"],
                    "name": log["name"],
                    "action": "卖出",
                    "price": log["price"],
                    "volume": log["volume"],
                    "time": log["time"],
                    "pnl": log.get("pnl", 0),
                })

        # 当前持仓列表
        for pos in position_summary.get("positions", []):
            changes.append({
                "code": pos["code"],
                "name": pos["name"],
                "action": "持仓",
                "buy_price": pos["buy_price"],
                "current_price": pos["current_price"],
                "volume": pos["volume"],
                "profit_pct": pos["profit_pct"],
                "market_value": pos["market_value"],
            })

        return changes

    def _analyze_signals(self) -> dict:
        """统计今日信号"""
        # 从 position_monitor 的 triggered_signals 中统计今日信号
        today = datetime.now().date().isoformat()

        stop_loss_count = 0
        take_profit_count = 0
        risk_alert_count = 0
        position_sell_count = 0

        for key, val in position_monitor.triggered_signals.items():
            trigger_time = val.get("time")
            if trigger_time and trigger_time.isoformat().startswith(today):
                if "stop_loss" in key:
                    stop_loss_count += 1
                elif "take_profit" in key or "trailing_stop" in key:
                    take_profit_count += 1
                elif "sector_weak" in key or "pv_divergence" in key or "break_" in key:
                    position_sell_count += 1

        # 从 risk_controller 的 daily_trades 和状态推断风控信号
        risk_status = risk_controller.get_status()
        if risk_status.is_locked:
            risk_alert_count += 1

        # 统计风控检查中触发的各类信号（基于今日交易次数等）
        daily_trade_count = risk_status.daily_trade_count
        if daily_trade_count >= 2:
            risk_alert_count += 1

        return {
            "stop_loss": stop_loss_count,
            "take_profit": take_profit_count,
            "risk_alert": risk_alert_count,
            "position_sell": position_sell_count,
            "total": stop_loss_count + take_profit_count + risk_alert_count + position_sell_count,
        }

    def _analyze_sector_performance(self, position_summary: dict, today_logs: List[dict]) -> List[dict]:
        """分析板块表现（简化版）

        实际场景中应从板块数据接口获取，此处基于持仓盈亏和交易日志模拟
        """
        sectors: Dict[str, dict] = {}

        # 从持仓汇总板块数据
        for pos in position_summary.get("positions", []):
            # Position 模型中有 sector 字段，但 summary 中可能未包含
            # 使用 code 前缀模拟板块分类
            sector_name = self._infer_sector(pos["code"])
            if sector_name not in sectors:
                sectors[sector_name] = {
                    "name": sector_name,
                    "total_change_pct": 0,
                    "count": 0,
                    "up_count": 0,
                    "down_count": 0,
                }
            sectors[sector_name]["count"] += 1
            profit = pos.get("profit_pct", 0)
            sectors[sector_name]["total_change_pct"] += profit
            if profit > 0:
                sectors[sector_name]["up_count"] += 1
            elif profit < 0:
                sectors[sector_name]["down_count"] += 1

        # 计算平均涨跌幅并排序
        result = []
        for name, data in sectors.items():
            avg_change = round(data["total_change_pct"] / data["count"], 2) if data["count"] > 0 else 0
            result.append({
                "name": name,
                "avg_change_pct": avg_change,
                "stock_count": data["count"],
                "up_count": data["up_count"],
                "down_count": data["down_count"],
            })

        result.sort(key=lambda x: x["avg_change_pct"], reverse=True)
        return result[:3]

    def _infer_sector(self, code: str) -> str:
        """根据股票代码推断板块（简化版）"""
        code = code.lower()
        # 创业板
        if code.startswith("sz300") or code.startswith("sz301"):
            return "创业板"
        # 科创板
        if code.startswith("sh688"):
            return "科创板"
        # 北交所
        if code.startswith("bj"):
            return "北交所"
        # 主板（根据代码段简单分类）
        if code.startswith("sh6"):
            return "沪市主板"
        if code.startswith("sz000") or code.startswith("sz001"):
            return "深市主板"
        if code.startswith("sz002") or code.startswith("sz003"):
            return "中小板"
        return "其他"

    def _get_risk_records(self) -> List[dict]:
        """获取今日风控触发记录"""
        records = []
        today = datetime.now().date().isoformat()

        # 检查风控锁定状态
        if risk_controller.is_locked:
            records.append({
                "time": risk_controller.lock_until.isoformat() if risk_controller.lock_until else datetime.now().isoformat(),
                "type": "交易锁定",
                "level": "emergency",
                "message": risk_controller.lock_reason or "交易已被锁定",
            })

        # 检查仓位超限
        risk_status = risk_controller.get_status()
        if risk_status.total_position_pct >= 0.5:
            records.append({
                "time": datetime.now().isoformat(),
                "type": "仓位告警",
                "level": "important",
                "message": f"总仓位已达{risk_status.total_position_pct*100:.1f}%，接近上限",
            })

        # 检查回撤
        if risk_status.daily_profit_pct <= -0.03:
            records.append({
                "time": datetime.now().isoformat(),
                "type": "回撤告警",
                "level": "emergency",
                "message": f"单日回撤达{abs(risk_status.daily_profit_pct)*100:.1f}%，触发风控线",
            })

        # 检查交易频率
        if risk_status.daily_trade_count >= 2:
            records.append({
                "time": datetime.now().isoformat(),
                "type": "频率告警",
                "level": "normal",
                "message": f"今日已交易{risk_status.daily_trade_count}次，达到日度上限附近",
            })

        return records

    def _generate_suggestions(
        self,
        total_pnl: float,
        return_pct: float,
        trade_count: int,
        signal_stats: dict,
        risk_records: List[dict],
        position_summary: dict,
    ) -> List[str]:
        """基于当日表现生成明日操作建议"""
        suggestions = []

        # 基于盈亏的建议
        if return_pct >= 2:
            suggestions.append("今日收益表现优异，明日可适当降低仓位，锁定利润。")
        elif return_pct >= 0.5:
            suggestions.append("今日小幅盈利，明日维持现有策略，关注早盘竞价强度。")
        elif return_pct >= -1:
            suggestions.append("今日基本持平，明日重点观察大盘方向选择，控制仓位。")
        else:
            suggestions.append("今日出现亏损，明日严格执行止损纪律，减少操作频率。")

        # 基于交易频率的建议
        if trade_count >= 3:
            suggestions.append("今日交易频繁，明日需减少冲动交易，提高开仓质量。")
        elif trade_count == 0:
            suggestions.append("今日无交易，明日可关注竞价超预期个股，把握早盘机会。")

        # 基于信号的建议
        if signal_stats["stop_loss"] > 0:
            suggestions.append(f"今日触发{signal_stats['stop_loss']}次止损，复盘止损时机是否合理，优化止损位设置。")
        if signal_stats["take_profit"] > 0:
            suggestions.append(f"今日触发{signal_stats['take_profit']}次止盈，总结止盈规律，完善分批卖出策略。")

        # 基于风控的建议
        if risk_records:
            emergency_count = sum(1 for r in risk_records if r["level"] == "emergency")
            if emergency_count > 0:
                suggestions.append("今日多次触发紧急风控，建议明日降低仓位至30%以下，冷静操作。")

        # 基于持仓的建议
        holding_count = position_summary.get("count", 0)
        if holding_count >= 3:
            suggestions.append(f"当前持仓{holding_count}只，明日优先处理弱势持仓，集中资金做最强个股。")
        elif holding_count == 0:
            suggestions.append("当前空仓，明日可积极寻找竞价超预期标的，把握早盘黄金时间。")

        # 通用建议
        suggestions.append("明日重点关注：竞价量能、板块龙头强度、大盘指数方向。")

        return suggestions

    async def get_last_report(self) -> Optional[dict]:
        """获取上一次生成的报告"""
        today = datetime.now().date().isoformat()
        # 先从内存缓存获取
        if self._report_date == today and self._last_report:
            return self._last_report
        # 从数据库获取
        report = await db_get_daily_report(today)
        if report:
            self._last_report = report.get("data")
            self._report_date = today
            return self._last_report
        # 获取最新的报告
        last = await db_get_last_daily_report()
        if last:
            return last.get("data")
        return None


# 单例
daily_report_generator = DailyReportGenerator()
