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
async def health_check(detailed: bool = False):
    """
    Check server health.

    Set detailed=true for more info (LLM status, integrations).
    """
    response = HealthResponse(
        status="ok",
        version="1.0.0",
        eva_status="ready"
    )

    if detailed:
        # Check LLM
        try:
            llm = get_llm_service()
            llm_ok = llm.llm is not None
        except Exception:
            llm_ok = False

        # Check integrations
        try:
            from integrations.telegram import get_telegram_integration
            telegram = get_telegram_integration()
            telegram_ok = telegram._running
        except Exception:
            telegram_ok = False

        from integrations.gmail import get_gmail_integration
        gmail = get_gmail_integration()
        gmail_ok = gmail.is_authenticated

        # Return extended info
        return {
            "status": "ok",
            "version": "1.0.0",
            "eva_status": "ready",
            "services": {
                "llm": "ok" if llm_ok else "not_configured",
                "stt": "ok",  # Always loaded at startup
                "tts": "ok",
                "telegram": "running" if telegram_ok else "stopped",
                "gmail": "connected" if gmail_ok else "not_connected"
            }
        }

    return response


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
        # Check for quick commands first
        from core.commands import get_command_parser, execute_command
        from schemas.models import Emotion

        parser = get_command_parser()
        cmd_result = parser.parse(request.text, request.user_id)

        if cmd_result.is_command and not cmd_result.execute:
            # Execute command and return response without LLM
            success, response_msg = execute_command(cmd_result)

            # Use command response or execution result
            final_response = response_msg or cmd_result.response or "Готово!"

            # Generate audio for command response
            tts = get_tts_service()
            lang = request.language.value
            if lang == "auto":
                cyrillic_count = sum(1 for c in final_response if '\u0400' <= c <= '\u04FF')
                lang = "ru" if cyrillic_count > len(final_response) * 0.3 else "en"

            audio_path = await tts.synthesize_with_emotion(
                text=final_response,
                language=lang,
                emotion="friendly"
            )
            audio_url = tts.get_audio_url(audio_path)

            # Save to memory
            memory_manager = get_memory_manager()
            memory_manager.add_message(request.user_id, "user", request.text, Language(lang))
            memory_manager.add_message(request.user_id, "assistant", final_response)

            return ChatMessageResponse(
                success=True,
                response_text=final_response,
                response_audio_url=audio_url,
                emotion=Emotion.FRIENDLY
            )

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


@router.get("/conversation/{user_id}/export")
async def export_conversation(user_id: str, format: str = "json"):
    """
    Export conversation history.

    Formats:
    - json: Full JSON export with timestamps
    - text: Human-readable text format
    - markdown: Markdown formatted
    """
    from fastapi.responses import PlainTextResponse

    memory_manager = get_memory_manager()
    messages = memory_manager.get_recent_messages(user_id, limit=1000)

    if not messages:
        raise HTTPException(status_code=404, detail="No conversation found")

    if format == "json":
        return {
            "user_id": user_id,
            "exported_at": datetime.now().isoformat() if 'datetime' in dir() else __import__('datetime').datetime.now().isoformat(),
            "message_count": len(messages),
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "language": msg.language.value if msg.language else None
                }
                for msg in messages
            ]
        }

    elif format == "text":
        from datetime import datetime as dt
        lines = [f"EVA Conversation Export - {user_id}", f"Exported: {dt.now().strftime('%Y-%m-%d %H:%M')}", "=" * 50, ""]

        for msg in messages:
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M")
            speaker = "You" if msg.role == "user" else "EVA"
            lines.append(f"[{timestamp}] {speaker}:")
            lines.append(msg.content)
            lines.append("")

        return PlainTextResponse("\n".join(lines), media_type="text/plain")

    elif format == "markdown":
        from datetime import datetime as dt
        lines = [f"# EVA Conversation", f"**User:** {user_id}", f"**Exported:** {dt.now().strftime('%Y-%m-%d %H:%M')}", "", "---", ""]

        for msg in messages:
            timestamp = msg.timestamp.strftime("%H:%M")
            if msg.role == "user":
                lines.append(f"**You** _{timestamp}_")
            else:
                lines.append(f"**EVA** _{timestamp}_")
            lines.append(f"> {msg.content}")
            lines.append("")

        return PlainTextResponse("\n".join(lines), media_type="text/markdown")

    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use: json, text, markdown")


# ============== Integrations ==============

@router.get("/integrations/status")
async def integrations_status():
    """Get status of all integrations."""
    settings = get_settings()

    status = {
        "telegram": {
            "configured": bool(settings.telegram_bot_token),
            "status": "unknown"
        },
        "gmail": {
            "configured": False,
            "status": "not_implemented"
        }
    }

    # Check Telegram status
    if settings.telegram_bot_token:
        try:
            from integrations.telegram import get_telegram_integration
            telegram = get_telegram_integration()
            status["telegram"]["status"] = "running" if telegram._running else "stopped"
            status["telegram"]["owner_set"] = telegram.owner_chat_id is not None
        except Exception:
            status["telegram"]["status"] = "error"

    return status


@router.post("/integrations/credentials")
async def store_credentials(
    service: str = Form(...),
    username: str = Form(default=None),
    password: str = Form(default=None),
    token: str = Form(default=None),
    api_key: str = Form(default=None)
):
    """
    Store credentials for a service.

    EVA can ask for credentials dynamically:
    "У меня нет доступа к Reddit" ->
    User: "Вот логин-пароль: user / pass123" ->
    EVA stores and uses them.
    """
    from integrations.vault import get_vault

    vault = get_vault()

    credentials = {}
    if username:
        credentials["username"] = username
    if password:
        credentials["password"] = password
    if token:
        credentials["token"] = token
    if api_key:
        credentials["api_key"] = api_key

    if not credentials:
        raise HTTPException(status_code=400, detail="No credentials provided")

    vault.store(service, credentials)

    return {
        "status": "ok",
        "service": service,
        "message": f"Credentials stored for {service}"
    }


@router.get("/integrations/credentials")
async def list_credentials():
    """List services with stored credentials (no secrets returned)."""
    from integrations.vault import get_vault

    vault = get_vault()
    services = vault.list_services()

    return {
        "services": [
            {
                "name": service,
                "has_credentials": True
            }
            for service in services
        ]
    }


@router.delete("/integrations/credentials/{service}")
async def delete_credentials(service: str):
    """Delete stored credentials for a service."""
    from integrations.vault import get_vault

    vault = get_vault()
    if vault.delete(service):
        return {"status": "ok", "message": f"Credentials deleted for {service}"}
    raise HTTPException(status_code=404, detail=f"No credentials found for {service}")


# ============== Scheduler ==============

@router.post("/scheduler/reminder")
async def add_reminder(
    user_id: str = Form(default="default"),
    message: str = Form(...),
    minutes: int = Form(...)
):
    """Add a reminder that fires in N minutes."""
    from datetime import datetime, timedelta
    from proactive.scheduler import get_scheduler

    scheduler = get_scheduler()
    run_at = datetime.now() + timedelta(minutes=minutes)

    reminder_id = scheduler.add_reminder(user_id, message, run_at)

    return {
        "status": "ok",
        "reminder_id": reminder_id,
        "will_fire_at": run_at.isoformat()
    }


@router.post("/scheduler/setup/{user_id}")
async def setup_user_schedule(user_id: str):
    """Setup default schedule for a user."""
    from proactive.scheduler import get_scheduler

    scheduler = get_scheduler()
    scheduler.setup_user_schedule(user_id)

    return {"status": "ok", "message": f"Schedule set up for {user_id}"}


# ============== Smart Integrations ==============

@router.get("/integrations/discover")
async def discover_devices():
    """
    Scan local network for smart devices.

    Returns list of discovered devices with integration suggestions.
    """
    from integrations.base import discover_network_devices, suggest_integrations

    try:
        devices = await discover_network_devices(timeout=5)
        suggestions = await suggest_integrations(devices)

        return {
            "success": True,
            "devices_found": len(devices),
            "devices": [
                {
                    "ip": d.ip,
                    "hostname": d.hostname,
                    "type": d.device_type,
                    "open_ports": d.open_ports,
                    "hint": d.integration_hint
                }
                for d in devices
            ],
            "suggested_integrations": suggestions
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "devices": [],
            "suggested_integrations": []
        }


@router.get("/integrations/available")
async def list_available_integrations():
    """List all available integration types."""
    from integrations.base import get_integration_registry, IntegrationType

    registry = get_integration_registry()

    return {
        "registered": registry.list_available(),
        "connected": registry.list_connected(),
        "types": [t.value for t in IntegrationType]
    }


@router.post("/integrations/connect/{integration_name}")
async def connect_integration(
    integration_name: str,
    credentials: dict
):
    """
    Connect to an integration.

    Credentials depend on integration type:
    - home_assistant: {"api_token": "xxx", "url": "http://..."}
    - mqtt: {"host": "...", "username": "...", "password": "..."}
    - etc.
    """
    from integrations.base import get_integration_registry
    from integrations.vault import get_vault

    registry = get_integration_registry()

    # Try to create/get integration
    integration = registry.get(integration_name)
    if not integration:
        integration = registry.create_integration(integration_name)

    if not integration:
        raise HTTPException(
            status_code=404,
            detail=f"Integration '{integration_name}' not found. Available: {registry.list_available()}"
        )

    # Try to connect
    try:
        success = await integration.connect(credentials)

        if success:
            # Store credentials in vault
            vault = get_vault()
            vault.store(f"integration_{integration_name}", credentials)

            return {
                "success": True,
                "message": f"Connected to {integration_name}",
                "capabilities": [
                    {"name": c.name, "description": c.description}
                    for c in integration.get_capabilities()
                ]
            }
        else:
            return {
                "success": False,
                "message": "Connection failed"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integrations/{integration_name}/execute")
async def execute_integration_action(
    integration_name: str,
    action: str,
    params: dict = None
):
    """
    Execute an action on an integration.

    Example:
    - POST /integrations/home_assistant/execute
      {"action": "turn_on", "params": {"entity_id": "light.living_room"}}
    """
    from integrations.base import get_integration_registry

    registry = get_integration_registry()
    integration = registry.get(integration_name)

    if not integration:
        raise HTTPException(status_code=404, detail=f"Integration not found: {integration_name}")

    if not integration.is_connected:
        raise HTTPException(status_code=400, detail=f"Integration not connected: {integration_name}")

    try:
        result = await integration.execute(action, params or {})
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
