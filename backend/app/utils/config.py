"""
config.py — Application configuration

Uses pydantic-settings to read environment variables from .env.
All configuration lives here; nothing else should import os.getenv directly.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ── Gemini AI ───────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"

    # ── Database ────────────────────────────────────────────────
    database_url: str = "sqlite:///./personal_ai_assistant.db"

    # ── Server ──────────────────────────────────────────────────
    secret_key: str = "dev-secret-key-change-in-production"

    # ── CORS ────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:3000"

    # ── Google OAuth ────────────────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/callback"

    # ── SMTP (Direct Email Sending) ────────────────────────────
    smtp_email: str = ""
    smtp_password: str = ""

    # ── Privacy Shield ──────────────────────────────────────────
    privacy_shield_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown env vars gracefully
    )

    @property
    def gemini_configured(self) -> bool:
        """True when a real Gemini API key has been provided."""
        return bool(self.gemini_api_key)

    @property
    def google_oauth_configured(self) -> bool:
        """True when Google OAuth credentials have been provided."""
        return bool(self.google_client_id and self.google_client_secret)


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Using lru_cache means the .env file is only parsed once per process.
    """
    return Settings()
