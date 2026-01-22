"""Habit tracker for EVA - track daily habits and build streaks."""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger("eva.habits")


@dataclass
class Habit:
    """A habit to track."""
    id: str
    name: str
    description: str
    frequency: str  # daily, weekly
    created_at: str
    user_id: str
    active: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Habit":
        return cls(**data)


@dataclass
class HabitLog:
    """A log entry for a habit."""
    habit_id: str
    date: str  # YYYY-MM-DD
    completed: bool
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HabitLog":
        return cls(**data)


class HabitTracker:
    """Tracks habits and streaks."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.habits_dir = os.path.join(data_dir, "habits")
        os.makedirs(self.habits_dir, exist_ok=True)

    def _get_habits_file(self, user_id: str) -> str:
        return os.path.join(self.habits_dir, f"{user_id}_habits.json")

    def _get_logs_file(self, user_id: str) -> str:
        return os.path.join(self.habits_dir, f"{user_id}_logs.json")

    def _load_habits(self, user_id: str) -> List[Habit]:
        file_path = self._get_habits_file(user_id)
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Habit.from_dict(h) for h in data]
        except Exception as e:
            logger.error(f"Error loading habits: {e}")
            return []

    def _save_habits(self, user_id: str, habits: List[Habit]):
        file_path = self._get_habits_file(user_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([h.to_dict() for h in habits], f, ensure_ascii=False, indent=2)

    def _load_logs(self, user_id: str) -> List[HabitLog]:
        file_path = self._get_logs_file(user_id)
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [HabitLog.from_dict(l) for l in data]
        except Exception as e:
            logger.error(f"Error loading habit logs: {e}")
            return []

    def _save_logs(self, user_id: str, logs: List[HabitLog]):
        file_path = self._get_logs_file(user_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([l.to_dict() for l in logs], f, ensure_ascii=False, indent=2)

    # ============== Habits ==============

    def add_habit(self, user_id: str, name: str, description: str = "", frequency: str = "daily") -> Habit:
        """Add a new habit to track."""
        habits = self._load_habits(user_id)

        habit = Habit(
            id=f"habit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(habits)}",
            name=name,
            description=description,
            frequency=frequency,
            created_at=datetime.now().isoformat(),
            user_id=user_id
        )

        habits.append(habit)
        self._save_habits(user_id, habits)

        logger.info(f"Added habit for {user_id}: {name}")
        return habit

    def get_habits(self, user_id: str, active_only: bool = True) -> List[Habit]:
        """Get user's habits."""
        habits = self._load_habits(user_id)
        if active_only:
            habits = [h for h in habits if h.active]
        return habits

    def delete_habit(self, user_id: str, habit_id: str = None, habit_name: str = None) -> bool:
        """Deactivate a habit by ID or name."""
        habits = self._load_habits(user_id)

        for habit in habits:
            if (habit_id and habit.id == habit_id) or \
               (habit_name and habit_name.lower() in habit.name.lower()):
                habit.active = False
                self._save_habits(user_id, habits)
                return True

        return False

    # ============== Tracking ==============

    def log_habit(self, user_id: str, habit_id: str = None, habit_name: str = None, note: str = "") -> Optional[HabitLog]:
        """Log a habit as completed for today."""
        habits = self._load_habits(user_id)

        # Find habit
        habit = None
        for h in habits:
            if (habit_id and h.id == habit_id) or \
               (habit_name and habit_name.lower() in h.name.lower()):
                habit = h
                break

        if not habit:
            return None

        logs = self._load_logs(user_id)
        today = datetime.now().strftime('%Y-%m-%d')

        # Check if already logged today
        for log in logs:
            if log.habit_id == habit.id and log.date == today:
                log.completed = True
                log.note = note
                self._save_logs(user_id, logs)
                return log

        # Create new log
        log = HabitLog(
            habit_id=habit.id,
            date=today,
            completed=True,
            note=note
        )
        logs.append(log)
        self._save_logs(user_id, logs)

        logger.info(f"Logged habit {habit.name} for {user_id}")
        return log

    def get_streak(self, user_id: str, habit: Habit) -> int:
        """Calculate current streak for a habit."""
        logs = self._load_logs(user_id)
        habit_logs = [l for l in logs if l.habit_id == habit.id and l.completed]

        if not habit_logs:
            return 0

        # Sort by date descending
        dates = sorted([l.date for l in habit_logs], reverse=True)

        streak = 0
        check_date = datetime.now().date()

        for date_str in dates:
            log_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            if log_date == check_date:
                streak += 1
                check_date -= timedelta(days=1)
            elif log_date == check_date - timedelta(days=1):
                # Allow missing today if checking yesterday
                streak += 1
                check_date = log_date - timedelta(days=1)
            else:
                break

        return streak

    def get_today_status(self, user_id: str) -> Dict[str, Any]:
        """Get today's habit completion status."""
        habits = self.get_habits(user_id)
        logs = self._load_logs(user_id)
        today = datetime.now().strftime('%Y-%m-%d')

        today_logs = {l.habit_id: l for l in logs if l.date == today}

        status = []
        completed_count = 0

        for habit in habits:
            is_done = habit.id in today_logs and today_logs[habit.id].completed
            streak = self.get_streak(user_id, habit)

            if is_done:
                completed_count += 1

            status.append({
                "id": habit.id,
                "name": habit.name,
                "completed": is_done,
                "streak": streak
            })

        return {
            "habits": status,
            "total": len(habits),
            "completed": completed_count,
            "remaining": len(habits) - completed_count
        }

    # ============== Formatting ==============

    def format_habits(self, habits: List[Habit], user_id: str) -> str:
        """Format habits list for voice output."""
        if not habits:
            return "У тебя пока нет привычек. Скажи 'новая привычка: название' чтобы добавить!"

        lines = [f"📊 Твои привычки ({len(habits)}):"]

        for habit in habits:
            streak = self.get_streak(user_id, habit)
            streak_text = f"🔥{streak}" if streak > 0 else ""
            lines.append(f"  • {habit.name} {streak_text}")

        return "\n".join(lines)

    def format_today(self, status: Dict[str, Any]) -> str:
        """Format today's status for voice output."""
        habits = status.get("habits", [])
        total = status.get("total", 0)
        completed = status.get("completed", 0)

        if total == 0:
            return "У тебя пока нет привычек для отслеживания."

        if completed == total:
            return f"🎉 Отлично! Все {total} привычек выполнены сегодня!"

        lines = [f"📊 Привычки на сегодня: {completed}/{total}"]

        for h in habits:
            emoji = "✅" if h["completed"] else "⬜"
            streak = f" 🔥{h['streak']}" if h["streak"] > 0 else ""
            lines.append(f"  {emoji} {h['name']}{streak}")

        if status.get("remaining", 0) > 0:
            lines.append(f"\nОсталось: {status['remaining']}")

        return "\n".join(lines)


# Singleton
_habit_tracker: Optional[HabitTracker] = None


def get_habit_tracker() -> HabitTracker:
    global _habit_tracker
    if _habit_tracker is None:
        from config import get_settings
        settings = get_settings()
        _habit_tracker = HabitTracker(settings.data_dir)
    return _habit_tracker
