"""EVA Personal Assistant - Main FastAPI Application."""

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events."""
    # Startup
    logger.info("🚀 EVA is starting up...")

    settings = get_settings()

    # Pre-load services for faster first request
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

        logger.info("Initializing LLM...")
        get_llm_service()
        logger.info("✓ LLM ready")

    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        raise

    logger.info("✨ EVA is ready!")

    yield

    # Shutdown
    logger.info("👋 EVA is shutting down...")


# Create FastAPI app
app = FastAPI(
    title="EVA Personal Assistant",
    description="Personal AI companion with voice interaction",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for Android client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "name": "EVA Personal Assistant",
        "version": "1.0.0",
        "status": "running",
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
