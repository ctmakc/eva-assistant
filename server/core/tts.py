"""Text-to-Speech service using Edge TTS."""

import os
import uuid
import edge_tts
from typing import Optional

from config import get_settings


class TTSService:
    """Converts text to speech using Microsoft Edge TTS."""

    def __init__(self):
        settings = get_settings()
        self.voice_ru = settings.tts_voice_ru
        self.voice_en = settings.tts_voice_en
        self.audio_dir = os.path.join(settings.data_dir, "audio")
        os.makedirs(self.audio_dir, exist_ok=True)

    def _get_voice(self, language: str) -> str:
        """Get appropriate voice for language."""
        if language in ["ru", "russian"]:
            return self.voice_ru
        return self.voice_en

    async def synthesize(
        self,
        text: str,
        language: str = "ru",
        filename: Optional[str] = None
    ) -> str:
        """
        Synthesize speech from text.

        Args:
            text: Text to convert to speech
            language: Language code ('ru' or 'en')
            filename: Optional custom filename

        Returns:
            Path to generated audio file
        """
        if not filename:
            filename = f"{uuid.uuid4()}.mp3"

        output_path = os.path.join(self.audio_dir, filename)
        voice = self._get_voice(language)

        # Generate speech
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

        return output_path

    async def synthesize_with_emotion(
        self,
        text: str,
        language: str = "ru",
        emotion: str = "friendly"
    ) -> str:
        """
        Synthesize speech with emotional styling.

        Edge TTS supports SSML for some emotion control.
        """
        voice = self._get_voice(language)

        # Adjust rate and pitch based on emotion
        rate = "+0%"
        pitch = "+0Hz"

        if emotion == "excited":
            rate = "+10%"
            pitch = "+5Hz"
        elif emotion == "calm":
            rate = "-5%"
            pitch = "-2Hz"
        elif emotion == "supportive":
            rate = "-3%"
            pitch = "+2Hz"
        elif emotion == "playful":
            rate = "+5%"
            pitch = "+3Hz"

        filename = f"{uuid.uuid4()}.mp3"
        output_path = os.path.join(self.audio_dir, filename)

        communicate = edge_tts.Communicate(
            text,
            voice,
            rate=rate,
            pitch=pitch
        )
        await communicate.save(output_path)

        return output_path

    def get_audio_url(self, file_path: str) -> str:
        """Convert file path to API URL."""
        filename = os.path.basename(file_path)
        return f"/api/v1/audio/{filename}"

    def cleanup_old_files(self, max_age_hours: int = 24):
        """Remove audio files older than max_age_hours."""
        import time
        now = time.time()
        max_age_seconds = max_age_hours * 3600

        for filename in os.listdir(self.audio_dir):
            file_path = os.path.join(self.audio_dir, filename)
            if os.path.isfile(file_path):
                file_age = now - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    os.unlink(file_path)


# Singleton instance
_tts_service = None


def get_tts_service() -> TTSService:
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
