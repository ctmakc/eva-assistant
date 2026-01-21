"""Admin API routes for EVA configuration."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Form
from pydantic import BaseModel
from typing import Optional

from auth import get_auth_manager, require_auth
from integrations.vault import get_vault
from config import get_settings

logger = logging.getLogger("eva.admin")

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ============== Models ==============

class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str


class SettingUpdate(BaseModel):
    key: str
    value: str


# ============== Public Routes ==============

@router.get("/status")
async def admin_status():
    """Check if admin is set up."""
    auth = get_auth_manager()
    return {
        "initialized": auth.is_initialized,
        "message": "Use POST /api/v1/admin/setup to initialize" if not auth.is_initialized else "Admin ready"
    }


@router.post("/setup")
async def setup_admin(password: str = Form(...)):
    """
    Initial admin setup. Sets the admin password.
    Only works once - subsequent calls will fail.
    """
    auth = get_auth_manager()

    if auth.is_initialized:
        raise HTTPException(
            status_code=400,
            detail="Admin already initialized. Use /login to authenticate."
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    auth.setup_admin(password)
    token = auth.create_access_token()

    return {
        "success": True,
        "message": "Admin initialized successfully",
        "token": token
    }


@router.post("/login", response_model=LoginResponse)
async def login(password: str = Form(...)):
    """
    Login to get access token.
    """
    auth = get_auth_manager()

    if not auth.verify_password(password):
        raise HTTPException(
            status_code=401,
            detail="Invalid password"
        )

    token = auth.create_access_token()

    return LoginResponse(
        success=True,
        token=token,
        message="Login successful"
    )


# ============== Protected Routes ==============

@router.post("/change-password")
async def change_password(
    old_password: str = Form(...),
    new_password: str = Form(...),
    _: bool = Depends(require_auth)
):
    """Change admin password."""
    if len(new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    auth = get_auth_manager()
    if not auth.change_password(old_password, new_password):
        raise HTTPException(
            status_code=400,
            detail="Invalid old password"
        )

    return {"success": True, "message": "Password changed"}


@router.get("/settings")
async def get_settings_list(_: bool = Depends(require_auth)):
    """Get current settings (without exposing secrets)."""
    settings = get_settings()
    vault = get_vault()

    return {
        "llm_provider": settings.llm_provider,
        "gemini_configured": bool(settings.gemini_api_key) or vault.has("gemini"),
        "anthropic_configured": bool(settings.anthropic_api_key) or vault.has("anthropic"),
        "telegram_configured": bool(settings.telegram_bot_token) or vault.has("telegram"),
        "whisper_model": settings.whisper_model,
        "tts_voice_ru": settings.tts_voice_ru,
        "tts_voice_en": settings.tts_voice_en,
    }


@router.post("/settings")
async def update_setting(
    key: str = Form(...),
    value: str = Form(...),
    _: bool = Depends(require_auth)
):
    """
    Update a setting. API keys are stored in the encrypted vault.

    Supported keys:
    - gemini_api_key
    - anthropic_api_key
    - telegram_bot_token
    - llm_provider (gemini/anthropic)
    """
    vault = get_vault()

    # API keys go to vault
    if key in ["gemini_api_key", "anthropic_api_key", "telegram_bot_token"]:
        service = key.replace("_api_key", "").replace("_bot_token", "")
        vault.store(service, {"api_key": value})

        # For telegram, we need to restart the bot
        if key == "telegram_bot_token":
            return {
                "success": True,
                "message": f"Telegram token stored. Restart required to apply.",
                "restart_required": True
            }

        return {
            "success": True,
            "message": f"{key} stored securely",
            "restart_required": False
        }

    # LLM provider can be changed
    if key == "llm_provider":
        if value not in ["gemini", "anthropic"]:
            raise HTTPException(status_code=400, detail="Invalid provider. Use 'gemini' or 'anthropic'")

        vault.store("settings", {"llm_provider": value})
        return {
            "success": True,
            "message": f"LLM provider set to {value}. Restart required.",
            "restart_required": True
        }

    raise HTTPException(status_code=400, detail=f"Unknown setting: {key}")


@router.delete("/settings/{key}")
async def delete_setting(key: str, _: bool = Depends(require_auth)):
    """Delete a stored setting/credential."""
    vault = get_vault()
    service = key.replace("_api_key", "").replace("_bot_token", "")

    if vault.delete(service):
        return {"success": True, "message": f"{key} deleted"}

    raise HTTPException(status_code=404, detail=f"Setting not found: {key}")


@router.get("/logs")
async def get_recent_logs(
    lines: int = 100,
    level: str = None,
    _: bool = Depends(require_auth)
):
    """
    Get recent application logs.

    - lines: Number of lines to return (default 100, max 500)
    - level: Filter by log level (INFO, WARNING, ERROR)
    """
    import os
    from collections import deque

    settings = get_settings()
    log_file = settings.log_file
    max_lines = min(lines, settings.max_log_lines)

    if not os.path.exists(log_file):
        return {"logs": [], "total": 0, "message": "No log file yet"}

    try:
        logs = deque(maxlen=max_lines)

        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # Filter by level if specified
                if level:
                    if f" - {level.upper()} - " not in line:
                        continue

                logs.append(line)

        log_list = list(logs)

        return {
            "logs": log_list,
            "total": len(log_list),
            "log_file": log_file
        }

    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        return {"logs": [], "total": 0, "error": str(e)}


@router.post("/restart")
async def request_restart(_: bool = Depends(require_auth)):
    """
    Request application restart.
    In Docker, this will signal for container restart.
    """
    # In practice, this could write to a file that a healthcheck monitors
    # or use Docker API. For now, just acknowledge.
    return {
        "success": True,
        "message": "Restart requested. In Docker, restart the container manually or redeploy the stack."
    }
