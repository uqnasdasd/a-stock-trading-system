"""告警推送服务 - 钉钉/企微Webhook"""
import httpx
import json
from typing import Optional
from datetime import datetime
from loguru import logger
from app.models.schemas import AlertLevel, SignalType
from app.core.config import settings


class AlertPusher:
    """告警推送器"""

    def __init__(self):
        self.dingtalk_webhook = settings.dingtalk_webhook
        self.wechat_webhook = settings.wechat_webhook

    async def push(self, signal: dict) -> bool:
        """推送告警"""
        level = signal.get("level", AlertLevel.INFO)
        title = signal.get("message", "")
        code = signal.get("code", "")
        name = signal.get("name", "")
        suggested_action = signal.get("suggested_action", "")
        trigger_condition = signal.get("trigger_condition", "")

        # 构建消息内容
        content = self._build_message(signal)

        success = True

        # 推送到钉钉
        if self.dingtalk_webhook:
            try:
                await self._push_dingtalk(title, content, level)
            except Exception as e:
                logger.error(f"钉钉推送失败: {e}")
                success = False

        # 推送到企微
        if self.wechat_webhook:
            try:
                await self._push_wechat(title, content, level)
            except Exception as e:
                logger.error(f"企微推送失败: {e}")
                success = False

        return success

    def _build_message(self, signal: dict) -> str:
        """构建推送消息"""
        level = signal.get("level", AlertLevel.INFO)
        signal_type = signal.get("type", SignalType.INFO)
        code = signal.get("code", "")
        name = signal.get("name", "")
        message = signal.get("message", "")
        trigger_price = signal.get("trigger_price")
        trigger_condition = signal.get("trigger_condition", "")
        suggested_action = signal.get("suggested_action", "")
        timestamp = signal.get("timestamp", datetime.now().isoformat())

        # 级别标签
        level_tags = {
            AlertLevel.EMERGENCY: "🚨 紧急",
            AlertLevel.IMPORTANT: "⚠️ 重要",
            AlertLevel.NORMAL: "📌 一般",
            AlertLevel.INFO: "ℹ️ 信息",
        }
        level_tag = level_tags.get(level, "ℹ️")

        # 类型标签
        type_tags = {
            SignalType.STOP_LOSS: "【止损】",
            SignalType.TAKE_PROFIT: "【止盈】",
            SignalType.AUCTION_BUY: "【竞价买点】",
            SignalType.OPEN_CONFIRM: "【开盘确认】",
            SignalType.POSITION_SELL: "【清仓】",
            SignalType.RISK_ALERT: "【风控】",
        }
        type_tag = type_tags.get(signal_type, "")

        lines = [
            f"{level_tag} {type_tag}",
            f"",
            f"{message}",
            f"",
        ]

        if code:
            lines.append(f"股票: {name}({code})")
        if trigger_price:
            lines.append(f"触发价: ¥{trigger_price:.2f}")
        if trigger_condition:
            lines.append(f"触发条件: {trigger_condition}")
        if suggested_action:
            lines.append(f"建议操作: {suggested_action}")

        lines.append(f"")
        lines.append(f"时间: {timestamp}")

        return "\n".join(lines)

    async def _push_dingtalk(self, title: str, content: str, level: AlertLevel):
        """推送到钉钉"""
        if not self.dingtalk_webhook:
            return

        # 钉钉Markdown消息
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title[:100],
                "text": content,
            }
        }

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                self.dingtalk_webhook,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

    async def _push_wechat(self, title: str, content: str, level: AlertLevel):
        """推送到企业微信"""
        if not self.wechat_webhook:
            return

        # 企微Markdown消息
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": content,
            }
        }

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                self.wechat_webhook,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()


# 单例
alert_pusher = AlertPusher()
