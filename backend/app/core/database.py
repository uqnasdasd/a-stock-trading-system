"""异步SQLite数据库模块 - 使用aiosqlite"""
import aiosqlite
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from loguru import logger

from app.core.config import settings


DB_PATH = Path(settings.database_url.replace("sqlite:///", ""))


async def get_db() -> aiosqlite.Connection:
    """获取数据库连接"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """初始化数据库，创建所有表"""
    db = await get_db()
    try:
        # positions 持仓表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                buy_price REAL NOT NULL,
                current_price REAL NOT NULL DEFAULT 0,
                volume INTEGER NOT NULL,
                sector TEXT DEFAULT '',
                buy_time TEXT NOT NULL,
                stop_loss REAL NOT NULL DEFAULT 0,
                take_profit REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # watchlist 自选股表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                add_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # trade_logs 交易日志表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trade_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                action TEXT NOT NULL,
                price REAL NOT NULL,
                volume INTEGER NOT NULL,
                reason TEXT DEFAULT '',
                profit REAL DEFAULT 0
            )
        """)

        # daily_reports 每日复盘报告表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_reports (
                date TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # settings 系统配置表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # limit_tracker 连板追踪表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS limit_tracker (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                continuous_days INTEGER NOT NULL DEFAULT 1,
                last_limit_date TEXT NOT NULL,
                history TEXT NOT NULL DEFAULT '[]'
            )
        """)

        # auction_volume 竞价量能表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS auction_volume (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                minute TEXT NOT NULL,
                volume INTEGER NOT NULL DEFAULT 0,
                amount REAL NOT NULL DEFAULT 0,
                date TEXT NOT NULL,
                UNIQUE(code, minute, date)
            )
        """)

        # risk_control 风控数据表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS risk_control (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                week_start TEXT NOT NULL,
                daily_trades_json TEXT NOT NULL DEFAULT '[]',
                weekly_trades_json TEXT NOT NULL DEFAULT '[]',
                daily_pnl REAL NOT NULL DEFAULT 0,
                weekly_pnl REAL NOT NULL DEFAULT 0,
                is_locked INTEGER NOT NULL DEFAULT 0,
                lock_reason TEXT DEFAULT NULL,
                lock_until TEXT DEFAULT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date)
            )
        """)

        await db.commit()
        logger.info("数据库初始化完成，所有表已创建")
    finally:
        await db.close()


# ==================== Positions CRUD ====================

async def db_add_position(
    code: str,
    name: str,
    buy_price: float,
    current_price: float,
    volume: int,
    sector: str = "",
    buy_time: Optional[str] = None,
    stop_loss: float = 0,
    take_profit: float = 0,
) -> dict:
    """添加持仓"""
    if buy_time is None:
        buy_time = datetime.now().isoformat()

    db = await get_db()
    try:
        await db.execute(
            """
            INSERT OR REPLACE INTO positions
            (code, name, buy_price, current_price, volume, sector, buy_time, stop_loss, take_profit, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (code, name, buy_price, current_price, volume, sector, buy_time, stop_loss, take_profit, datetime.now().isoformat()),
        )
        await db.commit()
        return {"status": "success", "code": code, "name": name}
    finally:
        await db.close()


async def db_remove_position(code: str) -> dict:
    """移除持仓"""
    db = await get_db()
    try:
        await db.execute("DELETE FROM positions WHERE code = ?", (code,))
        await db.commit()
        return {"status": "success", "code": code}
    finally:
        await db.close()


async def db_get_positions() -> List[dict]:
    """获取所有持仓"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM positions ORDER BY buy_time DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def db_update_position_price(code: str, current_price: float) -> dict:
    """更新持仓当前价格"""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE positions SET current_price = ?, updated_at = ? WHERE code = ?",
            (current_price, datetime.now().isoformat(), code),
        )
        await db.commit()
        return {"status": "success", "code": code, "current_price": current_price}
    finally:
        await db.close()


# ==================== Watchlist CRUD ====================

async def db_add_watchlist(code: str, name: str) -> dict:
    """添加自选股"""
    code = code.strip().lower()
    add_time = datetime.now().isoformat()
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR IGNORE INTO watchlist (code, name, add_time) VALUES (?, ?, ?)",
            (code, name, add_time),
        )
        await db.commit()
        return {"status": "success", "code": code, "name": name, "add_time": add_time}
    finally:
        await db.close()


async def db_remove_watchlist(code: str) -> dict:
    """删除自选股"""
    code = code.strip().lower()
    db = await get_db()
    try:
        await db.execute("DELETE FROM watchlist WHERE code = ?", (code,))
        await db.commit()
        return {"status": "success", "code": code}
    finally:
        await db.close()


async def db_get_watchlist() -> List[dict]:
    """获取所有自选股"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM watchlist ORDER BY add_time DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


# ==================== Trade Logs CRUD ====================

async def db_add_trade_log(
    code: str,
    name: str,
    action: str,
    price: float,
    volume: int,
    reason: str = "",
    profit: float = 0,
    time: Optional[str] = None,
) -> dict:
    """添加交易日志"""
    if time is None:
        time = datetime.now().isoformat()

    db = await get_db()
    try:
        await db.execute(
            """
            INSERT INTO trade_logs (time, code, name, action, price, volume, reason, profit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (time, code, name, action, price, volume, reason, profit),
        )
        await db.commit()
        return {"status": "success", "time": time, "code": code, "action": action}
    finally:
        await db.close()


async def db_get_trade_logs(
    code: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """获取交易日志"""
    db = await get_db()
    try:
        query = "SELECT * FROM trade_logs WHERE 1=1"
        params = []
        if code:
            query += " AND code = ?"
            params.append(code.strip().lower())
        if action:
            query += " AND action = ?"
            params.append(action)
        query += " ORDER BY time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        # 统计总数
        count_query = "SELECT COUNT(*) as total FROM trade_logs WHERE 1=1"
        count_params = []
        if code:
            count_query += " AND code = ?"
            count_params.append(code.strip().lower())
        if action:
            count_query += " AND action = ?"
            count_params.append(action)

        count_cursor = await db.execute(count_query, count_params)
        count_row = await count_cursor.fetchone()
        total = count_row["total"] if count_row else 0

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "logs": [dict(row) for row in rows],
        }
    finally:
        await db.close()


async def db_get_today_trade_logs() -> List[dict]:
    """获取今日交易日志"""
    today = datetime.now().date().isoformat()
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM trade_logs WHERE time LIKE ? ORDER BY time DESC",
            (f"{today}%",),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def db_get_trade_log_stats() -> dict:
    """获取交易日志统计"""
    today = datetime.now().date().isoformat()
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) as total FROM trade_logs"
        )
        total_row = await cursor.fetchone()

        cursor = await db.execute(
            "SELECT COUNT(*) as today FROM trade_logs WHERE time LIKE ?",
            (f"{today}%",),
        )
        today_row = await cursor.fetchone()

        cursor = await db.execute(
            "SELECT COUNT(*) as buy FROM trade_logs WHERE time LIKE ? AND action = ?",
            (f"{today}%", "buy"),
        )
        buy_row = await cursor.fetchone()

        cursor = await db.execute(
            "SELECT COUNT(*) as sell FROM trade_logs WHERE time LIKE ? AND action = ?",
            (f"{today}%", "sell"),
        )
        sell_row = await cursor.fetchone()

        cursor = await db.execute(
            "SELECT COUNT(*) as cancel FROM trade_logs WHERE time LIKE ? AND action = ?",
            (f"{today}%", "cancel"),
        )
        cancel_row = await cursor.fetchone()

        return {
            "total_logs": total_row["total"] if total_row else 0,
            "today_logs": today_row["today"] if today_row else 0,
            "today_buy": buy_row["buy"] if buy_row else 0,
            "today_sell": sell_row["sell"] if sell_row else 0,
            "today_cancel": cancel_row["cancel"] if cancel_row else 0,
        }
    finally:
        await db.close()


# ==================== Daily Reports CRUD ====================

async def db_save_daily_report(date: str, data: dict) -> dict:
    """保存每日复盘报告"""
    data_json = json.dumps(data, ensure_ascii=False, default=str)
    now = datetime.now().isoformat()
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT OR REPLACE INTO daily_reports (date, data_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (date, data_json, now, now),
        )
        await db.commit()
        return {"status": "success", "date": date}
    finally:
        await db.close()


async def db_get_daily_report(date: str) -> Optional[dict]:
    """获取每日复盘报告"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM daily_reports WHERE date = ?", (date,)
        )
        row = await cursor.fetchone()
        if row:
            data = dict(row)
            data["data"] = json.loads(data["data_json"])
            del data["data_json"]
            return data
        return None
    finally:
        await db.close()


async def db_get_last_daily_report() -> Optional[dict]:
    """获取最新的每日复盘报告"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM daily_reports ORDER BY date DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        if row:
            data = dict(row)
            data["data"] = json.loads(data["data_json"])
            del data["data_json"]
            return data
        return None
    finally:
        await db.close()


# ==================== Settings CRUD ====================

async def db_set_setting(key: str, value: str) -> dict:
    """设置配置项"""
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        await db.commit()
        return {"status": "success", "key": key, "value": value}
    finally:
        await db.close()


async def db_get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """获取配置项"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row["value"] if row else default
    finally:
        await db.close()


async def db_get_all_settings() -> Dict[str, str]:
    """获取所有配置项"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM settings")
        rows = await cursor.fetchall()
        return {row["key"]: row["value"] for row in rows}
    finally:
        await db.close()


# ==================== Limit Tracker CRUD ====================

async def db_save_limit_tracker(code: str, name: str, continuous_days: int, last_limit_date: str, history: List[dict]) -> dict:
    """保存连板追踪数据"""
    history_json = json.dumps(history, ensure_ascii=False, default=str)
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT OR REPLACE INTO limit_tracker (code, name, continuous_days, last_limit_date, history)
            VALUES (?, ?, ?, ?, ?)
            """,
            (code, name, continuous_days, last_limit_date, history_json),
        )
        await db.commit()
        return {"status": "success", "code": code}
    finally:
        await db.close()


async def db_get_limit_tracker(code: str) -> Optional[dict]:
    """获取单只股票连板追踪"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM limit_tracker WHERE code = ?", (code,)
        )
        row = await cursor.fetchone()
        if row:
            data = dict(row)
            data["history"] = json.loads(data["history"])
            return data
        return None
    finally:
        await db.close()


async def db_get_all_limit_trackers(min_days: int = 1) -> List[dict]:
    """获取所有连板追踪数据"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM limit_tracker WHERE continuous_days >= ? ORDER BY continuous_days DESC",
            (min_days,),
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data["history"] = json.loads(data["history"])
            result.append(data)
        return result
    finally:
        await db.close()


async def db_reset_limit_tracker() -> dict:
    """重置连板追踪数据"""
    db = await get_db()
    try:
        await db.execute("DELETE FROM limit_tracker")
        await db.commit()
        return {"status": "success"}
    finally:
        await db.close()


# ==================== Auction Volume CRUD ====================

async def db_save_auction_volume(
    code: str,
    name: str,
    minute: str,
    volume: int,
    amount: float,
    date: Optional[str] = None,
) -> dict:
    """保存竞价量能数据"""
    if date is None:
        date = datetime.now().date().isoformat()
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT OR REPLACE INTO auction_volume (code, name, minute, volume, amount, date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (code, name, minute, volume, amount, date),
        )
        await db.commit()
        return {"status": "success", "code": code, "minute": minute}
    finally:
        await db.close()


async def db_get_auction_volume(code: str, date: Optional[str] = None) -> List[dict]:
    """获取某只股票的竞价量能数据"""
    if date is None:
        date = datetime.now().date().isoformat()
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM auction_volume WHERE code = ? AND date = ? ORDER BY minute",
            (code, date),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def db_clear_auction_volume(date: Optional[str] = None) -> dict:
    """清除竞价量能数据"""
    db = await get_db()
    try:
        if date:
            await db.execute("DELETE FROM auction_volume WHERE date = ?", (date,))
        else:
            await db.execute("DELETE FROM auction_volume")
        await db.commit()
        return {"status": "success"}
    finally:
        await db.close()


# ==================== Risk Control CRUD ====================

async def db_save_risk_control(
    date: str,
    week_start: str,
    daily_trades: List[dict],
    weekly_trades: List[dict],
    daily_pnl: float,
    weekly_pnl: float,
    is_locked: bool = False,
    lock_reason: Optional[str] = None,
    lock_until: Optional[str] = None,
) -> dict:
    """保存风控数据"""
    daily_trades_json = json.dumps(daily_trades, ensure_ascii=False, default=str)
    weekly_trades_json = json.dumps(weekly_trades, ensure_ascii=False, default=str)
    now = datetime.now().isoformat()
    db = await get_db()
    try:
        await db.execute(
            """
            INSERT OR REPLACE INTO risk_control
            (date, week_start, daily_trades_json, weekly_trades_json, daily_pnl, weekly_pnl,
             is_locked, lock_reason, lock_until, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date, week_start, daily_trades_json, weekly_trades_json,
                daily_pnl, weekly_pnl,
                1 if is_locked else 0, lock_reason, lock_until, now,
            ),
        )
        await db.commit()
        return {"status": "success", "date": date}
    finally:
        await db.close()


async def db_get_risk_control(date: str) -> Optional[dict]:
    """获取指定日期的风控数据"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM risk_control WHERE date = ?", (date,)
        )
        row = await cursor.fetchone()
        if row:
            data = dict(row)
            data["daily_trades"] = json.loads(data["daily_trades_json"])
            data["weekly_trades"] = json.loads(data["weekly_trades_json"])
            del data["daily_trades_json"]
            del data["weekly_trades_json"]
            data["is_locked"] = bool(data["is_locked"])
            return data
        return None
    finally:
        await db.close()


async def db_get_latest_risk_control() -> Optional[dict]:
    """获取最新的风控数据"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM risk_control ORDER BY date DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        if row:
            data = dict(row)
            data["daily_trades"] = json.loads(data["daily_trades_json"])
            data["weekly_trades"] = json.loads(data["weekly_trades_json"])
            del data["daily_trades_json"]
            del data["weekly_trades_json"]
            data["is_locked"] = bool(data["is_locked"])
            return data
        return None
    finally:
        await db.close()


async def db_get_risk_control_by_week(week_start: str) -> List[dict]:
    """获取本周所有风控数据"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM risk_control WHERE week_start = ? ORDER BY date",
            (week_start,),
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data["daily_trades"] = json.loads(data["daily_trades_json"])
            data["weekly_trades"] = json.loads(data["weekly_trades_json"])
            del data["daily_trades_json"]
            del data["weekly_trades_json"]
            data["is_locked"] = bool(data["is_locked"])
            result.append(data)
        return result
    finally:
        await db.close()
