from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # LLM Provider: "gemini" or "anthropic"
    llm_provider: str = "gemini"  # Start with free Gemini

    # Gemini API (free tier)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"  # Fast and free

    # Claude API (paid, for later)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-haiku-20240307"

    # Security
    api_secret_key: str = "eva-secret-key-change-me"
    vault_master_key: str = "vault-key-change-me"

    # Whisper STT
    whisper_model: str = "small"  # tiny, base, small, medium, large
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # TTS voices
    tts_voice_ru: str = "ru-RU-SvetlanaNeural"
    tts_voice_en: str = "en-US-AriaNeural"

    # Memory
    max_conversation_history: int = 20
    data_dir: str = "/app/data"

    # EVA personality
    eva_name: str = "EVA"
    owner_name: str = "Максим"  # Will be updated during onboarding

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
