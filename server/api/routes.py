"""API routes for EVA assistant."""

import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from typing import Optional

from config import get_settings
from schemas.models import (
    HealthResponse,
    VoiceProcessResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    Language,
    UserProfile
)
from core.stt import get_stt_service
from core.tts import get_tts_service
from core.llm import get_llm_service
from personality.memory import get_memory_manager
from personality.profile import get_profile_manager


router = APIRouter(prefix="/api/v1")


# ============== Health ==============

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check server health."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        eva_status="ready"
    )


# ============== Voice Processing ==============

@router.post("/voice/process", response_model=VoiceProcessResponse)
async def process_voice(
    audio: UploadFile = File(...),
    user_id: str = Form(default="default")
):
    """
    Process voice input and return voice response.

    1. STT: Convert audio to text
    2. LLM: Generate response
    3. TTS: Convert response to audio
    """
    try:
        # Read audio data
        audio_data = await audio.read()

        # 1. Speech to Text
        stt = get_stt_service()
        recognized_text, detected_lang = await stt.transcribe(audio_data, audio.filename)

        if not recognized_text.strip():
            raise HTTPException(status_code=400, detail="Could not recognize speech")

        # 2. Get user profile and history
        profile_manager = get_profile_manager()
        memory_manager = get_memory_manager()

        profile = profile_manager.get_profile(user_id)
        history = memory_manager.get_recent_messages(user_id)

        # 3. Generate LLM response
        llm = get_llm_service()
        response_text, emotion = await llm.chat(
            user_message=recognized_text,
            conversation_history=history,
            profile=profile
        )

        # 4. Save to memory
        memory_manager.add_message(user_id, "user", recognized_text, Language(detected_lang))
        memory_manager.add_message(user_id, "assistant", response_text)

        # 5. Text to Speech
        tts = get_tts_service()
        audio_path = await tts.synthesize_with_emotion(
            text=response_text,
            language=detected_lang,
            emotion=emotion.value
        )
        audio_url = tts.get_audio_url(audio_path)

        return VoiceProcessResponse(
            success=True,
            recognized_text=recognized_text,
            detected_language=Language(detected_lang),
            response_text=response_text,
            response_audio_url=audio_url,
            emotion=emotion
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Chat (Text) ==============

@router.post("/chat/message", response_model=ChatMessageResponse)
async def chat_message(request: ChatMessageRequest):
    """
    Process text message and return text + audio response.
    """
    try:
        # Get user profile and history
        profile_manager = get_profile_manager()
        memory_manager = get_memory_manager()

        profile = profile_manager.get_profile(request.user_id)
        history = memory_manager.get_recent_messages(request.user_id)

        # Generate LLM response
        llm = get_llm_service()
        response_text, emotion = await llm.chat(
            user_message=request.text,
            conversation_history=history,
            profile=profile
        )

        # Detect language from input or use specified
        lang = request.language.value
        if lang == "auto":
            # Simple heuristic: if mostly cyrillic, it's Russian
            cyrillic_count = sum(1 for c in request.text if '\u0400' <= c <= '\u04FF')
            lang = "ru" if cyrillic_count > len(request.text) * 0.3 else "en"

        # Save to memory
        memory_manager.add_message(request.user_id, "user", request.text, Language(lang))
        memory_manager.add_message(request.user_id, "assistant", response_text)

        # Generate audio
        tts = get_tts_service()
        audio_path = await tts.synthesize_with_emotion(
            text=response_text,
            language=lang,
            emotion=emotion.value
        )
        audio_url = tts.get_audio_url(audio_path)

        return ChatMessageResponse(
            success=True,
            response_text=response_text,
            response_audio_url=audio_url,
            emotion=emotion
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Audio Files ==============

@router.get("/audio/{filename}")
async def get_audio(filename: str):
    """Serve generated audio files."""
    settings = get_settings()
    audio_dir = os.path.join(settings.data_dir, "audio")
    file_path = os.path.join(audio_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(file_path, media_type="audio/mpeg")


# ============== User Profile ==============

@router.get("/user/profile")
async def get_user_profile(user_id: str = "default"):
    """Get user profile."""
    profile_manager = get_profile_manager()
    profile = profile_manager.get_profile(user_id)
    return profile


@router.post("/user/profile/name")
async def update_user_name(
    user_id: str = "default",
    name: str = Form(...),
    preferred_name: str = Form(default=None)
):
    """Update user's name."""
    profile_manager = get_profile_manager()
    profile_manager.update_name(user_id, name, preferred_name)
    return {"status": "ok", "name": name, "preferred_name": preferred_name}


# ============== Memory ==============

@router.get("/conversation/{user_id}/history")
async def get_conversation_history(user_id: str):
    """Get conversation history."""
    memory_manager = get_memory_manager()
    messages = memory_manager.get_recent_messages(user_id)

    return {
        "user_id": user_id,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ]
    }


@router.delete("/memory/{user_id}")
async def clear_memory(user_id: str):
    """Clear user's conversation memory."""
    memory_manager = get_memory_manager()
    memory_manager.clear_history(user_id)
    return {"status": "ok", "message": f"Memory cleared for {user_id}"}


@router.delete("/user/{user_id}")
async def delete_user(user_id: str):
    """Delete user profile and all data."""
    profile_manager = get_profile_manager()
    memory_manager = get_memory_manager()

    profile_manager.delete_profile(user_id)
    memory_manager.clear_history(user_id)

    return {"status": "ok", "message": f"User {user_id} deleted"}
