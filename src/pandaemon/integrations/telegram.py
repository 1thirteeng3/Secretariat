"""Telegram bot integration for Pandaemon."""

import asyncio
import logging
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from pandaemon.config import get_settings

if TYPE_CHECKING:
    from pandaemon.kernel.router import KernelRouter

logger = logging.getLogger(__name__)


class TelegramBot:
    """
    Telegram bot integration for Pandaemon.
    
    Receives messages via Telegram and routes them through the kernel.
    """

    def __init__(self, kernel: "KernelRouter") -> None:
        self._kernel = kernel
        self._settings = get_settings()
        self._app: Application | None = None

    async def start(self) -> None:
        """Start the Telegram bot."""
        if not self._settings.telegram_bot_token:
            logger.error("Telegram bot token not configured")
            return

        # Build application
        self._app = (
            Application.builder()
            .token(self._settings.telegram_bot_token)
            .build()
        )

        # Add handlers
        self._app.add_handler(CommandHandler("start", self._cmd_start))
        self._app.add_handler(CommandHandler("help", self._cmd_help))
        self._app.add_handler(CommandHandler("status", self._cmd_status))
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )
        self._app.add_handler(
            MessageHandler(filters.VOICE, self._handle_voice)
        )

        # Initialize and start polling
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

        logger.info("Telegram bot started and polling")

    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
        logger.info("Telegram bot stopped")

    def _is_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to interact."""
        # If no restrictions, allow all
        if not self._settings.telegram_allowed_users:
            return True
        return user_id in self._settings.telegram_allowed_users

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not update.effective_user or not update.message:
            return

        if not self._is_allowed(update.effective_user.id):
            await update.message.reply_text("⛔ Access denied.")
            return

        await update.message.reply_text(
            "🤖 *Pandaemon* - Your cognitive daemon\n\n"
            "I can help you with:\n"
            "• Creating and managing Obsidian notes\n"
            "• Querying your knowledge base\n"
            "• Playing music (Spotify)\n"
            "• Web automation\n\n"
            "Just send me a message!",
            parse_mode="Markdown",
        )

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        if not update.message:
            return

        await update.message.reply_text(
            "📚 *Available Commands*\n\n"
            "/start - Start the bot\n"
            "/help - Show this help\n"
            "/status - System status\n\n"
            "*Natural Language*\n"
            "• \"Create a note about...\" - Create notes\n"
            "• \"What did I write about...\" - Query notes\n"
            "• \"Play Focus Noir\" - Spotify control\n"
            "• \"Search for...\" - Web search",
            parse_mode="Markdown",
        )

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        if not update.message:
            return

        result = await self._kernel.process("status", source="telegram")
        response = result.get("response", "System is running")
        await update.message.reply_text(f"✅ {response}")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages."""
        if not update.effective_user or not update.message or not update.message.text:
            return

        user_id = update.effective_user.id
        if not self._is_allowed(user_id):
            await update.message.reply_text("⛔ Access denied.")
            return

        text = update.message.text
        logger.info(f"Message from {update.effective_user.username}: {text[:50]}...")

        try:
            # Send typing action
            await update.message.chat.send_action("typing")

            # Route through kernel
            result = await self._kernel.process(text, source="telegram")

            # Send response
            response = result.get("response", "I processed your request.")
            status = result.get("status", "success")

            if status == "error":
                error = result.get("error", "Unknown error")
                await update.message.reply_text(f"❌ Error: {error}")
            else:
                # Split long messages
                if len(response) > 4000:
                    for i in range(0, len(response), 4000):
                        await update.message.reply_text(response[i:i+4000])
                else:
                    await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text(f"❌ Sorry, something went wrong.")

    async def _handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming voice messages."""
        if not update.message:
            return

        # TODO: Implement voice transcription
        await update.message.reply_text(
            "🎤 Voice messages will be supported soon!"
        )


async def create_telegram_bot(kernel: "KernelRouter") -> TelegramBot:
    """Factory function to create and start a Telegram bot."""
    bot = TelegramBot(kernel)
    await bot.start()
    return bot
