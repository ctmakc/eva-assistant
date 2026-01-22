"""Daily briefing module for EVA - morning summary of everything important."""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("eva.briefing")


class DailyBriefing:
    """Generates daily briefings with weather, calendar, tasks, etc."""

    def __init__(self):
        pass

    async def generate(self, user_id: str = "default") -> Dict[str, Any]:
        """Generate a complete daily briefing."""
        sections = []
        errors = []

        # 1. Greeting based on time
        greeting = self._get_greeting()
        sections.append({"type": "greeting", "content": greeting})

        # 2. Weather
        try:
            weather_section = await self._get_weather_section()
            if weather_section:
                sections.append(weather_section)
        except Exception as e:
            logger.error(f"Briefing weather error: {e}")
            errors.append("weather")

        # 3. Calendar - today's events
        try:
            calendar_section = await self._get_calendar_section()
            if calendar_section:
                sections.append(calendar_section)
        except Exception as e:
            logger.error(f"Briefing calendar error: {e}")
            errors.append("calendar")

        # 4. Tasks
        try:
            tasks_section = self._get_tasks_section(user_id)
            if tasks_section:
                sections.append(tasks_section)
        except Exception as e:
            logger.error(f"Briefing tasks error: {e}")
            errors.append("tasks")

        # 5. Unread emails (if Gmail connected)
        try:
            email_section = await self._get_email_section()
            if email_section:
                sections.append(email_section)
        except Exception as e:
            logger.error(f"Briefing email error: {e}")
            errors.append("email")

        # 6. Mood check prompt
        sections.append({
            "type": "mood_prompt",
            "content": "Как ты себя сегодня чувствуешь?"
        })

        return {
            "success": True,
            "sections": sections,
            "errors": errors,
            "generated_at": datetime.now().isoformat()
        }

    def _get_greeting(self) -> str:
        """Get time-appropriate greeting."""
        hour = datetime.now().hour

        if 5 <= hour < 12:
            return "Доброе утро! ☀️"
        elif 12 <= hour < 17:
            return "Добрый день! 👋"
        elif 17 <= hour < 22:
            return "Добрый вечер! 🌆"
        else:
            return "Доброй ночи! 🌙"

    async def _get_weather_section(self) -> Optional[Dict[str, Any]]:
        """Get weather section."""
        from integrations.weather import get_weather_service

        weather = get_weather_service()
        if not weather.is_configured:
            return None

        data = await weather.get_current()
        if not data.get("success"):
            return None

        temp = data["temp"]
        desc = data["description_ru"]
        city = data["city"]

        # Simple weather summary
        content = f"В {city} сейчас {desc}, {temp}°C."

        # Add advice based on weather
        if temp < 0:
            content += " Одевайся теплее!"
        elif temp > 30:
            content += " Не забудь воду!"
        elif "дождь" in desc.lower() or "rain" in desc.lower():
            content += " Возьми зонт!"

        return {
            "type": "weather",
            "content": content,
            "data": data
        }

    async def _get_calendar_section(self) -> Optional[Dict[str, Any]]:
        """Get today's calendar events."""
        from integrations.calendar import get_calendar_integration

        calendar = get_calendar_integration()
        if not calendar.is_authenticated:
            return None

        data = await calendar.get_today_events()
        if not data.get("success"):
            return None

        events = data.get("events", [])
        if not events:
            return {
                "type": "calendar",
                "content": "На сегодня встреч нет - свободный день!",
                "data": {"count": 0}
            }

        # Format events
        lines = [f"📅 Сегодня у тебя {len(events)} событий:"]
        for event in events[:5]:
            time = event.get("time", "")
            summary = event.get("summary", "")
            lines.append(f"  • {time} - {summary}")

        if len(events) > 5:
            lines.append(f"  ...и ещё {len(events) - 5}")

        return {
            "type": "calendar",
            "content": "\n".join(lines),
            "data": {"count": len(events), "events": events}
        }

    def _get_tasks_section(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get pending tasks."""
        from core.notes import get_notes_manager

        manager = get_notes_manager()
        tasks = manager.get_tasks(user_id)

        if not tasks:
            return None

        # Count by priority
        urgent = sum(1 for t in tasks if t.priority == "urgent")
        high = sum(1 for t in tasks if t.priority == "high")
        total = len(tasks)

        if urgent > 0:
            content = f"⚠️ У тебя {urgent} срочных задач из {total}!"
        elif high > 0:
            content = f"📋 У тебя {high} важных задач из {total}."
        else:
            content = f"📋 У тебя {total} задач в списке."

        # Show top 3 tasks
        top_tasks = tasks[:3]
        for task in top_tasks:
            emoji = {"urgent": "🔴", "high": "🟠", "normal": "🟡", "low": "🟢"}.get(task.priority, "📌")
            content += f"\n  {emoji} {task.title}"

        return {
            "type": "tasks",
            "content": content,
            "data": {"total": total, "urgent": urgent, "high": high}
        }

    async def _get_email_section(self) -> Optional[Dict[str, Any]]:
        """Get unread email summary."""
        from integrations.gmail import get_gmail_integration

        gmail = get_gmail_integration()
        if not gmail.is_authenticated:
            return None

        # Get unread count
        try:
            summary = await gmail.get_summary(max_emails=5)
            if not summary.get("success"):
                return None

            unread = summary.get("unread_count", 0)
            if unread == 0:
                return None

            content = f"📧 У тебя {unread} непрочитанных писем."

            # Show recent senders
            emails = summary.get("emails", [])
            if emails:
                senders = list(set(e.get("from", "").split("<")[0].strip() for e in emails[:3]))
                if senders:
                    content += f" От: {', '.join(senders[:3])}"

            return {
                "type": "email",
                "content": content,
                "data": {"unread": unread}
            }

        except Exception:
            return None

    def format_briefing(self, data: Dict[str, Any]) -> str:
        """Format briefing as text for voice output."""
        if not data.get("success"):
            return "Не удалось сформировать брифинг."

        sections = data.get("sections", [])
        lines = []

        for section in sections:
            content = section.get("content", "")
            if content:
                lines.append(content)

        return "\n\n".join(lines)


# Singleton
_briefing: Optional[DailyBriefing] = None


def get_briefing() -> DailyBriefing:
    global _briefing
    if _briefing is None:
        _briefing = DailyBriefing()
    return _briefing
