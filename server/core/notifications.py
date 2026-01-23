"""Notification system for EVA - push notifications via multiple channels."""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json
import os
import aiohttp

logger = logging.getLogger("eva.notifications")


class NotificationChannel(Enum):
    """Available notification channels."""
    TELEGRAM = "telegram"
    FIREBASE = "firebase"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """A notification to send."""
    id: str
    user_id: str
    title: str
    message: str
    priority: str
    channel: str
    created_at: str
    sent_at: Optional[str] = None
    delivered: bool = False
    data: Dict[str, Any] = None

    def to_dict(self) -> dict:
        result = asdict(self)
        if result['data'] is None:
            result['data'] = {}
        return result


class NotificationService:
    """
    Manages sending notifications through various channels.

    Supports:
    - Telegram (direct messages)
    - Firebase Cloud Messaging (Android push)
    - Webhooks (custom integrations)
    - In-app (when app is open)
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "notification_config.json")
        self.pending_file = os.path.join(data_dir, "pending_notifications.json")

        self.telegram_chat_ids: Dict[str, str] = {}  # user_id -> chat_id
        self.firebase_tokens: Dict[str, str] = {}    # user_id -> fcm_token
        self.webhook_urls: Dict[str, str] = {}       # user_id -> webhook_url

        self.in_app_handlers: List[Callable] = []

        self._load_config()

    def _load_config(self):
        """Load saved configuration."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.telegram_chat_ids = config.get("telegram_chat_ids", {})
                    self.firebase_tokens = config.get("firebase_tokens", {})
                    self.webhook_urls = config.get("webhook_urls", {})
            except Exception as e:
                logger.error(f"Failed to load notification config: {e}")

    def _save_config(self):
        """Save configuration."""
        config = {
            "telegram_chat_ids": self.telegram_chat_ids,
            "firebase_tokens": self.firebase_tokens,
            "webhook_urls": self.webhook_urls
        }
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    # ============== Registration ==============

    def register_telegram(self, user_id: str, chat_id: str):
        """Register Telegram chat for notifications."""
        self.telegram_chat_ids[user_id] = chat_id
        self._save_config()
        logger.info(f"Registered Telegram for user {user_id}: {chat_id}")

    def register_firebase(self, user_id: str, fcm_token: str):
        """Register Firebase token for push notifications."""
        self.firebase_tokens[user_id] = fcm_token
        self._save_config()
        logger.info(f"Registered Firebase token for user {user_id}")

    def register_webhook(self, user_id: str, webhook_url: str):
        """Register webhook URL for notifications."""
        self.webhook_urls[user_id] = webhook_url
        self._save_config()
        logger.info(f"Registered webhook for user {user_id}")

    def add_in_app_handler(self, handler: Callable):
        """Add handler for in-app notifications."""
        self.in_app_handlers.append(handler)

    # ============== Sending ==============

    async def send(
        self,
        user_id: str,
        message: str,
        title: str = "EVA",
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: List[NotificationChannel] = None,
        data: Dict[str, Any] = None
    ) -> Dict[str, bool]:
        """
        Send notification through configured channels.

        Returns dict of channel -> success status.
        """
        if channels is None:
            # Default: try all configured channels
            channels = []
            if user_id in self.telegram_chat_ids:
                channels.append(NotificationChannel.TELEGRAM)
            if user_id in self.firebase_tokens:
                channels.append(NotificationChannel.FIREBASE)
            if user_id in self.webhook_urls:
                channels.append(NotificationChannel.WEBHOOK)
            if self.in_app_handlers:
                channels.append(NotificationChannel.IN_APP)

        if not channels:
            logger.warning(f"No notification channels configured for user {user_id}")
            return {}

        notification = Notification(
            id=f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            user_id=user_id,
            title=title,
            message=message,
            priority=priority.value,
            channel=",".join(c.value for c in channels),
            created_at=datetime.now().isoformat(),
            data=data or {}
        )

        results = {}

        for channel in channels:
            try:
                if channel == NotificationChannel.TELEGRAM:
                    success = await self._send_telegram(user_id, title, message, priority)
                    results["telegram"] = success

                elif channel == NotificationChannel.FIREBASE:
                    success = await self._send_firebase(user_id, title, message, priority, data)
                    results["firebase"] = success

                elif channel == NotificationChannel.WEBHOOK:
                    success = await self._send_webhook(user_id, notification)
                    results["webhook"] = success

                elif channel == NotificationChannel.IN_APP:
                    success = await self._send_in_app(user_id, notification)
                    results["in_app"] = success

            except Exception as e:
                logger.error(f"Failed to send via {channel.value}: {e}")
                results[channel.value] = False

        # Log result
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Notification sent to {user_id}: {success_count}/{len(results)} channels")

        return results

    async def _send_telegram(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority
    ) -> bool:
        """Send via Telegram."""
        chat_id = self.telegram_chat_ids.get(user_id)
        if not chat_id:
            return False

        try:
            from integrations.telegram import get_telegram_integration
            telegram = get_telegram_integration()

            # Format message
            if priority == NotificationPriority.URGENT:
                text = f"🚨 *{title}*\n\n{message}"
            elif priority == NotificationPriority.HIGH:
                text = f"⚠️ *{title}*\n\n{message}"
            else:
                text = f"📬 *{title}*\n\n{message}"

            await telegram.send_message(chat_id, text, parse_mode="Markdown")
            return True

        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False

    async def _send_firebase(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority,
        data: Dict[str, Any] = None
    ) -> bool:
        """Send via Firebase Cloud Messaging."""
        fcm_token = self.firebase_tokens.get(user_id)
        if not fcm_token:
            return False

        try:
            from integrations.vault import get_vault
            vault = get_vault()
            fcm_config = vault.get("firebase")

            if not fcm_config or not fcm_config.get("server_key"):
                logger.warning("Firebase not configured")
                return False

            server_key = fcm_config["server_key"]

            # FCM priority mapping
            fcm_priority = "high" if priority in [NotificationPriority.HIGH, NotificationPriority.URGENT] else "normal"

            payload = {
                "to": fcm_token,
                "priority": fcm_priority,
                "notification": {
                    "title": title,
                    "body": message,
                    "sound": "default" if priority != NotificationPriority.LOW else None
                },
                "data": data or {}
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://fcm.googleapis.com/fcm/send",
                    json=payload,
                    headers={
                        "Authorization": f"key={server_key}",
                        "Content-Type": "application/json"
                    }
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("success", 0) > 0
                    else:
                        logger.error(f"FCM error: {resp.status}")
                        return False

        except Exception as e:
            logger.error(f"Firebase notification failed: {e}")
            return False

    async def _send_webhook(self, user_id: str, notification: Notification) -> bool:
        """Send via webhook."""
        webhook_url = self.webhook_urls.get(user_id)
        if not webhook_url:
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json=notification.to_dict(),
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    return resp.status in [200, 201, 202, 204]

        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return False

    async def _send_in_app(self, user_id: str, notification: Notification) -> bool:
        """Send via in-app handlers (WebSocket, etc.)."""
        if not self.in_app_handlers:
            return False

        success = False
        for handler in self.in_app_handlers:
            try:
                await handler(user_id, notification.to_dict())
                success = True
            except Exception as e:
                logger.error(f"In-app handler failed: {e}")

        return success

    # ============== Convenience methods ==============

    async def send_reminder(self, user_id: str, message: str):
        """Send a reminder notification."""
        return await self.send(
            user_id=user_id,
            message=message,
            title="⏰ Напоминание",
            priority=NotificationPriority.HIGH
        )

    async def send_alert(self, user_id: str, message: str):
        """Send an urgent alert."""
        return await self.send(
            user_id=user_id,
            message=message,
            title="🚨 Важно!",
            priority=NotificationPriority.URGENT
        )

    async def send_daily_summary(self, user_id: str, summary: str):
        """Send daily summary notification."""
        return await self.send(
            user_id=user_id,
            message=summary,
            title="📊 Дневная сводка",
            priority=NotificationPriority.NORMAL
        )

    # ============== Status ==============

    def get_user_channels(self, user_id: str) -> List[str]:
        """Get configured channels for a user."""
        channels = []
        if user_id in self.telegram_chat_ids:
            channels.append("telegram")
        if user_id in self.firebase_tokens:
            channels.append("firebase")
        if user_id in self.webhook_urls:
            channels.append("webhook")
        return channels


# Singleton
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    global _notification_service
    if _notification_service is None:
        from config import get_settings
        settings = get_settings()
        _notification_service = NotificationService(settings.data_dir)
    return _notification_service
