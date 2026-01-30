"""FastAPI application entrypoint for Pandaemon."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from pandaemon.config import get_settings
from pandaemon.kernel.router import KernelRouter


# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Global kernel router instance
kernel: KernelRouter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    global kernel
    
    logger.info("Starting Pandaemon daemon...")
    
    # Validate configuration
    if not settings.has_llm_provider():
        logger.warning("No LLM provider configured. Set DEEPSEEK_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY.")
    else:
        providers = settings.get_available_providers()
        logger.info(f"Available LLM providers: {', '.join(providers)}")
    
    if settings.obsidian_vault_path:
        logger.info(f"Obsidian vault: {settings.obsidian_vault_path}")
    else:
        logger.warning("OBSIDIAN_VAULT_PATH not set. Secretariat agent disabled.")
    
    # Initialize kernel router
    kernel = KernelRouter()
    await kernel.initialize()
    
    # Start Telegram bot if configured
    telegram_bot = None
    if settings.has_telegram():
        try:
            from pandaemon.integrations.telegram import create_telegram_bot
            telegram_bot = await create_telegram_bot(kernel)
            logger.info("Telegram bot started")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
    else:
        logger.info("Telegram not configured. Set TELEGRAM_BOT_TOKEN to enable.")
    
    logger.info("Pandaemon daemon ready.")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Pandaemon daemon...")
    
    if telegram_bot:
        await telegram_bot.stop()
        logger.info("Telegram bot stopped")
    
    if kernel:
        await kernel.shutdown()


app = FastAPI(
    title="Pandaemon",
    description="A cognitive daemon system - local-first AI assistant",
    version="1.0.0",
    lifespan=lifespan,
)


class WebhookMessage(BaseModel):
    """Incoming webhook message."""
    message: str
    source: str = "api"  # api, telegram, etc.
    user_id: str | None = None


class WebhookResponse(BaseModel):
    """Webhook response."""
    status: str
    response: str | None = None
    action_taken: str | None = None
    error: str | None = None


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "providers": ", ".join(settings.get_available_providers()) or "none",
    }


@app.post("/webhook", response_model=WebhookResponse)
async def webhook_handler(message: WebhookMessage) -> WebhookResponse:
    """
    Main webhook endpoint for receiving messages.
    
    This is the primary entry point for all user interactions.
    Messages are routed through the kernel to appropriate agents.
    """
    global kernel
    
    if kernel is None:
        return WebhookResponse(
            status="error",
            error="Kernel not initialized",
        )
    
    logger.info(f"Received message from {message.source}: {message.message[:50]}...")
    
    try:
        result = await kernel.process(message.message, source=message.source)
        return WebhookResponse(
            status="success",
            response=result.get("response"),
            action_taken=result.get("action"),
        )
    except Exception as e:
        logger.exception("Error processing message")
        return WebhookResponse(
            status="error",
            error=str(e),
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "error": "Internal server error"},
    )
