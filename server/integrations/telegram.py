"""Telegram integration for EVA assistant."""

import asyncio
import logging
from typing import Optional, List, Dict, Callable
from datetime import datetime

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from config import get_settings

logger = logging.getLogger("eva.telegram")


class TelegramIntegration:
    """Handles Telegram bot functionality."""

    def __init__(self):
        self.settings = get_settings()
        self.bot: Optional[Bot] = None
        self.app: Optional[Application] = None
        self.owner_chat_id: Optional[int] = None
        self._message_handlers: List[Callable] = []
        self._running = False

    async def initialize(self, token: str):
        """Initialize the Telegram bot."""
        self.app = Application.builder().token(token).build()
        self.bot = self.app.bot

        # Register handlers
        self.app.add_handler(CommandHandler("start", self._handle_start))
        self.app.add_handler(CommandHandler("status", self._handle_status))
        self.app.add_handler(CommandHandler("help", self._handle_help))
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self._handle_message
        ))

        logger.info("Telegram bot initialized")

    async def start(self):
        """Start polling for messages."""
        if self.app and not self._running:
            self._running = True
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            logger.info("Telegram bot started polling")

    async def stop(self):
        """Stop the bot."""
        if self.app and self._running:
            self._running = False
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            logger.info("Telegram bot stopped")

    def add_message_handler(self, handler: Callable):
        """Add external message handler (for EVA to process)."""
        self._message_handlers.append(handler)

    async def send_message(self, chat_id: int, text: str) -> bool:
        """Send a message to a chat."""
        try:
            if self.bot:
                await self.bot.send_message(chat_id=chat_id, text=text)
                return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
        return False

    async def send_to_owner(self, text: str) -> bool:
        """Send a message to the owner."""
        if self.owner_chat_id:
            return await self.send_message(self.owner_chat_id, text)
        logger.warning("Owner chat_id not set")
        return False

    async def send_voice(self, chat_id: int, audio_path: str) -> bool:
        """Send a voice message."""
        try:
            if self.bot:
                with open(audio_path, 'rb') as audio:
                    await self.bot.send_voice(chat_id=chat_id, voice=audio)
                return True
        except Exception as e:
            logger.error(f"Failed to send voice: {e}")
        return False

    async def get_unread_messages(self, chat_id: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """
        Get recent messages. Note: Telegram bots can't fetch history,
        so we store messages as they come in.
        """
        # This would need a message store - for now return empty
        # In practice, messages are handled via _handle_message
        return []

    # --- Internal handlers ---

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - register owner."""
        chat_id = update.effective_chat.id
        user = update.effective_user

        # First user to /start becomes owner
        if self.owner_chat_id is None:
            self.owner_chat_id = chat_id
            await update.message.reply_text(
                f"Привет, {user.first_name}! Я EVA, твой персональный ассистент. "
                f"Теперь я буду отправлять тебе уведомления сюда.\n\n"
                f"Команды:\n"
                f"/status - мой статус\n"
                f"/help - помощь"
            )
            logger.info(f"Owner registered: {chat_id} ({user.first_name})")
        else:
            await update.message.reply_text(
                f"Привет, {user.first_name}! Я EVA. Чем могу помочь?"
            )

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        status = (
            "🟢 EVA онлайн\n"
            f"⏰ Время: {datetime.now().strftime('%H:%M')}\n"
            f"👤 Владелец: {'установлен' if self.owner_chat_id else 'не установлен'}"
        )
        await update.message.reply_text(status)

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = (
            "🤖 EVA - Персональный ассистент\n\n"
            "Просто напиши мне сообщение, и я отвечу!\n\n"
            "Команды:\n"
            "/start - начать\n"
            "/status - статус\n"
            "/help - эта справка"
        )
        await update.message.reply_text(help_text)

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages."""
        chat_id = update.effective_chat.id
        text = update.message.text
        user = update.effective_user

        logger.info(f"Message from {user.first_name} ({chat_id}): {text}")

        # Call external handlers (EVA processing)
        for handler in self._message_handlers:
            try:
                response = await handler(text, str(chat_id))
                if response:
                    await update.message.reply_text(response)
                    return
            except Exception as e:
                logger.error(f"Handler error: {e}")

        # Default response if no handler processed it
        await update.message.reply_text(
            "Получила твоё сообщение! Обрабатываю..."
        )


# Singleton
_telegram_integration: Optional[TelegramIntegration] = None


def get_telegram_integration() -> TelegramIntegration:
    global _telegram_integration
    if _telegram_integration is None:
        _telegram_integration = TelegramIntegration()
    return _telegram_integration
