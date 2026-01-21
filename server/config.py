from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os


class Settings(BaseSettings):
    # API
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # LLM Provider: "gemini" or "anthropic"
    llm_provider: str = "gemini"

    # Gemini API (free tier)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Claude API (paid)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-haiku-20240307"

    # Security
    api_secret_key: str = "eva-secret-key-change-me"
    vault_master_key: str = "vault-key-change-me"
    admin_password: str = ""  # For initial setup only

    # Integrations
    telegram_bot_token: str = ""

    # Whisper STT
    whisper_model: str = "small"
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
    owner_name: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def get_api_key(service: str) -> Optional[str]:
    """
    Get API key - first from env, then from vault.
    This allows runtime configuration without restart.
    """
    settings = get_settings()

    # Check env first
    if service == "gemini" and settings.gemini_api_key:
        return settings.gemini_api_key
    if service == "anthropic" and settings.anthropic_api_key:
        return settings.anthropic_api_key
    if service == "telegram" and settings.telegram_bot_token:
        return settings.telegram_bot_token

    # Check vault
    try:
        from integrations.vault import get_vault
        vault = get_vault()
        creds = vault.get(service)
        if creds:
            return creds.get("api_key") or creds.get("token")
    except:
        pass

    return None


def get_llm_provider() -> str:
    """Get LLM provider - from vault settings or env."""
    settings = get_settings()

    # Check vault for override
    try:
        from integrations.vault import get_vault
        vault = get_vault()
        vault_settings = vault.get("settings")
        if vault_settings and "llm_provider" in vault_settings:
            return vault_settings["llm_provider"]
    except:
        pass

    return settings.llm_provider
