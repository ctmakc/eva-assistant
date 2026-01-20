"""EVA Personal Assistant - Main FastAPI Application."""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from config import get_settings
from api.routes import router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
            except:
                pass  # Telegram might not be configured

        scheduler.add_notification_handler(notify_handler)
        scheduler.start()

        # Setup default schedule for default user
        scheduler.setup_user_schedule("default")

        logger.info("✓ Proactive scheduler started")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


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
        get_llm_service()
        logger.info("✓ LLM ready")

    except Exception as e:
        logger.error(f"Error during core initialization: {e}")
        raise

    # Setup integrations
    await setup_telegram()
    await setup_scheduler()

    logger.info("✨ EVA is ready!")

    yield

    # Shutdown
    logger.info("👋 EVA is shutting down...")

    # Stop Telegram
    try:
        from integrations.telegram import get_telegram_integration
        telegram = get_telegram_integration()
        await telegram.stop()
    except:
        pass

    # Stop scheduler
    try:
        from proactive.scheduler import get_scheduler
        get_scheduler().stop()
    except:
        pass


# Create FastAPI app
app = FastAPI(
    title="EVA Personal Assistant",
    description="Personal AI companion with voice interaction",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


@app.get("/")
async def root():
    settings = get_settings()
    return {
        "name": "EVA Personal Assistant",
        "version": "1.0.0",
        "status": "running",
        "llm_provider": settings.llm_provider,
        "docs": "/docs"
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
