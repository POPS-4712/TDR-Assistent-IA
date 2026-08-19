"""
Configuration settings for Automation Center Backend.
This module handles all configuration loading and validation.
"""

import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Automation Center"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    USER_DATA_DIR: Optional[str] = None
    PORTABLE_MODE: bool = False
    DOCKER_COMPOSE_PROJECT: str = "automation-center"
    LOCAL_SERVICE_CONTROL_ENABLED: bool = False

    # PostgreSQL
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "assistant"
    POSTGRES_USER: str = "assistant"
    POSTGRES_PASSWORD: Optional[str] = None

    # n8n
    N8N_API_URL: str = "http://n8n:5678"
    N8N_API_KEY: Optional[str] = None

    # Playwright
    PLAYWRIGHT_API_URL: str = "http://playwright:3000"

    # OAuth
    OAUTH_REDIRECT_BASE_URL: str = "http://localhost:8000"
    OAUTH_STATE_EXPIRY_SECONDS: int = 300

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # Security
    SECRET_KEY: Optional[str] = None

    # Database
    ENABLE_DATABASE_MIGRATIONS: bool = True

    # App directory (for automations discovery)
    APP_DIR: str = "/app"

    @property
    def POSTGRES_URL(self) -> str:
        """Return the PostgreSQL connection URL."""
        if not self.POSTGRES_PASSWORD:
            raise RuntimeError("POSTGRES_PASSWORD must be provided by the local runtime")
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=None,
        case_sensitive=True,
        extra="ignore",
    )

# Create settings instance
settings = Settings()
