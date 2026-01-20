"""Memory manager for conversation history and context."""

import os
import json
from typing import Optional, List
from datetime import datetime

from config import get_settings
from schemas.models import Message, ConversationHistory, Language


class MemoryManager:
    """Manages conversation history and short-term memory."""

    def __init__(self):
        settings = get_settings()
        self.data_dir = os.path.join(settings.data_dir, "memory")
        self.max_history = settings.max_conversation_history
        os.makedirs(self.data_dir, exist_ok=True)

        # In-memory cache
        self._conversations: dict[str, ConversationHistory] = {}

    def _get_file_path(self, user_id: str) -> str:
        """Get file path for user's conversation history."""
        return os.path.join(self.data_dir, f"{user_id}_history.json")

    def _load_history(self, user_id: str) -> ConversationHistory:
        """Load conversation history from disk."""
        file_path = self._get_file_path(user_id)

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Convert messages to Message objects
                messages = []
                for msg_data in data.get("messages", []):
                    messages.append(Message(
                        role=msg_data["role"],
                        content=msg_data["content"],
                        timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                        language=Language(msg_data.get("language", "auto"))
                    ))
                return ConversationHistory(
                    user_id=user_id,
                    messages=messages,
                    last_updated=datetime.fromisoformat(data.get("last_updated", datetime.now().isoformat()))
                )

        return ConversationHistory(user_id=user_id)

    def _save_history(self, history: ConversationHistory):
        """Save conversation history to disk."""
        file_path = self._get_file_path(history.user_id)

        data = {
            "user_id": history.user_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "language": msg.language.value
                }
                for msg in history.messages
            ],
            "last_updated": history.last_updated.isoformat()
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_history(self, user_id: str) -> ConversationHistory:
        """Get conversation history for user."""
        if user_id not in self._conversations:
            self._conversations[user_id] = self._load_history(user_id)
        return self._conversations[user_id]

    def add_message(
        self,
        user_id: str,
        role: str,
        content: str,
        language: Language = Language.AUTO
    ):
        """Add message to conversation history."""
        history = self.get_history(user_id)
        history.add_message(role, content, language)

        # Trim if too long
        if len(history.messages) > self.max_history * 2:
            history.messages = history.messages[-self.max_history:]

        # Save to disk
        self._save_history(history)

    def get_recent_messages(self, user_id: str, n: int = None) -> List[Message]:
        """Get recent messages for user."""
        if n is None:
            n = self.max_history
        history = self.get_history(user_id)
        return history.get_recent(n)

    def clear_history(self, user_id: str):
        """Clear conversation history for user."""
        if user_id in self._conversations:
            del self._conversations[user_id]

        file_path = self._get_file_path(user_id)
        if os.path.exists(file_path):
            os.unlink(file_path)

    def get_context_summary(self, user_id: str) -> str:
        """Get a brief summary of recent conversation context."""
        messages = self.get_recent_messages(user_id, 5)
        if not messages:
            return "Нет предыдущих сообщений."

        summary_parts = []
        for msg in messages[-3:]:
            role = "Пользователь" if msg.role == "user" else "EVA"
            # Truncate long messages
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            summary_parts.append(f"{role}: {content}")

        return "\n".join(summary_parts)


# Singleton instance
_memory_manager = None


def get_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
