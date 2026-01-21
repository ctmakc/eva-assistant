"""Quick command parser for EVA - handles reminders, timers, etc."""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger("eva.commands")


class CommandResult:
    """Result of command parsing."""

    def __init__(
        self,
        is_command: bool = False,
        command_type: str = None,
        params: Dict[str, Any] = None,
        response: str = None,
        execute: bool = True
    ):
        self.is_command = is_command
        self.command_type = command_type
        self.params = params or {}
        self.response = response
        self.execute = execute  # Whether to also send to LLM


class CommandParser:
    """
    Parses user messages for quick commands.

    Supported commands:
    - "напомни через X минут/часов" -> reminder
    - "таймер на X минут" -> timer
    - "который час" / "сколько времени" -> time
    - "какой сегодня день" / "какая дата" -> date
    """

    # Time patterns
    MINUTES_PATTERN = re.compile(
        r'(?:напомни|напомнить|reminder).*?(?:через|in)\s*(\d+)\s*(?:минут|мин|minutes?|mins?)',
        re.IGNORECASE
    )
    HOURS_PATTERN = re.compile(
        r'(?:напомни|напомнить|reminder).*?(?:через|in)\s*(\d+)\s*(?:час|часа|часов|hours?|hrs?)',
        re.IGNORECASE
    )
    TIMER_PATTERN = re.compile(
        r'(?:таймер|timer).*?(?:на|for)\s*(\d+)\s*(?:минут|мин|minutes?|mins?)',
        re.IGNORECASE
    )

    # Info patterns
    TIME_QUERY = re.compile(
        r'(?:который\s+час|сколько\s+времени|what\s+time|current\s+time)',
        re.IGNORECASE
    )
    DATE_QUERY = re.compile(
        r'(?:какой\s+сегодня\s+день|какая\s+дата|what\s+day|today\'?s?\s+date|current\s+date)',
        re.IGNORECASE
    )

    # Reminder with text
    REMINDER_WITH_TEXT = re.compile(
        r'(?:напомни|напомнить|remind\s+me?).*?(?:через|in)\s*(\d+)\s*(?:минут|мин|час|часа|часов|minutes?|mins?|hours?|hrs?)[:\s]+["\']?(.+?)["\']?$',
        re.IGNORECASE
    )

    def parse(self, text: str, user_id: str = "default") -> CommandResult:
        """
        Parse message for commands.

        Returns CommandResult with:
        - is_command: True if a command was detected
        - command_type: Type of command
        - params: Parameters for execution
        - response: Optional immediate response
        - execute: Whether to also process with LLM
        """
        text = text.strip()

        # Check for time query
        if self.TIME_QUERY.search(text):
            now = datetime.now()
            return CommandResult(
                is_command=True,
                command_type="time",
                response=f"Сейчас {now.strftime('%H:%M')}",
                execute=False
            )

        # Check for date query
        if self.DATE_QUERY.search(text):
            now = datetime.now()
            weekdays_ru = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
            months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
            weekday = weekdays_ru[now.weekday()]
            month = months_ru[now.month - 1]
            return CommandResult(
                is_command=True,
                command_type="date",
                response=f"Сегодня {weekday}, {now.day} {month} {now.year} года",
                execute=False
            )

        # Check for reminder with text
        match = self.REMINDER_WITH_TEXT.search(text)
        if match:
            amount = int(match.group(1))
            reminder_text = match.group(2).strip()

            # Determine if minutes or hours
            if any(u in text.lower() for u in ['час', 'hour', 'hr']):
                minutes = amount * 60
                time_str = f"{amount} час" + ("а" if 2 <= amount <= 4 else "ов" if amount >= 5 else "")
            else:
                minutes = amount
                time_str = f"{amount} минут"

            run_at = datetime.now() + timedelta(minutes=minutes)

            return CommandResult(
                is_command=True,
                command_type="reminder",
                params={
                    "user_id": user_id,
                    "message": reminder_text,
                    "minutes": minutes,
                    "run_at": run_at
                },
                response=f"Хорошо, напомню тебе через {time_str}: \"{reminder_text}\"",
                execute=False
            )

        # Check for simple reminder (minutes)
        match = self.MINUTES_PATTERN.search(text)
        if match:
            minutes = int(match.group(1))
            run_at = datetime.now() + timedelta(minutes=minutes)

            return CommandResult(
                is_command=True,
                command_type="reminder",
                params={
                    "user_id": user_id,
                    "message": "Время пришло!",
                    "minutes": minutes,
                    "run_at": run_at
                },
                response=f"Окей, напомню через {minutes} минут!",
                execute=False
            )

        # Check for simple reminder (hours)
        match = self.HOURS_PATTERN.search(text)
        if match:
            hours = int(match.group(1))
            minutes = hours * 60
            run_at = datetime.now() + timedelta(hours=hours)

            return CommandResult(
                is_command=True,
                command_type="reminder",
                params={
                    "user_id": user_id,
                    "message": "Время пришло!",
                    "minutes": minutes,
                    "run_at": run_at
                },
                response=f"Окей, напомню через {hours} час" + ("а" if 2 <= hours <= 4 else "ов" if hours >= 5 else "") + "!",
                execute=False
            )

        # Check for timer
        match = self.TIMER_PATTERN.search(text)
        if match:
            minutes = int(match.group(1))
            run_at = datetime.now() + timedelta(minutes=minutes)

            return CommandResult(
                is_command=True,
                command_type="timer",
                params={
                    "user_id": user_id,
                    "message": f"Таймер на {minutes} минут завершён!",
                    "minutes": minutes,
                    "run_at": run_at
                },
                response=f"Таймер на {minutes} минут запущен!",
                execute=False
            )

        # Not a command
        return CommandResult(is_command=False)


def execute_command(result: CommandResult) -> bool:
    """
    Execute a parsed command.

    Returns True if execution was successful.
    """
    if not result.is_command:
        return False

    if result.command_type in ["reminder", "timer"]:
        try:
            from proactive.scheduler import get_scheduler
            scheduler = get_scheduler()

            scheduler.add_reminder(
                user_id=result.params["user_id"],
                message=result.params["message"],
                run_at=result.params["run_at"]
            )

            logger.info(f"Scheduled {result.command_type} for {result.params['run_at']}")
            return True

        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            return False

    # Time and date don't need execution, just response
    return True


# Singleton
_parser = None


def get_command_parser() -> CommandParser:
    global _parser
    if _parser is None:
        _parser = CommandParser()
    return _parser
