"""Quick command parser for EVA - handles reminders, timers, etc."""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List

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
    - "включи свет" / "выключи телевизор" -> smart_home
    - "помидор на 25 минут" / "pomodoro" -> pomodoro
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

    # Smart home patterns
    TURN_ON_PATTERN = re.compile(
        r'(?:включи|включить|врубай|врубить|turn\s*on|switch\s*on)\s+(.+)',
        re.IGNORECASE
    )
    TURN_OFF_PATTERN = re.compile(
        r'(?:выключи|выключить|выруби|вырубить|погаси|turn\s*off|switch\s*off)\s+(.+)',
        re.IGNORECASE
    )
    DEVICE_STATUS_PATTERN = re.compile(
        r'(?:статус|состояние|status|state)\s+(?:of\s+)?(.+)',
        re.IGNORECASE
    )

    # Pomodoro patterns
    POMODORO_PATTERN = re.compile(
        r'(?:помидор|pomodoro|помодоро)(?:\s+(?:на|for)\s+(\d+)\s*(?:минут|мин|minutes?)?)?',
        re.IGNORECASE
    )
    POMODORO_BREAK_PATTERN = re.compile(
        r'(?:перерыв|break|отдых)\s*(?:на\s+)?(\d+)?\s*(?:минут|мин|minutes?)?',
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

    # Weather patterns
    WEATHER_CURRENT = re.compile(
        r'(?:какая\s+)?погода(?:\s+(?:в|in)\s+(.+?))?(?:\s+сейчас|\s+сегодня)?$|'
        r'weather(?:\s+in\s+(.+?))?(?:\s+now|\s+today)?$',
        re.IGNORECASE
    )
    WEATHER_FORECAST = re.compile(
        r'прогноз\s+погоды(?:\s+(?:в|in|на)\s+(.+?))?|'
        r'погода\s+(?:на\s+)?(?:завтра|неделю|(\d+)\s+дн)|'
        r'weather\s+forecast(?:\s+(?:in|for)\s+(.+?))?',
        re.IGNORECASE
    )

    # Notes patterns
    NOTE_ADD = re.compile(
        r'(?:запомни|запиши|заметка|note|remember)[:\s]+(.+)',
        re.IGNORECASE
    )
    NOTE_LIST = re.compile(
        r'(?:мои\s+)?заметки|(?:покажи|список)\s+заметок?|my\s+notes|show\s+notes',
        re.IGNORECASE
    )
    NOTE_SEARCH = re.compile(
        r'(?:найди|поиск)\s+(?:в\s+)?заметк[аиу][хх]?\s+(.+)|search\s+notes?\s+(.+)',
        re.IGNORECASE
    )

    # Tasks patterns
    TASK_ADD = re.compile(
        r'(?:добавь|создай|новая)\s+задач[ау][:\s]+(.+)|'
        r'(?:add|create|new)\s+task[:\s]+(.+)|'
        r'задача[:\s]+(.+)',
        re.IGNORECASE
    )
    TASK_ADD_URGENT = re.compile(
        r'(?:срочн[ао]|urgent)[:\s]+(.+)',
        re.IGNORECASE
    )
    TASK_LIST = re.compile(
        r'(?:мои\s+)?задачи|(?:покажи|список)\s+задач|my\s+tasks|show\s+tasks|todo|туду',
        re.IGNORECASE
    )
    TASK_DONE = re.compile(
        r'(?:сделано|готово|выполнено|done|complete)[:\s]+(.+)|'
        r'(?:закрой|завершить)\s+задачу[:\s]+(.+)',
        re.IGNORECASE
    )

    # Mood patterns
    MOOD_LOG = re.compile(
        r'(?:я\s+)?(?:чувствую\s+себя|настроение|mood)[:\s]+(.+)|'
        r'(?:мне\s+)?(?:хорошо|плохо|грустно|отлично|устал[аи]?|стресс)',
        re.IGNORECASE
    )
    MOOD_STATS = re.compile(
        r'(?:моё?\s+)?(?:настроение|mood)\s+(?:за\s+неделю|статистика|stats)|'
        r'как\s+(?:я\s+)?себя\s+чувствовал|mood\s+history',
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

        # Check for Pomodoro
        match = self.POMODORO_PATTERN.search(text)
        if match:
            minutes = int(match.group(1)) if match.group(1) else 25  # Default 25 min
            run_at = datetime.now() + timedelta(minutes=minutes)

            return CommandResult(
                is_command=True,
                command_type="pomodoro",
                params={
                    "user_id": user_id,
                    "message": f"🍅 Помидор завершён! Время для перерыва.",
                    "minutes": minutes,
                    "run_at": run_at
                },
                response=f"🍅 Помидор на {minutes} минут запущен! Фокусируйся, я напомню когда закончится.",
                execute=False
            )

        # Check for break
        match = self.POMODORO_BREAK_PATTERN.search(text)
        if match:
            minutes = int(match.group(1)) if match.group(1) else 5  # Default 5 min
            run_at = datetime.now() + timedelta(minutes=minutes)

            return CommandResult(
                is_command=True,
                command_type="break",
                params={
                    "user_id": user_id,
                    "message": "☕ Перерыв окончен! Готов к новому помидору?",
                    "minutes": minutes,
                    "run_at": run_at
                },
                response=f"☕ Отдыхай {minutes} минут. Я скажу когда пора возвращаться.",
                execute=False
            )

        # Check for weather
        match = self.WEATHER_CURRENT.search(text)
        if match:
            city = match.group(1) or match.group(2)
            return CommandResult(
                is_command=True,
                command_type="weather",
                params={"city": city, "forecast": False},
                response=None,
                execute=False
            )

        match = self.WEATHER_FORECAST.search(text)
        if match:
            city = match.group(1) or match.group(4)
            days = int(match.group(3)) if match.group(3) else 3
            return CommandResult(
                is_command=True,
                command_type="weather",
                params={"city": city, "forecast": True, "days": days},
                response=None,
                execute=False
            )

        # Check for notes
        match = self.NOTE_ADD.search(text)
        if match:
            content = match.group(1).strip()
            return CommandResult(
                is_command=True,
                command_type="note_add",
                params={"user_id": user_id, "content": content},
                response=None,
                execute=False
            )

        if self.NOTE_LIST.search(text):
            return CommandResult(
                is_command=True,
                command_type="note_list",
                params={"user_id": user_id},
                response=None,
                execute=False
            )

        match = self.NOTE_SEARCH.search(text)
        if match:
            query = (match.group(1) or match.group(2)).strip()
            return CommandResult(
                is_command=True,
                command_type="note_search",
                params={"user_id": user_id, "query": query},
                response=None,
                execute=False
            )

        # Check for tasks
        match = self.TASK_ADD_URGENT.search(text)
        if match:
            title = match.group(1).strip()
            return CommandResult(
                is_command=True,
                command_type="task_add",
                params={"user_id": user_id, "title": title, "priority": "urgent"},
                response=None,
                execute=False
            )

        match = self.TASK_ADD.search(text)
        if match:
            title = (match.group(1) or match.group(2) or match.group(3)).strip()
            return CommandResult(
                is_command=True,
                command_type="task_add",
                params={"user_id": user_id, "title": title, "priority": "normal"},
                response=None,
                execute=False
            )

        if self.TASK_LIST.search(text):
            return CommandResult(
                is_command=True,
                command_type="task_list",
                params={"user_id": user_id},
                response=None,
                execute=False
            )

        match = self.TASK_DONE.search(text)
        if match:
            title = (match.group(1) or match.group(2)).strip()
            return CommandResult(
                is_command=True,
                command_type="task_done",
                params={"user_id": user_id, "title": title},
                response=None,
                execute=False
            )

        # Check for mood stats
        if self.MOOD_STATS.search(text):
            return CommandResult(
                is_command=True,
                command_type="mood_stats",
                params={"user_id": user_id},
                response=None,
                execute=False
            )

        # Check for mood log
        match = self.MOOD_LOG.search(text)
        if match:
            mood_text = match.group(1) if match.group(1) else text
            return CommandResult(
                is_command=True,
                command_type="mood_log",
                params={"user_id": user_id, "text": mood_text},
                response=None,
                execute=False
            )

        # Check for smart home - turn on
        match = self.TURN_ON_PATTERN.search(text)
        if match:
            device_name = match.group(1).strip()
            return CommandResult(
                is_command=True,
                command_type="smart_home",
                params={
                    "action": "turn_on",
                    "device": device_name,
                    "user_id": user_id
                },
                response=None,  # Will be set after execution
                execute=False
            )

        # Check for smart home - turn off
        match = self.TURN_OFF_PATTERN.search(text)
        if match:
            device_name = match.group(1).strip()
            return CommandResult(
                is_command=True,
                command_type="smart_home",
                params={
                    "action": "turn_off",
                    "device": device_name,
                    "user_id": user_id
                },
                response=None,
                execute=False
            )

        # Check for device status
        match = self.DEVICE_STATUS_PATTERN.search(text)
        if match:
            device_name = match.group(1).strip()
            return CommandResult(
                is_command=True,
                command_type="smart_home",
                params={
                    "action": "get_state",
                    "device": device_name,
                    "user_id": user_id
                },
                response=None,
                execute=False
            )

        # Not a command
        return CommandResult(is_command=False)


def execute_command(result: CommandResult) -> Tuple[bool, Optional[str]]:
    """
    Execute a parsed command.

    Returns (success, response_message) tuple.
    """
    if not result.is_command:
        return False, None

    if result.command_type in ["reminder", "timer", "pomodoro", "break"]:
        try:
            from proactive.scheduler import get_scheduler
            scheduler = get_scheduler()

            scheduler.add_reminder(
                user_id=result.params["user_id"],
                message=result.params["message"],
                run_at=result.params["run_at"]
            )

            logger.info(f"Scheduled {result.command_type} for {result.params['run_at']}")
            return True, result.response

        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            return False, f"Ошибка: {str(e)}"

    if result.command_type == "smart_home":
        return execute_smart_home_command(result)

    if result.command_type == "weather":
        return execute_weather_command(result)

    if result.command_type.startswith("note_"):
        return execute_note_command(result)

    if result.command_type.startswith("task_"):
        return execute_task_command(result)

    if result.command_type.startswith("mood_"):
        return execute_mood_command(result)

    # Time and date don't need execution, just response
    return True, result.response


def execute_smart_home_command(result: CommandResult) -> Tuple[bool, str]:
    """Execute smart home command through integrations."""
    try:
        from integrations.base import get_integration_registry

        registry = get_integration_registry()
        action = result.params.get("action")
        device = result.params.get("device", "")

        # Try Home Assistant first
        ha = registry.get("home_assistant")
        if ha and ha.is_connected:
            import asyncio

            # Find entity by name
            async def do_action():
                if action == "turn_on":
                    # Try to find entity
                    states = await ha.execute("list_devices", {})
                    entity_id = find_entity_by_name(states, device)
                    if entity_id:
                        return await ha.execute("turn_on", {"entity_id": entity_id})
                    return {"success": False, "message": f"Устройство '{device}' не найдено"}

                elif action == "turn_off":
                    states = await ha.execute("list_devices", {})
                    entity_id = find_entity_by_name(states, device)
                    if entity_id:
                        return await ha.execute("turn_off", {"entity_id": entity_id})
                    return {"success": False, "message": f"Устройство '{device}' не найдено"}

                elif action == "get_state":
                    states = await ha.execute("list_devices", {})
                    entity_id = find_entity_by_name(states, device)
                    if entity_id:
                        return await ha.execute("get_state", {"entity_id": entity_id})
                    return {"success": False, "message": f"Устройство '{device}' не найдено"}

                return {"success": False, "message": "Unknown action"}

            # Run async function
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, do_action())
                    result_data = future.result()
            else:
                result_data = loop.run_until_complete(do_action())

            if result_data.get("success"):
                if action == "turn_on":
                    return True, f"✅ Включил {device}"
                elif action == "turn_off":
                    return True, f"✅ Выключил {device}"
                elif action == "get_state":
                    state = result_data.get("state", "unknown")
                    name = result_data.get("friendly_name", device)
                    return True, f"📊 {name}: {state}"
            else:
                return False, result_data.get("message", "Ошибка")

        # Try MQTT
        mqtt = registry.get("mqtt")
        if mqtt and mqtt.is_connected:
            import asyncio

            async def do_mqtt_action():
                return await mqtt.execute(action, {"device": device})

            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, do_mqtt_action())
                    result_data = future.result()
            else:
                result_data = loop.run_until_complete(do_mqtt_action())

            if result_data.get("success"):
                return True, f"✅ {action} {device}"
            else:
                return False, result_data.get("message", "Ошибка")

        return False, "Нет подключенных интеграций умного дома. Настрой Home Assistant или MQTT в админке."

    except Exception as e:
        logger.error(f"Smart home command failed: {e}")
        return False, f"Ошибка: {str(e)}"


def find_entity_by_name(states_result: dict, name: str) -> Optional[str]:
    """Find Home Assistant entity ID by friendly name."""
    if not states_result.get("success"):
        return None

    name_lower = name.lower()
    devices = states_result.get("devices", {})

    for domain, entities in devices.items():
        for entity in entities:
            entity_name = entity.get("name", "").lower()
            entity_id = entity.get("entity_id", "")

            # Exact match
            if entity_name == name_lower:
                return entity_id

            # Partial match
            if name_lower in entity_name or entity_name in name_lower:
                return entity_id

            # Check entity_id
            if name_lower in entity_id.lower():
                return entity_id

    return None


def execute_weather_command(result: CommandResult) -> Tuple[bool, str]:
    """Execute weather command."""
    try:
        import asyncio
        from integrations.weather import get_weather_service

        weather = get_weather_service()
        if not weather.is_configured:
            return False, "Погода не настроена. Добавь OpenWeatherMap API ключ в настройках."

        city = result.params.get("city")
        is_forecast = result.params.get("forecast", False)

        async def get_weather():
            if is_forecast:
                days = result.params.get("days", 3)
                data = await weather.get_forecast(city, days)
                return weather.format_forecast(data)
            else:
                data = await weather.get_current(city)
                return weather.format_current(data)

        # Run async
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, get_weather())
                    response = future.result()
            else:
                response = loop.run_until_complete(get_weather())
        except RuntimeError:
            response = asyncio.run(get_weather())

        return True, response

    except Exception as e:
        logger.error(f"Weather command failed: {e}")
        return False, f"Ошибка получения погоды: {str(e)}"


def execute_note_command(result: CommandResult) -> Tuple[bool, str]:
    """Execute note commands."""
    try:
        from core.notes import get_notes_manager

        manager = get_notes_manager()
        user_id = result.params.get("user_id", "default")

        if result.command_type == "note_add":
            content = result.params.get("content", "")
            note = manager.add_note(user_id, content)
            return True, f"📝 Записала: \"{content[:50]}{'...' if len(content) > 50 else ''}\""

        elif result.command_type == "note_list":
            notes = manager.get_notes(user_id)
            return True, manager.format_notes(notes)

        elif result.command_type == "note_search":
            query = result.params.get("query", "")
            notes = manager.search_notes(user_id, query)
            if notes:
                return True, f"Найдено {len(notes)} заметок:\n" + manager.format_notes(notes)
            else:
                return True, f"Заметок с \"{query}\" не найдено"

        return False, "Неизвестная команда заметок"

    except Exception as e:
        logger.error(f"Note command failed: {e}")
        return False, f"Ошибка: {str(e)}"


def execute_task_command(result: CommandResult) -> Tuple[bool, str]:
    """Execute task commands."""
    try:
        from core.notes import get_notes_manager

        manager = get_notes_manager()
        user_id = result.params.get("user_id", "default")

        if result.command_type == "task_add":
            title = result.params.get("title", "")
            priority = result.params.get("priority", "normal")
            task = manager.add_task(user_id, title, priority=priority)

            priority_emoji = {"urgent": "🔴", "high": "🟠", "normal": "🟡", "low": "🟢"}
            emoji = priority_emoji.get(priority, "📋")
            return True, f"{emoji} Добавила задачу: \"{title}\""

        elif result.command_type == "task_list":
            tasks = manager.get_tasks(user_id)
            return True, manager.format_tasks(tasks)

        elif result.command_type == "task_done":
            title = result.params.get("title", "")
            task = manager.complete_task(user_id, task_title=title)
            if task:
                return True, f"✅ Отлично! Задача \"{task.title}\" выполнена!"
            else:
                return False, f"Задача \"{title}\" не найдена"

        return False, "Неизвестная команда задач"

    except Exception as e:
        logger.error(f"Task command failed: {e}")
        return False, f"Ошибка: {str(e)}"


def execute_mood_command(result: CommandResult) -> Tuple[bool, str]:
    """Execute mood commands."""
    try:
        from core.mood import get_mood_tracker

        tracker = get_mood_tracker()
        user_id = result.params.get("user_id", "default")

        if result.command_type == "mood_log":
            text = result.params.get("text", "")
            parsed = tracker.parse_mood(text)

            if parsed:
                mood, score = parsed
                tracker.log_mood(user_id, mood, score, text)
                response = tracker.get_response(mood)
                return True, response
            else:
                return True, "Не совсем поняла. Как именно ты себя чувствуешь? Можешь сказать: хорошо, устал, грустно, или оценить от 1 до 10."

        elif result.command_type == "mood_stats":
            stats = tracker.get_stats(user_id)
            return True, tracker.format_stats(stats)

        return False, "Неизвестная команда настроения"

    except Exception as e:
        logger.error(f"Mood command failed: {e}")
        return False, f"Ошибка: {str(e)}"


# Singleton
_parser = None


def get_command_parser() -> CommandParser:
    global _parser
    if _parser is None:
        _parser = CommandParser()
    return _parser
