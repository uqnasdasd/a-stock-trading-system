"""系统配置管理"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """系统配置"""
    # 数据源
    data_source_primary: str = "sina"
    data_source_backup: str = "tencent"
    poll_interval: int = 3

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # 数据库
    database_url: str = "sqlite:///./trading_system.db"

    # 告警推送
    dingtalk_webhook: Optional[str] = None
    wechat_webhook: Optional[str] = None

    # 风控
    max_single_position: float = 0.10
    max_total_position: float = 0.50
    stop_loss_pct: float = 0.03
    take_profit_pct: float = 0.05
    daily_max_loss: float = 0.03
    weekly_max_loss: float = 0.05
    max_trades_per_day: int = 2
    max_trades_per_week: int = 5

    # 交易时段
    market_open: str = "09:30"
    market_close: str = "15:00"
    auction_start: str = "09:15"
    auction_end: str = "09:25"
    morning_end: str = "11:30"
    afternoon_start: str = "13:00"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
