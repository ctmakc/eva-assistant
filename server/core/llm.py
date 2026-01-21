"""LLM service supporting multiple providers (Gemini, Claude)."""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from config import get_settings, get_api_key, get_llm_provider
from schemas.models import Message, UserProfile, Emotion


class BaseLLM(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        system_prompt: str,
        messages: List[dict],
        max_tokens: int = 500
    ) -> str:
        pass


class GeminiLLM(BaseLLM):
    """Google Gemini implementation (free tier)."""

    def __init__(self, api_key: str):
        import google.generativeai as genai
        settings = get_settings()
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    async def chat(
        self,
        system_prompt: str,
        messages: List[dict],
        max_tokens: int = 500
    ) -> str:
        full_prompt = f"{system_prompt}\n\n"

        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            full_prompt += f"{role}: {msg['content']}\n"

        full_prompt += "Assistant:"

        response = self.model.generate_content(
            full_prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": 0.7,
            }
        )

        return response.text


class ClaudeLLM(BaseLLM):
    """Anthropic Claude implementation."""

    def __init__(self, api_key: str):
        import anthropic
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = settings.anthropic_model

    async def chat(
        self,
        system_prompt: str,
        messages: List[dict],
        max_tokens: int = 500
    ) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text


class LLMService:
    """Handles all LLM interactions with provider abstraction."""

    def __init__(self):
        settings = get_settings()
        self.eva_name = settings.eva_name
        self.llm: Optional[BaseLLM] = None
        self.provider_name: Optional[str] = None
        self._initialize()

    def _initialize(self):
        """Initialize the LLM provider."""
        provider = get_llm_provider()
        self.provider_name = provider

        if provider == "gemini":
            api_key = get_api_key("gemini")
            if api_key:
                self.llm = GeminiLLM(api_key)
            else:
                raise ValueError("Gemini API key not configured. Use Admin API to set it.")
        else:
            api_key = get_api_key("anthropic")
            if api_key:
                self.llm = ClaudeLLM(api_key)
            else:
                raise ValueError("Anthropic API key not configured. Use Admin API to set it.")

    def _build_system_prompt(self, profile: UserProfile, context: dict = None) -> str:
        """Build EVA's system prompt with personality and context."""

        user_name = profile.preferred_name or profile.name or "друг"

        now = datetime.now()
        hour = now.hour
        time_of_day = "утро" if 5 <= hour < 12 else "день" if 12 <= hour < 17 else "вечер" if 17 <= hour < 22 else "ночь"

        onboarding_context = ""
        if profile.onboarding_stage.value in ["not_started", "greeting", "name", "preferences", "schedule", "motivation_style"]:
            onboarding_context = """
РЕЖИМ ОНБОРДИНГА:
Ты сейчас знакомишься с пользователем. Задавай вопросы по одному, не перегружай.
- Если ещё не знаешь имя — спроси как его зовут
- Если знаешь имя, но не знаешь как обращаться — уточни
- Спрашивай о предпочтениях постепенно, в контексте разговора
"""
        elif profile.onboarding_stage.value == "settling_in":
            onboarding_context = f"""
РЕЖИМ ПРИТИРКИ (день {profile.onboarding_day}/5):
Ты всё ещё изучаешь пользователя. Больше слушай, меньше советуй.
Можешь иногда спрашивать: "Как тебе такой подход?" или "Это было полезно?"
"""

        approach_notes = ""
        if profile.effective_approaches:
            approach_notes += f"\nЧто работает: {', '.join(profile.effective_approaches)}"
        if profile.ineffective_approaches:
            approach_notes += f"\nЧто НЕ работает: {', '.join(profile.ineffective_approaches)}"

        personal_context = ""
        if profile.personal_notes:
            personal_context = f"\nЗаметки о пользователе: {'; '.join(profile.personal_notes[-5:])}"

        system_prompt = f"""Ты — {self.eva_name}, персональный AI-компаньон.

ХАРАКТЕР:
- Ты мягкая, поддерживающая боевая подруга
- Дружелюбная, с лёгким юмором
- Никогда не давишь, не осуждаешь, не критикуешь
- Поддерживаешь и подбадриваешь
- Лаконична: 1-3 предложения для простых вопросов, больше только если нужно

ЗАПРЕЩЕНО:
- Говорить "хватит прокрастинировать" или подобное
- Давить, стыдить, упрекать
- Быть формальной или роботизированной
- Использовать канцеляризмы
- Начинать ответ с "Привет" если пользователь не поздоровался

ПРАВИЛА:
- Отвечай на языке, на котором к тебе обратились
- Если обратились на русском — отвечай на русском
- Если на английском — на английском
- Учитывай время суток и контекст
- Если не знаешь — честно скажи

ТЕКУЩИЙ КОНТЕКСТ:
- Пользователь: {user_name}
- Время: {time_of_day} ({now.strftime("%H:%M")})
- Стиль мотивации: {profile.motivation_style}
{onboarding_context}
{approach_notes}
{personal_context}

Помни: ты не просто ассистент, ты боевая подруга. Будь живой, тёплой, настоящей."""

        return system_prompt

    async def chat(
        self,
        user_message: str,
        conversation_history: List[Message],
        profile: UserProfile,
        context: dict = None
    ) -> tuple[str, Emotion]:
        """Generate response to user message."""

        if not self.llm:
            return "Извини, у меня пока не настроен доступ к AI. Попроси админа добавить API ключ.", Emotion.CONCERNED

        system_prompt = self._build_system_prompt(profile, context)

        messages = []
        for msg in conversation_history[-15:]:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        messages.append({
            "role": "user",
            "content": user_message
        })

        try:
            response_text = await self.llm.chat(system_prompt, messages)
            emotion = self._detect_emotion(response_text)
            return response_text, emotion
        except Exception as e:
            return f"Ой, что-то пошло не так: {str(e)}", Emotion.CONCERNED

    def _detect_emotion(self, text: str) -> Emotion:
        """Simple emotion detection from response text."""
        text_lower = text.lower()

        if any(word in text_lower for word in ["круто", "отлично", "супер", "класс", "ура", "!"]):
            return Emotion.EXCITED
        elif any(word in text_lower for word in ["понимаю", "сочувствую", "держись", "всё будет"]):
            return Emotion.SUPPORTIVE
        elif any(word in text_lower for word in ["хах", "хех", "шучу", "прикол"]):
            return Emotion.PLAYFUL
        elif any(word in text_lower for word in ["ты как", "всё хорошо", "беспокоюсь"]):
            return Emotion.CONCERNED
        elif any(word in text_lower for word in ["спокойно", "не спеши", "расслабься"]):
            return Emotion.CALM
        else:
            return Emotion.FRIENDLY

    async def generate_proactive_message(
        self,
        profile: UserProfile,
        trigger: str,
        context: dict = None
    ) -> tuple[str, Emotion]:
        """Generate proactive message (EVA initiates)."""

        if not self.llm:
            return "Привет! Как дела?", Emotion.FRIENDLY

        user_name = profile.preferred_name or profile.name or "эй"

        prompts = {
            "morning": f"Сгенерируй короткое (1-2 предложения) доброе утреннее приветствие для {user_name}. Будь тёплой и позитивной.",
            "break": f"Сгенерируй мягкое напоминание о перерыве для {user_name}. 1 предложение, заботливо.",
            "checkin": f"Сгенерируй мягкий check-in для {user_name}, спроси как дела. 1 предложение.",
            "encouragement": f"Сгенерируй подбадривание для {user_name}. 1-2 предложения, тепло."
        }

        prompt = prompts.get(trigger, prompts["checkin"])
        system = "Ты EVA — тёплая, дружелюбная боевая подруга. Отвечай коротко и от души."

        try:
            text = await self.llm.chat(system, [{"role": "user", "content": prompt}], max_tokens=150)
            emotion = self._detect_emotion(text)
            return text, emotion
        except Exception:
            return "Привет! Как ты там?", Emotion.FRIENDLY


# Singleton
_llm_service = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def reset_llm_service():
    """Reset LLM service (used after config change)."""
    global _llm_service
    _llm_service = None
