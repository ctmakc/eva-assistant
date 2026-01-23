"""Notification API routes for EVA."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


class TelegramRegisterRequest(BaseModel):
    user_id: str
    chat_id: str


class FirebaseRegisterRequest(BaseModel):
    user_id: str
    fcm_token: str


class WebhookRegisterRequest(BaseModel):
    user_id: str
    webhook_url: str


class SendNotificationRequest(BaseModel):
    user_id: str
    title: str = "EVA"
    message: str
    priority: str = "normal"  # low, normal, high, urgent


@router.post("/register/telegram")
async def register_telegram(request: TelegramRegisterRequest):
    """Register Telegram chat for push notifications."""
    from core.notifications import get_notification_service

    service = get_notification_service()
    service.register_telegram(request.user_id, request.chat_id)

    return {"success": True, "message": "Telegram registered"}


@router.post("/register/firebase")
async def register_firebase(request: FirebaseRegisterRequest):
    """Register Firebase token for push notifications."""
    from core.notifications import get_notification_service

    service = get_notification_service()
    service.register_firebase(request.user_id, request.fcm_token)

    return {"success": True, "message": "Firebase token registered"}


@router.post("/register/webhook")
async def register_webhook(request: WebhookRegisterRequest):
    """Register webhook URL for notifications."""
    from core.notifications import get_notification_service

    service = get_notification_service()
    service.register_webhook(request.user_id, request.webhook_url)

    return {"success": True, "message": "Webhook registered"}


@router.get("/channels/{user_id}")
async def get_user_channels(user_id: str):
    """Get registered notification channels for a user."""
    from core.notifications import get_notification_service

    service = get_notification_service()
    channels = service.get_user_channels(user_id)

    return {
        "user_id": user_id,
        "channels": channels,
        "count": len(channels)
    }


@router.post("/send")
async def send_notification(request: SendNotificationRequest):
    """Send a notification to a user."""
    from core.notifications import get_notification_service, NotificationPriority

    service = get_notification_service()

    # Map priority string to enum
    priority_map = {
        "low": NotificationPriority.LOW,
        "normal": NotificationPriority.NORMAL,
        "high": NotificationPriority.HIGH,
        "urgent": NotificationPriority.URGENT
    }
    priority = priority_map.get(request.priority, NotificationPriority.NORMAL)

    results = await service.send(
        user_id=request.user_id,
        title=request.title,
        message=request.message,
        priority=priority
    )

    if not results:
        raise HTTPException(
            status_code=400,
            detail="No notification channels configured for this user"
        )

    return {
        "success": True,
        "results": results
    }


@router.post("/test/{user_id}")
async def test_notification(user_id: str):
    """Send a test notification to verify setup."""
    from core.notifications import get_notification_service

    service = get_notification_service()
    channels = service.get_user_channels(user_id)

    if not channels:
        raise HTTPException(
            status_code=400,
            detail="No notification channels configured"
        )

    results = await service.send(
        user_id=user_id,
        title="🧪 Тест",
        message="Это тестовое уведомление от EVA. Если ты его видишь - всё работает!"
    )

    return {
        "success": True,
        "channels_tested": list(results.keys()),
        "results": results
    }
