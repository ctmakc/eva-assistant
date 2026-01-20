"""Speech-to-Text service using Faster Whisper."""

import os
import tempfile
from typing import Tuple
from faster_whisper import WhisperModel

from config import get_settings


class STTService:
    """Converts speech audio to text using Whisper."""

    def __init__(self):
        settings = get_settings()
        self.model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type
        )

    async def transcribe(self, audio_data: bytes, filename: str = "audio.wav") -> Tuple[str, str]:
        """
        Transcribe audio to text.

        Args:
            audio_data: Raw audio bytes
            filename: Original filename (for format detection)

        Returns:
            Tuple of (transcribed_text, detected_language)
        """
        # Save to temp file (Whisper needs file path)
        suffix = os.path.splitext(filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            # Transcribe with auto language detection
            segments, info = self.model.transcribe(
                tmp_path,
                beam_size=5,
                language=None,  # Auto-detect
                vad_filter=True,  # Voice activity detection
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200
                )
            )

            # Collect all segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            transcribed_text = " ".join(text_parts)
            detected_language = info.language

            # Map to our language enum
            lang = "ru" if detected_language in ["ru", "russian"] else "en"

            return transcribed_text, lang

        finally:
            # Cleanup temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    async def transcribe_file(self, file_path: str) -> Tuple[str, str]:
        """Transcribe audio from file path."""
        with open(file_path, "rb") as f:
            audio_data = f.read()
        return await self.transcribe(audio_data, os.path.basename(file_path))


# Singleton instance
_stt_service = None


def get_stt_service() -> STTService:
    global _stt_service
    if _stt_service is None:
        _stt_service = STTService()
    return _stt_service
