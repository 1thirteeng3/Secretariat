"""Pandaemon configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Providers
    anthropic_api_key: str | None = Field(default=None, description="Anthropic Claude API key")
    gemini_api_key: str | None = Field(default=None, description="Google Gemini API key")
    deepseek_api_key: str | None = Field(default=None, description="DeepSeek API key")
    
    # Default LLM settings
    default_llm_provider: Literal["anthropic", "gemini", "deepseek"] = Field(
        default="deepseek",
        description="Default LLM provider to use",
    )
    default_model_simple: str = Field(
        default="claude-3-haiku-20240307",
        description="Model for simple tasks",
    )
    default_model_reasoning: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Model for complex reasoning",
    )

    # Obsidian Vault
    obsidian_vault_path: Path | None = Field(
        default=Path(r"C:\Users\giovanni.barcelos\Desktop\obsidian"),
        description="Path to Obsidian vault (required for Secretariat)",
    )

    # Vector Database
    vector_db_path: Path = Field(
        default=Path("./data/vectors"),
        description="Path for ChromaDB storage",
    )

    # Telegram Integration
    telegram_bot_token: str | None = Field(
        default=None,
        description="Telegram bot token from @BotFather",
    )
    telegram_allowed_users: list[int] = Field(
        default_factory=list,
        description="List of allowed Telegram user IDs (empty = allow all)",
    )

    # Spotify Integration (SpotAPI - Cookie-based)
    spotify_email: str | None = Field(default=None, description="Spotify account email")
    spotify_password: str | None = Field(default=None, description="Spotify account password")
    spotify_cookies_path: Path = Field(
        default=Path("./data/spotify_cookies.json"),
        description="Path to Spotify cookies JSON file",
    )

    # Browser Automation
    browser_headless: bool = Field(default=True, description="Run browser in headless mode")
    browser_proxy: str | None = Field(default=None, description="Proxy URL for browser (optional)")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )

    @field_validator("obsidian_vault_path", mode="before")
    @classmethod
    def validate_vault_path(cls, v: str | Path | None) -> Path | None:
        """Convert string to Path and validate existence if provided."""
        if v is None or v == "":
            return None
        path = Path(v)
        return path

    def has_llm_provider(self) -> bool:
        """Check if at least one LLM provider is configured."""
        return bool(self.anthropic_api_key or self.gemini_api_key or self.deepseek_api_key)

    def get_available_providers(self) -> list[str]:
        """Get list of configured LLM providers."""
        providers = []
        if self.deepseek_api_key:
            providers.append("deepseek")
        if self.anthropic_api_key:
            providers.append("anthropic")
        if self.gemini_api_key:
            providers.append("gemini")
        return providers

    def has_spotify(self) -> bool:
        """Check if Spotify is configured (cookies or credentials)."""
        return bool(
            self.spotify_cookies_path.exists() or 
            (self.spotify_email and self.spotify_password)
        )

    def has_telegram(self) -> bool:
        """Check if Telegram is configured."""
        return bool(self.telegram_bot_token)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

