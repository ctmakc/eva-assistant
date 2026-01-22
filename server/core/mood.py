"""Mood tracking for EVA - tracks user's emotional state over time."""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from collections import Counter

logger = logging.getLogger("eva.mood")


@dataclass
class MoodEntry:
    """A mood entry."""
    timestamp: str
    mood: str  # happy, good, neutral, tired, sad, stressed, anxious, angry
    score: int  # 1-10
    note: str
    user_id: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MoodEntry":
        return cls(**data)


# Mood mappings
MOOD_SCORES = {
    "счастлив": ("happy", 9),
    "happy": ("happy", 9),
    "отлично": ("happy", 9),
    "великолепно": ("happy", 10),
    "хорошо": ("good", 7),
    "good": ("good", 7),
    "неплохо": ("good", 6),
    "нормально": ("neutral", 5),
    "normal": ("neutral", 5),
    "так себе": ("neutral", 4),
    "устал": ("tired", 4),
    "tired": ("tired", 4),
    "устала": ("tired", 4),
    "вымотан": ("tired", 3),
    "грустно": ("sad", 3),
    "sad": ("sad", 3),
    "печально": ("sad", 3),
    "плохо": ("sad", 2),
    "стресс": ("stressed", 3),
    "stressed": ("stressed", 3),
    "напряжён": ("stressed", 4),
    "тревожно": ("anxious", 3),
    "anxious": ("anxious", 3),
    "волнуюсь": ("anxious", 4),
    "злюсь": ("angry", 3),
    "angry": ("angry", 3),
    "раздражён": ("angry", 4),
    "бесит": ("angry", 2),
}

MOOD_EMOJI = {
    "happy": "😊",
    "good": "🙂",
    "neutral": "😐",
    "tired": "😴",
    "sad": "😢",
    "stressed": "😰",
    "anxious": "😟",
    "angry": "😠",
}

MOOD_RESPONSES = {
    "happy": [
        "Рада это слышать! 💛",
        "Отлично! Пусть так и будет! ✨",
        "Замечательно! Это заряжает и меня позитивом! 🌟",
    ],
    "good": [
        "Хорошо! 👍",
        "Приятно слышать!",
        "Рада за тебя!",
    ],
    "neutral": [
        "Понятно. Надеюсь, станет лучше! 🤗",
        "Бывает. Я рядом, если что.",
        "Окей. Могу чем-то помочь?",
    ],
    "tired": [
        "Отдохни, если есть возможность. 💤",
        "Понимаю. Не перенапрягайся!",
        "Может, небольшой перерыв?",
    ],
    "sad": [
        "Мне жаль это слышать. Я здесь, если хочешь поговорить. 💙",
        "Обнимаю тебя. Всё наладится.",
        "Грустить тоже нормально. Но я верю, что скоро станет лучше.",
    ],
    "stressed": [
        "Попробуй сделать пару глубоких вдохов. Я подожду. 🧘",
        "Стресс — это временно. Ты справишься!",
        "Хочешь, поставлю таймер на небольшой перерыв?",
    ],
    "anxious": [
        "Всё будет хорошо. Я рядом. 💙",
        "Попробуй сфокусироваться на том, что можешь контролировать.",
        "Тревога пройдёт. Дыши глубже.",
    ],
    "angry": [
        "Понимаю. Иногда нужно выпустить пар.",
        "Что случилось? Хочешь рассказать?",
        "Глубокий вдох... и выдох. 🌬️",
    ],
}


class MoodTracker:
    """Tracks user mood over time."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.mood_dir = os.path.join(data_dir, "mood")
        os.makedirs(self.mood_dir, exist_ok=True)

    def _get_mood_file(self, user_id: str) -> str:
        return os.path.join(self.mood_dir, f"{user_id}.json")

    def _load_moods(self, user_id: str) -> List[MoodEntry]:
        file_path = self._get_mood_file(user_id)
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [MoodEntry.from_dict(m) for m in data]
        except Exception as e:
            logger.error(f"Error loading moods: {e}")
            return []

    def _save_moods(self, user_id: str, moods: List[MoodEntry]):
        file_path = self._get_mood_file(user_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([m.to_dict() for m in moods], f, ensure_ascii=False, indent=2)

    def parse_mood(self, text: str) -> Optional[tuple]:
        """Parse mood from text, returns (mood_name, score) or None."""
        text_lower = text.lower()

        for keyword, (mood, score) in MOOD_SCORES.items():
            if keyword in text_lower:
                return (mood, score)

        # Try to parse numeric score
        import re
        match = re.search(r'(\d+)\s*(?:из|/|of)\s*10', text_lower)
        if match:
            score = int(match.group(1))
            score = max(1, min(10, score))

            if score >= 8:
                return ("happy", score)
            elif score >= 6:
                return ("good", score)
            elif score >= 4:
                return ("neutral", score)
            elif score >= 2:
                return ("tired", score)
            else:
                return ("sad", score)

        return None

    def log_mood(self, user_id: str, mood: str, score: int, note: str = "") -> MoodEntry:
        """Log a mood entry."""
        moods = self._load_moods(user_id)

        entry = MoodEntry(
            timestamp=datetime.now().isoformat(),
            mood=mood,
            score=score,
            note=note,
            user_id=user_id
        )

        moods.append(entry)

        # Keep last 1000 entries
        if len(moods) > 1000:
            moods = moods[-1000:]

        self._save_moods(user_id, moods)
        logger.info(f"Logged mood for {user_id}: {mood} ({score}/10)")

        return entry

    def get_response(self, mood: str) -> str:
        """Get an empathetic response for a mood."""
        import random
        responses = MOOD_RESPONSES.get(mood, MOOD_RESPONSES["neutral"])
        return random.choice(responses)

    def get_stats(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get mood statistics for the past N days."""
        moods = self._load_moods(user_id)

        cutoff = datetime.now() - timedelta(days=days)
        recent = [m for m in moods if datetime.fromisoformat(m.timestamp) > cutoff]

        if not recent:
            return {
                "entries": 0,
                "average_score": None,
                "most_common": None,
                "trend": None
            }

        scores = [m.score for m in recent]
        mood_counts = Counter(m.mood for m in recent)

        # Calculate trend (comparing first half to second half)
        mid = len(recent) // 2
        if mid > 0:
            first_half_avg = sum(m.score for m in recent[:mid]) / mid
            second_half_avg = sum(m.score for m in recent[mid:]) / (len(recent) - mid)
            trend = "up" if second_half_avg > first_half_avg + 0.5 else \
                    "down" if second_half_avg < first_half_avg - 0.5 else "stable"
        else:
            trend = "stable"

        return {
            "entries": len(recent),
            "average_score": round(sum(scores) / len(scores), 1),
            "most_common": mood_counts.most_common(1)[0][0] if mood_counts else None,
            "trend": trend,
            "by_mood": dict(mood_counts)
        }

    def format_stats(self, stats: Dict[str, Any]) -> str:
        """Format mood stats as human-readable text."""
        if stats["entries"] == 0:
            return "У меня пока нет данных о твоём настроении. Расскажи, как ты себя чувствуешь?"

        avg = stats["average_score"]
        most_common = stats["most_common"]
        trend = stats["trend"]
        emoji = MOOD_EMOJI.get(most_common, "")

        mood_ru = {
            "happy": "счастливым",
            "good": "хорошим",
            "neutral": "нормальным",
            "tired": "уставшим",
            "sad": "грустным",
            "stressed": "напряжённым",
            "anxious": "тревожным",
            "angry": "раздражённым",
        }

        trend_ru = {
            "up": "улучшается 📈",
            "down": "ухудшается 📉",
            "stable": "стабильное 📊",
        }

        text = f"За последнюю неделю ты чаще всего был(а) {mood_ru.get(most_common, most_common)} {emoji}\n"
        text += f"Средняя оценка настроения: {avg}/10\n"
        text += f"Тренд: {trend_ru.get(trend, trend)}"

        return text

    def should_ask_mood(self, user_id: str) -> bool:
        """Check if it's time to ask about mood (max once per 4 hours)."""
        moods = self._load_moods(user_id)
        if not moods:
            return True

        last = datetime.fromisoformat(moods[-1].timestamp)
        hours_since = (datetime.now() - last).total_seconds() / 3600

        return hours_since >= 4

    def get_mood_prompt(self) -> str:
        """Get a random prompt to ask about mood."""
        import random
        prompts = [
            "Кстати, как ты себя сегодня чувствуешь?",
            "Как настроение?",
            "Как дела? Правда интересно!",
            "Расскажи, как ты?",
        ]
        return random.choice(prompts)


# Singleton
_mood_tracker: Optional[MoodTracker] = None


def get_mood_tracker() -> MoodTracker:
    global _mood_tracker
    if _mood_tracker is None:
        from config import get_settings
        settings = get_settings()
        _mood_tracker = MoodTracker(settings.data_dir)
    return _mood_tracker
