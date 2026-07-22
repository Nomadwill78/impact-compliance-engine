"""
Application Configuration
==========================
Loads settings from environment variables or a .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/compliance_db"
    DEBUG: bool = False


settings = Settings()
