"""Notes and Tasks system for EVA - voice-controlled note taking."""

import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger("eva.notes")


class TaskPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class Note:
    """A simple note."""
    id: str
    content: str
    created_at: str
    tags: List[str]
    user_id: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Note":
        return cls(**data)


@dataclass
class Task:
    """A task/todo item."""
    id: str
    title: str
    description: str
    created_at: str
    due_date: Optional[str]
    priority: str
    status: str
    tags: List[str]
    user_id: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(**data)


class NotesManager:
    """Manages notes and tasks for users."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.notes_dir = os.path.join(data_dir, "notes")
        self.tasks_dir = os.path.join(data_dir, "tasks")
        os.makedirs(self.notes_dir, exist_ok=True)
        os.makedirs(self.tasks_dir, exist_ok=True)

    def _get_notes_file(self, user_id: str) -> str:
        return os.path.join(self.notes_dir, f"{user_id}.json")

    def _get_tasks_file(self, user_id: str) -> str:
        return os.path.join(self.tasks_dir, f"{user_id}.json")

    def _load_notes(self, user_id: str) -> List[Note]:
        file_path = self._get_notes_file(user_id)
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Note.from_dict(n) for n in data]
        except Exception as e:
            logger.error(f"Error loading notes: {e}")
            return []

    def _save_notes(self, user_id: str, notes: List[Note]):
        file_path = self._get_notes_file(user_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([n.to_dict() for n in notes], f, ensure_ascii=False, indent=2)

    def _load_tasks(self, user_id: str) -> List[Task]:
        file_path = self._get_tasks_file(user_id)
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Task.from_dict(t) for t in data]
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")
            return []

    def _save_tasks(self, user_id: str, tasks: List[Task]):
        file_path = self._get_tasks_file(user_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([t.to_dict() for t in tasks], f, ensure_ascii=False, indent=2)

    # ============== Notes ==============

    def add_note(self, user_id: str, content: str, tags: List[str] = None) -> Note:
        """Add a new note."""
        notes = self._load_notes(user_id)

        note = Note(
            id=f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(notes)}",
            content=content,
            created_at=datetime.now().isoformat(),
            tags=tags or [],
            user_id=user_id
        )

        notes.append(note)
        self._save_notes(user_id, notes)

        logger.info(f"Added note for {user_id}: {content[:50]}...")
        return note

    def get_notes(self, user_id: str, tag: str = None, limit: int = 10) -> List[Note]:
        """Get user's notes, optionally filtered by tag."""
        notes = self._load_notes(user_id)

        if tag:
            notes = [n for n in notes if tag.lower() in [t.lower() for t in n.tags]]

        # Return newest first
        notes.sort(key=lambda n: n.created_at, reverse=True)
        return notes[:limit]

    def search_notes(self, user_id: str, query: str) -> List[Note]:
        """Search notes by content."""
        notes = self._load_notes(user_id)
        query_lower = query.lower()

        matches = [n for n in notes if query_lower in n.content.lower()]
        matches.sort(key=lambda n: n.created_at, reverse=True)
        return matches

    def delete_note(self, user_id: str, note_id: str) -> bool:
        """Delete a note."""
        notes = self._load_notes(user_id)
        original_len = len(notes)
        notes = [n for n in notes if n.id != note_id]

        if len(notes) < original_len:
            self._save_notes(user_id, notes)
            return True
        return False

    # ============== Tasks ==============

    def add_task(
        self,
        user_id: str,
        title: str,
        description: str = "",
        due_date: str = None,
        priority: str = "normal",
        tags: List[str] = None
    ) -> Task:
        """Add a new task."""
        tasks = self._load_tasks(user_id)

        task = Task(
            id=f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(tasks)}",
            title=title,
            description=description,
            created_at=datetime.now().isoformat(),
            due_date=due_date,
            priority=priority,
            status=TaskStatus.PENDING.value,
            tags=tags or [],
            user_id=user_id
        )

        tasks.append(task)
        self._save_tasks(user_id, tasks)

        logger.info(f"Added task for {user_id}: {title}")
        return task

    def get_tasks(
        self,
        user_id: str,
        status: str = None,
        priority: str = None,
        include_done: bool = False
    ) -> List[Task]:
        """Get user's tasks."""
        tasks = self._load_tasks(user_id)

        if status:
            tasks = [t for t in tasks if t.status == status]
        elif not include_done:
            tasks = [t for t in tasks if t.status != TaskStatus.DONE.value]

        if priority:
            tasks = [t for t in tasks if t.priority == priority]

        # Sort by priority and due date
        priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        tasks.sort(key=lambda t: (priority_order.get(t.priority, 2), t.due_date or "9999"))

        return tasks

    def complete_task(self, user_id: str, task_id: str = None, task_title: str = None) -> Optional[Task]:
        """Mark a task as done by ID or title match."""
        tasks = self._load_tasks(user_id)

        for task in tasks:
            if task_id and task.id == task_id:
                task.status = TaskStatus.DONE.value
                self._save_tasks(user_id, tasks)
                return task
            elif task_title and task_title.lower() in task.title.lower():
                task.status = TaskStatus.DONE.value
                self._save_tasks(user_id, tasks)
                return task

        return None

    def delete_task(self, user_id: str, task_id: str) -> bool:
        """Delete a task."""
        tasks = self._load_tasks(user_id)
        original_len = len(tasks)
        tasks = [t for t in tasks if t.id != task_id]

        if len(tasks) < original_len:
            self._save_tasks(user_id, tasks)
            return True
        return False

    # ============== Formatted Output ==============

    def format_notes(self, notes: List[Note]) -> str:
        """Format notes for voice output."""
        if not notes:
            return "У тебя пока нет заметок."

        lines = [f"У тебя {len(notes)} заметок:"]
        for i, note in enumerate(notes[:5], 1):
            content = note.content[:100] + "..." if len(note.content) > 100 else note.content
            lines.append(f"{i}. {content}")

        if len(notes) > 5:
            lines.append(f"...и ещё {len(notes) - 5}")

        return "\n".join(lines)

    def format_tasks(self, tasks: List[Task]) -> str:
        """Format tasks for voice output."""
        if not tasks:
            return "У тебя нет активных задач. Отличная работа!"

        # Group by priority
        urgent = [t for t in tasks if t.priority == "urgent"]
        high = [t for t in tasks if t.priority == "high"]
        normal = [t for t in tasks if t.priority == "normal"]
        low = [t for t in tasks if t.priority == "low"]

        lines = [f"У тебя {len(tasks)} задач:"]

        if urgent:
            lines.append(f"🔴 Срочные ({len(urgent)}):")
            for t in urgent[:3]:
                lines.append(f"  • {t.title}")

        if high:
            lines.append(f"🟠 Важные ({len(high)}):")
            for t in high[:3]:
                lines.append(f"  • {t.title}")

        if normal:
            lines.append(f"🟡 Обычные ({len(normal)}):")
            for t in normal[:3]:
                lines.append(f"  • {t.title}")

        if low:
            lines.append(f"🟢 Неспешные ({len(low)}):")
            for t in low[:2]:
                lines.append(f"  • {t.title}")

        return "\n".join(lines)


# Singleton
_notes_manager: Optional[NotesManager] = None


def get_notes_manager() -> NotesManager:
    global _notes_manager
    if _notes_manager is None:
        from config import get_settings
        settings = get_settings()
        _notes_manager = NotesManager(settings.data_dir)
    return _notes_manager
