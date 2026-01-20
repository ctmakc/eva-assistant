from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class Language(str, Enum):
    RU = "ru"
    EN = "en"
    AUTO = "auto"


class Emotion(str, Enum):
    FRIENDLY = "friendly"
    SUPPORTIVE = "supportive"
    PLAYFUL = "playful"
    CONCERNED = "concerned"
    EXCITED = "excited"
    CALM = "calm"


class OnboardingStage(str, Enum):
    NOT_STARTED = "not_started"
    GREETING = "greeting"
    NAME = "name"
    PREFERENCES = "preferences"
    SCHEDULE = "schedule"
    MOTIVATION_STYLE = "motivation_style"
    COMPLETED = "completed"
    SETTLING_IN = "settling_in"  # First 5 days
    FULL = "full"  # After settling


# Request models
class ChatMessageRequest(BaseModel):
    text: str
    user_id: str = "default"
    language: Language = Language.AUTO


class CredentialRequest(BaseModel):
    service: str
    credentials: dict


# Response models
class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    eva_status: str = "ready"


class VoiceProcessResponse(BaseModel):
    success: bool
    recognized_text: str
    detected_language: Language
    response_text: str
    response_audio_url: str
    emotion: Emotion = Emotion.FRIENDLY


class ChatMessageResponse(BaseModel):
    success: bool
    response_text: str
    response_audio_url: Optional[str] = None
    emotion: Emotion = Emotion.FRIENDLY


# Memory models
class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = None
    language: Language = Language.AUTO

    def __init__(self, **data):
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.now()
        super().__init__(**data)


class UserProfile(BaseModel):
    user_id: str = "default"
    name: str = ""
    preferred_name: str = ""  # How EVA should call them
    created_at: datetime = None

    # Onboarding
    onboarding_stage: OnboardingStage = OnboardingStage.NOT_STARTED
    onboarding_day: int = 0  # Days since onboarding started

    # Preferences
    preferred_language: Language = Language.RU
    wake_time: str = "09:00"
    peak_productivity_time: str = "10:00-14:00"
    motivation_style: str = "soft"  # soft, moderate, strict

    # Learned patterns
    energy_patterns: dict = {}  # time_of_day -> energy_level
    effective_approaches: List[str] = []  # What motivation works
    ineffective_approaches: List[str] = []  # What doesn't work

    # Notes
    personal_notes: List[str] = []  # Things EVA learned about user

    def __init__(self, **data):
        if data.get('created_at') is None:
            data['created_at'] = datetime.now()
        super().__init__(**data)


class ConversationHistory(BaseModel):
    user_id: str
    messages: List[Message] = []
    last_updated: datetime = None

    def __init__(self, **data):
        if data.get('last_updated') is None:
            data['last_updated'] = datetime.now()
        super().__init__(**data)

    def add_message(self, role: str, content: str, language: Language = Language.AUTO):
        self.messages.append(Message(role=role, content=content, language=language))
        self.last_updated = datetime.now()

    def get_recent(self, n: int = 20) -> List[Message]:
        return self.messages[-n:]
