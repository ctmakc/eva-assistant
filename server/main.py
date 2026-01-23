"""EVA Personal Assistant - Main FastAPI Application."""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import logging.handlers
import os

from config import get_settings, get_api_key, get_llm_provider
from api.routes import router
from api.admin import router as admin_router
from api.gmail_routes import router as gmail_router
from api.calendar_routes import router as calendar_router
from api.notification_routes import router as notification_router
from api.dashboard import router as dashboard_router

# Setup logging
from config import get_settings
_settings = get_settings()

# Ensure log directory exists
os.makedirs(os.path.dirname(_settings.log_file), exist_ok=True)

# Create log handlers
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.handlers.RotatingFileHandler(
            _settings.log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger("eva")


# Global references for cleanup
_telegram_task = None


async def setup_telegram():
    """Setup Telegram bot if token is configured."""
    settings = get_settings()

    if not settings.telegram_bot_token:
        logger.info("Telegram bot token not configured, skipping")
        return

    try:
        from integrations.telegram import get_telegram_integration
        from core.llm import get_llm_service
        from personality.profile import get_profile_manager
        from personality.memory import get_memory_manager

        telegram = get_telegram_integration()
        await telegram.initialize(settings.telegram_bot_token)

        # Add message handler to process through EVA
        async def handle_telegram_message(text: str, chat_id: str) -> str:
            llm = get_llm_service()
            profile = get_profile_manager().get_profile(chat_id)
            history = get_memory_manager().get_recent_messages(chat_id)

            response, _ = await llm.chat(text, history, profile)

            # Save to memory
            get_memory_manager().add_message(chat_id, "user", text)
            get_memory_manager().add_message(chat_id, "assistant", response)

            return response

        telegram.add_message_handler(handle_telegram_message)
        await telegram.start()

        logger.info("✓ Telegram bot started")
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")


async def setup_scheduler():
    """Setup proactive scheduler."""
    try:
        from proactive.scheduler import get_scheduler
        from integrations.telegram import get_telegram_integration

        scheduler = get_scheduler()

        # Add notification handler (send via Telegram if available)
        async def notify_handler(user_id: str, message: str, trigger: str):
            logger.info(f"Proactive notification [{trigger}] for {user_id}: {message}")

            # Try to send via Telegram
            try:
                telegram = get_telegram_integration()
                if telegram.owner_chat_id:
                    await telegram.send_to_owner(message)
            except Exception:
                pass  # Telegram might not be configured

        scheduler.add_notification_handler(notify_handler)
        scheduler.start()

        # Setup default schedule for default user
        scheduler.setup_user_schedule("default")

        logger.info("✓ Proactive scheduler started")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


async def setup_integrations():
    """Load saved integrations from vault."""
    try:
        from integrations.base import get_integration_registry
        from integrations.vault import get_vault

        registry = get_integration_registry()
        vault = get_vault()

        # Try to load Home Assistant
        ha_creds = vault.get("integration_home_assistant")
        if ha_creds:
            logger.info("Loading Home Assistant integration...")
            ha = registry.create_integration("home_assistant")
            if ha:
                success = await ha.connect(ha_creds)
                if success:
                    logger.info("✓ Home Assistant connected")
                else:
                    logger.warning("⚠ Home Assistant connection failed")

        # Try to load MQTT
        mqtt_creds = vault.get("integration_mqtt")
        if mqtt_creds:
            logger.info("Loading MQTT integration...")
            mqtt = registry.create_integration("mqtt")
            if mqtt:
                success = await mqtt.connect(mqtt_creds)
                if success:
                    logger.info("✓ MQTT connected")
                else:
                    logger.warning("⚠ MQTT connection failed")

        connected = registry.list_connected()
        if connected:
            logger.info(f"✓ Integrations loaded: {', '.join(connected)}")
        else:
            logger.info("No saved integrations found")

    except Exception as e:
        logger.error(f"Failed to load integrations: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events."""
    # Startup
    logger.info("🚀 EVA is starting up...")

    settings = get_settings()

    # Pre-load core services
    try:
        from core.stt import get_stt_service
        from core.tts import get_tts_service
        from core.llm import get_llm_service

        logger.info("Loading STT model (Whisper)...")
        get_stt_service()
        logger.info("✓ STT ready")

        logger.info("Initializing TTS...")
        get_tts_service()
        logger.info("✓ TTS ready")

        logger.info(f"Initializing LLM ({settings.llm_provider})...")
        try:
            get_llm_service()
            logger.info("✓ LLM ready")
        except ValueError as e:
            logger.warning(f"⚠ LLM not configured: {e}")
            logger.warning("  Use Admin API to configure API keys")

    except Exception as e:
        logger.error(f"Error during core initialization: {e}")
        raise

    # Setup integrations
    await setup_telegram()
    await setup_scheduler()
    await setup_integrations()

    logger.info("✨ EVA is ready!")

    yield

    # Shutdown
    logger.info("👋 EVA is shutting down...")

    # Stop Telegram
    try:
        from integrations.telegram import get_telegram_integration
        telegram = get_telegram_integration()
        await telegram.stop()
    except Exception:
        pass  # Telegram might not have been initialized

    # Stop scheduler
    try:
        from proactive.scheduler import get_scheduler
        get_scheduler().stop()
    except Exception:
        pass  # Scheduler might not have been initialized


# Create FastAPI app
app = FastAPI(
    title="EVA Personal Assistant",
    description="Personal AI companion with voice interaction",
    version="1.0.0",
    lifespan=lifespan
)

# Rate limiting middleware
from middleware.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

# CORS middleware (more restrictive for production)
# In production, replace ["*"] with your actual domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)
app.include_router(admin_router)
app.include_router(gmail_router)
app.include_router(calendar_router)
app.include_router(notification_router)
app.include_router(dashboard_router)


@app.get("/api")
async def api_info():
    """API info endpoint."""
    settings = get_settings()
    return {
        "name": "EVA Personal Assistant",
        "version": "1.0.0",
        "status": "running",
        "llm_provider": get_llm_provider(),
        "docs": "/docs",
        "dashboard": "/"
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
