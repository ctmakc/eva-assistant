"""
Learning and Evolution Module for EVA.

This module enables EVA to:
- Learn user's communication style preferences
- Adapt emotional responses
- Remember important facts about the user
- Evolve personality based on interactions
- Track patterns and preferences
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from collections import Counter
import re

logger = logging.getLogger("eva.learning")


@dataclass
class UserFact:
    """A fact learned about the user."""
    key: str              # e.g., "favorite_color", "pet_name", "birthday"
    value: str
    confidence: float     # 0.0 - 1.0
    source: str           # "explicit" (user said), "inferred" (EVA guessed)
    learned_at: str
    last_used: str = ""
    use_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "UserFact":
        return cls(**data)


@dataclass
class CommunicationStyle:
    """User's preferred communication style."""
    formality: float = 0.5      # 0 = casual, 1 = formal
    verbosity: float = 0.5      # 0 = brief, 1 = detailed
    humor_level: float = 0.5    # 0 = serious, 1 = playful
    emoji_usage: float = 0.3    # 0 = none, 1 = lots
    encouragement: float = 0.5  # 0 = neutral, 1 = very supportive
    directness: float = 0.5     # 0 = soft, 1 = direct

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CommunicationStyle":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class EmotionalPattern:
    """Tracked emotional patterns."""
    morning_mood_avg: float = 5.0
    evening_mood_avg: float = 5.0
    stress_triggers: List[str] = field(default_factory=list)
    happiness_triggers: List[str] = field(default_factory=list)
    weekly_pattern: Dict[str, float] = field(default_factory=dict)  # day -> avg mood
    mood_volatility: float = 0.5  # How much mood varies

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "EmotionalPattern":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class InteractionStats:
    """Statistics about user interactions."""
    total_messages: int = 0
    total_voice_minutes: float = 0.0
    favorite_topics: Dict[str, int] = field(default_factory=dict)
    active_hours: Dict[int, int] = field(default_factory=dict)  # hour -> count
    avg_message_length: float = 0.0
    response_preferences: Dict[str, int] = field(default_factory=dict)  # short/medium/long
    last_interaction: str = ""
    streak_days: int = 0
    longest_streak: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "InteractionStats":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class LearningModule:
    """
    Core learning module that tracks and adapts to user behavior.

    This module observes interactions and gradually learns:
    - How the user likes to communicate
    - What topics interest them
    - Their emotional patterns
    - Facts about their life
    - When they're most active
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.learning_dir = os.path.join(data_dir, "learning")
        os.makedirs(self.learning_dir, exist_ok=True)

        # Learning rate - how quickly to adapt (0.1 = slow, 0.5 = fast)
        self.learning_rate = 0.15

    def _get_user_file(self, user_id: str) -> str:
        return os.path.join(self.learning_dir, f"{user_id}_learning.json")

    def _load_user_data(self, user_id: str) -> Dict[str, Any]:
        file_path = self._get_user_file(user_id)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading learning data: {e}")

        # Default structure
        return {
            "facts": {},
            "style": CommunicationStyle().to_dict(),
            "emotional_patterns": EmotionalPattern().to_dict(),
            "stats": InteractionStats().to_dict(),
            "feedback_history": [],
            "evolution_log": []
        }

    def _save_user_data(self, user_id: str, data: Dict[str, Any]):
        file_path = self._get_user_file(user_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ============== Fact Learning ==============

    def learn_fact(
        self,
        user_id: str,
        key: str,
        value: str,
        source: str = "explicit",
        confidence: float = 1.0
    ):
        """Learn a fact about the user."""
        data = self._load_user_data(user_id)

        fact = UserFact(
            key=key,
            value=value,
            confidence=confidence,
            source=source,
            learned_at=datetime.now().isoformat()
        )

        data["facts"][key] = fact.to_dict()
        self._save_user_data(user_id, data)

        logger.info(f"Learned fact for {user_id}: {key}={value}")

    def get_fact(self, user_id: str, key: str) -> Optional[str]:
        """Get a learned fact about the user."""
        data = self._load_user_data(user_id)
        fact_data = data["facts"].get(key)

        if fact_data:
            # Update usage stats
            fact_data["last_used"] = datetime.now().isoformat()
            fact_data["use_count"] = fact_data.get("use_count", 0) + 1
            data["facts"][key] = fact_data
            self._save_user_data(user_id, data)
            return fact_data["value"]

        return None

    def get_all_facts(self, user_id: str) -> Dict[str, str]:
        """Get all known facts about the user."""
        data = self._load_user_data(user_id)
        return {k: v["value"] for k, v in data["facts"].items()}

    def extract_facts_from_message(self, user_id: str, message: str):
        """Try to extract facts from user message."""
        message_lower = message.lower()

        # Patterns for fact extraction
        patterns = [
            # Name patterns
            (r"(?:меня зовут|я\s+)(\w+)", "user_name"),
            (r"(?:my name is|i\'?m\s+)(\w+)", "user_name"),

            # Pet patterns
            (r"(?:мо[йяего]+\s+)?(?:кот[аику]?|собак[аеу]?|питом[е|ц]а?)\s+(?:зовут\s+)?(\w+)", "pet_name"),
            (r"(?:my\s+)?(?:cat|dog|pet)(?:\'s name is|named)\s+(\w+)", "pet_name"),

            # Location patterns
            (r"(?:я из|живу в|я в)\s+(\w+)", "location"),
            (r"(?:i\'?m from|i live in)\s+(\w+)", "location"),

            # Work patterns
            (r"(?:я работаю|работаю)\s+(\w+)", "job"),
            (r"(?:i work as|i\'?m a)\s+(\w+)", "job"),

            # Birthday
            (r"(?:день рождения|родился)\s+(\d{1,2}[.\s/]\d{1,2})", "birthday"),

            # Preferences
            (r"(?:люблю|обожаю|нравится)\s+(\w+)", "likes"),
            (r"(?:не люблю|ненавижу|бесит)\s+(\w+)", "dislikes"),
        ]

        for pattern, key in patterns:
            match = re.search(pattern, message_lower)
            if match:
                value = match.group(1).strip()
                if len(value) > 1:  # Avoid single letters
                    self.learn_fact(user_id, key, value, source="inferred", confidence=0.7)

    # ============== Style Learning ==============

    def get_style(self, user_id: str) -> CommunicationStyle:
        """Get user's learned communication style."""
        data = self._load_user_data(user_id)
        return CommunicationStyle.from_dict(data["style"])

    def update_style_from_message(self, user_id: str, message: str):
        """Update style preferences based on user message."""
        data = self._load_user_data(user_id)
        style = CommunicationStyle.from_dict(data["style"])

        # Analyze message characteristics
        msg_len = len(message)
        has_emoji = bool(re.search(r'[\U0001F300-\U0001F9FF]', message))
        is_formal = any(word in message.lower() for word in
                       ["пожалуйста", "будьте добры", "не могли бы", "please", "would you"])
        is_casual = any(word in message.lower() for word in
                       ["чё", "ваще", "норм", "ок", "круто", "yo", "sup", "cool"])
        has_humor = any(word in message.lower() for word in
                       ["хаха", "лол", "ржу", "😂", "🤣", "haha", "lol", "lmao"])

        # Gradually adjust style based on observations
        lr = self.learning_rate

        # Adjust formality
        if is_formal:
            style.formality = min(1.0, style.formality + lr)
        elif is_casual:
            style.formality = max(0.0, style.formality - lr)

        # Adjust verbosity based on message length
        if msg_len > 200:
            style.verbosity = min(1.0, style.verbosity + lr * 0.5)
        elif msg_len < 30:
            style.verbosity = max(0.0, style.verbosity - lr * 0.5)

        # Adjust emoji preference
        if has_emoji:
            style.emoji_usage = min(1.0, style.emoji_usage + lr)

        # Adjust humor level
        if has_humor:
            style.humor_level = min(1.0, style.humor_level + lr)

        data["style"] = style.to_dict()
        self._save_user_data(user_id, data)

    def update_style_from_feedback(self, user_id: str, feedback: str):
        """Update style based on explicit feedback."""
        data = self._load_user_data(user_id)
        style = CommunicationStyle.from_dict(data["style"])

        feedback_lower = feedback.lower()

        # Process feedback
        if "короче" in feedback_lower or "кратко" in feedback_lower:
            style.verbosity = max(0.0, style.verbosity - 0.2)
        elif "подробнее" in feedback_lower or "детальнее" in feedback_lower:
            style.verbosity = min(1.0, style.verbosity + 0.2)

        if "серьёзн" in feedback_lower or "без шуток" in feedback_lower:
            style.humor_level = max(0.0, style.humor_level - 0.2)
        elif "веселее" in feedback_lower or "шутить" in feedback_lower:
            style.humor_level = min(1.0, style.humor_level + 0.2)

        if "проще" in feedback_lower or "неформально" in feedback_lower:
            style.formality = max(0.0, style.formality - 0.2)
        elif "официальн" in feedback_lower or "формальн" in feedback_lower:
            style.formality = min(1.0, style.formality + 0.2)

        # Log feedback
        data["feedback_history"].append({
            "feedback": feedback,
            "timestamp": datetime.now().isoformat(),
            "style_after": style.to_dict()
        })

        data["style"] = style.to_dict()
        self._save_user_data(user_id, data)

        logger.info(f"Updated style for {user_id} based on feedback")

    # ============== Emotional Learning ==============

    def get_emotional_patterns(self, user_id: str) -> EmotionalPattern:
        """Get user's emotional patterns."""
        data = self._load_user_data(user_id)
        return EmotionalPattern.from_dict(data["emotional_patterns"])

    def update_emotional_data(self, user_id: str, mood: str, score: int, context: str = ""):
        """Update emotional pattern data."""
        data = self._load_user_data(user_id)
        patterns = EmotionalPattern.from_dict(data["emotional_patterns"])

        hour = datetime.now().hour
        day = datetime.now().strftime("%A")

        # Update time-based averages
        if 5 <= hour < 12:
            patterns.morning_mood_avg = (patterns.morning_mood_avg + score) / 2
        elif 17 <= hour < 23:
            patterns.evening_mood_avg = (patterns.evening_mood_avg + score) / 2

        # Update weekly pattern
        if day in patterns.weekly_pattern:
            patterns.weekly_pattern[day] = (patterns.weekly_pattern[day] + score) / 2
        else:
            patterns.weekly_pattern[day] = score

        # Track triggers
        if context:
            if score <= 3:  # Negative mood
                if context not in patterns.stress_triggers:
                    patterns.stress_triggers.append(context)
                    patterns.stress_triggers = patterns.stress_triggers[-10:]  # Keep last 10
            elif score >= 8:  # Positive mood
                if context not in patterns.happiness_triggers:
                    patterns.happiness_triggers.append(context)
                    patterns.happiness_triggers = patterns.happiness_triggers[-10:]

        data["emotional_patterns"] = patterns.to_dict()
        self._save_user_data(user_id, data)

    # ============== Interaction Stats ==============

    def get_stats(self, user_id: str) -> InteractionStats:
        """Get interaction statistics."""
        data = self._load_user_data(user_id)
        return InteractionStats.from_dict(data["stats"])

    def record_interaction(self, user_id: str, message: str, is_voice: bool = False):
        """Record an interaction for stats."""
        data = self._load_user_data(user_id)
        stats = InteractionStats.from_dict(data["stats"])

        # Update counts
        stats.total_messages += 1

        if is_voice:
            # Estimate voice duration (avg speaking rate ~150 wpm)
            word_count = len(message.split())
            stats.total_voice_minutes += word_count / 150

        # Update active hours
        hour = datetime.now().hour
        stats.active_hours[str(hour)] = stats.active_hours.get(str(hour), 0) + 1

        # Update average message length
        total_len = stats.avg_message_length * (stats.total_messages - 1) + len(message)
        stats.avg_message_length = total_len / stats.total_messages

        # Update streak
        today = datetime.now().date().isoformat()
        if stats.last_interaction:
            last_date = datetime.fromisoformat(stats.last_interaction).date()
            if (datetime.now().date() - last_date).days == 1:
                stats.streak_days += 1
                stats.longest_streak = max(stats.longest_streak, stats.streak_days)
            elif (datetime.now().date() - last_date).days > 1:
                stats.streak_days = 1

        stats.last_interaction = datetime.now().isoformat()

        # Extract topics (simple keyword extraction)
        topics = self._extract_topics(message)
        for topic in topics:
            stats.favorite_topics[topic] = stats.favorite_topics.get(topic, 0) + 1

        data["stats"] = stats.to_dict()
        self._save_user_data(user_id, data)

    def _extract_topics(self, message: str) -> List[str]:
        """Extract topics from message."""
        topics = []
        message_lower = message.lower()

        topic_keywords = {
            "work": ["работа", "работу", "офис", "проект", "задач", "work", "office", "project"],
            "health": ["здоровь", "болит", "устал", "спорт", "тренировк", "health", "tired", "workout"],
            "family": ["семь", "родител", "дети", "мама", "папа", "family", "parents", "kids"],
            "money": ["деньг", "зарплат", "бюджет", "купить", "money", "salary", "budget"],
            "hobby": ["хобби", "игр", "фильм", "книг", "музык", "hobby", "game", "movie", "book"],
            "food": ["еда", "есть", "готовить", "рецепт", "food", "eat", "cook", "recipe"],
            "travel": ["путешеств", "отпуск", "поездк", "travel", "vacation", "trip"],
            "tech": ["код", "программ", "компьютер", "телефон", "code", "programming", "computer"],
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in message_lower for kw in keywords):
                topics.append(topic)

        return topics

    # ============== Style Prompts ==============

    def get_style_prompt(self, user_id: str) -> str:
        """Generate a prompt describing the learned communication style."""
        style = self.get_style(user_id)
        facts = self.get_all_facts(user_id)
        patterns = self.get_emotional_patterns(user_id)
        stats = self.get_stats(user_id)

        prompt_parts = []

        # Communication style
        if style.formality < 0.3:
            prompt_parts.append("Общайся неформально и дружелюбно")
        elif style.formality > 0.7:
            prompt_parts.append("Поддерживай вежливый и формальный тон")

        if style.verbosity < 0.3:
            prompt_parts.append("Отвечай кратко и по делу")
        elif style.verbosity > 0.7:
            prompt_parts.append("Давай развёрнутые ответы с деталями")

        if style.humor_level > 0.6:
            prompt_parts.append("Используй юмор и шутки")
        elif style.humor_level < 0.2:
            prompt_parts.append("Будь серьёзной, избегай шуток")

        if style.emoji_usage > 0.5:
            prompt_parts.append("Используй эмодзи в ответах")

        if style.encouragement > 0.7:
            prompt_parts.append("Будь очень поддерживающей и ободряющей")

        # Known facts
        if facts:
            fact_str = ", ".join(f"{k}: {v}" for k, v in list(facts.items())[:5])
            prompt_parts.append(f"Помни о пользователе: {fact_str}")

        # Emotional context
        if patterns.stress_triggers:
            prompt_parts.append(f"Триггеры стресса: {', '.join(patterns.stress_triggers[:3])}")

        # Interaction context
        if stats.streak_days > 7:
            prompt_parts.append(f"Пользователь общается {stats.streak_days} дней подряд!")

        return ". ".join(prompt_parts) if prompt_parts else ""

    # ============== Evolution Log ==============

    def log_evolution(self, user_id: str, event: str, details: Dict[str, Any] = None):
        """Log an evolution event."""
        data = self._load_user_data(user_id)

        data["evolution_log"].append({
            "event": event,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })

        # Keep last 100 events
        data["evolution_log"] = data["evolution_log"][-100:]

        self._save_user_data(user_id, data)

    def get_evolution_summary(self, user_id: str) -> str:
        """Get summary of how EVA has evolved for this user."""
        style = self.get_style(user_id)
        stats = self.get_stats(user_id)
        facts = self.get_all_facts(user_id)

        summary_parts = []

        if stats.total_messages > 0:
            summary_parts.append(f"Мы общаемся уже {stats.total_messages} сообщений")

        if stats.streak_days > 1:
            summary_parts.append(f"Общаемся {stats.streak_days} дней подряд")

        if facts:
            summary_parts.append(f"Я знаю о тебе {len(facts)} фактов")

        style_desc = []
        if style.formality < 0.4:
            style_desc.append("неформальному общению")
        if style.humor_level > 0.5:
            style_desc.append("шуткам")
        if style.verbosity < 0.4:
            style_desc.append("кратким ответам")
        elif style.verbosity > 0.6:
            style_desc.append("подробным ответам")

        if style_desc:
            summary_parts.append(f"Адаптировалась к: {', '.join(style_desc)}")

        if stats.favorite_topics:
            top_topics = sorted(stats.favorite_topics.items(), key=lambda x: x[1], reverse=True)[:3]
            topics = [t[0] for t in top_topics]
            summary_parts.append(f"Твои любимые темы: {', '.join(topics)}")

        return ". ".join(summary_parts) if summary_parts else "Я только начинаю узнавать тебя!"


# Singleton
_learning_module: Optional[LearningModule] = None


def get_learning_module() -> LearningModule:
    global _learning_module
    if _learning_module is None:
        from config import get_settings
        settings = get_settings()
        _learning_module = LearningModule(settings.data_dir)
    return _learning_module
