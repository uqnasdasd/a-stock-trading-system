"""API路由"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Body, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime
import asyncio
import json
from loguru import logger

from app.models.schemas import Position, StockQuote
from app.services.auction_engine.engine import auction_engine
from app.services.position_monitor.monitor import position_monitor
from app.services.risk_control.controller import risk_controller
from app.services.alert_push.pusher import alert_pusher
from app.services.data_collector.sina_api import collector
from app.services.limit_monitor.monitor import limit_monitor
from app.services.limit_monitor.tracker import limit_tracker
from app.services.watchlist.manager import watchlist_manager
from app.services.trade_log.logger import trade_logger
from app.services.daily_report.generator import daily_report_generator
from app.services.concept_tracker.tracker import concept_tracker
from app.services.dragon_tiger.dragon import dragon_tiger_service
from app.services.open_confirm.confirm import open_confirm
from app.services.morning_breakout.breakout import morning_breakout
from app.services.afternoon_stable.stable import afternoon_stable
from app.services.backtest.engine import backtest_engine, BacktestParams
from app.services.history.replay import history_replay_engine, ReplayParams
from app.core.database import db_get_accounts, db_save_account, db_delete_account

router = APIRouter()

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()


# ============ REST API ============

@router.get("/api/market/indices")
async def get_market_indices():
    """获取大盘指数"""
    quotes = await collector.get_index_quotes()
    return {
        "timestamp": datetime.now().isoformat(),
        "indices": [
            {
                "code": q.code,
                "name": q.name,
                "price": q.price,
                "change_pct": q.change_pct,
                "up_down": q.up_down,
            }
            for q in quotes.values()
        ]
    }


@router.post("/api/auction/analyze")
async def run_auction_analysis(watchlist: List[str] = None):
    """运行竞价分析"""
    if watchlist is None:
        watchlist = []
    result = await auction_engine.run_auction_analysis(watchlist)
    return result


@router.get("/api/positions")
async def get_positions():
    """获取持仓列表"""
    return await position_monitor.get_position_summary()


@router.post("/api/positions")
async def add_position(position: Position):
    """添加持仓"""
    await position_monitor.add_position(position)
    risk_controller.add_position(position)
    return {"status": "success", "message": f"已添加持仓: {position.name}"}


@router.delete("/api/positions/{code}")
async def remove_position(code: str):
    """移除持仓"""
    await position_monitor.remove_position(code)
    risk_controller.remove_position(code)
    return {"status": "success", "message": f"已移除持仓: {code}"}


@router.get("/api/risk/status")
async def get_risk_status():
    """获取风控状态"""
    status = risk_controller.get_status()
    can_trade, reason = await risk_controller.can_trade()
    return {
        "status": status.model_dump(),
        "can_trade": can_trade,
        "reason": reason,
    }


@router.post("/api/risk/capital")
async def set_capital(request: Request):
    """设置总资金"""
    body = await request.json()
    capital = body.get("total_capital")
    if capital is None:
        return JSONResponse(status_code=400, content={"status": "error", "message": "缺少 total_capital 参数"})
    await risk_controller.set_capital(float(capital))
    return {"status": "success", "capital": capital}


@router.get("/api/risk/capital/available")
async def get_available_capital():
    """获取可用资金"""
    available = risk_controller.get_available_capital()
    return {
        "available_capital": available,
        "total_capital": risk_controller.total_capital,
    }


@router.get("/api/risk/calculate-buy")
async def calculate_buy_volume(price: float, position_ratio: float = 0.10):
    """计算可买股数"""
    volume = risk_controller.calculate_buy_volume(price, position_ratio)
    available = risk_controller.get_available_capital()
    return {
        "price": price,
        "position_ratio": position_ratio,
        "available_capital": available,
        "buy_volume": volume,
        "buy_amount": round(price * volume, 2),
    }


@router.get("/api/signals")
async def get_signals():
    """获取最新信号"""
    # 运行监控
    position_signals = await position_monitor.monitor()
    risk_signals = risk_controller.check_all()

    # 新增信号模块
    open_signals = await open_confirm.analyze_watchlist()
    breakout_signals = await morning_breakout.analyze_watchlist()
    stable_signals = await afternoon_stable.analyze_watchlist()

    all_signals = position_signals + risk_signals + open_signals + breakout_signals + stable_signals

    return {
        "timestamp": datetime.now().isoformat(),
        "signals": all_signals,
    }


@router.get("/api/signals/open-confirm")
async def get_open_confirm_signals():
    """获取开盘确认信号"""
    signals = await open_confirm.analyze_watchlist()
    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(signals),
        "signals": signals,
    }


@router.get("/api/signals/morning-breakout")
async def get_morning_breakout_signals():
    """获取早盘突破信号"""
    signals = await morning_breakout.analyze_watchlist()
    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(signals),
        "signals": signals,
    }


@router.get("/api/signals/afternoon-stable")
async def get_afternoon_stable_signals():
    """获取尾盘稳健信号"""
    signals = await afternoon_stable.analyze_watchlist()
    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(signals),
        "signals": signals,
    }


@router.get("/api/stock/search")
async def search_stock(code: str):
    """搜索个股实时行情"""
    # 标准化代码
    code = code.strip().lower()
    if not code.startswith(("sh", "sz", "bj")):
        # 尝试自动补全
        if code.startswith("6"):
            code = "sh" + code
        elif code.startswith(("0", "3")):
            code = "sz" + code
        elif code.startswith("8"):
            code = "bj" + code

    quotes = await collector.get_quotes([code])
    if code in quotes:
        q = quotes[code]
        return {
            "found": True,
            "code": q.code,
            "name": q.name,
            "price": q.price,
            "change_pct": q.change_pct,
            "open": q.open,
            "high": q.high,
            "low": q.low,
            "pre_close": q.pre_close,
            "volume": q.volume,
            "amount": q.amount,
            "timestamp": datetime.now().isoformat(),
        }
    return {"found": False, "message": "未找到该股票"}


@router.get("/api/stock/quote")
async def get_stock_quote(codes: str):
    """批量获取个股行情 codes=sh600000,sz000001"""
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    quotes = await collector.get_quotes(code_list)
    return {
        "timestamp": datetime.now().isoformat(),
        "quotes": [
            {
                "code": q.code,
                "name": q.name,
                "price": q.price,
                "change_pct": q.change_pct,
                "open": q.open,
                "high": q.high,
                "low": q.low,
                "volume": q.volume,
            }
            for q in quotes.values()
        ]
    }


@router.get("/api/stock/kline")
async def get_kline_data(code: str, scale: int = 5, datalen: int = 100):
    """获取K线数据
    scale: 1=1分钟 5=5分钟 15=15分钟 30=30分钟 60=60分钟 240=日线
    datalen: 数据条数(最大1023)
    """
    # 标准化代码
    code = code.strip().lower()
    if not code.startswith(("sh", "sz", "bj")):
        if code.startswith("6"):
            code = "sh" + code
        elif code.startswith(("0", "3")):
            code = "sz" + code
        elif code.startswith("8"):
            code = "bj" + code

    kline = await collector.get_kline(code, scale, datalen)
    return {
        "code": code,
        "scale": scale,
        "datalen": len(kline),
        "data": kline,
    }


@router.get("/api/stock/minute")
async def get_minute_data(code: str):
    """获取分时图数据"""
    # 标准化代码
    code = code.strip().lower()
    if not code.startswith(("sh", "sz", "bj")):
        if code.startswith("6"):
            code = "sh" + code
        elif code.startswith(("0", "3")):
            code = "sz" + code
        elif code.startswith("8"):
            code = "bj" + code

    minute_data = await collector.get_minute_data(code)
    return {
        "code": code,
        "count": len(minute_data),
        "data": minute_data,
        "timestamp": datetime.now().isoformat(),
    }


# ============ 涨跌停监控路由 ============

@router.get("/api/limit/stocks")
async def get_limit_stocks():
    """获取涨跌停数据"""
    data = await limit_monitor.fetch_limit_data()
    return data


@router.get("/api/limit/summary")
async def get_limit_summary():
    """获取涨跌停概览（使用缓存数据，不实时请求）"""
    return limit_monitor.get_summary()


# ============ 连板股追踪路由 ============

@router.get("/api/limit/continuous")
async def get_continuous_boards(min_days: int = 2):
    """获取连板股列表"""
    boards = await limit_tracker.get_continuous_boards(min_days=min_days)
    return {
        "timestamp": datetime.now().isoformat(),
        "min_days": min_days,
        "count": len(boards),
        "boards": boards,
    }


@router.get("/api/limit/tracker/summary")
async def get_tracker_summary():
    """获取连板追踪概览"""
    return await limit_tracker.get_summary()


@router.post("/api/limit/tracker/set-yesterday")
async def set_yesterday_limit_up(stocks: List[dict]):
    """设置昨日涨停列表（手动导入）"""
    limit_tracker.set_yesterday_limit_up(stocks)
    return {"status": "success", "count": len(stocks)}


# ============ 自选股管理路由 ============

@router.get("/api/watchlist")
async def get_watchlist():
    """获取自选股列表"""
    return await watchlist_manager.get_all()


@router.post("/api/watchlist")
async def add_watchlist(request: Request):
    """添加自选股"""
    body = await request.json()
    code = body.get("code")
    name = body.get("name")
    if not code or not name:
        return JSONResponse(status_code=400, content={"status": "error", "message": "缺少 code 或 name 参数"})
    return await watchlist_manager.add(code, name)


@router.delete("/api/watchlist/{code}")
async def remove_watchlist(code: str):
    """删除自选股"""
    return await watchlist_manager.remove(code)


# ============ 交易日志路由 ============

@router.get("/api/trade/log")
async def get_trade_logs(
    code: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """获取交易日志"""
    return await trade_logger.get_logs(
        code=code,
        action=action,
        limit=limit,
        offset=offset,
    )


@router.post("/api/trade/log")
async def add_trade_log(
    code: str,
    name: str,
    action: str,
    price: float,
    volume: int,
    reason: str = "",
):
    """添加交易日志"""
    return await trade_logger.add_log(
        code=code,
        name=name,
        action=action,
        price=price,
        volume=volume,
        reason=reason,
    )


@router.get("/api/trade/log/stats")
async def get_trade_log_stats():
    """获取交易日志统计"""
    return await trade_logger.get_stats()


# ============ 每日复盘报告路由 ============

@router.get("/api/report/daily")
async def get_daily_report():
    """获取每日复盘报告"""
    report = await daily_report_generator.get_last_report()
    if report is None:
        report = await daily_report_generator.generate_report()
    return report


# ============ 概念板块轮动路由 ============

@router.get("/api/concept/hot")
async def get_hot_concepts():
    """获取热点概念板块"""
    concepts = await concept_tracker.get_hot_concepts(num=20)
    summary = await concept_tracker.get_concept_summary()
    return {
        "timestamp": datetime.now().isoformat(),
        "concepts": concepts,
        "summary": summary,
    }


# ============ 龙虎榜路由 ============

@router.get("/api/dragon/today")
async def get_today_dragon_tiger():
    """获取当日龙虎榜数据"""
    dragons = await dragon_tiger_service.get_today_dragon_tiger()
    summary = await dragon_tiger_service.get_dragon_summary()
    return {
        "timestamp": datetime.now().isoformat(),
        "dragons": dragons,
        "summary": summary,
    }


# ============ 账户管理路由 ============

@router.get("/api/accounts")
async def get_accounts():
    """获取所有账户"""
    accounts = await db_get_accounts()
    return {
        "accounts": accounts,
    }


@router.post("/api/accounts")
async def save_accounts(request: Request):
    """保存账户列表（批量覆盖）"""
    body = await request.json()
    accounts = body.get("accounts", [])
    for account in accounts:
        await db_save_account(account)
    return {"status": "success", "count": len(accounts)}


@router.delete("/api/accounts/{account_id}")
async def delete_account(account_id: str):
    """删除账户"""
    return await db_delete_account(account_id)


# ============ WebSocket ============

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket实时数据推送"""
    await manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            msg = json.loads(data)
            action = msg.get("action")

            if action == "subscribe_market":
                # 订阅市场行情
                await websocket.send_json({
                    "type": "subscribed",
                    "channel": "market"
                })

            elif action == "subscribe_auction":
                # 订阅竞价数据
                watchlist = msg.get("watchlist", [])
                result = await auction_engine.run_auction_analysis(watchlist)
                await websocket.send_json({
                    "type": "auction_update",
                    "data": result
                })

            elif action == "subscribe_positions":
                # 订阅持仓数据
                summary = await position_monitor.get_position_summary()
                await websocket.send_json({
                    "type": "positions_update",
                    "data": summary
                })

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(websocket)


# ============ 后台任务 ============

async def background_monitor_task():
    """后台监控任务 - 全天实时运行"""
    report_generated_today = False
    signals_reset_today = False
    while True:
        try:
            now = datetime.now()

            # 0. 每日开盘前重置信号状态
            if now.hour == 9 and now.minute == 15 and not signals_reset_today:
                open_confirm.reset()
                morning_breakout.reset()
                afternoon_stable.reset()
                signals_reset_today = True
                logger.info("9:15 已重置所有交易信号状态")

            # 跨日重置标记
            if now.hour == 0 and now.minute == 0:
                report_generated_today = False
                signals_reset_today = False

            # 1. 获取大盘指数（全天获取）
            indices = await collector.get_index_quotes()

            # 2. 竞价分析（全天获取，不限于9:15-9:25）
            auction_data = await auction_engine.run_auction_analysis([])

            # 3. 监控持仓（全天监控）
            position_signals = await position_monitor.monitor()
            position_summary = await position_monitor.get_position_summary()

            # 4. 风控检查（全天检查）
            risk_signals = risk_controller.check_all()
            risk_status = risk_controller.get_status()

            # 5. 涨跌停监控（全天监控）
            limit_data = await limit_monitor.fetch_limit_data()

            # 6. 更新连板追踪
            await limit_tracker.update_today_limit_up(limit_data.get("limit_up", []))

            # 7. 新增交易信号检测
            open_signals = await open_confirm.analyze_watchlist()
            breakout_signals = await morning_breakout.analyze_watchlist()
            stable_signals = await afternoon_stable.analyze_watchlist()

            # 8. 合并信号
            all_signals = (
                position_signals
                + risk_signals
                + open_signals
                + breakout_signals
                + stable_signals
            )

            # 9. 推送告警
            for signal in all_signals:
                await alert_pusher.push(signal)

            # 10. 收盘后自动生成复盘报告（15:05）
            if now.hour == 15 and now.minute == 5 and not report_generated_today:
                report = await daily_report_generator.generate_report()
                await manager.broadcast({
                    "type": "report",
                    "timestamp": now.isoformat(),
                    "data": report,
                })
                report_generated_today = True
                logger.info("15:05 自动生成当日复盘报告并已推送")

            # 11. 广播到所有WebSocket客户端
            await manager.broadcast({
                "type": "market_update",
                "timestamp": now.isoformat(),
                "indices": [
                    {"code": q.code, "name": q.name, "price": q.price, "change_pct": q.change_pct}
                    for q in indices.values()
                ],
                "auction": auction_data,
                "positions": position_summary,
                "risk": risk_status.model_dump(),
                "signals": all_signals,
                "signal_summary": {
                    "open_confirm": len(open_signals),
                    "morning_breakout": len(breakout_signals),
                    "afternoon_stable": len(stable_signals),
                    "position": len(position_signals),
                    "risk": len(risk_signals),
                },
                "limit": {
                    "limit_up_count": limit_data.get("limit_up_count", len(limit_data.get("limit_up", []))),
                    "limit_down_count": limit_data.get("limit_down_count", len(limit_data.get("limit_down", []))),
                    "broken_board": limit_data.get("broken_board", []),
                },
                "continuous_boards": await limit_tracker.get_continuous_boards(min_days=2),
            })

            await asyncio.sleep(3)  # 3秒轮询

        except Exception as e:
            logger.error(f"后台监控任务错误: {e}")
            await asyncio.sleep(5)


# ==================== 回测API ====================

@router.post("/backtest/run")
async def api_backtest_run(params: dict = Body(...)):
    """运行策略回测"""
    try:
        bp = BacktestParams(
            code=params.get("code", "sh000001"),
            buy_condition=params.get("buy_condition", "ma_break"),
            sell_condition=params.get("sell_condition", "stop_profit_loss"),
            hold_period=params.get("hold_period", 5),
            start_date=params.get("start_date", "2024-01-01"),
            end_date=params.get("end_date", "2024-06-01"),
            initial_capital=params.get("initial_capital", 100000.0),
            stop_loss_pct=params.get("stop_loss_pct", 0.03),
            take_profit_pct=params.get("take_profit_pct", 0.05),
            ma_period=params.get("ma_period", 5),
            volume_ratio_threshold=params.get("volume_ratio_threshold", 1.5),
        )
        result = await backtest_engine.run(bp)
        return {
            "result": {
                "totalReturn": result.total_return,
                "maxDrawdown": result.max_drawdown,
                "winRate": result.win_rate,
                "profitLossRatio": result.profit_loss_ratio,
                "tradeCount": result.trade_count,
                "profitTrades": result.profit_trades,
                "lossTrades": result.loss_trades,
                "finalCapital": result.final_capital,
                "annualizedReturn": result.annualized_return,
                "sharpeRatio": result.sharpe_ratio,
                "equityCurve": result.equity_curve,
                "drawdownCurve": result.drawdown_curve,
                "trades": [
                    {
                        "date": t.date,
                        "code": t.code,
                        "name": t.name,
                        "action": t.action,
                        "price": t.price,
                        "volume": t.volume,
                        "pnl": t.pnl,
                        "pnlPct": t.pnl_pct,
                        "reason": t.reason,
                    }
                    for t in result.trades
                ],
            }
        }
    except Exception as e:
        logger.error(f"回测运行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backtest/compare")
async def api_backtest_compare(params: dict = Body(...)):
    """多策略对比回测"""
    try:
        results = await backtest_engine.run_multi_strategy(
            code=params.get("code", "sh000001"),
            start_date=params.get("start_date", "2024-01-01"),
            end_date=params.get("end_date", "2024-06-01"),
            strategies=params.get("strategies", []),
        )
        return {"results": results}
    except Exception as e:
        logger.error(f"多策略对比失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 历史回放API ====================

@router.post("/history/replay/load")
async def api_history_replay_load(params: dict = Body(...)):
    """加载历史回放数据"""
    try:
        rp = ReplayParams(
            code=params.get("code", "sh000001"),
            date=params.get("date", "2024-01-15"),
            speed=params.get("speed", 1.0),
        )
        result = await history_replay_engine.load_day_data(rp)
        if result.get("success"):
            report = history_replay_engine.generate_report()
            return {
                "success": True,
                "code": result["code"],
                "name": result["name"],
                "date": result["date"],
                "total_ticks": result["total_ticks"],
                "ticks": history_replay_engine.get_all_ticks(),
                "report": {
                    "code": report.code,
                    "name": report.name,
                    "date": report.date,
                    "total_ticks": report.total_ticks,
                    "open_price": report.open_price,
                    "close_price": report.close_price,
                    "high_price": report.high_price,
                    "low_price": report.low_price,
                    "total_volume": report.total_volume,
                    "total_amount": report.total_amount,
                    "change_pct": report.change_pct,
                    "amplitude": report.amplitude,
                    "key_signals": report.key_signals,
                    "phase_summary": report.phase_summary,
                },
            }
        else:
            return result
    except Exception as e:
        logger.error(f"历史回放加载失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/history/replay/report")
async def api_history_replay_report(params: dict = Body(...)):
    """生成历史复盘报告"""
    try:
        report = history_replay_engine.generate_report()
        return {
            "report": {
                "code": report.code,
                "name": report.name,
                "date": report.date,
                "total_ticks": report.total_ticks,
                "open_price": report.open_price,
                "close_price": report.close_price,
                "high_price": report.high_price,
                "low_price": report.low_price,
                "total_volume": report.total_volume,
                "total_amount": report.total_amount,
                "change_pct": report.change_pct,
                "amplitude": report.amplitude,
                "key_signals": report.key_signals,
                "phase_summary": report.phase_summary,
            }
        }
    except Exception as e:
        logger.error(f"生成复盘报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
