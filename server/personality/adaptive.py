"""Adaptive behavior engine - learns what works and what doesn't."""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from config import get_settings

logger = logging.getLogger("eva.adaptive")


class ApproachType(str, Enum):
    """Types of motivation approaches."""
    GENTLE_REMINDER = "gentle_reminder"
    HUMOR = "humor"
    ENCOURAGEMENT = "encouragement"
    QUESTION = "question"
    CHALLENGE = "challenge"
    SUPPORT = "support"
    DISTRACTION = "distraction"  # When stressed, offer distraction


class InteractionOutcome(str, Enum):
    """Outcomes of EVA's interactions."""
    POSITIVE = "positive"  # User engaged, responded well
    NEUTRAL = "neutral"  # No clear reaction
    NEGATIVE = "negative"  # User ignored or reacted poorly
    UNKNOWN = "unknown"


class AdaptiveEngine:
    """
    Learns from interactions to improve EVA's approach.

    Tracks:
    - What motivation approaches work/don't work
    - Best times to interact
    - User's energy patterns
    - Context-dependent preferences
    """

    def __init__(self):
        settings = get_settings()
        self.data_dir = os.path.join(settings.data_dir, "adaptive")
        os.makedirs(self.data_dir, exist_ok=True)

        # In-memory cache per user
        self._user_data: Dict[str, Dict] = {}

    def _get_file_path(self, user_id: str) -> str:
        return os.path.join(self.data_dir, f"{user_id}_adaptive.json")

    def _load_user_data(self, user_id: str) -> Dict:
        """Load adaptive data for user."""
        file_path = self._get_file_path(user_id)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._create_default_data()

    def _save_user_data(self, user_id: str, data: Dict):
        """Save adaptive data for user."""
        file_path = self._get_file_path(user_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _create_default_data(self) -> Dict:
        """Create default adaptive data structure."""
        return {
            "approach_scores": {
                approach.value: {
                    "success": 0,
                    "failure": 0,
                    "last_used": None
                }
                for approach in ApproachType
            },
            "time_patterns": {
                # hour -> engagement score
            },
            "context_preferences": {
                # context -> preferred approach
                "stressed": None,
                "tired": None,
                "energetic": None,
                "default": None
            },
            "recent_interactions": [],  # Last 50 interactions
            "insights": []  # Learned insights
        }

    def get_user_data(self, user_id: str) -> Dict:
        """Get adaptive data for user."""
        if user_id not in self._user_data:
            self._user_data[user_id] = self._load_user_data(user_id)
        return self._user_data[user_id]

    def record_interaction(
        self,
        user_id: str,
        approach: ApproachType,
        context: str,
        outcome: InteractionOutcome,
        notes: str = None
    ):
        """Record an interaction and its outcome."""
        data = self.get_user_data(user_id)
        now = datetime.now()

        # Update approach scores
        approach_data = data["approach_scores"].get(approach.value, {
            "success": 0, "failure": 0, "last_used": None
        })

        if outcome == InteractionOutcome.POSITIVE:
            approach_data["success"] += 1
        elif outcome == InteractionOutcome.NEGATIVE:
            approach_data["failure"] += 1

        approach_data["last_used"] = now.isoformat()
        data["approach_scores"][approach.value] = approach_data

        # Update time patterns
        hour = str(now.hour)
        if hour not in data["time_patterns"]:
            data["time_patterns"][hour] = {"positive": 0, "negative": 0}

        if outcome == InteractionOutcome.POSITIVE:
            data["time_patterns"][hour]["positive"] += 1
        elif outcome == InteractionOutcome.NEGATIVE:
            data["time_patterns"][hour]["negative"] += 1

        # Update context preferences
        if outcome == InteractionOutcome.POSITIVE and context in data["context_preferences"]:
            data["context_preferences"][context] = approach.value

        # Record interaction
        interaction = {
            "timestamp": now.isoformat(),
            "approach": approach.value,
            "context": context,
            "outcome": outcome.value,
            "notes": notes
        }
        data["recent_interactions"].append(interaction)
        data["recent_interactions"] = data["recent_interactions"][-50:]  # Keep last 50

        self._user_data[user_id] = data
        self._save_user_data(user_id, data)

        logger.info(f"Recorded interaction for {user_id}: {approach.value} -> {outcome.value}")

    def get_best_approach(
        self,
        user_id: str,
        context: str = "default",
        exclude_recent: bool = True
    ) -> ApproachType:
        """
        Get the best approach for current context.

        Args:
            user_id: User ID
            context: Current context (stressed, tired, energetic, default)
            exclude_recent: Avoid recently used approaches for variety
        """
        data = self.get_user_data(user_id)

        # Check if there's a preferred approach for this context
        if context in data["context_preferences"] and data["context_preferences"][context]:
            return ApproachType(data["context_preferences"][context])

        # Calculate scores for each approach
        scores = {}
        for approach, stats in data["approach_scores"].items():
            total = stats["success"] + stats["failure"]
            if total == 0:
                # Unexplored approach - give it a chance
                scores[approach] = 0.5
            else:
                scores[approach] = stats["success"] / total

            # Reduce score if used recently
            if exclude_recent and stats["last_used"]:
                last_used = datetime.fromisoformat(stats["last_used"])
                hours_ago = (datetime.now() - last_used).total_seconds() / 3600
                if hours_ago < 24:
                    scores[approach] *= 0.7  # Reduce score for variety

        # Get best approach
        best = max(scores, key=scores.get)
        return ApproachType(best)

    def get_worst_approaches(self, user_id: str, n: int = 2) -> List[ApproachType]:
        """Get approaches that don't work for this user."""
        data = self.get_user_data(user_id)

        scores = {}
        for approach, stats in data["approach_scores"].items():
            total = stats["success"] + stats["failure"]
            if total >= 3:  # Need enough data
                scores[approach] = stats["failure"] / total

        # Sort by failure rate
        sorted_approaches = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [ApproachType(a[0]) for a in sorted_approaches[:n]]

    def get_best_time(self, user_id: str) -> Optional[int]:
        """Get best hour to interact based on patterns."""
        data = self.get_user_data(user_id)

        if not data["time_patterns"]:
            return None

        best_hour = None
        best_score = -1

        for hour, stats in data["time_patterns"].items():
            total = stats["positive"] + stats["negative"]
            if total >= 3:  # Need enough data
                score = stats["positive"] / total
                if score > best_score:
                    best_score = score
                    best_hour = int(hour)

        return best_hour

    def add_insight(self, user_id: str, insight: str):
        """Add a learned insight about the user."""
        data = self.get_user_data(user_id)
        data["insights"].append({
            "timestamp": datetime.now().isoformat(),
            "insight": insight
        })
        data["insights"] = data["insights"][-20:]  # Keep last 20
        self._save_user_data(user_id, data)

    def get_insights(self, user_id: str) -> List[str]:
        """Get learned insights about user."""
        data = self.get_user_data(user_id)
        return [i["insight"] for i in data.get("insights", [])]

    def detect_user_context(
        self,
        user_id: str,
        message: str,
        time_of_day: int
    ) -> str:
        """
        Detect user's current context from message and time.

        Returns: stressed, tired, energetic, or default
        """
        message_lower = message.lower()

        # Stress indicators
        stress_words = ["бесит", "достало", "выбесил", "злой", "раздражает", "ненавижу", "капец", "пипец"]
        if any(word in message_lower for word in stress_words):
            return "stressed"

        # Tired indicators
        tired_words = ["устал", "сонный", "нет сил", "выдохся", "не могу", "лень", "спать"]
        if any(word in message_lower for word in tired_words):
            return "tired"

        # Energetic indicators
        energy_words = ["круто", "супер", "погнали", "давай", "готов", "хочу", "класс"]
        if any(word in message_lower for word in energy_words):
            return "energetic"

        # Time-based defaults
        if 6 <= time_of_day < 10:
            return "default"  # Morning - neutral
        elif 14 <= time_of_day < 16:
            return "tired"  # Post-lunch dip
        elif 22 <= time_of_day or time_of_day < 6:
            return "tired"  # Late night

        return "default"


# Singleton
_engine: Optional[AdaptiveEngine] = None


def get_adaptive_engine() -> AdaptiveEngine:
    global _engine
    if _engine is None:
        _engine = AdaptiveEngine()
    return _engine
