"""Proactive scheduler for EVA - morning greetings, break reminders, etc."""

import asyncio
import logging
from datetime import datetime, time
from typing import Optional, Callable, List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import get_settings
from personality.profile import get_profile_manager

logger = logging.getLogger("eva.scheduler")


class ProactiveScheduler:
    """
    Manages scheduled proactive behaviors:
    - Morning briefing
    - Break reminders
    - Check-ins
    - Custom reminders
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._notification_handlers: List[Callable] = []
        self._running = False

    def add_notification_handler(self, handler: Callable):
        """
        Add handler for notifications.
        Handler signature: async def handler(user_id: str, message: str, trigger: str)
        """
        self._notification_handlers.append(handler)

    async def _notify(self, user_id: str, message: str, trigger: str):
        """Send notification through all handlers."""
        for handler in self._notification_handlers:
            try:
                await handler(user_id, message, trigger)
            except Exception as e:
                logger.error(f"Notification handler error: {e}")

    def start(self):
        """Start the scheduler."""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Proactive scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if self._running:
            self.scheduler.shutdown()
            self._running = False
            logger.info("Proactive scheduler stopped")

    def setup_user_schedule(self, user_id: str, profile_manager=None):
        """
        Setup scheduled tasks for a user based on their profile.
        """
        if profile_manager is None:
            profile_manager = get_profile_manager()

        profile = profile_manager.get_profile(user_id)

        # Parse wake time
        wake_hour, wake_minute = 9, 0
        if profile.wake_time:
            try:
                parts = profile.wake_time.split(":")
                wake_hour, wake_minute = int(parts[0]), int(parts[1])
            except:
                pass

        # Morning briefing - 5 minutes after wake time
        self.add_job(
            job_id=f"{user_id}_morning",
            func=self._morning_briefing,
            args=[user_id],
            hour=wake_hour,
            minute=wake_minute + 5
        )

        # Break reminders - every 90 minutes during work hours
        self.add_job(
            job_id=f"{user_id}_break",
            func=self._break_reminder,
            args=[user_id],
            hour="10-18",
            minute="30"
        )

        # Evening check-in
        self.add_job(
            job_id=f"{user_id}_evening",
            func=self._evening_checkin,
            args=[user_id],
            hour=18,
            minute=0
        )

        logger.info(f"Scheduled tasks set up for user {user_id}")

    def add_job(
        self,
        job_id: str,
        func: Callable,
        args: list = None,
        hour: Any = None,
        minute: Any = None,
        day_of_week: str = "mon-fri"
    ):
        """Add a scheduled job."""
        # Remove existing job with same ID
        try:
            self.scheduler.remove_job(job_id)
        except:
            pass

        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            day_of_week=day_of_week
        )

        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            args=args or [],
            replace_existing=True
        )

        logger.info(f"Added job {job_id}: {hour}:{minute} ({day_of_week})")

    def remove_job(self, job_id: str):
        """Remove a scheduled job."""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job {job_id}")
        except Exception as e:
            logger.warning(f"Could not remove job {job_id}: {e}")

    def add_reminder(
        self,
        user_id: str,
        message: str,
        run_at: datetime,
        reminder_id: str = None
    ):
        """Add a one-time reminder."""
        if reminder_id is None:
            reminder_id = f"{user_id}_reminder_{run_at.timestamp()}"

        self.scheduler.add_job(
            self._send_reminder,
            'date',
            run_date=run_at,
            id=reminder_id,
            args=[user_id, message]
        )

        logger.info(f"Added reminder for {user_id} at {run_at}")
        return reminder_id

    # --- Scheduled task implementations ---

    async def _morning_briefing(self, user_id: str):
        """Morning greeting and briefing."""
        from core.llm import get_llm_service
        from personality.profile import get_profile_manager

        profile = get_profile_manager().get_profile(user_id)
        llm = get_llm_service()

        message, _ = await llm.generate_proactive_message(profile, "morning")
        await self._notify(user_id, message, "morning")

    async def _break_reminder(self, user_id: str):
        """Remind to take a break."""
        from core.llm import get_llm_service
        from personality.profile import get_profile_manager

        profile = get_profile_manager().get_profile(user_id)
        llm = get_llm_service()

        message, _ = await llm.generate_proactive_message(profile, "break")
        await self._notify(user_id, message, "break")

    async def _evening_checkin(self, user_id: str):
        """Evening check-in."""
        from core.llm import get_llm_service
        from personality.profile import get_profile_manager

        profile = get_profile_manager().get_profile(user_id)
        llm = get_llm_service()

        message, _ = await llm.generate_proactive_message(profile, "checkin")
        await self._notify(user_id, message, "checkin")

    async def _send_reminder(self, user_id: str, message: str):
        """Send a custom reminder."""
        await self._notify(user_id, f"⏰ Напоминание: {message}", "reminder")


# Singleton
_scheduler: Optional[ProactiveScheduler] = None


def get_scheduler() -> ProactiveScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = ProactiveScheduler()
    return _scheduler
