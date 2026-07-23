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

    # --- Security / API auth ---
    # Comma-separated list of valid API keys accepted via the X-API-Key header.
    # If empty, auth is disabled (useful for local dev) but a startup warning is logged.
    API_KEYS: str = ""

    # Comma-separated list of allowed CORS origins. Defaults to no origins (deny-all)
    # in production; set explicitly via environment for the frontend's real origin(s).
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- Database migrations ---
    # When True (default), the app will NOT auto-create tables on startup via
    # Base.metadata.create_all. Use `alembic upgrade head` to manage schema instead.
    USE_ALEMBIC_MIGRATIONS: bool = False

    @property
    def api_keys_list(self) -> list[str]:
        return [k.strip() for k in self.API_KEYS.split(",") if k.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
