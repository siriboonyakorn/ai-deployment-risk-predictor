from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Central configuration.

    Every setting can be overridden via an environment variable of the same
    name or through the ``.env`` file located next to ``manage.py`` /
    ``alembic.ini``.
    """

    # ── Application ────────────────────────────────────────────────────
    APP_NAME: str = "AI Deployment Risk Predictor"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_PREFIX: str = "/api/v1"

    # ── Database ───────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./dev.db"

    # ── Redis ──────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── GitHub OAuth ───────────────────────────────────────────────────
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""

    # ── Google OAuth ───────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    # ── Clerk Authentication ───────────────────────────────────────────
    CLERK_SECRET_KEY: str = ""

    # ── GitHub API (PAT for fetching repo data) ────────────────────────
    GITHUB_TOKEN: str = ""

    # ── Security ───────────────────────────────────────────────────────
    SECRET_KEY: str = "change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"

    # ── Frontend / CORS ────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # ── Commit sync ───────────────────────────────────────────────────
    COMMIT_FETCH_LIMIT: int = 100  # max commits to pull per sync

    # ── Validators ─────────────────────────────────────────────────────

    @field_validator("LOG_LEVEL")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got '{v}'")
        return upper

    @field_validator("DATABASE_URL")
    @classmethod
    def _validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL must not be empty")
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def _warn_default_secret(cls, v: str) -> str:
        if v == "change-this-in-production":
            logging.getLogger("app.config").warning(
                "SECRET_KEY is still the default placeholder — change it for production!"
            )
        return v

    @model_validator(mode="after")
    def _derive_google_redirect_uri(self) -> "Settings":
        """Derive GOOGLE_REDIRECT_URI from FRONTEND_URL when left blank."""
        if not self.GOOGLE_REDIRECT_URI and self.FRONTEND_URL:
            object.__setattr__(
                self,
                "GOOGLE_REDIRECT_URI",
                f"{self.FRONTEND_URL.rstrip('/')}/api/v1/auth/google/callback",
            )
        return self

    # ── Helpers ────────────────────────────────────────────────────────

    @property
    def github_token_or_none(self) -> Optional[str]:
        """Return the configured PAT or ``None`` (avoids ``or None`` everywhere)."""
        return self.GITHUB_TOKEN or None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
